from allauth.socialaccount.providers.saml.provider import SAMLProvider
from rest_framework import serializers
from .models import SSOSettings

from core.serializers import BaseModelSerializer


class SSOSettingsReadSerializer(BaseModelSerializer):
    name = serializers.CharField(read_only=True, source="get_name")
    provider = serializers.CharField(read_only=True, source="get_provider_display")
    settings = serializers.CharField(read_only=True)

    class Meta:
        model = SSOSettings
        fields = "__all__"


class SSOSettingsWriteSerializer(BaseModelSerializer):
    attribute_mapping_uid = serializers.ListField(
        child=serializers.CharField(
            required=False, allow_blank=True, allow_null=True, write_only=True
        ),
        write_only=True,
        required=False,
        allow_null=True,
    )
    attribute_mapping_email_verified = serializers.ListField(
        child=serializers.CharField(
            required=False, allow_blank=True, allow_null=True, write_only=True
        ),
        write_only=True,
        required=False,
        allow_null=True,
    )
    attribute_mapping_email = serializers.ListField(
        child=serializers.CharField(
            required=False, allow_blank=True, allow_null=True, write_only=True
        ),
        write_only=True,
        required=False,
        allow_null=True,
    )
    idp_entity_id = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    metadata_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    sso_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    slo_url = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    x509cert = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    sp_entity_id = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    allow_repeat_attribute_name = serializers.BooleanField(
        required=False, write_only=True
    )
    allow_single_label_domains = serializers.BooleanField(
        required=False, write_only=True
    )
    authn_request_signed = serializers.BooleanField(required=False, write_only=True)
    digest_algorithm = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    logout_request_signed = serializers.BooleanField(required=False, write_only=True)
    logout_response_signed = serializers.BooleanField(required=False, write_only=True)
    metadata_signed = serializers.BooleanField(required=False, write_only=True)
    name_id_encrypted = serializers.BooleanField(required=False, write_only=True)
    reject_deprecated_algorithm = serializers.BooleanField(
        required=False, write_only=True
    )
    reject_idp_initiated_sso = serializers.BooleanField(required=False, write_only=True)
    signature_algorithm = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    want_assertion_encrypted = serializers.BooleanField(required=False, write_only=True)
    want_assertion_signed = serializers.BooleanField(required=False, write_only=True)
    want_attribute_statement = serializers.BooleanField(required=False, write_only=True)
    want_message_signed = serializers.BooleanField(required=False, write_only=True)
    want_name_id = serializers.BooleanField(required=False, write_only=True)
    want_name_id_encrypted = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = SSOSettings
        fields = "__all__"

    def create(self, validated_data):
        if validated_data.get("provider") == "saml":
            settings = self.build_saml_settings(validated_data)
            validated_data["settings"] = settings
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("provider") == "saml":
            settings = self.build_saml_settings(validated_data)
            validated_data["settings"] = settings
        return super().update(instance, validated_data)

    def build_saml_settings(self, validated_data):
        default_attribute_mapping = SAMLProvider.default_attribute_mapping
        attribute_mapping = {
            "uid": validated_data.pop("attribute_mapping_uid", None),
            "email_verified": validated_data.pop(
                "attribute_mapping_email_verified", None
            ),
            "email": validated_data.pop("attribute_mapping_email", None),
        }
        return {
            "attribute_mapping": {
                key: value if value is not None else default_attribute_mapping[key]
                for key, value in attribute_mapping.items()
            },
            "idp": {
                "entity_id": validated_data.pop("idp_entity_id", ""),
                "metadata_url": validated_data.pop("metadata_url", ""),
                "sso_url": validated_data.pop("sso_url", ""),
                "slo_url": validated_data.pop("slo_url", ""),
                "x509cert": validated_data.pop("x509cert", ""),
            },
            "sp": {
                # Optional entity ID of the SP. If not set, defaults to the `saml_metadata` urlpattern
                "entity_id": validated_data.pop("sp_entity_id", ""),
            },
            # Advanced settings.
            "advanced": {
                "allow_repeat_attribute_name": validated_data.pop(
                    "allow_repeat_attribute_name", True
                ),
                "allow_single_label_domains": validated_data.pop(
                    "allow_single_label_domains", False
                ),
                "authn_request_signed": validated_data.pop(
                    "authn_request_signed", False
                ),
                "digest_algorithm": validated_data.pop(
                    "digest_algorithm",
                    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                ),
                "logout_request_signed": validated_data.pop(
                    "logout_request_signed", False
                ),
                "logout_response_signed": validated_data.pop(
                    "logout_response_signed", False
                ),
                "metadata_signed": validated_data.pop("metadata_signed", False),
                "name_id_encrypted": validated_data.pop("name_id_encrypted", False),
                "reject_deprecated_algorithm": validated_data.pop(
                    "reject_deprecated_algorithm", True
                ),
                # Due to security concerns, IdP initiated SSO is rejected by default.
                "reject_idp_initiated_sso": validated_data.pop(
                    "reject_idp_initiated_sso", False
                ),
                "signature_algorithm": validated_data.pop(
                    "signature_algorithm",
                    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                ),
                "want_assertion_encrypted": validated_data.pop(
                    "want_assertion_encrypted", False
                ),
                "want_assertion_signed": validated_data.pop(
                    "want_assertion_signed", False
                ),
                "want_attribute_statement": validated_data.pop(
                    "want_attribute_statement", True
                ),
                "want_message_signed": validated_data.pop("want_message_signed", False),
                "want_name_id": validated_data.pop("want_name_id", False),
                "want_name_id_encrypted": validated_data.pop(
                    "want_name_id_encrypted", False
                ),
            },
        }
