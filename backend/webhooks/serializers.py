from rest_framework import serializers

from core.serializers import BaseModelSerializer
from iam.models import Folder, RoleAssignment
from .models import WebhookEndpoint, WebhookEventType


class WebhookEndpointSerializer(BaseModelSerializer):
    """
    Serializer for the WebhookEndpoint model.
    Handles the 'show once' secret logic.
    """

    # This field is write-only, for user-provided secrets
    secret = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="HMAC signing secret",
    )

    event_types = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        queryset=WebhookEventType.objects.all(),
        required=False,
    )

    target_folders = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Folder.objects.all(), required=False
    )

    has_secret = serializers.SerializerMethodField()

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "name",
            "description",
            "payload_format",
            "url",
            "event_types",
            "is_active",
            "created_at",
            "secret",
            "has_secret",
            "target_folders",
        ]
        read_only_fields = ["id", "created_at"]

    def get_has_secret(self, obj):
        """
        Indicates whether the webhook endpoint has a secret set.
        """
        return bool(obj.secret)

    def validate_target_folders(self, value):
        return _validate_accessible_folders(self.context.get("request"), value)


def _validate_accessible_folders(request, value):
    if not request and hasattr(request, "user"):
        raise serializers.ValidationError("Request context with user is required.")
    user = getattr(request, "user")
    (viewable_folders_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, Folder
    )
    if not all(folder.id in viewable_folders_ids for folder in value):
        raise serializers.ValidationError(
            "One or more target folders are not accessible by the user."
        )
    return value


class AuditSinkSerializer(BaseModelSerializer):
    """
    Serializer for audit-sink endpoints (kind=AUDIT_SINK): admin-managed
    destinations that forward the audit log to an external SIEM. No HMAC secret
    or per-event subscription — the whole audit feed is forwarded in the chosen
    body_format, authenticated via static headers.
    """

    target_folders = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Folder.objects.all(), required=False
    )

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "name",
            "description",
            "url",
            "transport",
            "body_format",
            "headers",
            "is_active",
            "target_folders",
            "folder",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_target_folders(self, value):
        return _validate_accessible_folders(self.context.get("request"), value)
