"""Service accounts: OAuth2 client_credentials via the allauth OIDC IdP.

Covers provisioning (User + Client + Role + RoleAssignment bundle), the
token flow against the real allauth token endpoint, RBAC scoping through
the SA's role assignment, lifecycle (deactivate/rotate/delete), and the
exclusion of SA artifacts from user-facing surfaces.
"""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from allauth.idp.oidc.models import Client, Token

from core.startup import startup
from django.contrib.auth.models import Permission
from global_settings.models import GlobalSettings
from iam.models import Folder, Role, RoleAssignment, ServiceAccount, User, UserGroup

TOKEN_ENDPOINT = "/api/identity/o/api/token"
SA_ENDPOINT = "/api/iam/service-accounts/"


@pytest.fixture
def app_config():
    startup(sender=None, **{})
    # The service accounts API is gated behind this feature flag (off by default).
    ff_settings, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    ff_settings.value = {**(ff_settings.value or {}), "service_accounts": True}
    ff_settings.save()


@pytest.fixture
def admin_client(app_config):
    admin = User.objects.create_superuser("admin@sa-tests.com", is_published=True)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def domain_folder(app_config):
    return Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="sa test domain",
        content_type=Folder.ContentType.DOMAIN,
    )


def _view_folder_permission_ids():
    return list(
        Permission.objects.filter(codename="view_folder").values_list("id", flat=True)
    )


def _create_sa(admin_client, domain_folder, name="reporter", is_recursive=False):
    response = admin_client.post(
        SA_ENDPOINT,
        {
            "name": name,
            "description": "test service account",
            "permissions": _view_folder_permission_ids(),
            "perimeter_folders": [str(domain_folder.id)],
            "is_recursive": is_recursive,
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()


def _fetch_token(client_id, client_secret):
    client = APIClient()
    return client.post(
        TOKEN_ENDPOINT,
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        format="multipart",
    )


def _bearer_client(access_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    return client


@pytest.mark.django_db
class TestServiceAccountProvisioning:
    def test_create_returns_secret_once_and_builds_bundle(
        self, admin_client, domain_folder
    ):
        payload = _create_sa(admin_client, domain_folder)
        assert payload["client_id"]
        assert payload["client_secret"]
        assert payload["is_active"] is True

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.client.check_secret(payload["client_secret"])
        assert sa.client.get_grant_types() == [Client.GrantType.CLIENT_CREDENTIALS]
        assert not sa.user.has_usable_password()
        assert set(sa.role.permissions.values_list("codename", flat=True)) == {
            "view_folder"
        }
        ra = sa.role_assignment
        assert ra is not None
        assert list(ra.perimeter_folders.all()) == [domain_folder]

        # secret never appears on subsequent reads
        detail = admin_client.get(f"{SA_ENDPOINT}{payload['id']}/").json()
        assert "client_secret" not in detail

    def test_create_requires_admin(self, app_config, domain_folder):
        user = User.objects.create_user(email="plain@sa-tests.com", password="x")
        client = APIClient()
        token = AuthToken.objects.create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
        response = client.post(
            SA_ENDPOINT,
            {
                "name": "nope",
                "permissions": _view_folder_permission_ids(),
                "perimeter_folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 403

    def test_create_rejects_ignored_permissions(self, admin_client, domain_folder):
        bad_permission = Permission.objects.filter(
            content_type__model="role", codename__startswith="view"
        ).first()
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "bad-perms",
                "permissions": [bad_permission.id],
                "perimeter_folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_api_requires_feature_flag(self, admin_client):
        ff_settings = GlobalSettings.objects.get(
            name=GlobalSettings.Names.FEATURE_FLAGS
        )
        ff_settings.value = {**(ff_settings.value or {}), "service_accounts": False}
        ff_settings.save()
        assert admin_client.get(SA_ENDPOINT).status_code == 403
        assert admin_client.get(f"{SA_ENDPOINT}permissions/").status_code == 403

    def test_permissions_catalog_excludes_ignored_models(self, admin_client):
        response = admin_client.get(f"{SA_ENDPOINT}permissions/")
        assert response.status_code == 200
        entries = response.json()
        codenames = {entry["codename"] for entry in entries}
        assert "view_folder" in codenames
        assert "viewFolder" in {entry["normalized_codename"] for entry in entries}
        assert not any(entry["codename"].endswith("_role") for entry in entries)
        assert not any("serviceaccount" in entry["codename"] for entry in entries)


@pytest.mark.django_db
class TestServiceAccountTokenFlow:
    def test_client_credentials_flow_and_scoped_access(
        self, admin_client, domain_folder
    ):
        payload = _create_sa(admin_client, domain_folder)
        response = _fetch_token(payload["client_id"], payload["client_secret"])
        assert response.status_code == 200, response.content
        access_token = response.json()["access_token"]

        token_row = Token.objects.get(client_id=payload["client_id"])
        assert token_row.user is None

        other_domain = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="unreachable domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        bearer = _bearer_client(access_token)
        response = bearer.get("/api/folders/")
        assert response.status_code == 200, response.content
        folder_ids = {row["id"] for row in response.json()["results"]}
        assert str(domain_folder.id) in folder_ids
        assert str(other_domain.id) not in folder_ids

        # read-only role: no write access anywhere
        response = bearer.post(
            "/api/folders/",
            {"name": "sa-created", "parent_folder": str(domain_folder.id)},
            format="json",
        )
        assert response.status_code == 403

    def test_wrong_secret_rejected(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        response = _fetch_token(payload["client_id"], "wrong-secret")
        assert response.status_code in (400, 401)

    def test_deactivate_blocks_issuance_and_revokes_tokens(
        self, admin_client, domain_folder
    ):
        payload = _create_sa(admin_client, domain_folder)
        access_token = _fetch_token(
            payload["client_id"], payload["client_secret"]
        ).json()["access_token"]

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/", {"is_active": False}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        # issuance blocked
        response = _fetch_token(payload["client_id"], payload["client_secret"])
        assert response.status_code in (400, 401)
        # outstanding token revoked
        response = _bearer_client(access_token).get("/api/folders/")
        assert response.status_code == 401

        # reactivate restores issuance
        admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/", {"is_active": True}, format="json"
        )
        response = _fetch_token(payload["client_id"], payload["client_secret"])
        assert response.status_code == 200

    def test_rotate_secret(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        old_secret = payload["client_secret"]
        old_token = _fetch_token(payload["client_id"], old_secret).json()[
            "access_token"
        ]

        response = admin_client.post(
            f"{SA_ENDPOINT}{payload['id']}/rotate-secret/", format="json"
        )
        assert response.status_code == 200
        new_secret = response.json()["client_secret"]
        assert new_secret != old_secret

        assert _fetch_token(payload["client_id"], old_secret).status_code in (400, 401)
        assert _fetch_token(payload["client_id"], new_secret).status_code == 200
        # rotation revoked the pre-rotation token
        assert _bearer_client(old_token).get("/api/folders/").status_code == 401

    def test_delete_tears_down_bundle(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        access_token = _fetch_token(
            payload["client_id"], payload["client_secret"]
        ).json()["access_token"]
        sa = ServiceAccount.objects.get(id=payload["id"])
        user_id, role_id, client_id = sa.user_id, sa.role_id, sa.client_id

        response = admin_client.delete(f"{SA_ENDPOINT}{payload['id']}/")
        assert response.status_code == 204

        assert not ServiceAccount.objects.filter(id=payload["id"]).exists()
        assert not Client.objects.filter(id=client_id).exists()
        assert not User.objects.filter(id=user_id).exists()
        assert not Role.objects.filter(id=role_id).exists()
        assert not RoleAssignment.objects.filter(user_id=user_id).exists()
        assert not Token.objects.filter(client_id=client_id).exists()
        assert _bearer_client(access_token).get("/api/folders/").status_code == 401


@pytest.mark.django_db
class TestServiceAccountExclusions:
    def test_sa_user_hidden_from_users_and_editors(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        sa = ServiceAccount.objects.get(id=payload["id"])

        response = admin_client.get("/api/users/")
        emails = {row["email"] for row in response.json()["results"]}
        assert sa.user.email not in emails

        assert sa.user not in User.get_editors()

    def test_update_permissions_and_folders(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        new_folder = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="second domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        perm_ids = list(
            Permission.objects.filter(
                codename__in=["view_folder", "view_perimeter"]
            ).values_list("id", flat=True)
        )
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {
                "permissions": perm_ids,
                "perimeter_folders": [str(new_folder.id)],
                "is_recursive": True,
            },
            format="json",
        )
        assert response.status_code == 200, response.content

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert set(sa.role.permissions.values_list("codename", flat=True)) == {
            "view_folder",
            "view_perimeter",
        }
        ra = sa.role_assignment
        assert list(ra.perimeter_folders.all()) == [new_folder]
        assert ra.is_recursive is True

        # effective access follows the update
        access_token = _fetch_token(
            payload["client_id"], payload["client_secret"]
        ).json()["access_token"]
        response = _bearer_client(access_token).get("/api/folders/")
        folder_ids = {row["id"] for row in response.json()["results"]}
        assert str(new_folder.id) in folder_ids
        assert str(domain_folder.id) not in folder_ids
