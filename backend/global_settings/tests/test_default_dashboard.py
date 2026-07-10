"""
Tests for the default_custom_analytics_dashboard general setting.

Covers:
- POST /settings/general/set-default-dashboard/
  - 403 for non-admin (no change_globalsettings)
  - 400 for invalid UUID
  - 400 for non-existent dashboard
  - 200 + persisted value for admin (set, change, clear)
  - updated_at advances (auto_now)
- GET /settings/general/default_custom_analytics_dashboard/
  - Returns only dashboards accessible to the requesting user

The serializer validation branch is also exercised through PUT
/settings/general/ to make sure both code paths agree.
"""

import time

import pytest
from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.apps import startup
from global_settings.models import GlobalSettings
from iam.models import Folder, User, UserGroup
from metrology.models import Dashboard


@pytest.fixture
def app_config():
    startup(sender=None, **{})


def _client_for(user):
    client = APIClient()
    token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def admin_client(app_config):
    admin = User.objects.create_superuser(
        "admin@default-dashboard-tests.com", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    return _client_for(admin)


@pytest.fixture
def non_admin_client(app_config):
    user = User.objects.create_user(
        email="user@default-dashboard-tests.com", is_published=True
    )
    return _client_for(user)


@pytest.fixture
def root_dashboard(app_config):
    return Dashboard.objects.create(
        name="Root Dashboard", folder=Folder.get_root_folder()
    )


SET_URL_NAME = "general-settings-set-default-dashboard"
LIST_URL_NAME = "general-settings-default-custom-analytics-dashboard"


@pytest.mark.django_db
class TestSetDefaultDashboardEndpoint:
    def test_admin_can_set_dashboard(self, admin_client, root_dashboard):
        url = reverse(SET_URL_NAME)
        resp = admin_client.post(
            url, {"dashboard_id": str(root_dashboard.id)}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.content
        assert resp.json()["default_custom_analytics_dashboard"] == str(
            root_dashboard.id
        )

        gs = GlobalSettings.objects.get(name="general")
        assert gs.value["default_custom_analytics_dashboard"] == str(root_dashboard.id)

    def test_admin_can_clear_dashboard(self, admin_client, root_dashboard):
        url = reverse(SET_URL_NAME)
        # First set, then clear
        admin_client.post(url, {"dashboard_id": str(root_dashboard.id)}, format="json")
        resp = admin_client.post(url, {"dashboard_id": ""}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["default_custom_analytics_dashboard"] is None

        gs = GlobalSettings.objects.get(name="general")
        assert gs.value["default_custom_analytics_dashboard"] is None

    def test_non_admin_gets_403(self, non_admin_client, root_dashboard):
        url = reverse(SET_URL_NAME)
        resp = non_admin_client.post(
            url, {"dashboard_id": str(root_dashboard.id)}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_uuid_returns_400(self, admin_client):
        url = reverse(SET_URL_NAME)
        resp = admin_client.post(url, {"dashboard_id": "not-a-uuid"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_dashboard_returns_400(self, admin_client):
        url = reverse(SET_URL_NAME)
        # Well-formed but unknown UUID
        resp = admin_client.post(
            url,
            {"dashboard_id": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_updated_at_advances(self, admin_client, root_dashboard):
        url = reverse(SET_URL_NAME)
        admin_client.post(url, {"dashboard_id": str(root_dashboard.id)}, format="json")
        gs1 = GlobalSettings.objects.get(name="general")
        first_updated = gs1.updated_at

        # Sleep a touch so the timestamp can advance — if update_fields ever drops
        # updated_at again this assertion will catch it.
        time.sleep(0.01)
        admin_client.post(url, {"dashboard_id": ""}, format="json")
        gs2 = GlobalSettings.objects.get(name="general")
        assert gs2.updated_at > first_updated


@pytest.mark.django_db
class TestDashboardListingEndpoint:
    def test_listing_returns_dashboards(self, admin_client, root_dashboard):
        url = reverse(LIST_URL_NAME)
        resp = admin_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        # Always includes the empty option
        assert "" in body
        assert str(root_dashboard.id) in body
        assert body[str(root_dashboard.id)] == "Root Dashboard"

    def test_listing_scoped_by_accessibility(self, non_admin_client, root_dashboard):
        # Non-admin can't see root-folder dashboards by default
        url = reverse(LIST_URL_NAME)
        resp = non_admin_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert str(root_dashboard.id) not in body


@pytest.mark.django_db
class TestSerializerValidationBranch:
    def test_put_with_invalid_uuid_returns_400(self, admin_client):
        # PUT /settings/general/ exercises GeneralSettingsSerializer.update
        # which routes invalid default_custom_analytics_dashboard through the
        # shared validator.
        url = "/api/settings/general/"
        resp = admin_client.put(
            url,
            {"value": {"default_custom_analytics_dashboard": "not-a-uuid"}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_put_with_valid_uuid(self, admin_client, root_dashboard):
        url = "/api/settings/general/"
        resp = admin_client.put(
            url,
            {"value": {"default_custom_analytics_dashboard": str(root_dashboard.id)}},
            format="json",
        )
        # GeneralSettings.PUT replaces the entire value dict, so this asserts
        # the validation passes; the side effect of wiping other keys is the
        # serializer's documented behavior (out of scope for this test).
        assert resp.status_code == status.HTTP_200_OK
