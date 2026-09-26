import pytest
from rest_framework.fields import empty

from global_settings.models import GlobalSettings
from iam.sso.models import SSOSettings
from iam.sso.serializers import SSOSettingsWriteSerializer


def test_no_write_field_declares_a_default():
    # A default turns an omitted field into an explicit value and defeats the
    # "omitted keeps stored" contract implemented in update().
    offenders = [
        name
        for name, field in SSOSettingsWriteSerializer().fields.items()
        if field.default is not empty
    ]
    assert offenders == []


@pytest.mark.django_db
def test_update_omitting_flags_keeps_stored_values():
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "slo_enabled": True,
                "provider": "openid_connect",
                "client_id": "cid",
                "settings": {
                    "trust_email_without_verified_claim": True,
                    "oauth_pkce_enabled": True,
                    "advanced": {},
                },
            }
        },
    )
    serializer = SSOSettingsWriteSerializer(
        SSOSettings.objects.get(), data={"force_sso": True}
    )
    assert serializer.is_valid(), serializer.errors
    serializer.save()

    value = GlobalSettings.objects.get(name=GlobalSettings.Names.SSO).value
    assert value["slo_enabled"] is True
    assert value["settings"]["trust_email_without_verified_claim"] is True
    assert value["settings"]["oauth_pkce_enabled"] is True
