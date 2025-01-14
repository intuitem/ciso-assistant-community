import gzip
import io
import json
import sys
import re
from datetime import datetime

from django.core import management
from django.core.management.commands import dumpdata, loaddata
from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ciso_assistant.settings import VERSION, SQLITE_FILE
from serdes.serializers import LoadBackupSerializer, ImportSerializer
from serdes.utils import import_export_serializer_class, topological_sort, build_dependency_graph
from django.apps import apps
from rest_framework.exceptions import ValidationError

import structlog

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
        buffer.write(f'[{{"meta": [{{"media_version": "{VERSION}"}}]}},\n')
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
        with open(SQLITE_FILE, "rb") as database_file:
            database_recover_data = database_file.read()

        sys.stdin = io.StringIO(decompressed_data)
        request.session.flush()
        management.call_command("flush", interactive=False)
        try:
            # Here we load the data from stdin
            management.call_command(
                loaddata.Command(),
                "-",
                format="json",
                verbosity=0,
                exclude=[
                    "contenttypes",
                    "auth.permission",
                    "sessions.session",
                    "iam.ssosettings",
                    "knox.authtoken",
                ],
            )
        except Exception as e:
            logger.error("Error while loading backup", exc_info=e)
            with open(SQLITE_FILE, "wb") as database_file:
                database_file.write(database_recover_data)

            if backup_version != current_version:
                logger.error("Backup version different than current version")
                return Response(
                    {"error": "LowerBackupVersion"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
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

        backup_version = None
        for metadata_part in metadata:
            backup_version = metadata_part.get("media_version")
            if backup_version is not None:
                break

        if backup_version is None:
            logger.error("Backup malformed: no version found")
            return Response(
                {"erroe": "errorBackupNoVersion"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if backup_version.lower() == "dev":
            backup_version = "v0.0.0"

        VERSION_REGEX = r"^v[0-9]+\.[0-9]+\.[0-9]+"
        match = re.match(VERSION_REGEX, backup_version)
        if match is None:
            logger.error(
                "Backup malformed: invalid version",
                backup_version=backup_version,
                current_version=VERSION,
            )
            return Response(
                {"error": "errorBackupInvalidVersion"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        backup_version = match.group()
        current_version = VERSION.split("-")[0]

        if current_version.lower() == "dev":
            current_version = "v0.0.0"

        backup_version = [int(num) for num in backup_version.lstrip("v").split(".")]
        current_version = [int(num) for num in current_version.lstrip("v").split(".")]
        # All versions are composed of 3 numbers (see git tag)
        for i in range(3):
            if backup_version[i] > current_version[i]:
                logger.error(
                    "Backup version greater than current version",
                    version=backup_version,
                )
                # Refuse to import the backup and ask to update the instance before importing the backup
                return Response(
                    {"error": "GreaterBackupVersion"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        decompressed_data = json.dumps(decompressed_data)
        return self.load_backup(
            request, decompressed_data, backup_version, current_version
        )


class ImportView(APIView):
    parser_classes = (FileUploadParser,)
    serializer_class = ImportSerializer
    
    def import_objects(self, parsed_data):
        """Import and validate objects using appropriate serializers."""
        # Store validation errors
        validation_errors = []
        
        # Retrieve all models referenced in the data
        model_names = {obj['model'] for obj in parsed_data.get('objects', [])}
        models = [apps.get_model(model_name) for model_name in model_names]
        
        # Build dependency graph and resolve creation order
        graph = build_dependency_graph(models)
        try:
            creation_order = topological_sort(graph)
        except ValueError as e:
            logger.error(
            "Cyclic dependency detected",
            error=str(e),
            )
            raise ValidationError({"error": f"Cyclic dependency detected: {str(e)}"})
        
        # Process objects
        for model in creation_order:
            model_name = f"{model._meta.app_label}.{model._meta.model_name}"
            for obj in parsed_data.get('objects', []):
                if obj['model'] != model_name:
                    continue

                fields = obj.get('fields', {})
                obj_id = obj.get('id')
            
                try:
                    # Get model class from model_name (e.g., 'core.folder' -> Folder model class)
                    model_class = apps.get_model(model_name)
                    
                    # Get appropriate serializer
                    SerializerClass = import_export_serializer_class(model_class)
                    
                    # Validate object data
                    serializer = SerializerClass(data=fields)
                    if not serializer.is_valid():
                        validation_errors.append({
                            'model': model_name,
                            'id': obj_id,
                            'errors': serializer.errors
                        })
                        continue
                        
                    try:
                        # Store validated data (or save, depending on your needs)
                        validated_data = serializer.validated_data
                        logger.info(
                            "Validated object",
                            model=model_name,
                            id=obj_id,
                            data=validated_data,
                        )
                    except Exception as e:
                        validation_errors.append({
                            'model': model_name,
                            'id': obj_id,
                            'errors': str(e)
                        })
                        
                except LookupError:
                    validation_errors.append({
                        'model': model_name,
                        'id': obj_id,
                        'errors': f"Unknown model type: {model_name}"
                    })
                except Exception as e:
                    validation_errors.append({
                        'model': model_name,
                        'id': obj_id,
                        'errors': f"Error processing object: {str(e)}"
                    })
        
        if validation_errors:
            raise ValidationError(validation_errors)
        
        return True

    def post(self, request, *args, **kwargs):
        backup_file = request.data["file"]
        data = backup_file.read()
        is_gzip = data.startswith(GZIP_MAGIC_NUMBER)
        decompressed_data = gzip.decompress(data) if is_gzip else data
        
        # Convert bytes to string if necessary
        if isinstance(decompressed_data, bytes):
            decompressed_data = decompressed_data.decode('utf-8')
        
        # Extract JSON content from multipart form-data
        if '{\n  "meta"' in decompressed_data:
            # Find the start and end of the JSON content
            json_start = decompressed_data.index('{\n  "meta"')
            json_end = decompressed_data.rindex('}') + 1
            json_content = decompressed_data[json_start:json_end]
            
            try:
                # Parse the JSON content
                parsed_data = json.loads(json_content)
                
                # Validate and import the data
                self.import_objects(parsed_data)
                return Response(
                    {"message": "Import successful"}, 
                    status=status.HTTP_200_OK
                )
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid JSON format"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            except ValidationError as e:
                return Response(
                    {"errors": e.detail}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"error": "Invalid file format"}, 
                status=status.HTTP_400_BAD_REQUEST
            )