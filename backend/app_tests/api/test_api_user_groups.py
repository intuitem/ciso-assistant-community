import pytest
from uuid import uuid4
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from knox.models import AuthToken
from core.models import User

from iam.models import Folder, Role, RoleAssignment, UserGroup
from test_vars import GROUPS_PERMISSIONS, TEST_USER_EMAIL


@pytest.mark.django_db
class TestUserGroups:
    """Perform tests on User Groups API endpoint with authentication"""

    def test_group_permissions(self, test):
        """test that a user with a specific role has the correct permissions"""

        user_permissions = RoleAssignment.get_permissions(
            User.objects.get(email=TEST_USER_EMAIL)
        )
        for perm in GROUPS_PERMISSIONS[test.user_group]["perms"]:
            assert perm in user_permissions.keys(), (
                f"Permission {perm} not found in user permissions (group: {test.user_group})"
            )

    def test_cannot_delete_builtin_user_group(self, authenticated_client):
        """test that a builtin user group cannot be deleted via the API (blocked by
        the generic builtin-immutability guard in RBACPermissions)"""

        builtin_group = UserGroup.objects.filter(builtin=True).first()
        assert builtin_group is not None, "No builtin user group found in DB"

        url = reverse("user-groups-detail", args=[builtin_group.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        # Confirm the group still exists
        assert UserGroup.objects.filter(id=builtin_group.id).exists()

    def test_can_delete_non_builtin_user_group(self, authenticated_client):
        """test that a non-builtin user group can be deleted via the API"""
        from iam.models import Folder

        folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        non_builtin_group = UserGroup.objects.create(
            name="custom-group-to-delete", folder=folder, builtin=False
        )

        url = reverse("user-groups-detail", args=[non_builtin_group.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserGroup.objects.filter(id=non_builtin_group.id).exists()


def _domain_manager_role() -> Role:
    """A role holding change_usergroup + view_user but NOT change_user — the exact
    shape of a domain manager, who can manage groups in their domain but has no
    write access to the (Global-scoped) User object."""
    role, _ = Role.objects.get_or_create(name="test domain manager")
    role.permissions.set(
        Permission.objects.filter(
            codename__in=[
                # view_folder is required for any object under the domain to be
                # visible at all (see get_accessible_object_ids).
                "view_folder",
                "view_usergroup",
                "change_usergroup",
                "view_user",
            ]
        )
    )
    role.save()
    return role


def _client_for(user: User) -> APIClient:
    client = APIClient()
    token = AuthToken.objects.create(user=user)[1]
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.mark.django_db
class TestUserGroupMembership:
    """A domain manager can add/remove members of groups in their domain via the
    add-members / remove-members actions, without holding change_user (Global-only).
    Authorization is enforced on the group's folder via change_usergroup."""

    def _setup_domain(self, name="D1"):
        root = Folder.get_root_folder()
        domain = Folder.objects.create(
            name=name,
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        group = UserGroup.objects.create(name=f"{name} team", folder=domain)
        manager = User.objects.create_user(f"dm-{name}@tests.com", is_published=True)
        ra = RoleAssignment.objects.create(
            user=manager,
            role=_domain_manager_role(),
            folder=domain,
            is_recursive=True,
        )
        ra.perimeter_folders.add(domain)
        ra.save()
        return domain, group, manager

    def test_domain_manager_can_add_members(self, app_config):
        _, group, manager = self._setup_domain()
        a = User.objects.create_user("a@tests.com", is_published=True)
        b = User.objects.create_user("b@tests.com", is_published=True)
        client = _client_for(manager)

        url = reverse("user-groups-add-members", args=[group.id])
        response = client.post(url, {"users": [str(a.id), str(b.id)]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert group.user_set.filter(pk=a.pk).exists()
        assert group.user_set.filter(pk=b.pk).exists()

    def test_domain_manager_can_batch_remove_members(self, app_config):
        _, group, manager = self._setup_domain()
        keep = User.objects.create_user("keep@tests.com", is_published=True)
        drop1 = User.objects.create_user("drop1@tests.com", is_published=True)
        drop2 = User.objects.create_user("drop2@tests.com", is_published=True)
        group.user_set.add(keep, drop1, drop2)
        client = _client_for(manager)

        url = reverse("user-groups-remove-members", args=[group.id])
        response = client.post(
            url, {"users": [str(drop1.id), str(drop2.id)]}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert group.user_set.filter(pk=keep.pk).exists()
        assert not group.user_set.filter(pk__in=[drop1.pk, drop2.pk]).exists()

    def test_domain_manager_cannot_add_outside_domain(self, app_config):
        """Authorization follows the group's folder: a manager of D1 can't touch a
        group belonging to a sibling domain D2."""
        _, _, manager = self._setup_domain("D1")
        _, other_group, _ = self._setup_domain("D2")
        target = User.objects.create_user("member@tests.com", is_published=True)
        client = _client_for(manager)

        url = reverse("user-groups-add-members", args=[other_group.id])
        response = client.post(url, {"users": [str(target.id)]}, format="json")

        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )
        assert not other_group.user_set.filter(pk=target.pk).exists()

    def test_domain_manager_cannot_edit_user_directly(self, app_config):
        """Control: the manager still has no write access to the User object, so the
        legacy user-form path stays Global-admin-only. Only the group-scoped path
        is newly permitted."""
        _, group, manager = self._setup_domain()
        target = User.objects.create_user("member@tests.com", is_published=True)
        client = _client_for(manager)

        url = reverse("users-detail", args=[target.id])
        response = client.patch(url, {"user_groups": [str(group.id)]}, format="json")

        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )
        assert not group.user_set.filter(pk=target.pk).exists()

    def test_cannot_remove_last_admin(self, authenticated_client):
        """The last direct BI-UG-ADM administrator is protected on the group path too,
        mirroring UserViewSet."""
        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        sole_admin = admin_group.user_set.get()

        url = reverse("user-groups-remove-members", args=[admin_group.id])
        response = authenticated_client.post(
            url, {"users": [str(sole_admin.id)]}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data.get("error") == "attemptToRemoveOnlyAdminUserGroup"
        assert admin_group.user_set.filter(pk=sole_admin.pk).exists()

    def _dma_group(self, name="D1", parent=None):
        """A domain plus a group that GRANTS Domain Manager (BI-RL-DMA) scoped to it,
        so membership in the group is what confers domain-admin entitlement."""
        root = Folder.get_root_folder()
        domain = Folder.objects.create(
            name=name,
            parent_folder=parent or root,
            content_type=Folder.ContentType.DOMAIN,
        )
        group = UserGroup.objects.create(name=f"{name} managers", folder=domain)
        ra = RoleAssignment.objects.create(
            user_group=group,
            role=Role.objects.get(name="BI-RL-DMA"),
            folder=root,
            is_recursive=True,
        )
        ra.perimeter_folders.add(domain)
        return domain, group

    def test_domain_manager_cannot_remove_self_from_dma_group(self, app_config):
        """A sole domain admin can't strip their own entitlement (self-lockout)."""
        _, group = self._dma_group()
        manager = User.objects.create_user("dm@tests.com", is_published=True)
        group.user_set.add(manager)
        client = _client_for(manager)

        url = reverse("user-groups-remove-members", args=[group.id])
        response = client.post(url, {"users": [str(manager.id)]}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data.get("error") == "attemptToRemoveSelfFromDomainAdminGroup"
        assert group.user_set.filter(pk=manager.pk).exists()

    def test_domain_manager_can_remove_another_from_dma_group(self, app_config):
        """The self-lockout guard only blocks removing oneself; removing a peer
        (even the last other member) stays allowed."""
        _, group = self._dma_group()
        manager = User.objects.create_user("dm@tests.com", is_published=True)
        other = User.objects.create_user("other@tests.com", is_published=True)
        group.user_set.add(manager, other)
        client = _client_for(manager)

        url = reverse("user-groups-remove-members", args=[group.id])
        response = client.post(url, {"users": [str(other.id)]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert not group.user_set.filter(pk=other.pk).exists()
        assert group.user_set.filter(pk=manager.pk).exists()

    def test_global_admin_can_remove_self_from_dma_group(self, app_config):
        """A global admin retains admin from a higher level (root), so self-removal
        from a domain admin group is allowed."""
        _, group = self._dma_group()
        admin = User.objects.create_user("ga@tests.com", is_published=True)
        admin.user_groups.add(UserGroup.objects.get(name="BI-UG-ADM"))
        group.user_set.add(admin)
        client = _client_for(admin)

        url = reverse("user-groups-remove-members", args=[group.id])
        response = client.post(url, {"users": [str(admin.id)]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert not group.user_set.filter(pk=admin.pk).exists()

    def test_parent_domain_manager_can_remove_self_from_child_dma_group(
        self, app_config
    ):
        """Admin of a parent domain administers the child too, so self-removal from
        the child's domain admin group is allowed (higher-level exemption)."""
        parent, _ = self._dma_group("P")
        _, child_group = self._dma_group("C", parent=parent)
        manager = User.objects.create_user("pm@tests.com", is_published=True)
        parent_ra = RoleAssignment.objects.create(
            user=manager,
            role=Role.objects.get(name="BI-RL-DMA"),
            folder=Folder.get_root_folder(),
            is_recursive=True,
        )
        parent_ra.perimeter_folders.add(parent)
        child_group.user_set.add(manager)
        client = _client_for(manager)

        url = reverse("user-groups-remove-members", args=[child_group.id])
        response = client.post(url, {"users": [str(manager.id)]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert not child_group.user_set.filter(pk=manager.pk).exists()

    def test_add_members_rejects_oversized_batch(self, app_config):
        """The users list is capped, mirroring batch_action's limit."""
        _, group, manager = self._setup_domain()
        client = _client_for(manager)

        url = reverse("user-groups-add-members", args=[group.id])
        response = client.post(
            url, {"users": [str(uuid4()) for _ in range(101)]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_exclude_user_groups_ignored_when_group_not_readable(self, app_config):
        """exclude_user_groups must not leak membership of groups the caller can't
        read: a D1 manager excluding a D2 group has the filter ignored, so D2's
        member still shows up in the autocomplete results."""
        _, _, manager = self._setup_domain("D1")
        _, d2_group, _ = self._setup_domain("D2")
        d2_member = User.objects.create_user("d2member@tests.com", is_published=True)
        d2_group.user_set.add(d2_member)
        client = _client_for(manager)

        url = reverse("users-autocomplete")
        response = client.get(url, {"exclude_user_groups": str(d2_group.id)})

        assert response.status_code == status.HTTP_200_OK
        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        assert "d2member@tests.com" in [r["email"] for r in rows]

    def test_cannot_rename_builtin_group_via_patch(self, app_config):
        """A builtin group's fields are immutable via the API even with
        change_usergroup: the name field is read-only, so a rename is ignored
        (UserGroup has no builtin-editable fields)."""
        domain, _, manager = self._setup_domain()
        builtin_group = UserGroup.objects.create(
            name="D1 anchor", folder=domain, builtin=True
        )
        client = _client_for(manager)

        url = reverse("user-groups-detail", args=[builtin_group.id])
        client.patch(url, {"name": "renamed"}, format="json")

        builtin_group.refresh_from_db()
        assert builtin_group.name == "D1 anchor"

    def test_cannot_rename_builtin_group_via_batch_action(self, app_config):
        """The batch-action path is guarded too (change_field on a builtin object)."""
        domain, _, manager = self._setup_domain()
        builtin_group = UserGroup.objects.create(
            name="D1 anchor", folder=domain, builtin=True
        )
        client = _client_for(manager)

        url = reverse("user-groups-batch-action")
        response = client.post(
            url,
            {
                "action": "change_field",
                "ids": [str(builtin_group.id)],
                "field": "name",
                "value": "renamed",
            },
            format="json",
        )

        builtin_group.refresh_from_db()
        assert builtin_group.name == "D1 anchor"
        failed = (
            response.data.get("failed", []) if isinstance(response.data, dict) else []
        )
        assert any("builtin" in str(f.get("error", "")).lower() for f in failed)

    def test_cannot_set_builtin_flag(self, app_config):
        """The builtin flag is read-only via the API — it can't be toggled on to
        turn an ordinary object into a protected one."""
        domain, _, manager = self._setup_domain()
        group = UserGroup.objects.create(name="D1 custom", folder=domain, builtin=False)
        client = _client_for(manager)

        batch = client.post(
            reverse("user-groups-batch-action"),
            {
                "action": "change_field",
                "ids": [str(group.id)],
                "field": "builtin",
                "value": True,
            },
            format="json",
        )
        assert batch.status_code == status.HTTP_400_BAD_REQUEST

        client.patch(
            reverse("user-groups-detail", args=[group.id]),
            {"builtin": True},
            format="json",
        )

        group.refresh_from_db()
        assert group.builtin is False

    def test_membership_allowed_on_builtin_group(self, app_config):
        """The builtin guard blocks field edits (PUT/PATCH/DELETE) but must not block
        membership — which uses POST add/remove-members. Real per-domain groups are
        builtin, so this is the common case."""
        domain, _, manager = self._setup_domain()
        builtin_group = UserGroup.objects.create(
            name="D1 anchor", folder=domain, builtin=True
        )
        target = User.objects.create_user("member@tests.com", is_published=True)
        client = _client_for(manager)

        url = reverse("user-groups-add-members", args=[builtin_group.id])
        response = client.post(url, {"users": [str(target.id)]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert builtin_group.user_set.filter(pk=target.pk).exists()
