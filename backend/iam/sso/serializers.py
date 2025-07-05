from allauth.socialaccount.providers.saml.provider import SAMLProvider
from rest_framework import serializers

from global_settings.models import GlobalSettings
from .models import SSOSettings

from core.serializers import BaseModelSerializer


class SSOSettingsReadSerializer(BaseModelSerializer):
    name = serializers.CharField(read_only=True, source="get_name")
    provider = serializers.CharField(read_only=True, source="get_provider_display")

    class Meta:
        model = SSOSettings
        fields = ["id", "name", "provider", "is_enabled", "force_sso"]


class SSOSettingsWriteSerializer(BaseModelSerializer):
    is_enabled = serializers.BooleanField(
        required=False,
    )
    force_sso = serializers.BooleanField(
        required=False,
    )
    provider = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    provider_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    client_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    secret = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        required=False,
        allow_blank=True,
        allow_null=True,
    )  # NOTE: Only used for OIDC
    server_url = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.server_url",
    )  # NOTE: Only used for OIDC
    token_auth_method = serializers.ChoiceField(
        choices=[
            "client_secret_basic",
            "client_secret_post",
            "client_secret_jwt",
            "private_key_jwt",
            "none",
        ],
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.token_auth_method",
    )  # NOTE: Only used for OIDC
    oauth_pkce_enabled = serializers.BooleanField(
        default=False,
        source="settings.oauth_pkce_enabled",
    )  # NOTE: Only used for OIDC
    provider_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.name",
    )
    attribute_mapping_uid = serializers.ListField(
        child=serializers.CharField(
            required=False,
            allow_blank=True,
            allow_null=True,
        ),
        required=False,
        allow_null=True,
        source="settings.attribute_mapping.uid",
    )
    attribute_mapping_email_verified = serializers.ListField(
        child=serializers.CharField(
            required=False,
            allow_blank=True,
            allow_null=True,
        ),
        required=False,
        allow_null=True,
        source="settings.attribute_mapping.email_verified",
    )
    attribute_mapping_email = serializers.ListField(
        child=serializers.CharField(
            required=False,
            allow_blank=True,
            allow_null=True,
        ),
        required=False,
        allow_null=True,
        source="settings.attribute_mapping.email",
    )
    idp_entity_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.idp.entity_id",
    )
    metadata_url = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.idp.metadata_url",
    )
    sso_url = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.idp.sso_url",
    )
    slo_url = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.idp.slo_url",
    )
    x509cert = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.idp.x509cert",
    )
    sp_entity_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.sp.entity_id",
    )
    allow_repeat_attribute_name = serializers.BooleanField(
        required=False,
        source="settings.advanced.allow_repeat_attribute_name",
    )
    allow_single_label_domains = serializers.BooleanField(
        required=False,
        source="settings.advanced.allow_single_label_domains",
    )
    authn_request_signed = serializers.BooleanField(
        required=False,
        source="settings.advanced.authn_request_signed",
    )
    digest_algorithm = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.advanced.digest_algorithm",
    )
    logout_request_signed = serializers.BooleanField(
        required=False,
        source="settings.advanced.logout_request_signed",
    )
    logout_response_signed = serializers.BooleanField(
        required=False,
        source="settings.advanced.logout_response_signed",
    )
    metadata_signed = serializers.BooleanField(
        required=False,
        source="settings.advanced.metadata_signed",
    )
    name_id_encrypted = serializers.BooleanField(
        required=False,
        source="settings.advanced.name_id_encrypted",
    )
    reject_deprecated_algorithm = serializers.BooleanField(
        required=False,
        source="settings.advanced.reject_deprecated_algorithm",
    )
    reject_idp_initiated_sso = serializers.BooleanField(
        required=False,
        source="settings.advanced.reject_idp_initiated_sso",
    )
    signature_algorithm = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="settings.advanced.signature_algorithm",
    )
    want_assertion_encrypted = serializers.BooleanField(
        required=False,
        source="settings.advanced.want_assertion_encrypted",
    )
    want_assertion_signed = serializers.BooleanField(
        required=False,
        source="settings.advanced.want_assertion_signed",
    )
    want_attribute_statement = serializers.BooleanField(
        required=False,
        source="settings.advanced.want_attribute_statement",
    )
    want_message_signed = serializers.BooleanField(
        required=False,
        source="settings.advanced.want_message_signed",
    )
    want_name_id = serializers.BooleanField(
        required=False,
        source="settings.advanced.want_name_id",
    )
    want_name_id_encrypted = serializers.BooleanField(
        required=False,
        source="settings.advanced.want_name_id_encrypted",
    )
    oidc_has_secret = serializers.SerializerMethodField()

    def get_oidc_has_secret(self, obj) -> bool:
        try:
            return bool(SSOSettings.objects.get().secret)
        except SSOSettings.DoesNotExist:
            return False

    class Meta:
        model = SSOSettings
        exclude = ["value"]

    def update(self, instance, validated_data):
        settings_object = GlobalSettings.objects.get(name=GlobalSettings.Names.SSO)

        # Use stored secret if no secret is transmitted
        validated_data["secret"] = validated_data.get(
            "secret", settings_object.value.get("secret", "")
        )
        validated_data["provider_id"] = validated_data.get("provider", "n/a")
        if "settings" not in validated_data:
            validated_data["settings"] = {}
        validated_data["settings"]["name"] = validated_data.get("provider", "n/a")

        settings_object.value = validated_data
        settings_object.save()
        return instance
