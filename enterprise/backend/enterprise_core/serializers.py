from django.conf import settings
from global_settings.models import GlobalSettings
from rest_framework import serializers
from core.serializers import (
    BaseModelSerializer,
    UserWriteSerializer as CommunityUserWriteSerializer,
)
from core.serializer_fields import FieldsRelatedField
from iam.models import Folder, User, Role

from global_settings.models import GlobalSettings
from global_settings.serializers import (
    FeatureFlagsSerializer as CommunityFeatureFlagSerializer,
)

from .models import ClientSettings, LogEntryAction
from auditlog.models import LogEntry
from global_settings.serializers import (
    FeatureFlagsSerializer as CommunityFeatureFlagSerializer,
)
import structlog

logger = structlog.get_logger(__name__)


class FolderWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Folder
        exclude = [
            "builtin",
            "content_type",
        ]

    def validate_parent_folder(self, parent_folder):
        """
        Check that the folders graph will not contain cycles
        """
        if not self.instance:
            return parent_folder
        if parent_folder:
            if (
                parent_folder == self.instance
                or parent_folder in self.instance.get_sub_folders()
            ):
                raise serializers.ValidationError(
                    "errorFolderGraphMustNotContainCycles"
                )
        return parent_folder


class RoleReadSerializer(BaseModelSerializer):
    name = serializers.CharField(source="__str__")
    permissions = serializers.SerializerMethodField()
    folder = FieldsRelatedField()

    class Meta:
        model = Role
        fields = "__all__"

    def get_permissions(self, obj):
        return [{"str": perm.codename} for perm in obj.permissions.all()]


class RoleWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


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
    logo = serializers.SerializerMethodField()
    favicon = serializers.SerializerMethodField()
    logo_mime_type = serializers.CharField()
    favicon_mime_type = serializers.CharField()

    def get_logo(self, obj):
        if obj.logo:
            return obj.logo.name.split("/")[-1]
        return None

    def get_favicon(self, obj):
        if obj.favicon:
            return obj.favicon.name.split("/")[-1]
        return None

    class Meta:
        model = ClientSettings
        exclude = ["is_published", "folder"]


class FeatureFlagsSerializer(CommunityFeatureFlagSerializer):
    """
    Serializer for managing Feature Flags stored within the 'value' JSON field
    of a GlobalSettings instance. Each flag is represented as an explicit
    BooleanField, mapping directly to keys within the 'value' dictionary.
    """

    campaigns = serializers.BooleanField(
        source="value.campaigns", required=False, default=True
    )

    class Meta:
        model = GlobalSettings
        fields = [
            "xrays",
            "incidents",
            "tasks",
            "risk_acceptances",
            "exceptions",
            "follow_up",
            "ebiosrm",
            "scoring_assistant",
            "vulnerabilities",
            "compliance",
            "tprm",
            "privacy",
            "experimental",
            "inherent_risk",
            "organisation_objectives",
            "organisation_issues",
            "quantitative_risk_studies",
            "terminologies",
            "bia",
            "project_management",
            "contracts",
            "reports",
            "validation_flows",
            "campaigns",
        ]
        read_only_fields = ["name"]


class LogEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for the LogEntry model.
    """

    actor = serializers.SerializerMethodField(method_name="get_actor")
    action = serializers.SerializerMethodField(method_name="get_action_display")
    content_type = serializers.SerializerMethodField(method_name="get_content_type")
    folder = serializers.CharField(source="additional_data.folder", read_only=True)

    def get_action_display(self, obj):
        return LogEntryAction(obj.action).to_string()

    def get_actor(self, obj):
        return obj.additional_data.get("user_email") if obj.additional_data else None

    def get_content_type(self, obj):
        return obj.content_type.name

    def to_representation(self, instance):
        log_data = super().to_representation(instance)
        content_type = log_data.get("content_type")
        change_dict = log_data.get("changes", {})

        if (
            isinstance(change_dict, dict)
            and content_type == "user"
            and "password" in change_dict
        ):
            # We want to mask the password in the audit logs.
            change_dict["password"] = ["[old password]", "[new password]"]

        log_data["changes"] = change_dict
        return log_data

    class Meta:
        model = LogEntry
        fields = "__all__"
        read_only_fields = ["id", "timestamp", "actor", "action", "changes_text"]


class FeatureFlagsSerializer(CommunityFeatureFlagSerializer):
    """
    Serializer for managing Feature Flags stored within the 'value' JSON field
    of a GlobalSettings instance. Each flag is represented as an explicit
    BooleanField, mapping directly to keys within the 'value' dictionary.
    """

    focus_mode = serializers.BooleanField(
        source="value.focus_mode", required=False, default=False
    )

    class Meta:
        model = GlobalSettings
        fields = "__all__"
        read_only_fields = ["name"]
