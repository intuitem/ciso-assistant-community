import pytest

from iam.models import IdPGroup, User
from iam.scim.views import _add_members, _set_members
from iam.utils import sync_user_idp_groups


@pytest.mark.django_db
class TestIdPGroupSource:
    def test_manually_created_group_has_no_source(self):
        group = IdPGroup.objects.create(name="Pre-created Group")
        assert group.source is None

    def test_sso_sync_stamps_source_sso(self):
        user = User.objects.create_user(email="alice@example.com", password="pw")

        sync_user_idp_groups(user, ["Marketing"])

        group = IdPGroup.objects.get(name="Marketing")
        assert group.source == IdPGroup.Source.SSO

    def test_scim_add_members_stamps_source_scim(self):
        user = User.objects.create_user(email="bob@example.com", password="pw")
        user.is_scim_managed = True
        user.save(update_fields=["is_scim_managed"])
        group = IdPGroup.objects.create(name="Sales")

        _add_members(group, [str(user.id)])

        group.refresh_from_db()
        assert group.source == IdPGroup.Source.SCIM
        assert list(group.users.all()) == [user]


@pytest.mark.django_db
class TestScimSsoMembershipIsolation:
    def _shared_group_with_mixed_members(self):
        scim_user = User.objects.create_user(
            email="scim.user@example.com", password="pw"
        )
        scim_user.is_scim_managed = True
        scim_user.save(update_fields=["is_scim_managed"])

        sso_user = User.objects.create_user(email="sso.user@example.com", password="pw")

        group = IdPGroup.objects.create(name="Shared Group")
        group.users.add(scim_user, sso_user)
        return group, scim_user, sso_user

    def test_set_members_full_replace_leaves_sso_member_untouched(self):
        group, scim_user, sso_user = self._shared_group_with_mixed_members()
        other_scim_user = User.objects.create_user(
            email="other.scim@example.com", password="pw"
        )
        other_scim_user.is_scim_managed = True
        other_scim_user.save(update_fields=["is_scim_managed"])

        _set_members(group, [str(other_scim_user.id)])

        members = set(group.users.all())
        assert sso_user in members, "SSO/JIT member must survive a SCIM full replace"
        assert scim_user not in members
        assert other_scim_user in members

    def test_set_members_empty_list_clears_only_scim_members(self):
        group, scim_user, sso_user = self._shared_group_with_mixed_members()

        _set_members(group, [])

        members = set(group.users.all())
        assert sso_user in members
        assert scim_user not in members

    def test_set_members_unresolvable_ids_is_a_noop_not_a_wipe(self):
        group, scim_user, sso_user = self._shared_group_with_mixed_members()
        local_only_user = User.objects.create_user(
            email="local.only@example.com", password="pw"
        )

        _set_members(group, [str(local_only_user.id)])

        members = set(group.users.all())
        assert members == {scim_user, sso_user}

    def test_patch_clear_action_removes_only_scim_members(self):
        group, scim_user, sso_user = self._shared_group_with_mixed_members()

        scim_managed = group.users.filter(is_scim_managed=True)
        if scim_managed.exists():
            group.users.remove(*scim_managed)

        members = set(group.users.all())
        assert members == {sso_user}
