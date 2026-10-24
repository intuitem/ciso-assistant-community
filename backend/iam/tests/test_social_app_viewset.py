import socket
from unittest.mock import patch

import pytest

from allauth.socialaccount.models import SocialApp
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from core.net_safety import assert_public_url
from iam.utils import mask_social_app_settings

from .test_federated_service_accounts import (
    CLIENT_ID,
    SERVER_URL,
    _create_federated_sa,
    admin_client,  # noqa: F401
    app_config,  # noqa: F401
    domain_folder,  # noqa: F401
    mocked_idp,  # noqa: F401
    rsa_keypair,  # noqa: F401
    social_app,  # noqa: F401
)

SOCIAL_APPS_ENDPOINT = "/api/iam/social-apps/"


@pytest.mark.django_db
class TestSocialAppViewSet:
    def test_create_registers_and_verifies_live(self, admin_client, mocked_idp):
        response = admin_client.post(
            SOCIAL_APPS_ENDPOINT,
            {
                "name": "Test IdP",
                "provider_id": "test-idp",
                "client_id": CLIENT_ID,
                "server_url": SERVER_URL,
            },
        )
        assert response.status_code == 201, response.content
        payload = response.json()
        assert payload["provider"] == "openid_connect"
        assert payload["server_url"] == SERVER_URL
        assert mocked_idp["discovery"] == 1
        assert mocked_idp["jwks"] == 1

    def test_create_fails_closed_on_unreachable_idp(self, admin_client, mocked_idp):
        response = admin_client.post(
            SOCIAL_APPS_ENDPOINT,
            {
                "name": "Broken IdP",
                "provider_id": "broken-idp",
                "client_id": "broken-client",
                "server_url": "https://unreachable.example.com",
            },
        )
        assert response.status_code == 400, response.content
        assert not SocialApp.objects.filter(provider_id="broken-idp").exists()

    def test_duplicate_provider_id_rejected(self, admin_client, mocked_idp, social_app):
        response = admin_client.post(
            SOCIAL_APPS_ENDPOINT,
            {
                "name": "Duplicate",
                "provider_id": social_app.provider_id,
                "client_id": "another-client",
                "server_url": SERVER_URL,
            },
        )
        assert response.status_code == 400, response.content

    def test_duplicate_client_id_rejected(self, admin_client, mocked_idp, social_app):
        response = admin_client.post(
            SOCIAL_APPS_ENDPOINT,
            {
                "name": "Duplicate client",
                "provider_id": "another-idp",
                "client_id": social_app.client_id,
                "server_url": SERVER_URL,
            },
        )
        assert response.status_code == 400, response.content

    def test_invalid_provider_id_format_rejected(self, admin_client):
        response = admin_client.post(
            SOCIAL_APPS_ENDPOINT,
            {
                "name": "Bad slug",
                "provider_id": "Not A Slug!",
                "client_id": "client",
                "server_url": SERVER_URL,
            },
        )
        assert response.status_code == 400, response.content

    def test_list_and_retrieve(self, admin_client, social_app):
        list_response = admin_client.get(SOCIAL_APPS_ENDPOINT)
        assert list_response.status_code == 200
        assert any(
            item["id"] == social_app.id for item in list_response.json()["results"]
        )

        detail_response = admin_client.get(f"{SOCIAL_APPS_ENDPOINT}{social_app.id}/")
        assert detail_response.status_code == 200
        assert detail_response.json()["client_id"] == CLIENT_ID

    def test_partial_update(self, admin_client, mocked_idp, social_app):
        response = admin_client.patch(
            f"{SOCIAL_APPS_ENDPOINT}{social_app.id}/",
            {"name": "Renamed IdP"},
        )
        assert response.status_code == 200, response.content
        assert response.json()["name"] == "Renamed IdP"
        social_app.refresh_from_db()
        assert social_app.name == "Renamed IdP"

    def test_provider_id_can_be_changed(self, admin_client, mocked_idp, social_app):
        response = admin_client.patch(
            f"{SOCIAL_APPS_ENDPOINT}{social_app.id}/",
            {"provider_id": "renamed-idp"},
        )
        assert response.status_code == 200, response.content
        social_app.refresh_from_db()
        assert social_app.provider_id == "renamed-idp"

    def test_provider_id_change_to_duplicate_rejected(
        self, admin_client, mocked_idp, social_app
    ):
        SocialApp.objects.create(
            provider="openid_connect",
            provider_id="taken-idp",
            name="Other IdP",
            client_id="other-client-id",
            settings={"server_url": SERVER_URL},
        )
        response = admin_client.patch(
            f"{SOCIAL_APPS_ENDPOINT}{social_app.id}/",
            {"provider_id": "taken-idp"},
        )
        assert response.status_code == 400, response.content
        social_app.refresh_from_db()
        assert social_app.provider_id == "test-idp"

    def test_changes_are_audited_without_credentials(
        self, admin_client, mocked_idp, social_app
    ):
        social_app.secret = "s3cret-value-never-logged"
        social_app.key = "k3y-value-never-logged"
        social_app.settings = {
            **social_app.settings,
            "certificate_key": "cert-key-value-never-logged",
        }
        social_app.save()
        new_server_url = "https://test-idp.example.com/realms/new"
        with patch(
            "iam.oidc_federation.check_social_app_live"
        ):  # the mocked IdP only answers the original URL
            response = admin_client.patch(
                f"{SOCIAL_APPS_ENDPOINT}{social_app.id}/",
                {"name": "Renamed IdP", "server_url": new_server_url},
            )
        assert response.status_code == 200, response.content

        entries = LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(SocialApp),
            object_pk=str(social_app.pk),
        )
        assert any("name" in (entry.changes or {}) for entry in entries)
        logged = " ".join(
            f"{entry.changes} {entry.serialized_data} {entry.additional_data}"
            for entry in entries
        )
        assert new_server_url in logged
        assert "certificate_key" not in logged
        assert "cert-key-value-never-logged" not in logged
        assert "s3cret-value-never-logged" not in logged
        assert "k3y-value-never-logged" not in logged


def test_settings_mask_fails_closed_on_unparseable_value():
    assert mask_social_app_settings("not json {certificate_key: x}") == "**********"

    def test_destroy_blocked_while_referenced_by_service_account(
        self, admin_client, domain_folder, social_app
    ):
        create_response = _create_federated_sa(admin_client, domain_folder, social_app)
        assert create_response.status_code == 201, create_response.content

        delete_response = admin_client.delete(f"{SOCIAL_APPS_ENDPOINT}{social_app.id}/")
        assert delete_response.status_code == 400, delete_response.content
        assert SocialApp.objects.filter(pk=social_app.pk).exists()

    def test_destroy_succeeds_once_unreferenced(self, admin_client, social_app):
        response = admin_client.delete(f"{SOCIAL_APPS_ENDPOINT}{social_app.id}/")
        assert response.status_code == 204, response.content
        assert not SocialApp.objects.filter(pk=social_app.pk).exists()


@pytest.mark.django_db
class TestSocialAppSSRFGuard:
    """Registration fetches (discovery + JWKS) must go through the net_safety
    guard. The shared conftest no-ops the guard (fake IdP hosts have no DNS);
    these tests restore the real check with a stubbed resolver."""

    @staticmethod
    def _resolver(ip_by_host):
        def getaddrinfo(host, *args, **kwargs):
            ip = ip_by_host.get(host, "203.0.113.10")
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]

        return getaddrinfo

    @pytest.fixture
    def real_guard(self, monkeypatch):
        monkeypatch.setattr(
            "iam.oidc_federation.assert_public_url_unless_dev", assert_public_url
        )

    def test_private_server_url_rejected(
        self, admin_client, mocked_idp, real_guard, monkeypatch
    ):
        monkeypatch.setattr(
            "core.net_safety.socket.getaddrinfo",
            self._resolver({"test-idp.example.com": "10.13.37.1"}),
        )
        response = admin_client.post(
            SOCIAL_APPS_ENDPOINT,
            {
                "name": "Internal IdP",
                "provider_id": "internal-idp",
                "client_id": "internal-client",
                "server_url": SERVER_URL,
            },
        )
        assert response.status_code == 400, response.content
        assert not SocialApp.objects.filter(provider_id="internal-idp").exists()

    def test_private_jwks_uri_from_discovery_rejected(
        self, admin_client, real_guard, monkeypatch
    ):
        """jwks_uri comes from the remote discovery document, not the admin: a
        public server_url must not be able to pivot the JWKS fetch inward."""
        issuer = "https://pivot-idp.example.com/"
        server_url = issuer + ".well-known/openid-configuration"
        internal_jwks = "https://metadata.internal.example.com/jwks"
        monkeypatch.setattr(
            "core.net_safety.socket.getaddrinfo",
            self._resolver({"metadata.internal.example.com": "169.254.169.254"}),
        )

        class FakeResponse:
            is_redirect = False

            def raise_for_status(self):
                pass

            def json(self):
                return {"issuer": issuer, "jwks_uri": internal_jwks}

        def fake_get(session_self, url, *args, **kwargs):
            assert url == server_url, f"blocked URL was fetched: {url}"
            return FakeResponse()

        monkeypatch.setattr("requests.Session.get", fake_get)
        response = admin_client.post(
            SOCIAL_APPS_ENDPOINT,
            {
                "name": "Pivot IdP",
                "provider_id": "pivot-idp",
                "client_id": "pivot-client",
                "server_url": server_url,
            },
        )
        assert response.status_code == 400, response.content
        assert not SocialApp.objects.filter(provider_id="pivot-idp").exists()

    def test_redirecting_discovery_endpoint_rejected(
        self, admin_client, monkeypatch, db
    ):
        """A redirect would fetch a URL the SSRF guard never checked (scheme
        downgrade or internal pivot), so it must fail closed."""

        class RedirectResponse:
            is_redirect = True
            status_code = 302

            def raise_for_status(self):
                pass

            def json(self):  # pragma: no cover - must not be reached
                raise AssertionError("redirect response body was consumed")

        monkeypatch.setattr(
            "requests.Session.get", lambda self, url, *a, **k: RedirectResponse()
        )
        response = admin_client.post(
            SOCIAL_APPS_ENDPOINT,
            {
                "name": "Redirecting IdP",
                "provider_id": "redirect-idp",
                "client_id": "redirect-client",
                "server_url": "https://redirecting-idp.example.com",
            },
        )
        assert response.status_code == 400, response.content
        assert not SocialApp.objects.filter(provider_id="redirect-idp").exists()
