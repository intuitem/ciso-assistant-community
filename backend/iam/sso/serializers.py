from rest_framework import serializers
from .models import IdentityProvider
from pprint import pprint

from core.serializers import BaseModelSerializer


class IdentityProviderReadSerializer(BaseModelSerializer):
    class Meta:
        model = IdentityProvider
        fields = "__all__"


class IdentityProviderWriteSerializer(BaseModelSerializer):
    attribute_mapping_uid = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    attribute_mapping_email_verified = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    attribute_mapping_email = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
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
        model = IdentityProvider
        fields = "__all__"

    def create(self, validated_data):
        if validated_data.get("provider") == "saml":
            settings = {
                "attribute_mapping": {
                    "uid": validated_data.pop("attribute_mapping_uid", None),
                    "email_verified": validated_data.pop(
                        "attribute_mapping_email_verified", None
                    ),
                    "email": validated_data.pop("attribute_mapping_email", None),
                },
                "idp": {
                    "entity_id": validated_data.pop("idp_entity_id", None),
                    "metadata_url": validated_data.pop("metadata_url", None),
                    "sso_url": validated_data.pop("sso_url", None),
                    "slo_url": validated_data.pop("slo_url", None),
                    "x509cert": validated_data.pop("x509cert", None),
                },
                "sp": {
                    # Optional entity ID of the SP. If not set, defaults to the `saml_metadata` urlpattern
                    "entity_id": validated_data.pop("sp_entity_id", None),
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
                    "want_message_signed": validated_data.pop(
                        "want_message_signed", False
                    ),
                    "want_name_id": validated_data.pop("want_name_id", False),
                    "want_name_id_encrypted": validated_data.pop(
                        "want_name_id_encrypted", False
                    ),
                },
            }
            validated_data["settings"] = settings
            pprint(validated_data)
        return super().create(validated_data)
