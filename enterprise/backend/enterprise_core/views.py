from datetime import datetime
from django.utils.formats import date_format

import magic
import structlog
from core.permissions import IsAdministrator
from django.db import models, transaction
from django.db.models import CharField, Value, Case, When
from django.db.models.functions import Lower, Cast
import django_filters as df
from django.contrib.auth.models import Permission
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
from rest_framework import mixins, viewsets, filters

from django_filters.rest_framework import DjangoFilterBackend

from django.conf import settings

from core.views import BaseModelViewSet, GenericFilterSet
from core.utils import MAIN_ENTITY_DEFAULT_NAME
from iam.models import User, Role, UserGroup, RoleAssignment
from tprm.models import Entity

from tprm.models import Folder
from uuid import UUID

import shutil
from pathlib import Path
import humanize

from .models import ClientSettings
from .serializers import ClientSettingsReadSerializer, LogEntrySerializer

from auditlog.models import LogEntry

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
        show_data = (
            instance.show_images_unauthenticated or request.user.is_authenticated
        )
        if not (instance.logo and show_data):
            return Response(
                {"error": "No logo uploaded"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {"data": instance.logo_base64, "mime_type": instance.logo_mime_type}
        )

    @action(methods=["get"], detail=False, permission_classes=[AllowAny])
    def favicon(self, request):
        instance = ClientSettings.objects.get()
        show_data = (
            instance.show_images_unauthenticated or request.user.is_authenticated
        )
        if not (instance.favicon and show_data):
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
                {"status": "active", "message": "No expiration date set"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            expiration_date = datetime.fromisoformat(expiry_date_str)
        except ValueError as e:
            logger.error("Invalid expiration date format", exc_info=e)
            error_msg = "noExpirationDateSet"
            return Response(
                {"status": "active", "message": error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        now = datetime.now()

        if expiration_date > now:
            days_left = (expiration_date - now).days
            return Response({"status": "active", "days_left": days_left})
        else:
            days_expired = (now - expiration_date).days
            return Response({"status": "expired", "days_expired": days_expired})


class RoleViewSet(BaseModelViewSet):
    """
    API endpoint that allows roles to be viewed or edited
    """

    model = Role
    ordering = ["builtin", "name"]

    def perform_create(self, serializer):
        """
        Create per-folder UserGroups and RoleAssignments for the new role.
        """
        role = serializer.save()
        role.permissions.add(
            Permission.objects.get(
                codename="view_folder",
                content_type__app_label="iam",
                content_type__model="folder",
            )
        )
        with transaction.atomic():
            for folder in Folder.objects.exclude(content_type="EN"):
                ug, _ = UserGroup.objects.get_or_create(
                    folder=folder, name=role.name, defaults={"builtin": False}
                )
                ra = RoleAssignment.objects.create(
                    folder=Folder.get_root_folder(),
                    role=role,
                    user_group=ug,
                    is_recursive=True,
                )
                ra.perimeter_folders.add(folder)

    def perform_update(self, serializer):
        """
        Update the user groups associated with the role
        """
        role = serializer.save()
        role.permissions.add(
            Permission.objects.get(
                codename="view_folder",
                content_type__app_label="iam",
                content_type__model="folder",
            )
        )
        ug_ids = (
            RoleAssignment.objects.filter(
                role=role, user_group__isnull=False, user_group__builtin=False
            )
            .values_list("user_group_id", flat=True)
            .distinct()
        )
        if ug_ids:
            UserGroup.objects.filter(id__in=ug_ids).update(name=role.name)

    def perform_destroy(self, instance):
        """
        Delete only user groups tied to this role’s assignments, atomically.
        """
        with transaction.atomic():
            ras_qs = RoleAssignment.objects.select_related("user_group").filter(
                role=instance
            )
            ug_ids = list(
                ras_qs.exclude(user_group__isnull=True).values_list(
                    "user_group_id", flat=True
                )
            )
            # Remove this role's assignments first
            ras_qs.delete()
            if ug_ids:
                # Delete only non-builtin groups that are now orphaned (no remaining RAs)
                orphan_ug_ids = list(
                    UserGroup.objects.filter(id__in=ug_ids, builtin=False)
                    .annotate(ra_count=models.Count("roleassignment"))
                    .filter(ra_count=0)
                    .values_list("id", flat=True)
                )
                if orphan_ug_ids:
                    UserGroup.objects.filter(id__in=orphan_ug_ids).delete()
            super().perform_destroy(instance)


class PermissionViewSet(BaseModelViewSet):
    """
    API endpoint that allows permissions to be viewed or edited.
    """

    model = Permission
    ordering = ["codename"]
    filterset_fields = ["codename", "content_type"]
    search_fields = ["codename", "name"]


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
            "diskSpace": f"{humanize.naturalsize(total)}",
            "diskUsed": f"{humanize.naturalsize(used)} ({int((used / total) * 100)} %)",
        }
    else:
        disk_response = {
            "diskSpace": "Unable to retrieve disk usage",
        }
    return Response(
        {
            "version": VERSION,
            "build": BUILD,
            "infrastructure": database_type,
            "licenseSeats": LICENSE_SEATS,
            "availableSeats": LICENSE_SEATS - len(User.get_editors()),
            "licenseExpiration": license_expiration,
            **disk_response,
        }
    )


class LogEntryFilterSet(GenericFilterSet):
    actor = df.CharFilter(field_name="actor__email", lookup_expr="icontains")
    folder = df.CharFilter(
        field_name="additional_data__folder", lookup_expr="icontains"
    )
    content_type = df.CharFilter(method="filter_content_type_model")

    class Meta:
        model = LogEntry
        fields = {
            "actor": ["exact"],
            "content_type": ["exact"],
            "action": ["exact"],
        }

    def filter_content_type_model(self, queryset, name, value):
        if not value:
            return queryset
        normalized = value.replace(" ", "").lower()
        return queryset.filter(content_type__model__icontains=normalized)


class LogEntryViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering = ["-timestamp"]
    ordering_fields = "__all__"
    search_fields = [
        "content_type__model",
        "action",
        "actor__email",
        "actor__first_name",
        "actor__last_name",
        "changes",  # allows to search for last_login (for example)
        "additional_data__folder",
    ]
    filterset_class = LogEntryFilterSet

    permission_classes = (IsAdministrator,)
    serializer_class = LogEntrySerializer

    def get_queryset(self):
        return LogEntry.objects.all().annotate(
            folder=Lower(
                Case(
                    When(additional_data__isnull=True, then=Value("")),
                    When(additional_data__folder=None, then=Value("")),
                    default=Cast("additional_data__folder", CharField()),
                    output_field=CharField(),
                )
            ),
        )
