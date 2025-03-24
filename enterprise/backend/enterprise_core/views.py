from datetime import datetime
from django.utils.formats import date_format

import magic
import structlog
from core.views import BaseModelViewSet
from django.conf import settings
from iam.models import User
from rest_framework import status
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
)
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from core.views import BaseModelViewSet
from core.utils import MAIN_ENTITY_DEFAULT_NAME
from iam.models import User
from tprm.models import Entity

from iam.models import RoleAssignment
from tprm.models import Folder
from uuid import UUID

import shutil
from pathlib import Path
import humanize

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

    def perform_update(self, serializer):
        instance = serializer.save()
        self._update_main_entity_name(instance)

    def _update_main_entity_name(self, instance):
        main_entity = Entity.get_main_entity()

        if instance.name:
            self._set_main_entity_name(main_entity, instance.name)
        elif main_entity.name != MAIN_ENTITY_DEFAULT_NAME:
            self._set_main_entity_name(main_entity, MAIN_ENTITY_DEFAULT_NAME)

    def _set_main_entity_name(self, main_entity, new_name):
        if main_entity.name == new_name:
            return

        logger.info("Updating main entity name", entity=main_entity, name=new_name)
        try:
            main_entity.name = new_name
            main_entity.save()
            logger.info("Main entity name updated", entity=main_entity, name=new_name)
        except Exception as e:
            logger.error("An error occurred while renaming main entity", exc_info=e)
            raise

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

    @action(methods=["put"], detail=True, url_path="logo/delete")
    def delete_logo(self, request, pk):
        (
            object_ids_view,
            _,
            _,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, ClientSettings
        )
        response = Response(status=status.HTTP_403_FORBIDDEN)
        if UUID(pk) in object_ids_view:
            settings = self.get_object()
            if settings.logo:
                settings.logo.delete()
                settings.save()
                response = Response(status=status.HTTP_200_OK)
        return response

    @action(methods=["put"], detail=True, url_path="favicon/delete")
    def delete_favicon(self, request, pk):
        (
            object_ids_view,
            _,
            _,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, ClientSettings
        )
        response = Response(status=status.HTTP_403_FORBIDDEN)
        if UUID(pk) in object_ids_view:
            settings = self.get_object()
            if settings.favicon:
                settings.favicon.delete()
                settings.save()
                response = Response(status=status.HTTP_200_OK)
        return response


class LicenseStatusView(APIView):
    def get(self, request):
        expiry_date_str = settings.LICENSE_EXPIRATION

        if not expiry_date_str:
            return Response(
                {"status": "active", "message": "No expiratiion date set"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            try:
                expiration_date = datetime.fromisoformat(expiry_date_str)
            except ValueError:
                expiration_date = "noExpirationDateSet"
                return Response({"status": "active", "message": expiration_date})
        except ValueError as e:
            logger.error("Invalid expiration date format", exc_info=e)
            return Response(
                {"status": "error", "message": "Invalid expiration date format"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        now = datetime.now()

        if expiration_date > now:
            days_left = (expiration_date - now).days
            return Response({"status": "active", "days_left": days_left})
        else:
            days_expired = (now - expiration_date).days
            return Response({"status": "expired", "days_expired": days_expired})


def get_disk_usage():
    try:
        path = Path(settings.BASE_DIR) / "db"
        usage = shutil.disk_usage(path)
        return usage
    except PermissionError:
        logger.error(
            "Permission issue: cannot access the path to retrieve the disk_usage info"
        )
        return None
    except FileNotFoundError:
        logger.error(
            "Path issue: cannot access the path to retrieve the disk_usage info"
        )
        return None


@api_view(["GET"])
def get_build(request):
    """
    API endpoint that returns the build version of the application.
    """
    VERSION = settings.VERSION
    BUILD = settings.BUILD
    LICENSE_SEATS = settings.LICENSE_SEATS
    LICENSE_EXPIRATION = settings.LICENSE_EXPIRATION
    default_db_engine = settings.DATABASES["default"]["ENGINE"]
    if "postgresql" in default_db_engine:
        database_type = "P-FS"
    elif "sqlite" in default_db_engine:
        database_type = "S-FS"
    else:
        database_type = "Unknown"
    try:
        try:
            expiration_iso = datetime.fromisoformat(LICENSE_EXPIRATION)
            license_expiration = date_format(expiration_iso, use_l10n=True)
        except ValueError:
            license_expiration = "noExpirationDateSet"
    except ValueError:
        logger.error("Invalid expiry date format", exc_info=True)
        license_expiration = LICENSE_EXPIRATION

    disk_info = get_disk_usage()

    if disk_info:
        total, used, free = disk_info
        disk_response = {
            "Disk space": f"{humanize.naturalsize(total)}",
            "Used": f"{humanize.naturalsize(used)} ({int((used/total)*100)} %)",
        }
    else:
        disk_response = {
            "Disk space": "Unable to retrieve disk usage",
        }
    return Response(
        {
            "version": VERSION,
            "build": BUILD,
            "infrastructure": database_type,
            "license_seats": LICENSE_SEATS,
            "available_seats": LICENSE_SEATS - len(User.get_editors()),
            "license_expiration": license_expiration,
            **disk_response,
        }
    )
