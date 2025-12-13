import gzip
import io
import json
import sys
from datetime import datetime

from serdes.export_utils import AttachmentExporter, AttachmentImporter
import structlog
from django.core import management
from django.core.management.commands import dumpdata
from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ciso_assistant.settings import SCHEMA_VERSION, VERSION
from core.utils import compare_schema_versions
from serdes.serializers import LoadBackupSerializer

from auditlog.models import LogEntry
from django.db.models.signals import post_save
from core.custom_middleware import add_user_info_to_log_entry
from django.apps import apps

from auditlog.context import disable_auditlog

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


class ExportAttachmentsView(APIView):
    def get(self, request, *args, **kwargs):
        if not request.user.has_backup_permission:
            logger.warning(
                "Unauthorized attachment export attempt",
                user=request.user.username,
            )
            return Response(status=status.HTTP_403_FORBIDDEN)

        logger.info(
            "Starting attachment export",
            user=request.user.username,
        )

        try:
            exporter = AttachmentExporter()
            zip_buffer, count = exporter.create_attachments_zip()

            if count == 0:
                logger.info("No attachments found to export")
                return Response(
                    {"message": "No attachments found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Create response with ZIP file
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"ciso-assistant-attachments-{timestamp}.zip"

            response = HttpResponse(
                zip_buffer.getvalue(), content_type="application/zip"
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

            logger.info(
                "Attachment export completed successfully",
                attachments_count=count,
                filename=filename,
                zip_size=len(zip_buffer.getvalue()),
            )

            return response

        except Exception as e:
            logger.error(
                "Attachment export failed",
                user=request.user.username,
                error=str(e),
                exc_info=True,
            )
            return Response(
                {"error": "AttachmentExportFailed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LoadAttachmentsView(APIView):
    parser_classes = (FileUploadParser,)

    def post(self, request, *args, **kwargs):
        if not request.user.has_backup_permission:
            logger.warning(
                "Unauthorized attachment import attempt",
                user=request.user.username,
            )
            return Response(status=status.HTTP_403_FORBIDDEN)

        logger.info(
            "Starting attachment import",
            user=request.user.username,
        )

        # Get the uploaded file
        if "file" not in request.data:
            return Response(
                {"error": "NoFileProvided"}, status=status.HTTP_400_BAD_REQUEST
            )

        zip_file = request.data["file"]

        # Validate file type
        if not zip_file.name.endswith(".zip"):
            return Response(
                {"error": "InvalidFileType"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            importer = AttachmentImporter()
            stats = importer.extract_attachments_from_zip(zip_file, dry_run=False)

            logger.info(
                "Attachment import completed",
                processed=stats["processed"],
                restored=stats["restored"],
                errors_count=len(stats["errors"]),
            )

            if stats["errors"]:
                return Response(
                    {
                        "status": "partial_success",
                        "processed": stats["processed"],
                        "restored": stats["restored"],
                        "errors": stats["errors"],
                    },
                    status=status.HTTP_207_MULTI_STATUS,
                )

            return Response(
                {
                    "status": "success",
                    "processed": stats["processed"],
                    "restored": stats["restored"],
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                "Attachment import failed",
                user=request.user.username,
                error=str(e),
                exc_info=True,
            )
            return Response(
                {"error": "AttachmentImportFailed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FullRestoreView(APIView):
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
        attachments_file = request.FILES.get("attachments")

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

        # Step 2: Restore attachments if provided
        attachment_stats = None
        if attachments_file:
            logger.info("Step 2/2: Restoring attachments")

            if not attachments_file.name.endswith(".zip"):
                return Response(
                    {"error": "InvalidAttachmentFileType"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                importer = AttachmentImporter()
                attachment_stats = importer.extract_attachments_from_zip(
                    attachments_file, dry_run=False
                )

                logger.info(
                    "Attachments restored successfully",
                    processed=attachment_stats["processed"],
                    restored=attachment_stats["restored"],
                    errors_count=len(attachment_stats["errors"]),
                )

            except Exception as e:
                logger.error("Attachment restore failed", exc_info=e)
                return Response(
                    {
                        "error": "AttachmentRestoreFailed",
                        "message": "Database restored but attachments failed",
                        "details": str(e),
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            logger.info("No attachments file provided, skipping attachment restore")

        # Build response
        response_data = {
            "status": "success",
            "database_restored": True,
        }

        if attachment_stats:
            response_data["attachments_restored"] = attachment_stats["restored"]
            response_data["attachments_processed"] = attachment_stats["processed"]
            if attachment_stats["errors"]:
                response_data["attachment_errors"] = attachment_stats["errors"]
                response_data["status"] = "partial_success"

        logger.info(
            "Full restore completed successfully",
            user=request.user.username,
            has_attachments=bool(attachments_file),
        )

        return Response(response_data, status=status.HTTP_200_OK)
