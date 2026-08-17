import pytest

from allauth.socialaccount.models import SocialApp

from iam.models import ServiceAccount

from .test_federated_service_accounts import (
    CLIENT_ID,
    JWKS_URL,
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

    def test_create_fails_closed_on_unreachable_idp(self, admin_client):
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
