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

    @action(methods=["get"], detail=False, permission_classes=[AllowAny])
    def logo(self, request):
        instance = ClientSettings.objects.get()
        if not instance.logo:
            return Response(
                {"error": "No logo uploaded"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {"data": instance.logo_base64, "mime_type": instance.logo_mime_type}
        )

    @permission_classes((AllowAny,))
    @action(methods=["get"], detail=False)
    def favicon(self, request):
        instance = ClientSettings.objects.get()
        if not instance.favicon:
            return Response(
                {"error": "No favicon uploaded"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {"data": instance.favicon_base64, "mime_type": instance.favicon_mime_type}
        )

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
