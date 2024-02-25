import json
from django.http import HttpResponse
from django.core import management
from django.core.management.commands import loaddata, dumpdata
from django.contrib.auth.decorators import user_passes_test
from datetime import datetime
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from rest_framework.views import APIView

from ciso_assistant.settings import VERSION

import sys
import io

from serdes.serializers import LoadBackupSerializer


def is_admin_check(user):
    return user.has_backup_permission


@user_passes_test(is_admin_check)
def dump_db_view(request):
    response = HttpResponse(content_type="application/json")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="ciso-assistant-db-{timestamp}.json"'

    response.write(f'[{{"meta": [{{"media_version": "{VERSION}"}}]}},\n')
    # Here we dump th data to stdout
    # NOTE: We will not be able to dump selected folders with this method.
    management.call_command(
        dumpdata.Command(),
        exclude=["contenttypes", "auth.permission", "sessions.session"],
        indent=4,
        stdout=response,
        natural_foreign=True,
    )
    response.write("]")
    return response


class LoadBackupView(APIView):
    parser_classes = (JSONParser,)
    serializer_class = LoadBackupSerializer

    def post(self, request, *args, **kwargs):
        if not is_admin_check(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.data:
            sys.stdin = io.StringIO(json.dumps(request.data[1]))
            request.session.flush()
            management.call_command("flush", interactive=False)
            # Here we load the data from stdin
            management.call_command(
                loaddata.Command(),
                "-",
                format="json",
                verbosity=0,
                exclude=["contenttypes", "auth.permission", "sessions.session"],
            )
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)
