import gzip
import io
import json
import sys
from datetime import datetime

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
            f'attachment; filename="ciso-assistant-db-{timestamp}.json"'
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

        # Back up current database state using dumpdata into an in-memory string.
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
        except (ValueError, TypeError) as e:
            logger.error(
                "Invalid schema version format",
                schema_version=schema_version,
                exc_info=e,
            )
            return Response(
                {"error": "InvalidSchemaVersion"}, status=status.HTTP_400_BAD_REQUEST
            )
        compare_schema_versions(schema_version_int, backup_version)

        decompressed_data = json.dumps(decompressed_data)
        return self.load_backup(
            request, decompressed_data, backup_version, current_version
        )
