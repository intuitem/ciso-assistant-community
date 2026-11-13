from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.test import Client

from global_settings.models import GlobalSettings

SP_ENTITY_ID = "ciso-assistant"
IDP_SSO_URL = "https://idp.example.com/sso"


def _make_key_and_cert() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sp.example.com")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return key_pem, cert_pem


def _make_signed_saml_settings(key_pem: str, cert_pem: str) -> None:
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "provider": "saml",
                "provider_id": SP_ENTITY_ID,
                "name": "Test SAML",
                "client_id": SP_ENTITY_ID,
                "settings": {
                    "idp": {
                        "entity_id": "https://idp.example.com",
                        "sso_url": IDP_SSO_URL,
                        "x509cert": cert_pem,
                    },
                    "sp": {"entity_id": SP_ENTITY_ID},
                    "advanced": {
                        "authn_request_signed": True,
                        "signature_algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                        "private_key": key_pem,
                        "x509cert": cert_pem,
                    },
                },
            }
        },
    )


def _post_sso_redirect() -> str:
    response = Client().post(
        "/api/iam/sso/redirect/",
        {
            "provider": SP_ENTITY_ID,
            "process": "login",
            "callback_url": "/sso/authenticate",
        },
        HTTP_HOST="localhost",
    )
    assert response.status_code == 302, response.content
    return response["Location"]


@pytest.mark.django_db
class TestSAMLRedirectRelayState:
    def test_signed_authn_request_carries_default_relay_state(self) -> None:
        key_pem, cert_pem = _make_key_and_cert()
        _make_signed_saml_settings(key_pem, cert_pem)

        location = _post_sso_redirect()

        assert location.startswith(IDP_SSO_URL)
        params = parse_qs(urlsplit(location).query, keep_blank_values=True)
        assert params["RelayState"] == ["/"]
