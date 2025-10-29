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
        Validate provider-specific credentials and settings using the IntegrationRegistry.
        
        Parameters:
            data (dict): Input data containing at least:
                - provider: IntegrationProvider instance
                - credentials: dict of provider credentials
                - settings: dict of provider-specific settings
        
        Returns:
            dict: The validated input `data`.
        
        Raises:
            serializers.ValidationError: If provider-specific validation fails. The error detail is provided under the
            "provider_specific_errors" key.
        """
        provider = data.get("provider")  # This is the IntegrationProvider instance
        # The full configuration dictionary to be validated
        config_data = {
            "credentials": data.get("credentials", {}),
            "settings": data.get("settings", {}),
        }

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
        ]
        read_only_fields = ["id", "last_sync_at", "webhook_url_full"]

    def get_webhook_url_full(self, obj: IntegrationConfiguration) -> str:
        """
        Return the full absolute webhook URL for the given integration configuration.
        
        If the configuration has not been persisted or lacks a webhook secret, returns an empty string. If the serializer context has no request, returns the message "Webhook URL requires request context." Otherwise returns the absolute URL pointing to the webhook-receiver endpoint for this configuration.
         
        Parameters:
            obj (IntegrationConfiguration): The integration configuration instance to build the webhook URL for.
        
        Returns:
            str: The webhook URL string, an empty string, or an informational message if the request context is missing.
        """
        if not obj.pk or not obj.webhook_secret:
            return ""

        request = self.context.get("request")
        if not request:
            return "Webhook URL requires request context."

        # Build the path to the webhook receiver view
        path = reverse("integrations:webhook-receiver", kwargs={"config_id": obj.id})

        return request.build_absolute_uri(path)

    def get_has_api_token(self, obj: IntegrationConfiguration) -> bool:
        """
        Indicates whether the integration configuration contains an API token.
        
        Parameters:
            obj (IntegrationConfiguration): The configuration instance to inspect.
        
        Returns:
            bool: `True` if `obj.credentials` contains an `api_token`, `False` otherwise.
        """
        return bool(obj.credentials and obj.credentials.get("api_token"))

    def get_has_webhook_secret(self, obj: IntegrationConfiguration) -> bool:
        """
        Indicates whether the given integration configuration contains a webhook secret.
        
        Parameters:
            obj (IntegrationConfiguration): The integration configuration to inspect.
        
        Returns:
            `true` if the configuration has a webhook secret, `false` otherwise.
        """
        return bool(obj.webhook_secret)

    def to_representation(self, instance):
        """
        Remove sensitive credential fields from the serialized representation.
        
        This method returns the instance's serialized representation with sensitive fields (for example, the `api_token` key inside the `credentials` mapping) removed so they are not exposed in API responses.
        
        Returns:
            dict: The serialized representation of `instance` with sensitive credential fields removed.
        """
        # Get the default representation
        ret = super().to_representation(instance)

        # Never expose the full credentials, especially the API token, in GET responses.
        if "credentials" in ret and isinstance(ret["credentials"], dict):
            ret["credentials"].pop("api_token", None)  # Remove api_token if it exists

        return ret

    def validate(self, data):
        """
        Validate integration configuration data against the provider's schema using IntegrationRegistry.
        
        If the incoming credentials omit an `api_token` and the serializer is bound to an existing configuration, the existing `api_token` will be preserved for validation. If the provider-specific validation fails, a `serializers.ValidationError` is raised with a `provider_specific_errors` key containing the registry's errors.
        
        Parameters:
            data (dict): Incoming serializer data containing `credentials` and optional `settings` and `provider`.
        
        Returns:
            dict: The validated input `data`.
        
        Raises:
            serializers.ValidationError: When provider-specific validation reports errors (attached under `provider_specific_errors`).
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