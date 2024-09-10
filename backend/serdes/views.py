import io
import json
import sys
from datetime import datetime

from django.core import management
from django.core.management.commands import dumpdata, loaddata
from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView
import gzip, io

from ciso_assistant.settings import VERSION
from serdes.serializers import LoadBackupSerializer


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

    def post(self, request, *args, **kwargs):
        if not request.user.has_backup_permission:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.data:
            backup_file = request.data["file"]
            is_json = backup_file.name.split(".")[-1].lower() == "json"
            data = backup_file.read()
            decompressed_data = data if is_json else gzip.decompress(data)
            # Performances could be improved (by avoiding the json.loads + json.dumps calls with a direct raw manipulation on the JSON body)
            # But performances of the backup loading is not that much important.
            decompressed_data = json.loads(decompressed_data)[1]
            decompressed_data = json.dumps(decompressed_data)

            sys.stdin = io.StringIO(decompressed_data)
            request.session.flush()
            management.call_command("flush", interactive=False)
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
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)
