from icecream import ic
import structlog
from django.urls import reverse
from django.utils.crypto import get_random_string
from rest_framework import serializers

from iam.models import Folder
from .models import IntegrationProvider, IntegrationConfiguration, SyncMapping
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

    provider = serializers.CharField(write_only=True)
    configuration_id = serializers.PrimaryKeyRelatedField(
        queryset=IntegrationConfiguration.objects.filter(is_active=True),
        label="Configuration ID",
        required=False,
    )
    credentials = serializers.DictField()
    # Settings are sometimes needed for the client to initialize correctly
    settings = serializers.DictField(required=False, default=dict)

    def validate(self, data):
        """
        Use the IntegrationRegistry to validate provider-specific schema requirements.
        """
        provider = data.get("provider")  # This is the IntegrationProvider instance
        config: IntegrationConfiguration = data.get("configuration_id", None)
        # The full configuration dictionary to be validated
        config_data = {
            "credentials": data.get("credentials", {}),
            "settings": data.get("settings", {}),
        }

        if not config_data["credentials"].get("api_token") and config:
            config_data["credentials"]["api_token"] = config.credentials.get(
                "api_token"
            )

        # Use the validation logic from your registry
        is_valid, errors = IntegrationRegistry.validate_configuration(
            provider, config_data
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

    webhook_secret = serializers.CharField(write_only=True, required=False)

    # A generated, read-only field to show the full webhook URL
    webhook_url_full = serializers.SerializerMethodField()

    has_api_token = serializers.SerializerMethodField()
    has_webhook_secret = serializers.SerializerMethodField()

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
            "webhook_url_full",
            "has_api_token",
            "has_webhook_secret",
            "webhook_secret",
        ]
        read_only_fields = ["id", "last_sync_at", "webhook_url_full"]

    def get_webhook_url_full(self, obj: IntegrationConfiguration) -> str:
        """Construct the full, absolute webhook URL"""
        if not obj.pk:
            return ""

        request = self.context.get("request")
        if not request:
            return "Webhook URL requires request context."

        # Build the path to the webhook receiver view
        path = reverse("integrations:webhook-receiver", kwargs={"config_id": obj.id})

        return path

    def get_has_api_token(self, obj: IntegrationConfiguration) -> bool:
        return bool(obj.credentials and obj.credentials.get("api_token"))

    def get_has_webhook_secret(self, obj: IntegrationConfiguration) -> bool:
        return bool(obj.webhook_secret)

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
        Use the IntegrationRegistry to validate provider-specific schema requirements.
        """
        config: IntegrationConfiguration = self.instance
        provider: IntegrationProvider = data.get(
            "provider", config.provider if config else None
        )

        # The full configuration dictionary to be validated
        config_data = {
            "credentials": data.get("credentials", {}),
            "settings": data.get("settings", {}),
        }

        if not config_data["credentials"].get("api_token") and config:
            config_data["credentials"]["api_token"] = config.credentials.get(
                "api_token"
            )

        is_valid, errors = IntegrationRegistry.validate_configuration(
            provider.name, config_data
        )

        # Use the validation logic from your registry
        if not is_valid:
            # Raise a validation error that DRF can render nicely
            raise serializers.ValidationError({"provider_specific_errors": errors})

        return data


class SyncMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for the SyncMapping model, used for deletion.
    """

    class Meta:
        model = SyncMapping
        fields = ["id", "local_object_id", "remote_id", "sync_status"]
        read_only_fields = fields
