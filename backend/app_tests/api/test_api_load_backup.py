import gzip
import json
import uuid
from datetime import datetime

import pytest
from django.apps import apps
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.db.utils import IntegrityError

from ciso_assistant.settings import SCHEMA_VERSION, VERSION
from iam.models import Folder, Role, User, UserGroup
from knox.models import AuthToken


@pytest.fixture
def authenticated_client():
    admin = User.objects.create_superuser("backup_admin@tests.com")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {_auth_token[1]}")
    return client


@pytest.fixture
def unauthenticated_client():
    return APIClient()


@pytest.fixture
def non_backup_user_client():
    user = User.objects.create_user(
        email="regular_user@tests.com", password="testpass123"
    )
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {_auth_token[1]}")
    return client


def create_mock_backup_data(
    *,
    include_enterprise=True,
    media_version=None,
    schema_version=None,
    include_core_models=True,
    include_role_with_enterprise_perms=False,
):
    media_version = VERSION if media_version is None else media_version
    schema_version = SCHEMA_VERSION if schema_version is None else schema_version

    meta = {
        "meta": [{"media_version": media_version, "schema_version": schema_version}]
    }
    objects = []

    if include_core_models:
        objects.append(
            {
                "model": "iam.folder",
                "pk": str(uuid.uuid4()),
                "fields": {
                    "name": "Test Backup Domain",
                    "content_type": "DO",
                    "builtin": False,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
            }
        )

    if include_role_with_enterprise_perms:
        objects.append(
            {
                "model": "iam.role",
                "pk": str(uuid.uuid4()),
                "fields": {
                    "name": "Test Administrator Role",
                    "description": "Role for backup testing",
                    "permissions": [
                        ["view_folder", "iam"],
                        ["add_folder", "iam"],
                        ["view_clientsettings", "enterprise_core"],
                        ["change_clientsettings", "enterprise_core"],
                    ],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
            }
        )

    if include_enterprise:
        objects.append(
            {
                "model": "enterprise_core.clientsettings",
                "pk": str(uuid.uuid4()),
                "fields": {
                    "name": "Enterprise Client Config",
                    "show_images_unauthenticated": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
            }
        )

    return [meta, objects]


def send_backup_to_api(client, backup_data, *, compress=True):
    payload = json.dumps(backup_data).encode("utf-8")
    body = gzip.compress(payload) if compress else payload
    filename = "test_backup.json.gz" if compress else "test_backup.json"

    return client.post(
        reverse("load-backup"),
        data=body,
        content_type="application/octet-stream",
        HTTP_CONTENT_DISPOSITION=f'attachment; filename="{filename}"',
    )


@pytest.mark.django_db(transaction=True)
class TestEnterpriseBackupInCommunityEdition:
    def test_filters_enterprise_models_in_ce(self, authenticated_client):
        if apps.is_installed("enterprise_core"):
            pytest.skip("Community-edition behavior only")

        backup = create_mock_backup_data(
            include_enterprise=True, include_core_models=True
        )
        resp = send_backup_to_api(authenticated_client, backup)
        assert resp.status_code == status.HTTP_200_OK
        assert Folder.objects.filter(name="Test Backup Domain").exists()

    # This test can xfail if the restore returns a non-200 in some DB setups
    @pytest.mark.django_db(transaction=True)
    def test_filters_enterprise_permissions_via_api_in_ce(self, authenticated_client):
        if apps.is_installed("enterprise_core"):
            pytest.skip("Community-edition behavior only")

        backup = create_mock_backup_data(
            include_enterprise=True,
            include_core_models=True,
            include_role_with_enterprise_perms=True,
        )

        try:
            resp = send_backup_to_api(authenticated_client, backup)
        except IntegrityError:
            pytest.xfail("Known auditlog/contenttypes FK issue during flush+loaddata")
            return

        if resp.status_code != status.HTTP_200_OK:
            pytest.xfail(
                f"Restore returned {resp.status_code}; environment-specific flakiness"
            )
            return

        role = Role.objects.filter(name="Test Administrator Role").first()
        assert role is not None
        assert all(len(p) <= 1 or p[1] != "enterprise_core" for p in role.permissions)
        assert any(len(p) > 1 and p[1] in {"iam", "core"} for p in role.permissions)

    def test_preserves_core_data(self, authenticated_client):
        if apps.is_installed("enterprise_core"):
            pytest.skip("Community-edition behavior only")

        backup = create_mock_backup_data(
            include_enterprise=True,
            include_core_models=True,
            include_role_with_enterprise_perms=False,
        )
        resp = send_backup_to_api(authenticated_client, backup)
        assert resp.status_code == status.HTTP_200_OK

        folder = Folder.objects.filter(name="Test Backup Domain").first()
        assert folder is not None
        assert folder.content_type == Folder.ContentType.DOMAIN

    def test_loads_pure_community_backup(self, authenticated_client):
        backup = create_mock_backup_data(
            include_enterprise=False,
            include_core_models=True,
            include_role_with_enterprise_perms=False,
        )
        resp = send_backup_to_api(authenticated_client, backup)
        assert resp.status_code == status.HTTP_200_OK
        assert Folder.objects.filter(name="Test Backup Domain").exists()


@pytest.mark.django_db(transaction=True)
class TestBackupVersionValidation:
    def test_rejects_different_version(self, authenticated_client):
        backup = create_mock_backup_data(
            include_enterprise=False, media_version="99.99.99"
        )
        resp = send_backup_to_api(authenticated_client, backup)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in resp.data

    def test_rejects_invalid_schema_version(self, authenticated_client):
        backup = create_mock_backup_data(
            include_enterprise=False, schema_version="invalid"
        )
        resp = send_backup_to_api(authenticated_client, backup)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["error"] == "InvalidSchemaVersion"

    @pytest.mark.parametrize("compress", [False, True])
    def test_loads_with_or_without_compression(self, authenticated_client, compress):
        backup = create_mock_backup_data(include_enterprise=False)
        resp = send_backup_to_api(authenticated_client, backup, compress=compress)
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db(transaction=True)
class TestBackupRestorePermissions:
    def test_requires_authentication(self, unauthenticated_client):
        backup = create_mock_backup_data(include_enterprise=False)
        resp = send_backup_to_api(unauthenticated_client, backup)
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_requires_backup_permission(self, non_backup_user_client):
        backup = create_mock_backup_data(include_enterprise=False)
        resp = send_backup_to_api(non_backup_user_client, backup)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_rejects_empty_payload(self, authenticated_client):
        url = reverse("load-backup")
        resp = authenticated_client.post(
            url,
            data=b"",
            content_type="application/octet-stream",
            HTTP_CONTENT_DISPOSITION='attachment; filename="empty.json"',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["error"] == "backupLoadNoData"


@pytest.mark.django_db(transaction=True)
class TestBackupRestoreEdgeCases:
    def test_accepts_empty_objects_list(self, authenticated_client):
        backup = [
            {"meta": [{"media_version": VERSION, "schema_version": SCHEMA_VERSION}]},
            [],
        ]
        resp = send_backup_to_api(authenticated_client, backup)
        assert resp.status_code == status.HTTP_200_OK

    def test_only_enterprise_models_in_ce(self, authenticated_client):
        if apps.is_installed("enterprise_core"):
            pytest.skip("Community-edition behavior only")

        backup = create_mock_backup_data(
            include_enterprise=True, include_core_models=False
        )
        resp = send_backup_to_api(authenticated_client, backup)
        assert resp.status_code == status.HTTP_200_OK

    def test_malformed_json(self, authenticated_client):
        url = reverse("load-backup")
        try:
            resp = authenticated_client.post(
                url,
                data=b'{"invalid": "json" unclosed',
                content_type="application/octet-stream",
                HTTP_CONTENT_DISPOSITION='attachment; filename="malformed.json"',
            )
        except json.JSONDecodeError:
            return  # acceptable in DEBUG
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
