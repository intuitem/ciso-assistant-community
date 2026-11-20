from icecream import ic
import structlog
from django.urls import reverse
from django.utils.crypto import get_random_string
from rest_framework import serializers

from core.serializers import BaseModelSerializer
from iam.models import Folder, RoleAssignment
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


# Write-only credential keys that are kept from the stored row when a save
# omits them (the edit form hides a secret once it is set).
SECRET_CREDENTIAL_KEYS = ("api_token", "password", "client_secret")


def with_stored_credentials(submitted: dict, stored: dict | None, keys) -> dict | None:
    """``submitted`` completed with the stored values of the ``keys`` it leaves
    empty, or None when that would send a stored value to another connection.

    A stored value is only reusable for the connection it was stored for: every
    other submitted value must match what is stored, including keys the row
    lacks or stores empty, otherwise an empty stored host would let a stored
    secret be sent to any host. A new value for a secret the row already holds
    is not part of what identifies the connection: one of two secrets can be
    replaced while the other is kept. Empty stored values (e.g. a stale
    ``password: null`` written by older saves) are not secrets to reuse and pin
    nothing."""
    stored = {k: v for k, v in (stored or {}).items() if v}
    reused = {k for k in keys if k in stored and not submitted.get(k)}
    replaced = {k for k in SECRET_CREDENTIAL_KEYS if k in stored and submitted.get(k)}
    identity = {
        k: v for k, v in submitted.items() if k not in reused and k not in replaced
    }
    if reused and any(v != stored.get(k) for k, v in identity.items()):
        return None
    return {**submitted, **{k: stored[k] for k in reused}}


class ConnectionTestSerializer(serializers.Serializer):
    provider = serializers.CharField(write_only=True)
    configuration_id = serializers.PrimaryKeyRelatedField(
        queryset=IntegrationConfiguration.objects.filter(is_active=True),
        label="Configuration ID",
        required=False,
    )
    credentials = serializers.DictField()
    settings = serializers.DictField(required=False, default=dict)

    def validate_configuration_id(self, config):
        request = self.context.get("request")
        if request is None:
            raise serializers.ValidationError("Configuration not found.")
        # Viewable, not changeable: a Domain Manager may create a configuration
        # without holding change_, and must still be able to test it. What keeps
        # the stored secret safe is the same-connection pinning below, not this.
        viewable_ids = RoleAssignment.get_viewable_object_ids(
            request.user, IntegrationConfiguration
        )

        if config.id not in viewable_ids:
            raise serializers.ValidationError("Configuration not found.")
        return config

    def validate(self, data):
        provider = data.get("provider")
        config: IntegrationConfiguration | None = data.get("configuration_id")
        credentials = dict(data.get("credentials") or {})

        if config:
            if provider != config.provider.name:
                raise serializers.ValidationError(
                    {"provider": "Provider does not match configuration."}
                )
            # The test may leave any stored value out, not only the secrets.
            stored = config.credentials or {}
            credentials = with_stored_credentials(credentials, stored, stored)
            if credentials is None:
                raise serializers.ValidationError(
                    {"credentials": "reenterSecretToTestModifiedConnection"}
                )

        is_valid, errors = IntegrationRegistry.validate_configuration(
            provider,
            {"credentials": credentials, "settings": data.get("settings", {})},
        )

        if not is_valid:
            raise serializers.ValidationError({"provider_specific_errors": errors})

        data["credentials"] = credentials
        return data


class IntegrationConfigurationSerializer(BaseModelSerializer):
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
        queryset=Folder.objects.all(),
        source="folder",
        label="Folder ID",
    )

    webhook_secret = serializers.CharField(write_only=True, required=False)

    # A generated, read-only field to show the full webhook URL
    webhook_url_full = serializers.SerializerMethodField()

    has_api_token = serializers.SerializerMethodField()
    has_webhook_secret = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and "folder_id" in self.fields:
            accessible_folders = RoleAssignment.get_viewable_object_ids(
                request.user, Folder
            )

            self.fields["folder_id"].queryset = Folder.objects.filter(
                id__in=accessible_folders
            )

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

    def _check_m2m_visibility(self, validated_data: dict) -> None:
        # Providers are a global catalog, listed to every authenticated user
        # and served without RBAC: no role holds view on them, so the link
        # check could never pass. ``provider_id`` already only accepts active
        # providers; every other link is checked as usual.
        super()._check_m2m_visibility(
            {k: v for k, v in validated_data.items() if k != "provider"}
        )

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
        return bool(
            obj.credentials
            and any(obj.credentials.get(key) for key in SECRET_CREDENTIAL_KEYS)
        )

    def get_has_webhook_secret(self, obj: IntegrationConfiguration) -> bool:
        return bool(obj.webhook_secret)

    def update(self, instance, validated_data):
        """Invalidate the cached remote schema when credentials change.

        Repointing instance_url (or swapping accounts) makes the cached
        tables/columns/choices describe the wrong instance; drop the row so the
        next page load lazily re-fetches from the new target.
        """
        old_credentials = dict(instance.credentials or {})
        instance = super().update(instance, validated_data)
        new_credentials = instance.credentials or {}
        if "credentials" in validated_data and new_credentials != old_credentials:
            from integrations.models import IntegrationSchemaCache

            deleted, _ = IntegrationSchemaCache.objects.filter(
                configuration=instance
            ).delete()
            if deleted:
                logger.info(
                    "Invalidated schema cache after credential change",
                    config_id=str(instance.id),
                )
        return instance

    def to_representation(self, instance):
        """
        Modify the output representation to protect sensitive credentials.
        """
        # Get the default representation
        ret = super().to_representation(instance)

        # Never expose stored secrets in GET responses.
        if "credentials" in ret and isinstance(ret["credentials"], dict):
            for key in SECRET_CREDENTIAL_KEYS:
                ret["credentials"].pop(key, None)

        return ret

    def validate(self, data):
        """
        Use the IntegrationRegistry to validate provider-specific schema requirements.
        """
        config: IntegrationConfiguration = self.instance
        provider: IntegrationProvider = data.get(
            "provider", config.provider if config else None
        )

        # Work on a copy: the request dict must not be mutated, and only secrets
        # the stored row actually holds are carried over. Writing a key the
        # provider never uses (``password: None`` on Jira) pollutes the stored
        # credentials and breaks the connection-test secret pinning.
        credentials = dict(data.get("credentials") or {})
        if config:
            credentials = with_stored_credentials(
                credentials, config.credentials, SECRET_CREDENTIAL_KEYS
            )
            if credentials is None:
                raise serializers.ValidationError(
                    {
                        "credentials": "The connection details changed. "
                        "Enter the secret again to save them."
                    }
                )
        if "credentials" in data:
            data["credentials"] = credentials

        # The full configuration dictionary to be validated
        config_data = {
            "credentials": credentials,
            "settings": data.get("settings", {}),
        }

        is_valid, errors = IntegrationRegistry.validate_configuration(
            provider.name, config_data
        )

        # Use the validation logic from your registry
        if not is_valid:
            # Raise a validation error that DRF can render nicely
            raise serializers.ValidationError({"provider_specific_errors": errors})

        registered = IntegrationRegistry.get_provider(provider.name)
        if registered and "settings" in data:
            errors = registered.orchestrator_class.settings_errors(
                config, data["settings"] or {}
            )
            if errors:
                raise serializers.ValidationError({"provider_specific_errors": errors})

        return super().validate(data)


# Aliases expected by BaseModelViewSet's SerializerFactory
IntegrationConfigurationReadSerializer = IntegrationConfigurationSerializer
IntegrationConfigurationWriteSerializer = IntegrationConfigurationSerializer


class SyncMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for the SyncMapping model, used for deletion.
    """

    class Meta:
        model = SyncMapping
        fields = ["id", "local_object_id", "remote_id", "sync_status"]
        read_only_fields = fields
