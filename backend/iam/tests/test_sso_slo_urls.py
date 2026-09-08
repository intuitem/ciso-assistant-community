import pytest
from types import SimpleNamespace

from django.test import RequestFactory, override_settings

from global_settings.models import GlobalSettings
from iam.sso.slo import _build_public_saml_config, build_idp_logout_url

PUBLIC_URL = "https://app.example.com"
IDP_SLO_URL = "https://idp.example.com/slo"
INTERNAL_HOST = "backend:8000"
CLIENT_ID = "0"

SAML_SETTINGS = {
    "sp": {"entity_id": "ciso-assistant"},
    "idp": {
        "entity_id": "https://idp.example.com/metadata",
        "x509cert": "",
        "sso_url": "https://idp.example.com/sso",
        "slo_url": IDP_SLO_URL,
    },
    "advanced": {"allow_single_label_domains": False},
}

SLO_STATE = {
    "provider": "saml",
    "name_id": "user@example.com",
    "session_index": "_session_index",
    "name_id_format": None,
    "name_id_nq": None,
    "name_id_spnq": None,
}

test_settings = override_settings(
    CISO_ASSISTANT_URL=PUBLIC_URL,
    ALLOWED_HOSTS=["backend", "localhost", "testserver", "app.example.com"],
)


def _internal_request():
    """A logout-url call issued by the frontend server, not by the browser."""
    return RequestFactory().post("/api/iam/sso/logout-url/", HTTP_HOST=INTERNAL_HOST)


def _make_saml_sso_settings():
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "slo_enabled": True,
                "provider": "saml",
                "provider_id": "test-saml",
                "name": "Test SAML",
                "client_id": CLIENT_ID,
                "settings": SAML_SETTINGS,
            }
        },
    )


@test_settings
def test_saml_sp_config_uses_public_origin_on_internal_host():
    provider = SimpleNamespace(
        app=SimpleNamespace(client_id=CLIENT_ID, settings=SAML_SETTINGS)
    )

    config = _build_public_saml_config(_internal_request(), provider)

    assert (
        config["sp"]["assertionConsumerService"]["url"]
        == f"{PUBLIC_URL}/api/accounts/saml/{CLIENT_ID}/acs/"
    )
    assert (
        config["sp"]["singleLogoutService"]["url"]
        == f"{PUBLIC_URL}/api/accounts/saml/{CLIENT_ID}/sls/"
    )


@pytest.mark.django_db
@test_settings
def test_saml_logout_url_resolved_for_a_call_on_the_internal_host():
    """python3-saml rejects the internal host, which used to skip SLO silently."""
    _make_saml_sso_settings()

    logout_url = build_idp_logout_url(_internal_request(), SLO_STATE)

    assert logout_url is not None
    assert logout_url.startswith(f"{IDP_SLO_URL}?")
    assert "SAMLRequest=" in logout_url
