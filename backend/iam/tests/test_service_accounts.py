"""Service accounts: provisioning, token flow, RBAC scoping, and lifecycle."""

from datetime import timedelta

import pytest
from django.test import override_settings
from knox.models import AuthToken
from rest_framework.test import APIClient

from allauth.idp.oidc.models import Client, Token

from core.startup import startup
from django.contrib.auth.models import Permission
from django.utils import timezone
from global_settings import utils as ff_utils
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import Folder, Role, RoleAssignment, ServiceAccount, User, UserGroup
from iam.service_accounts import get_selectable_permissions

TOKEN_ENDPOINT = "/api/identity/o/api/token"
SA_ENDPOINT = "/api/iam/service-accounts/"


@pytest.fixture(autouse=True)
def _enterprise_flags(monkeypatch):
    """service_accounts is enterprise-only (declared on the EE
    FeatureFlagsSerializer, hence unsupported on CE); these tests exercise
    the EE-gated behavior from the CE test bed."""
    supported = ff_utils.get_supported_feature_flags() | {"service_accounts"}
    monkeypatch.setattr(ff_utils, "get_supported_feature_flags", lambda: supported)


@pytest.fixture
def app_config():
    startup(sender=None, **{})
    # The service accounts API is gated behind this feature flag (off by default).
    ff_settings, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    ff_settings.value = {**(ff_settings.value or {}), "service_accounts": True}
    ff_settings.save()
    # Direct ORM write: bypasses the serializer, the single invalidation point.
    clear_feature_flags_cache()


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
            "folders": [str(domain_folder.id)],
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

        # secret is prefixed, and only a short, non-reversible preview is persisted
        assert payload["client_secret"].startswith(ServiceAccount.SECRET_PREFIX)
        assert sa.secret_preview == payload["secret_preview"]
        assert sa.secret_preview.startswith(
            payload["client_secret"][: len(ServiceAccount.SECRET_PREFIX) + 3]
        )
        assert sa.secret_preview != payload["client_secret"]

        # secret never appears on subsequent reads
        detail = admin_client.get(f"{SA_ENDPOINT}{payload['id']}/").json()
        assert "client_secret" not in detail
        assert detail["secret_preview"] == sa.secret_preview

    def test_is_recursive_defaults_to_true(self, admin_client, domain_folder):
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "default-recursive",
                "permissions": _view_folder_permission_ids(),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        assert response.json()["is_recursive"] is True

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
                "folders": [str(domain_folder.id)],
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
                "folders": [str(domain_folder.id)],
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
        clear_feature_flags_cache()
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

    def test_builtin_roles_lists_selectable_permissions_only(self, admin_client):
        response = admin_client.get(f"{SA_ENDPOINT}roles/")
        assert response.status_code == 200
        roles = response.json()
        assert roles
        names = {r["name"] for r in roles}
        assert any("permissions" in r for r in roles)
        assert all(isinstance(r["permissions"], list) for r in roles)

        all_ids = {p for r in roles for p in r["permissions"]}
        selectable_ids = set(get_selectable_permissions().values_list("id", flat=True))
        assert all_ids <= selectable_ids
        assert names  # at least the seeded builtin roles are present

    def test_create_rejects_duplicate_name(self, admin_client, domain_folder):
        _create_sa(admin_client, domain_folder, name="dup-name")
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "dup-name",
                "permissions": _view_folder_permission_ids(),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_create_rejects_name_over_100_chars(self, admin_client, domain_folder):
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "x" * 101,
                "permissions": _view_folder_permission_ids(),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_rename_to_own_name_is_allowed(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder, name="keep-name")
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"name": "keep-name"},
            format="json",
        )
        assert response.status_code == 200

    def test_rename_to_other_account_name_rejected(self, admin_client, domain_folder):
        _create_sa(admin_client, domain_folder, name="taken-name")
        payload = _create_sa(admin_client, domain_folder, name="renamable")
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"name": "taken-name"},
            format="json",
        )
        assert response.status_code == 400


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
        rotate_payload = response.json()
        new_secret = rotate_payload["client_secret"]
        assert new_secret != old_secret

        # preview is refreshed to reflect the new secret
        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.secret_preview == rotate_payload["secret_preview"]
        assert sa.secret_preview != payload["secret_preview"]

        assert _fetch_token(payload["client_id"], old_secret).status_code in (400, 401)
        assert _fetch_token(payload["client_id"], new_secret).status_code == 200
        # rotation revoked the pre-rotation token
        assert _bearer_client(old_token).get("/api/folders/").status_code == 401

    def test_rotate_secret_with_grace_period(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        old_secret = payload["client_secret"]

        response = admin_client.post(
            f"{SA_ENDPOINT}{payload['id']}/rotate-secret/",
            {"grace_period_days": 1},
            format="json",
        )
        assert response.status_code == 200
        new_secret = response.json()["client_secret"]

        # both secrets mint tokens during the grace period
        assert _fetch_token(payload["client_id"], old_secret).status_code == 200
        assert _fetch_token(payload["client_id"], new_secret).status_code == 200

        sa = ServiceAccount.objects.get(id=payload["id"])
        sa.previous_secret_expires_at = timezone.now() - timedelta(seconds=1)
        sa.save(update_fields=["previous_secret_expires_at"])

        # old secret rejected once the grace period has elapsed
        assert _fetch_token(payload["client_id"], old_secret).status_code in (400, 401)
        assert _fetch_token(payload["client_id"], new_secret).status_code == 200

    def test_rotate_secret_grace_period_within_a_week_allowed(
        self, admin_client, domain_folder
    ):
        payload = _create_sa(admin_client, domain_folder)
        response = admin_client.post(
            f"{SA_ENDPOINT}{payload['id']}/rotate-secret/",
            {"grace_period_days": 7},
            format="json",
        )
        assert response.status_code == 200, response.content

    def test_rotate_secret_grace_period_capped(self, admin_client, domain_folder):
        from iam.views import MAX_GRACE_PERIOD_DAYS

        payload = _create_sa(admin_client, domain_folder)
        response = admin_client.post(
            f"{SA_ENDPOINT}{payload['id']}/rotate-secret/",
            {"grace_period_days": MAX_GRACE_PERIOD_DAYS + 1},
            format="json",
        )
        assert response.status_code == 400

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

    def test_sa_user_hidden_from_actor_pickers(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        sa = ServiceAccount.objects.get(id=payload["id"])

        response = admin_client.get("/api/actors/")
        assert response.status_code == 200
        names = {row["str"] for row in response.json()["results"]}
        assert sa.user.email not in names
        # regular user actors are unaffected by the exclusion
        assert "admin@sa-tests.com" in names

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
                "folders": [str(new_folder.id)],
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

    def test_update_permissions_to_empty_is_allowed(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        access_token = _fetch_token(
            payload["client_id"], payload["client_secret"]
        ).json()["access_token"]

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"permissions": []},
            format="json",
        )
        assert response.status_code == 200, response.content

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.role.permissions.count() == 0

        # still authenticates (not deactivated) but has no RBAC grants left
        assert (
            _fetch_token(payload["client_id"], payload["client_secret"]).status_code
            == 200
        )
        response = _bearer_client(access_token).get("/api/folders/")
        assert response.status_code == 200
        assert response.json()["results"] == []


@pytest.mark.django_db
class TestServiceAccountExpiry:
    def test_create_with_expiry_date(self, admin_client, domain_folder):
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "expiring",
                "permissions": _view_folder_permission_ids(),
                "folders": [str(domain_folder.id)],
                "expiry_date": "2099-01-01",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        assert response.json()["expiry_date"] == "2099-01-01"

    def test_update_sets_and_clears_expiry_date(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        assert payload["expiry_date"] is None

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"expiry_date": "2099-01-01"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["expiry_date"] == "2099-01-01"

        # a partial update that omits expiry_date leaves it untouched
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"description": "still expiring"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["expiry_date"] == "2099-01-01"

        # explicitly sending null clears it
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"expiry_date": None},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["expiry_date"] is None

    def test_update_sets_and_clears_description(self, admin_client, domain_folder):
        payload = _create_sa(admin_client, domain_folder)
        assert payload["description"] == "test service account"

        # a partial update that omits description leaves it untouched
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"name": payload["name"]},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["description"] == "test service account"

        # explicitly sending null clears it
        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"description": None},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["description"] is None

    def test_expired_service_account_is_deactivated_by_periodic_task(
        self, admin_client, domain_folder
    ):
        from datetime import date, timedelta as td

        from core.tasks import deactivate_expired_service_accounts

        payload = _create_sa(admin_client, domain_folder)
        access_token = _fetch_token(
            payload["client_id"], payload["client_secret"]
        ).json()["access_token"]

        sa = ServiceAccount.objects.get(id=payload["id"])
        sa.expiry_date = date.today() - td(days=1)
        sa.save(update_fields=["expiry_date"])

        deactivate_expired_service_accounts.call_local()

        sa.refresh_from_db()
        assert sa.is_active is False
        # deactivate() semantics: grant types revoked, outstanding tokens gone
        assert sa.client.get_grant_types() == []
        assert _fetch_token(
            payload["client_id"], payload["client_secret"]
        ).status_code in (
            400,
            401,
        )
        assert _bearer_client(access_token).get("/api/folders/").status_code == 401

    def test_future_expiry_date_not_deactivated(self, admin_client, domain_folder):
        from datetime import date, timedelta as td

        from core.tasks import deactivate_expired_service_accounts

        payload = _create_sa(admin_client, domain_folder)
        sa = ServiceAccount.objects.get(id=payload["id"])
        sa.expiry_date = date.today() + td(days=1)
        sa.save(update_fields=["expiry_date"])

        deactivate_expired_service_accounts.call_local()

        sa.refresh_from_db()
        assert sa.is_active is True

    def test_periodic_task_isolates_per_account_failures(
        self, admin_client, domain_folder
    ):
        from datetime import date, timedelta as td
        from unittest.mock import patch

        from core.tasks import deactivate_expired_service_accounts
        from iam.models import ServiceAccount as SAModel

        payload_broken = _create_sa(admin_client, domain_folder, name="broken")
        payload_ok = _create_sa(admin_client, domain_folder, name="ok")

        for payload in (payload_broken, payload_ok):
            sa = ServiceAccount.objects.get(id=payload["id"])
            sa.expiry_date = date.today() - td(days=1)
            sa.save(update_fields=["expiry_date"])

        original_deactivate = SAModel.deactivate

        def flaky_deactivate(self):
            if str(self.id) == payload_broken["id"]:
                raise RuntimeError("boom")
            return original_deactivate(self)

        with patch.object(SAModel, "deactivate", flaky_deactivate):
            deactivate_expired_service_accounts.call_local()

        broken = ServiceAccount.objects.get(id=payload_broken["id"])
        ok = ServiceAccount.objects.get(id=payload_ok["id"])
        # the failing account's exception doesn't abort the loop
        assert ok.is_active is False
        # ...and doesn't leave the failing one silently marked inactive either
        assert broken.is_active is True


@pytest.mark.django_db
class TestServiceAccountRoleLinked:
    def _reader_role(self):
        return Role.objects.get(name="BI-RL-AUD", builtin=True)

    def test_create_with_role_links_live_permissions(self, admin_client, domain_folder):
        role = self._reader_role()
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "role-linked",
                "role": str(role.id),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        payload = response.json()
        assert payload["is_role_linked"] is True
        assert payload["role_name"]

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.role_id == role.id

        # a permission added to the shared role afterwards is immediately reflected;
        extra_perm = Permission.objects.get(codename="add_perimeter")
        assert not role.permissions.filter(id=extra_perm.id).exists()
        role.permissions.add(extra_perm)
        detail = admin_client.get(f"{SA_ENDPOINT}{payload['id']}/").json()
        codenames = {p["codename"] for p in detail["permissions"]}
        assert "add_perimeter" in codenames

    def test_create_rejects_role_and_permissions_together(
        self, admin_client, domain_folder
    ):
        role = self._reader_role()
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "both-given",
                "role": str(role.id),
                "permissions": _view_folder_permission_ids(),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_create_rejects_neither_role_nor_permissions(
        self, admin_client, domain_folder
    ):
        response = admin_client.post(
            SA_ENDPOINT,
            {"name": "neither-given", "folders": [str(domain_folder.id)]},
            format="json",
        )
        assert response.status_code == 400

    def test_create_rejects_non_builtin_role(self, admin_client, domain_folder):
        custom_role = Role.objects.create(
            name="not-builtin", folder=Folder.get_root_folder()
        )
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "custom-role-rejected",
                "role": str(custom_role.id),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_update_with_different_permissions_detaches_to_a_dedicated_role(
        self, admin_client, domain_folder
    ):
        role = self._reader_role()
        create_response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "role-linked-2",
                "role": str(role.id),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        payload = create_response.json()
        new_permission_ids = _view_folder_permission_ids()

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"permissions": new_permission_ids},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["is_role_linked"] is False

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert not sa.role.builtin
        assert sa.role_id != role.id
        assert set(sa.role.permissions.values_list("id", flat=True)) == set(
            new_permission_ids
        )
        # the shared builtin role itself is untouched
        assert Role.objects.get(id=role.id, builtin=True).permissions.exists()

    def test_update_tolerates_resubmitting_the_roles_own_permissions(
        self, admin_client, domain_folder
    ):
        role = self._reader_role()
        create_response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "role-linked-3",
                "role": str(role.id),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        payload = create_response.json()
        current_permission_ids = list(role.permissions.values_list("id", flat=True))

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"name": "role-linked-3-renamed", "permissions": current_permission_ids},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["name"] == "role-linked-3-renamed"

    def test_update_can_switch_a_dedicated_account_to_role_linked(
        self, admin_client, domain_folder
    ):
        role = self._reader_role()
        payload = _create_sa(admin_client, domain_folder, name="dedicated-role")
        old_role_id = ServiceAccount.objects.get(id=payload["id"]).role_id

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"role": str(role.id)},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["is_role_linked"] is True

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.role_id == role.id
        assert not Role.objects.filter(id=old_role_id).exists()

    def test_update_tolerates_a_stray_empty_permissions_list_alongside_role(
        self, admin_client, domain_folder
    ):
        role = self._reader_role()
        payload = _create_sa(admin_client, domain_folder, name="dedicated-role-2")

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"role": str(role.id), "permissions": []},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["is_role_linked"] is True

    def test_update_tolerates_a_stray_empty_permissions_list_without_role(
        self, admin_client, domain_folder
    ):
        role = self._reader_role()
        create_response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "role-linked-stray-perms",
                "role": str(role.id),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        payload = create_response.json()

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"permissions": []},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["is_role_linked"] is True

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.role_id == role.id

    def test_update_can_switch_between_two_builtin_roles(
        self, admin_client, domain_folder
    ):
        reader = self._reader_role()
        approver = Role.objects.get(name="BI-RL-APP", builtin=True)
        create_response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "role-linked-4",
                "role": str(reader.id),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        payload = create_response.json()

        response = admin_client.patch(
            f"{SA_ENDPOINT}{payload['id']}/",
            {"role": str(approver.id)},
            format="json",
        )
        assert response.status_code == 200, response.content

        sa = ServiceAccount.objects.get(id=payload["id"])
        assert sa.role_id == approver.id
        assert Role.objects.filter(id=reader.id, builtin=True).exists()

    def test_delete_does_not_delete_shared_role(self, admin_client, domain_folder):
        role = self._reader_role()
        create_response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "role-linked-delete",
                "role": str(role.id),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        payload = create_response.json()
        response = admin_client.delete(f"{SA_ENDPOINT}{payload['id']}/")
        assert response.status_code == 204
        assert Role.objects.filter(id=role.id, builtin=True).exists()

    def test_role_assignment_exclusion_is_scoped_to_the_sa_user_not_the_role(
        self, admin_client, domain_folder
    ):
        """RoleAssignmentViewSet excludes SA-owned assignments by user, not by
        role, so a human sharing a role with a role-linked SA stays visible."""
        role = self._reader_role()
        human = User.objects.create_user(
            email="human-reader@sa-tests.com", password="x"
        )
        human_assignment = RoleAssignment.objects.create(
            user=human, role=role, folder=Folder.get_root_folder()
        )
        human_assignment.perimeter_folders.set([domain_folder])

        create_response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "role-linked-shared",
                "role": str(role.id),
                "folders": [str(domain_folder.id)],
            },
            format="json",
        )
        sa = ServiceAccount.objects.get(id=create_response.json()["id"])

        visible_ids = set(
            RoleAssignment.objects.exclude(
                user__service_account__isnull=False
            ).values_list("id", flat=True)
        )
        assert human_assignment.id in visible_ids
        assert sa.role_assignment.id not in visible_ids


@pytest.mark.django_db
class TestServiceAccountGlobalAdmin:
    """The explicit global-admin case: BI-RL-ADM linked with the Global folder,
    recursive. The API does not enforce this shape (admins can grant anything
    via custom permissions anyway) — the frontend steers it via the roles
    catalog's global_only flag and the read serializer's is_global_admin."""

    def _admin_role(self):
        return Role.objects.get(name="BI-RL-ADM", builtin=True)

    def test_global_admin_sa_reads_into_domains(self, admin_client, domain_folder):
        response = admin_client.post(
            SA_ENDPOINT,
            {
                "name": "global-admin-bot",
                "role": str(self._admin_role().id),
                "folders": [str(Folder.get_root_folder().id)],
                "is_recursive": True,
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        payload = response.json()
        assert payload["is_global_admin"] is True
        assert payload["is_role_linked"] is True

        access_token = _fetch_token(
            payload["client_id"], payload["client_secret"]
        ).json()["access_token"]
        response = _bearer_client(access_token).get("/api/folders/")
        assert response.status_code == 200, response.content
        folder_ids = {row["id"] for row in response.json()["results"]}
        assert str(domain_folder.id) in folder_ids

    def test_builtin_roles_endpoint_flags_administrator_as_global_only(
        self, admin_client
    ):
        response = admin_client.get(f"{SA_ENDPOINT}roles/")
        assert response.status_code == 200
        roles = response.json()
        global_only_ids = {r["id"] for r in roles if r["global_only"]}
        assert global_only_ids == {str(self._admin_role().id)}


QUOTA_SETTINGS = dict(
    LICENSE_SEATS=1,
    MODULE_PATHS={"serializers": "iam.tests.ee_stub_serializers"},
)


@pytest.mark.django_db
class TestServiceAccountSeatQuota:
    """The enterprise build layers "active service accounts <= licensed seats"
    onto the community viewset by shadowing the write serializer through
    MODULE_PATHS (see enterprise_core.serializers). CE stays uncapped: these
    tests exercise the seam with an EE-shaped stub."""

    def test_ce_default_is_uncapped(self, admin_client, domain_folder):
        _create_sa(admin_client, domain_folder, name="bot-1")
        _create_sa(admin_client, domain_folder, name="bot-2")

    def test_create_blocked_at_quota(self, admin_client, domain_folder):
        with override_settings(**QUOTA_SETTINGS):
            _create_sa(admin_client, domain_folder, name="only-bot")
            response = admin_client.post(
                SA_ENDPOINT,
                {
                    "name": "one-too-many",
                    "permissions": _view_folder_permission_ids(),
                    "folders": [str(domain_folder.id)],
                },
                format="json",
            )
            assert response.status_code == 400
            assert response.json()["error"] == ["errorServiceAccountSeatsExceeded"]

    def test_deactivation_frees_the_slot_and_reactivation_is_gated(
        self, admin_client, domain_folder
    ):
        with override_settings(**QUOTA_SETTINGS):
            first = _create_sa(admin_client, domain_folder, name="first-bot")
            # deactivating is always allowed, and frees the slot
            response = admin_client.patch(
                f"{SA_ENDPOINT}{first['id']}/", {"is_active": False}, format="json"
            )
            assert response.status_code == 200

            second = _create_sa(admin_client, domain_folder, name="second-bot")
            assert second["is_active"] is True

            # the slot is taken again: reactivating the first is refused
            response = admin_client.patch(
                f"{SA_ENDPOINT}{first['id']}/", {"is_active": True}, format="json"
            )
            assert response.status_code == 400
            assert response.json()["error"] == ["errorServiceAccountSeatsExceeded"]

            # updates that do not activate stay allowed on the inactive account
            response = admin_client.patch(
                f"{SA_ENDPOINT}{first['id']}/",
                {"description": "still editable"},
                format="json",
            )
            assert response.status_code == 200, response.content
