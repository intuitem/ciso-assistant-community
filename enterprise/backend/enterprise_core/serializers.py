from django.conf import settings
from rest_framework import serializers
from core.serializers import (
    BaseModelSerializer,
    UserWriteSerializer as CommunityUserWriteSerializer,
)
from iam.models import Folder, User

from .models import ClientSettings
import structlog

logger = structlog.get_logger(__name__)


class FolderWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Folder
        exclude = [
            "builtin",
            "content_type",
        ]


class EditorPermissionMixin:
    @staticmethod
    def check_editor_permissions(instance, group):
        editor_prefixes = {"add_", "change_", "delete_"}
        editors = User.get_editors()
        seats = settings.LICENSE_SEATS

        perms = group.permissions
        if any(perm.startswith(prefix) for prefix in editor_prefixes for perm in perms):
            logger.info("Adding editor permissions to user", user=instance, group=group)
            if instance not in editors and len(editors) >= seats:
                logger.error(
                    "License seats exceeded, cannot add editor user groups to user",
                    user=instance,
                    seats=seats,
                )
                raise serializers.ValidationError(
                    {"user_groups": "errorLicenseSeatsExceeded"}
                )


class UserWriteSerializer(CommunityUserWriteSerializer, EditorPermissionMixin):
    def _update_user_groups(self, instance, validated_data):
        if validated_data.get("user_groups"):
            logger.info(
                "Updating user groups",
                user=instance,
                groups=validated_data["user_groups"],
            )
            for group in validated_data["user_groups"]:
                self.check_editor_permissions(instance, group)

    def update(self, instance: User, validated_data):
        self._update_user_groups(instance, validated_data)
        return super().update(instance, validated_data)

    def partial_update(self, instance, validated_data):
        self._update_user_groups(instance, validated_data)
        return super().partial_update(instance, validated_data)


class ClientSettingsWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ClientSettings
        exclude = ["is_published", "folder"]


class ClientSettingsReadSerializer(BaseModelSerializer):
    logo_hash = serializers.CharField()
    favicon_hash = serializers.CharField()

    class Meta:
        model = ClientSettings
        exclude = ["is_published", "folder"]
