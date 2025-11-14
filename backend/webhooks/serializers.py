from rest_framework import serializers
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
        help_text="Provide a secret, or leave blank to auto-generate.",
    )

    event_types = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        queryset=WebhookEventType.objects.all(),
        required=False,
    )

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "url",
            "event_types",
            "is_active",
            "created_at",
            "secret",
        ]
        read_only_fields = ["id", "created_at"]
