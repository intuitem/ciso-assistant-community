import pytest
from rest_framework.test import APIClient

from global_settings.models import GlobalSettings

SSO_INFO_URL = "/api/settings/sso/info/"


def _store_sso_settings(provider, settings):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "provider": provider,
                "provider_id": provider,
                "name": "Test IdP",
                "client_id": "ciso-assistant",
                "settings": settings,
            }
        },
    )


@pytest.mark.django_db
class TestGetSsoInfo:
    def test_saml_settings_expose_sp_entity_id(self):
        _store_sso_settings("saml", {"sp": {"entity_id": "ciso-assistant"}})

        response = APIClient().get(SSO_INFO_URL)

        assert response.status_code == 200
        assert response.json()["sp_entity_id"] == "ciso-assistant"

    @pytest.mark.parametrize(
        "settings", [{}, {"server_url": "https://idp.example.com"}, None]
    )
    def test_oidc_settings_without_sp_section(self, settings):
        """OIDC settings have no SAML "sp" section. The login page loads this
        endpoint, so it must not fail, and the value it posts as the provider
        must still identify the configured one."""
        _store_sso_settings("openid_connect", settings)

        response = APIClient().get(SSO_INFO_URL)

        assert response.status_code == 200
        assert response.json()["is_enabled"] is True
        assert response.json()["sp_entity_id"] == "openid_connect"
