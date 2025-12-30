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
        request = self.context.get("request")
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
