import mimetypes
import magic

import structlog
from core.views import BaseModelViewSet
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import (
    action,
    permission_classes,
)
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from .models import ClientSettings
from .serializers import ClientSettingsReadSerializer

logger = structlog.get_logger(__name__)


class ClientSettingsViewSet(BaseModelViewSet):
    model = ClientSettings

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "detail": "Client settings object cannot be created outside of AppConfig."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def delete(self, request, *args, **kwargs):
        return Response(
            {"detail": "Client settings object cannot be deleted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _get_file_response(self, request, pk, file_field):
        client = ClientSettings.objects.get(pk=pk)
        file = getattr(client, file_field)

        if not file:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method != "GET":
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        filename = client.filename(
            field=getattr(ClientSettings.FileField, file_field.upper())
        )
        content_type = mimetypes.guess_type(filename)[0]

        return HttpResponse(
            file,
            content_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], detail=False, permission_classes=[AllowAny])
    def info(self, request):
        try:
            client = ClientSettings.objects.get()
            return Response(
                ClientSettingsReadSerializer(client).data, status=status.HTTP_200_OK
            )
        except ClientSettings.DoesNotExist:
            return Response(
                {"error": "Client settings not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(methods=["get"], detail=True, permission_classes=[AllowAny])
    def logo(self, request, pk):
        return self._get_file_response(request, pk, "logo")

    @permission_classes((AllowAny,))
    @action(methods=["get"], detail=True)
    def favicon(self, request, pk):
        return self._get_file_response(request, pk, "favicon")

    def handle_file_upload(self, request, pk, field_name):
        if "file" not in request.FILES:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            settings = ClientSettings.objects.get(id=pk)
            file = request.FILES["file"]
            content_type = magic.Magic(mime=True).from_buffer(file.read())

            if content_type not in [
                "image/png",
                "image/jpeg",
                "image/webp",
                "image/x-icon",
                "image/vnd.microsoft.icon",
                "image/svg+xml",
            ]:
                return Response(
                    {field_name: "invalidFileType"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            setattr(settings, field_name, request.FILES["file"])
            settings.save()
            return Response(status=status.HTTP_200_OK)
        except ClientSettings.DoesNotExist:
            return Response(
                {"error": "Client settings not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error("Error uploading file", exc_info=e)
            return Response(
                {"error": "Error uploading file"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        methods=["post"],
        detail=True,
        url_path="logo/upload",
        parser_classes=(FileUploadParser,),
    )
    def upload_logo(self, request, pk):
        return self.handle_file_upload(request, pk, "logo")

    @action(
        methods=["post"],
        detail=True,
        url_path="favicon/upload",
        parser_classes=(FileUploadParser,),
    )
    def upload_favicon(self, request, pk):
        return self.handle_file_upload(request, pk, "favicon")
