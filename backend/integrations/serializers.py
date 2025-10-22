import structlog
from django.urls import reverse
from django.utils.crypto import get_random_string
from rest_framework import serializers

from iam.models import Folder
from .models import IntegrationProvider, IntegrationConfiguration
from .registry import IntegrationRegistry

logger = structlog.get_logger(__name__)


class IntegrationProviderSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for listing available integration providers.
    """

    class Meta:
        model = IntegrationProvider
        fields = ["id", "name", "provider_type", "is_active"]
        read_only_fields = fields


class ConnectionTestSerializer(serializers.Serializer):
    """
    Serializer for validating and testing connection credentials before saving.
    This is not a ModelSerializer, so it doesn't save anything.
    """

    provider_id = serializers.PrimaryKeyRelatedField(
        queryset=IntegrationProvider.objects.filter(is_active=True), label="Provider ID"
    )
    credentials = serializers.DictField()
    # Settings are sometimes needed for the client to initialize correctly
    settings = serializers.DictField(required=False, default=dict)

    def validate(self, data):
        """
        Use the IntegrationRegistry to validate provider-specific schema requirements.
        """
        provider = data.get("provider_id")  # This is the IntegrationProvider instance

        # The full configuration dictionary to be validated
        config_data = {
            "credentials": data.get("credentials", {}),
            "settings": data.get("settings", {}),
        }

        # Use the validation logic from your registry
        is_valid, errors = IntegrationRegistry.validate_configuration(
            provider.name, config_data
        )

        if not is_valid:
            # Raise a validation error that DRF can render nicely
            raise serializers.ValidationError({"provider_specific_errors": errors})

        return data


class IntegrationConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer for creating, reading, and updating IntegrationConfiguration instances.
    """

    # On read, show the provider's name for better readability
    provider = serializers.StringRelatedField(read_only=True)
    # On write, accept the provider's primary key
    provider_id = serializers.PrimaryKeyRelatedField(
        queryset=IntegrationProvider.objects.filter(is_active=True),
        source="provider",
        label="Provider ID",
    )

    # On read, show the folder's name
    folder = serializers.StringRelatedField(read_only=True)
    # On write, accept the folder's primary key
    folder_id = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),  # You might want to filter this based on user permissions
        source="folder",
        label="Folder ID",
    )

    # A generated, read-only field to show the full webhook URL
    webhook_url_full = serializers.SerializerMethodField()

    class Meta:
        model = IntegrationConfiguration
        fields = [
            "id",
            "provider",
            "provider_id",
            "folder",
            "folder_id",
            "credentials",
            "settings",
            "is_active",
            "last_sync_at",
            "webhook_url_full",  # Our generated field
        ]
        read_only_fields = ["id", "last_sync_at", "webhook_url_full"]

    def get_webhook_url_full(self, obj: IntegrationConfiguration) -> str:
        """Construct the full, absolute webhook URL"""
        if not obj.pk or not obj.webhook_secret:
            return ""

        request = self.context.get("request")
        if not request:
            return "Webhook URL requires request context."

        # Build the path to the webhook receiver view
        path = reverse("integrations:webhook-receiver", kwargs={"config_id": obj.id})

        return request.build_absolute_uri(path)

    def to_representation(self, instance):
        """
        Modify the output representation to protect sensitive credentials.
        """
        # Get the default representation
        ret = super().to_representation(instance)

        # Never expose the full credentials, especially the API token, in GET responses.
        if "credentials" in ret and isinstance(ret["credentials"], dict):
            ret["credentials"].pop("api_token", None)  # Remove api_token if it exists

        return ret

    def validate(self, data):
        """
        Use the IntegrationRegistry to validate provider-specific settings and credentials.
        """
        provider = data.get("provider")  # This is the IntegrationProvider instance
        if not provider:
            raise serializers.ValidationError("Provider is required.")

        # The full configuration dictionary to be validated
        config_data = {
            "credentials": data.get("credentials", {}),
            "settings": data.get("settings", {}),
        }

        # Use the logic from your registry
        is_valid, errors = IntegrationRegistry.validate_configuration(
            provider.name, config_data
        )

        if not is_valid:
            # Raise a validation error that DRF can render nicely
            raise serializers.ValidationError({"provider_specific_errors": errors})

        return data

    # def create(self, validated_data):
    #     """
    #     Generate a webhook secret on creation.
    #     """
    #     # Generate a secure, random string for the webhook secret
    #     validated_data["webhook_secret"] = get_random_string(50)
    #
    #     instance = super().create(validated_data)
    #
    #     return instance
