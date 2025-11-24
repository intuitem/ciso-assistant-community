from rest_framework import serializers

from iam.models import Folder, RoleAssignment
from .models import WebhookEndpoint, WebhookEventType


class WebhookEndpointSerializer(serializers.ModelSerializer):
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
        many=True, queryset=Folder.objects.none(), required=False
    )

    has_secret = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
            (viewable_folders_ids, _, _) = RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), user, Folder
            )
            self.fields["target_folders"].queryset = Folder.objects.filter(
                id__in=viewable_folders_ids
            )

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
