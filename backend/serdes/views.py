import gzip
import io
import json
import struct
import sys
from datetime import datetime

import structlog
from django.core import management
from django.core.management.commands import dumpdata
from django.core.files.storage import default_storage
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import LimitOffsetPagination
from ciso_assistant.settings import SCHEMA_VERSION, VERSION
from core.models import EvidenceRevision
from core.utils import compare_schema_versions
from iam.models import User
from serdes.serializers import LoadBackupSerializer

from auditlog.models import LogEntry
from django.db.models.signals import post_save
from core.custom_middleware import add_user_info_to_log_entry
from django.apps import apps
from django.conf import settings
from auditlog.context import disable_auditlog
from django.core.files.base import ContentFile
import hashlib

logger = structlog.get_logger(__name__)

GZIP_MAGIC_NUMBER = b"\x1f\x8b"


class ExportBackupView(APIView):
    def get(self, request, *args, **kwargs):
        if not request.user.has_backup_permission:
            return Response(status=status.HTTP_403_FORBIDDEN)
        response = HttpResponse(content_type="application/json")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        response["Content-Disposition"] = (
            f'attachment; filename="ciso-assistant-db-{VERSION}-{timestamp}.json"'
        )

        buffer = io.StringIO()
        buffer.write(
            f'[{{"meta": [{{"media_version": "{VERSION}", "schema_version": "{SCHEMA_VERSION}"}}]}},\n'
        )
        # Here we dump th data to stdout
        # NOTE: We will not be able to dump selected folders with this method.
        management.call_command(
            dumpdata.Command(),
            exclude=[
                "contenttypes",
                "auth.permission",
                "sessions.session",
                "iam.personalaccesstoken",
                "iam.ssosettings",
                "knox.authtoken",
                "auditlog.logentry",
            ],
            indent=4,
            stdout=buffer,
            natural_foreign=True,
        )
        buffer.write("]")
        buffer.seek(0)
        buffer_data = gzip.compress(buffer.getvalue().encode())
        response.write(buffer_data)
        return response


class LoadBackupView(APIView):
    parser_classes = (FileUploadParser,)
    serializer_class = LoadBackupSerializer

    def load_backup(self, request, decompressed_data, backup_version, current_version):
        # Temporarily disconnect the problematic signal
        post_save.disconnect(add_user_info_to_log_entry, sender=LogEntry)

        backup_buffer = io.StringIO()
        try:
            management.call_command(
                "dumpdata",
                stdout=backup_buffer,
                format="json",
                verbosity=0,
                exclude=[
                    "contenttypes",
                    "sessions.session",
                    "iam.ssosettings",
                    "knox.authtoken",
                ],
            )
        except Exception as e:
            logger.error("Error dumping current DB state", exc_info=e)
            return Response(
                {"error": "BackupDumpFailed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        current_backup = backup_buffer.getvalue()

        # Prepare to load the uploaded backup.
        # Reset sys.stdin so loaddata reads from our provided backup data.
        sys.stdin = io.StringIO(decompressed_data)
        request.session.flush()

        try:
            last_model = None

            def fixture_callback(sender, **kwargs):
                nonlocal last_model
                if "instance" in kwargs:
                    instance = kwargs["instance"]
                    last_model = (
                        f"{instance._meta.app_label}.{instance._meta.model_name}"
                    )
                    logger.debug(f"Loaded: {last_model} with pk={instance.pk}")

            # Connect to the post_save signal
            post_save.connect(fixture_callback)
            with disable_auditlog():
                management.call_command("flush", interactive=False)
                management.call_command(
                    "loaddata",
                    "-",
                    format="json",
                    verbosity=2,
                    exclude=[
                        "contenttypes",
                        "auth.permission",
                        "sessions.session",
                        "iam.personalaccesstoken",
                        "iam.ssosettings",
                        "knox.authtoken",
                        "auditlog.logentry",
                    ],
                )

        except Exception as e:
            logger.error("Error while loading backup", exc_info=e)
            logger.error(
                f"Error while loading backup. Last successful model: {last_model}",
                exc_info=e,
            )
            # On failure, restore the original data.
            try:
                sys.stdin = io.StringIO(current_backup)
                management.call_command("flush", interactive=False)
                management.call_command(
                    "loaddata",
                    "-",
                    format="json",
                    verbosity=0,
                )
            except Exception as restore_error:
                logger.error("Error restoring original backup", exc_info=restore_error)
                return Response(
                    {"error": "RestoreFailed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            if backup_version != current_version:
                logger.error("Backup version different than current version")
                return Response(
                    {"error": "LowerBackupVersion"}, status=status.HTTP_400_BAD_REQUEST
                )
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            post_save.disconnect(fixture_callback)
            post_save.connect(add_user_info_to_log_entry, sender=LogEntry)

        # Enforce LICENSE_SEATS after successful restore
        license_seats = getattr(settings, "LICENSE_SEATS", None)
        if license_seats is not None:
            editor_count = len(User.get_editors())
            if editor_count > license_seats:
                logger.error(
                    "Backup exceeds license seats, rolling back",
                    editor_count=editor_count,
                    license_seats=license_seats,
                )
                try:
                    sys.stdin = io.StringIO(current_backup)
                    management.call_command("flush", interactive=False)
                    management.call_command(
                        "loaddata",
                        "-",
                        format="json",
                        verbosity=0,
                    )
                except Exception as restore_error:
                    logger.error(
                        "Error restoring original backup", exc_info=restore_error
                    )
                    return Response(
                        {"error": "RestoreFailed"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                return Response(
                    {"error": "errorLicenseSeatsExceeded"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response({}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if not request.user.has_backup_permission:
            logger.error("Unauthorized user tried to load a backup", user=request.user)
            return Response({}, status=status.HTTP_403_FORBIDDEN)
        if not request.data:
            logger.error("Request has no data")

            return Response(
                {"error": "backupLoadNoData"}, status=status.HTTP_400_BAD_REQUEST
            )
        backup_file = request.data["file"]
        data = backup_file.read()
        is_gzip = data.startswith(GZIP_MAGIC_NUMBER)
        full_decompressed_data = gzip.decompress(data) if is_gzip else data
        # Performances could be improved (by avoiding the json.loads + json.dumps calls with a direct raw manipulation on the JSON body)
        # But performances of the backup loading is not that much important.

        full_decompressed_data = json.loads(full_decompressed_data)
        metadata, decompressed_data = full_decompressed_data
        metadata = metadata["meta"]

        current_version = VERSION.split("-")[0]
        backup_version = None
        schema_version = 0

        for metadata_part in metadata:
            backup_version = metadata_part.get("media_version")
            schema_version = metadata_part.get("schema_version")
            if backup_version is not None or schema_version is not None:
                break

        try:
            schema_version_int = int(schema_version)
            compare_schema_versions(schema_version_int, backup_version)
            if backup_version != VERSION:
                raise ValueError(
                    "The version of the current instance and the one that generated the backup are not the same."
                )
        except (ValueError, TypeError) as e:
            logger.error(
                "Invalid schema version format",
                schema_version=schema_version,
                exc_info=e,
            )
            return Response(
                {"error": "InvalidSchemaVersion"}, status=status.HTTP_400_BAD_REQUEST
            )

        is_enterprise = apps.is_installed("enterprise_core")
        if not is_enterprise:
            for obj in decompressed_data:
                if obj["model"] != "iam.role":
                    continue
                permissions = obj["fields"]["permissions"]
                enterprise_perms_indices = [
                    i
                    for i, perm in enumerate(permissions)
                    if perm[1] == "enterprise_core"
                ]
                for perm_index in reversed(enterprise_perms_indices):
                    permissions.pop(perm_index)

            decompressed_data = [
                obj
                for obj in decompressed_data
                if obj["model"].split(".", 1)[0] != "enterprise_core"
            ]

        decompressed_data = json.dumps(decompressed_data)
        return self.load_backup(
            request, decompressed_data, backup_version, current_version
        )


class FullRestoreView(APIView):
    """
    POST endpoint for atomic database + attachments restore.
    Accepts multipart form data with:
    - backup: database backup file (required)
    - attachments: streaming binary data in custom format (optional)

    This ensures both operations happen in a single authenticated request,
    avoiding token invalidation issues.
    """

    def post(self, request, *args, **kwargs):
        if not request.user.has_backup_permission:
            logger.error("Unauthorized full restore attempt", user=request.user)
            return Response(status=status.HTTP_403_FORBIDDEN)

        logger.info(
            "Starting full restore (database + attachments)",
            user=request.user.username,
        )

        # Get uploaded files from multipart form data
        backup_file = request.FILES.get("backup")
        attachments_data = request.FILES.get("attachments")

        if not backup_file:
            return Response(
                {"error": "NoBackupFileProvided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Step 1: Restore database backup
        logger.info("Step 1/2: Restoring database backup")

        try:
            data = backup_file.read()
            is_gzip = data.startswith(GZIP_MAGIC_NUMBER)
            full_decompressed_data = gzip.decompress(data) if is_gzip else data

            full_decompressed_data = json.loads(full_decompressed_data)
            metadata, decompressed_data = full_decompressed_data
            metadata = metadata["meta"]

            current_version = VERSION.split("-")[0]
            backup_version = None
            schema_version = 0

            for metadata_part in metadata:
                backup_version = metadata_part.get("media_version")
                schema_version = metadata_part.get("schema_version")
                if backup_version is not None or schema_version is not None:
                    break

            try:
                schema_version_int = int(schema_version)
                compare_schema_versions(schema_version_int, backup_version)
                if backup_version != VERSION:
                    raise ValueError(
                        "The version of the current instance and the one that generated the backup are not the same."
                    )
            except (ValueError, TypeError) as e:
                logger.error(
                    "Invalid schema version format",
                    schema_version=schema_version,
                    exc_info=e,
                )
                return Response(
                    {"error": "InvalidSchemaVersion"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            is_enterprise = apps.is_installed("enterprise_core")
            if not is_enterprise:
                for obj in decompressed_data:
                    if obj["model"] != "iam.role":
                        continue
                    permissions = obj["fields"]["permissions"]
                    enterprise_perms_indices = [
                        i
                        for i, perm in enumerate(permissions)
                        if perm[1] == "enterprise_core"
                    ]
                    for perm_index in reversed(enterprise_perms_indices):
                        permissions.pop(perm_index)

                decompressed_data = [
                    obj
                    for obj in decompressed_data
                    if obj["model"].split(".", 1)[0] != "enterprise_core"
                ]

            decompressed_data = json.dumps(decompressed_data)

            # Reuse existing load_backup logic
            load_backup_view = LoadBackupView()
            db_response = load_backup_view.load_backup(
                request, decompressed_data, backup_version, current_version
            )

            if db_response.status_code != 200:
                return db_response

            logger.info("Database backup restored successfully")

        except Exception as e:
            logger.error("Database restore failed", exc_info=e)
            return Response(
                {"error": "DatabaseRestoreFailed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Step 2: Restore attachments if provided (using streaming format)
        attachment_stats = None
        if attachments_data:
            logger.info("Step 2/2: Restoring attachments from streaming data")

            try:
                # Read the uploaded file data (it's already in memory from multipart)
                body = attachments_data.read()

                stats = {
                    "processed": 0,
                    "restored": 0,
                    "skipped": 0,
                    "errors": [],
                }

                offset = 0
                while offset < len(body):
                    try:
                        # Read 4-byte length prefix
                        if offset + 4 > len(body):
                            break

                        total_size = struct.unpack(">I", body[offset : offset + 4])[0]
                        offset += 4

                        if offset + total_size > len(body):
                            stats["errors"].append(
                                {
                                    "error": "Incomplete data block",
                                    "offset": offset,
                                }
                            )
                            break

                        # Extract the data block
                        block_data = body[offset : offset + total_size]
                        offset += total_size

                        # Parse JSON header
                        header = None
                        header_end = 0

                        for i in range(1, min(1024, len(block_data))):
                            try:
                                header = json.loads(block_data[:i].decode("utf-8"))
                                header_end = i
                                break
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                continue

                        if not header:
                            stats["errors"].append(
                                {
                                    "error": "Invalid JSON header in block",
                                }
                            )
                            stats["processed"] += 1
                            continue

                        file_bytes = block_data[header_end:]
                        stats["processed"] += 1

                        # Validate header
                        revision_id = header.get("id")
                        expected_hash = header.get("hash")
                        filename = header.get("filename")

                        if not revision_id or not filename:
                            stats["errors"].append(
                                {
                                    "revision_id": revision_id,
                                    "filename": filename,
                                    "error": "Missing required fields in header",
                                }
                            )
                            continue

                        # Verify file hash
                        actual_hash = hashlib.sha256(file_bytes).hexdigest()

                        if expected_hash and actual_hash != expected_hash:
                            stats["errors"].append(
                                {
                                    "revision_id": revision_id,
                                    "filename": filename,
                                    "error": "Hash mismatch",
                                }
                            )
                            continue

                        # Find the revision
                        try:
                            revision = EvidenceRevision.objects.get(id=revision_id)
                        except EvidenceRevision.DoesNotExist:
                            stats["errors"].append(
                                {
                                    "revision_id": revision_id,
                                    "filename": filename,
                                    "error": "Revision not found",
                                }
                            )
                            continue

                        # Check if attachment already exists with same hash
                        if (
                            revision.attachment
                            and revision.attachment_hash
                            and revision.attachment_hash == actual_hash
                            and default_storage.exists(revision.attachment.name)
                        ):
                            stats["skipped"] += 1
                            logger.debug(
                                "Skipping attachment with matching hash",
                                revision_id=revision_id,
                                hash=actual_hash,
                            )
                            continue

                        # Save the attachment
                        evidence_id = header.get("evidence_id", revision.evidence_id)
                        version = header.get("version", revision.version)

                        storage_path = (
                            f"evidence-revisions/{evidence_id}/v{version}/{filename}"
                        )

                        # Delete old attachment if exists
                        if revision.attachment:
                            try:
                                default_storage.delete(revision.attachment.name)
                            except Exception as e:
                                logger.warning(
                                    "Failed to delete old attachment",
                                    revision_id=revision_id,
                                    error=str(e),
                                )

                        # Save new attachment
                        saved_path = default_storage.save(
                            storage_path, ContentFile(file_bytes)
                        )

                        revision.attachment = saved_path
                        revision.attachment_hash = actual_hash
                        revision.save(update_fields=["attachment", "attachment_hash"])

                        stats["restored"] += 1

                    except Exception as e:
                        logger.error(
                            "Error processing block",
                            offset=offset,
                            error=str(e),
                            exc_info=True,
                        )
                        stats["errors"].append(
                            {
                                "error": f"Error processing block",
                                "offset": offset,
                            }
                        )

                attachment_stats = stats
                logger.info(
                    "Attachments restored successfully",
                    processed=attachment_stats["processed"],
                    restored=attachment_stats["restored"],
                    skipped=attachment_stats["skipped"],
                    errors_count=len(attachment_stats["errors"]),
                )

            except Exception as e:
                logger.error("Attachment restore failed", exc_info=True)
                return Response(
                    {
                        "error": "AttachmentRestoreFailed",
                        "message": "Database restored but attachments failed. Check server logs for details.",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            logger.info("No attachments data provided, skipping attachment restore")

        # Build response
        response_data = {
            "status": "success",
            "database_restored": True,
        }

        if attachment_stats:
            response_data["attachments_restored"] = attachment_stats["restored"]
            response_data["attachments_processed"] = attachment_stats["processed"]
            response_data["attachments_skipped"] = attachment_stats["skipped"]
            if attachment_stats["errors"]:
                response_data["attachment_errors_count"] = len(
                    attachment_stats["errors"]
                )
                response_data["status"] = "partial_success"

        logger.info(
            "Full restore completed successfully",
            user=request.user.username,
            has_attachments=bool(attachments_data),
        )

        return Response(response_data, status=status.HTTP_200_OK)


class AttachmentMetadataView(APIView):
    """
    GET endpoint that returns paginated metadata for all attachments.
    Supports filtering by folder, created_after, and created_before.
    """

    def get(self, request, *args, **kwargs):
        if not request.user.has_backup_permission:
            logger.warning(
                "Unauthorized attachment metadata request",
                user=request.user.username,
            )
            return Response(status=status.HTTP_403_FORBIDDEN)

        logger.info(
            "Fetching attachment metadata",
            user=request.user.username,
        )

        # Build queryset with filters
        queryset = (
            EvidenceRevision.objects.filter(attachment__isnull=False)
            .exclude(attachment="")
            .select_related("evidence", "folder")
        )

        folder_id = request.query_params.get("folder")
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)

        created_after = request.query_params.get("created_after")
        if created_after:
            queryset = queryset.filter(created_at__gte=created_after)

        created_before = request.query_params.get("created_before")
        if created_before:
            queryset = queryset.filter(created_at__lte=created_before)

        queryset = queryset.order_by("created_at", "id")
        paginator = LimitOffsetPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        results = []
        for revision in paginated_queryset:
            try:
                file_size = None
                if revision.attachment and default_storage.exists(
                    revision.attachment.name
                ):
                    file_size = default_storage.size(revision.attachment.name)

                results.append(
                    {
                        "id": str(revision.id),
                        "evidence_id": str(revision.evidence_id),
                        "version": revision.version,
                        "filename": revision.filename()
                        if revision.attachment
                        else None,
                        "size": file_size,
                        "attachment_hash": revision.attachment_hash,
                        "created_at": revision.created_at.isoformat()
                        if revision.created_at
                        else None,
                    }
                )
            except Exception as e:
                logger.warning(
                    "Error building metadata for revision",
                    revision_id=revision.id,
                    error=str(e),
                )
                continue

        response_data = {
            "count": queryset.count(),
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": results,
        }

        logger.info(
            "Attachment metadata fetched successfully",
            count=len(results),
            total=response_data["count"],
        )

        return Response(response_data, status=status.HTTP_200_OK)


class BatchDownloadAttachmentsView(APIView):
    """
    POST endpoint that streams multiple attachments in a custom binary format.
    Request body: {"revision_ids": ["id1", "id2", ...]}
    Response format: for each file: [4-byte length][JSON header][file bytes]
    """

    def post(self, request, *args, **kwargs):
        if not request.user.has_backup_permission:
            logger.warning(
                "Unauthorized batch download attempt",
                user=request.user.username,
            )
            return Response(status=status.HTTP_403_FORBIDDEN)

        revision_ids = request.data.get("revision_ids", [])

        if not revision_ids:
            return Response(
                {"error": "NoRevisionIDsProvided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check batch size limit
        max_batch_size = getattr(settings, "BACKUP_BATCH_SIZE", 200)

        if len(revision_ids) > max_batch_size:
            return Response(
                {
                    "error": "BatchTooLarge",
                    "message": f"Maximum batch size is {max_batch_size} files",
                    "requested": len(revision_ids),
                    "max": max_batch_size,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "Starting batch download",
            user=request.user.username,
            revision_count=len(revision_ids),
        )

        def stream_attachments():
            """Generator that yields attachment data in custom binary format."""
            processed = 0
            errors = 0

            for revision_id in revision_ids:
                try:
                    revision = EvidenceRevision.objects.select_related("evidence").get(
                        id=revision_id
                    )

                    if not revision.attachment or not default_storage.exists(
                        revision.attachment.name
                    ):
                        errors += 1
                        logger.warning(
                            "Attachment not found for revision",
                            revision_id=revision_id,
                        )
                        continue

                    header = {
                        "id": str(revision.id),
                        "evidence_id": str(revision.evidence_id),
                        "version": revision.version,
                        "filename": revision.filename(),
                        "hash": revision.attachment_hash,
                        "size": default_storage.size(revision.attachment.name),
                    }
                    header_bytes = json.dumps(header).encode("utf-8")

                    # Read file in chunks
                    file_buffer = io.BytesIO()
                    with default_storage.open(revision.attachment.name, "rb") as f:
                        for chunk in iter(lambda: f.read(10240 * 1024), b""):
                            file_buffer.write(chunk)

                    file_bytes = file_buffer.getvalue()

                    # Calculate total size: header_length + header + file
                    total_size = len(header_bytes) + len(file_bytes)

                    # Yield: [4-byte total size][header bytes][file bytes]
                    yield struct.pack(">I", total_size)
                    yield header_bytes
                    yield file_bytes

                    processed += 1

                except EvidenceRevision.DoesNotExist:
                    errors += 1
                    logger.warning(
                        "Revision not found",
                        revision_id=revision_id,
                    )
                except Exception as e:
                    errors += 1
                    logger.error(
                        "Error streaming attachment",
                        revision_id=revision_id,
                        error=str(e),
                        exc_info=True,
                    )

            logger.info(
                "Batch download completed",
                processed=processed,
                errors=errors,
            )

        response = StreamingHttpResponse(
            stream_attachments(),
            content_type="application/octet-stream",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="attachments-batch-{datetime.now().strftime("%Y%m%d-%H%M%S")}.dat"'
        )

        return response


class BatchUploadAttachmentsView(APIView):
    """
    POST endpoint that accepts multiple attachments in custom binary format.
    Request body: same format as batch download (4-byte length, JSON header, file bytes)
    Response: {"processed": N, "restored": N, "skipped": N, "errors": [...]}
    """

    def post(self, request, *args, **kwargs):
        if not request.user.has_backup_permission:
            logger.warning(
                "Unauthorized batch upload attempt",
                user=request.user.username,
            )
            return Response(status=status.HTTP_403_FORBIDDEN)

        logger.info(
            "Starting batch upload",
            user=request.user.username,
        )

        stats = {
            "processed": 0,
            "restored": 0,
            "skipped": 0,
            "errors": [],
        }

        try:
            # Read the entire body
            body = request.body
            offset = 0

            while offset < len(body):
                try:
                    # Read 4-byte length prefix
                    if offset + 4 > len(body):
                        break

                    total_size = struct.unpack(">I", body[offset : offset + 4])[0]
                    offset += 4

                    if offset + total_size > len(body):
                        stats["errors"].append(
                            {
                                "error": "Incomplete data block",
                                "offset": offset,
                            }
                        )
                        break

                    # Extract the data block
                    block_data = body[offset : offset + total_size]
                    offset += total_size

                    # Find the boundary between JSON header and file bytes
                    # The header is UTF-8 JSON, we need to parse it first
                    # Try to decode as much JSON as possible
                    header = None
                    header_end = 0

                    for i in range(
                        1, min(1024, len(block_data))
                    ):  # Header should be < 1KB
                        try:
                            header = json.loads(block_data[:i].decode("utf-8"))
                            header_end = i
                            break
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue

                    if not header:
                        stats["errors"].append(
                            {
                                "error": "Invalid JSON header in block",
                            }
                        )
                        stats["processed"] += 1
                        continue

                    file_bytes = block_data[header_end:]
                    stats["processed"] += 1

                    # Validate header
                    revision_id = header.get("id")
                    expected_hash = header.get("hash")
                    filename = header.get("filename")

                    if not revision_id or not filename:
                        stats["errors"].append(
                            {
                                "revision_id": revision_id,
                                "filename": filename,
                                "error": "Missing required fields in header",
                            }
                        )
                        continue

                    # Verify file hash

                    actual_hash = hashlib.sha256(file_bytes).hexdigest()

                    if expected_hash and actual_hash != expected_hash:
                        stats["errors"].append(
                            {
                                "revision_id": revision_id,
                                "filename": filename,
                                "error": "Hash mismatch",
                            }
                        )
                        continue

                    # Find the revision
                    try:
                        revision = EvidenceRevision.objects.get(id=revision_id)
                    except EvidenceRevision.DoesNotExist:
                        stats["errors"].append(
                            {
                                "revision_id": revision_id,
                                "filename": filename,
                                "error": "Revision not found",
                            }
                        )
                        continue

                    # Check if attachment already exists with same hash & verify the file actually exists in storage
                    if (
                        revision.attachment
                        and revision.attachment_hash
                        and revision.attachment_hash == actual_hash
                        and default_storage.exists(revision.attachment.name)
                    ):
                        stats["skipped"] += 1
                        logger.debug(
                            "Skipping attachment with matching hash",
                            revision_id=revision_id,
                            hash=actual_hash,
                        )
                        continue

                    # Save the attachment
                    evidence_id = header.get("evidence_id", revision.evidence_id)
                    version = header.get("version", revision.version)

                    storage_path = (
                        f"evidence-revisions/{evidence_id}/v{version}/{filename}"
                    )

                    # Delete old attachment if exists
                    if revision.attachment:
                        try:
                            default_storage.delete(revision.attachment.name)
                        except Exception as e:
                            logger.warning(
                                "Failed to delete old attachment",
                                revision_id=revision_id,
                                error=str(e),
                            )

                    # Save new attachment

                    saved_path = default_storage.save(
                        storage_path, ContentFile(file_bytes)
                    )

                    revision.attachment = saved_path
                    revision.attachment_hash = actual_hash
                    revision.save(update_fields=["attachment", "attachment_hash"])

                    stats["restored"] += 1

                except Exception as e:
                    logger.error(
                        "Error processing block",
                        offset=offset,
                        error=str(e),
                        exc_info=True,
                    )
                    stats["errors"].append(
                        {
                            "error": "Error processing block",
                            "offset": offset,
                        }
                    )

        except Exception as e:
            logger.error(
                "Batch upload failed",
                user=request.user.username,
                error=str(e),
                exc_info=True,
            )
            return Response(
                {
                    "error": "BatchUploadFailed",
                    "message": "An internal error has occurred.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Batch upload completed",
            processed=stats["processed"],
            restored=stats["restored"],
            skipped=stats["skipped"],
            errors_count=len(stats["errors"]),
        )

        response_status = status.HTTP_200_OK
        if stats["errors"] and stats["restored"] == 0:
            response_status = status.HTTP_400_BAD_REQUEST
        elif stats["errors"]:
            response_status = status.HTTP_207_MULTI_STATUS

        return Response(stats, status=response_status)
