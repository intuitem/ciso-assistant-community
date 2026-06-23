"""Security regression tests for SCIM 2.0 provisioning and IdP-group inheritance.

These pin the invariants added to harden the feature for release:
  * SCIM only reads/mutates the accounts it provisioned (scim_external_id set),
    and never adopts or rewrites an administrator / local-login account.
  * Only SCIM-managed users can be pulled into an IdP group, so a locally
    managed admin can never inherit admin via a SCIM membership push.
  * SCIM cannot deactivate the last active administrator.
  * IdP-group role inheritance is gated behind the idp_groups feature flag.
"""

import json

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from global_settings.models import GlobalSettings
from iam.cache_builders import invalidate_assignments_cache, invalidate_groups_cache
from iam.models import IdPGroup, SCIMToken, User, UserGroup

USERS_URL = "/api/scim/v2/Users"
GROUPS_URL = "/api/scim/v2/Groups"


def _set_idp_groups_flag(enabled: bool):
    ff, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    ff.value = {**(ff.value or {}), "idp_groups": enabled}
    ff.save()
    # The groups cache bakes the flag in at build time.
    invalidate_groups_cache()
    invalidate_assignments_cache()


@pytest.fixture
def enable_idp_groups(app_config):
    _set_idp_groups_flag(True)


def _scim_client():
    """A client authenticated with a genuine SCIM bearer token (Knox token
    wrapped in a SCIMToken). The owner is a non-admin so it does not affect
    admin-count assertions."""
    owner = User.objects.create_user("scim-bot@tests.com", is_published=True)
    instance, token = AuthToken.objects.create(user=owner)
    SCIMToken.objects.create(auth_token=instance, name="test")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _scim_user(email, external_id):
    # create_user only persists a whitelist of fields, so set the SCIM marker
    # explicitly to mark the account as SCIM-managed.
    user = User.objects.create_user(email, is_published=True)
    user.scim_external_id = external_id
    user.save(update_fields=["scim_external_id"])
    return user


def _admin_group():
    return UserGroup.objects.get(name="BI-UG-ADM")


@pytest.mark.django_db
class TestSCIMAuthentication:
    def test_unauthenticated_is_rejected(self, enable_idp_groups):
        assert APIClient().get(USERS_URL).status_code == 401

    def test_non_scim_token_is_rejected(self, enable_idp_groups):
        # A valid Knox token that is NOT a SCIM token must not reach SCIM.
        user = User.objects.create_user("plain@tests.com", is_published=True)
        _, token = AuthToken.objects.create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        assert client.get(USERS_URL).status_code == 403

    def test_flag_off_is_forbidden(self, app_config):
        _set_idp_groups_flag(False)
        assert _scim_client().get(USERS_URL).status_code == 403


@pytest.mark.django_db
class TestSCIMOwnershipInvariant:
    def test_list_returns_only_scim_managed_users(self, enable_idp_groups):
        _scim_user("provisioned@tests.com", "ext-1")
        User.objects.create_user("local@tests.com", is_published=True)  # not SCIM
        resp = _scim_client().get(USERS_URL)
        assert resp.status_code == 200
        emails = {r["userName"] for r in json.loads(resp.content)["Resources"]}
        assert emails == {"provisioned@tests.com"}

    def test_create_refuses_to_adopt_an_admin(self, enable_idp_groups):
        admin = User.objects.create_user("boss@tests.com", is_published=True)
        _admin_group().user_set.add(admin)
        resp = _scim_client().post(
            USERS_URL,
            data={"userName": "boss@tests.com", "active": False},
            format="json",
        )
        assert resp.status_code == 409
        admin.refresh_from_db()
        assert admin.is_active is True
        assert admin.scim_external_id is None

    def test_create_refuses_to_adopt_a_local_login_account(self, enable_idp_groups):
        User.objects.create_user(
            "keeplocal@tests.com", is_published=True, keep_local_login=True
        )
        resp = _scim_client().post(
            USERS_URL, data={"userName": "keeplocal@tests.com"}, format="json"
        )
        assert resp.status_code == 409

    def test_create_adopts_a_plain_local_account(self, enable_idp_groups):
        User.objects.create_user("joiner@tests.com", is_published=True)
        resp = _scim_client().post(
            USERS_URL,
            data={"userName": "joiner@tests.com", "externalId": "ext-99"},
            format="json",
        )
        assert resp.status_code == 200
        adopted = User.objects.get(email="joiner@tests.com")
        assert adopted.scim_external_id == "ext-99"

    def test_cannot_patch_a_non_scim_user(self, enable_idp_groups):
        local = User.objects.create_user("local@tests.com", is_published=True)
        resp = _scim_client().patch(
            f"{USERS_URL}/{local.id}",
            data={"Operations": [{"op": "replace", "path": "active", "value": False}]},
            format="json",
        )
        assert resp.status_code == 404
        local.refresh_from_db()
        assert local.is_active is True


@pytest.mark.django_db
class TestSCIMGroupMembershipEscalation:
    def test_non_scim_user_cannot_be_added_to_a_group(self, enable_idp_groups):
        local_admin = User.objects.create_user("victim@tests.com", is_published=True)
        resp = _scim_client().post(
            GROUPS_URL,
            data={
                "displayName": "engineers",
                "members": [{"value": str(local_admin.id)}],
            },
            format="json",
        )
        assert resp.status_code == 201
        idp_group = IdPGroup.objects.get(name="engineers")
        # The locally-managed user is dropped: it never becomes a member.
        assert idp_group.users.count() == 0

    def test_scim_user_inherits_admin_via_mapped_group(self, enable_idp_groups):
        member = _scim_user("eng@tests.com", "ext-eng")
        idp_group = IdPGroup.objects.create(name="admins-idp")
        idp_group.user_groups.add(_admin_group())  # admin maps the group
        resp = _scim_client().patch(
            f"{GROUPS_URL}/{idp_group.id}",
            data={
                "Operations": [
                    {
                        "op": "add",
                        "path": "members",
                        "value": [{"value": str(member.id)}],
                    }
                ]
            },
            format="json",
        )
        assert resp.status_code == 200
        assert idp_group.users.filter(pk=member.pk).exists()
        assert member.is_admin() is True


@pytest.mark.django_db
class TestSCIMLastAdminGuard:
    def test_cannot_deactivate_the_last_admin(self, enable_idp_groups):
        admin = _scim_user("solo-admin@tests.com", "ext-solo")
        _admin_group().user_set.add(admin)
        resp = _scim_client().delete(f"{USERS_URL}/{admin.id}")
        assert resp.status_code == 409
        admin.refresh_from_db()
        assert admin.is_active is True

    def test_can_deactivate_a_non_last_admin(self, enable_idp_groups):
        a = _scim_user("admin-a@tests.com", "ext-a")
        b = _scim_user("admin-b@tests.com", "ext-b")
        _admin_group().user_set.add(a, b)
        resp = _scim_client().delete(f"{USERS_URL}/{a.id}")
        assert resp.status_code == 204
        a.refresh_from_db()
        assert a.is_active is False


@pytest.mark.django_db
class TestIdPGroupsFlagGating:
    def test_flag_toggle_revokes_inherited_admin(self, app_config):
        _set_idp_groups_flag(True)
        member = _scim_user("inherits@tests.com", "ext-i")
        idp_group = IdPGroup.objects.create(name="admins-idp")
        idp_group.user_groups.add(_admin_group())
        idp_group.users.add(member)
        assert member.is_admin() is True
        assert member in User.get_admin_users()

        _set_idp_groups_flag(False)
        assert member.is_admin() is False
        assert member not in User.get_admin_users()
