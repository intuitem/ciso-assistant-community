"""Tests for RoleAssignment.has_permission_anywhere, the explicit existential
permission check that replaced the User/UserGroup `.permissions` antipattern."""

import pytest
from django.contrib.auth.models import AnonymousUser, Permission

from iam.models import Folder, Role, RoleAssignment, User, UserGroup


@pytest.fixture
def domain_folder(db):
    return Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="test domain",
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.fixture
def viewer_role(db):
    role = Role.objects.create(name="test viewer")
    role.permissions.set(
        Permission.objects.filter(codename__in=["view_folder", "view_riskassessment"])
    )
    return role


def _assign(role, folder, *, user=None, user_group=None, is_recursive=False):
    ra = RoleAssignment.objects.create(
        user=user,
        user_group=user_group,
        role=role,
        folder=folder,
        is_recursive=is_recursive,
    )
    ra.perimeter_folders.add(folder)
    return ra


@pytest.mark.django_db
class TestHasPermissionAnywhere:
    def test_anonymous_user_has_nothing(self):
        assert not RoleAssignment.has_permission_anywhere(
            AnonymousUser(), "view_riskassessment"
        )

    def test_user_without_assignments_has_nothing(self):
        user = User.objects.create_user(email="noperm@example.com")
        assert not RoleAssignment.has_permission_anywhere(user, "view_riskassessment")

    def test_direct_assignment_grants_permission(self, domain_folder, viewer_role):
        user = User.objects.create_user(email="viewer@example.com")
        _assign(viewer_role, domain_folder, user=user)

        assert RoleAssignment.has_permission_anywhere(user, "view_riskassessment")
        # codename not in the role
        assert not RoleAssignment.has_permission_anywhere(user, "add_riskassessment")

    def test_permission_via_user_group(self, domain_folder, viewer_role):
        user = User.objects.create_user(email="member@example.com")
        group = UserGroup.objects.create(name="test group", folder=domain_folder)
        user.user_groups.add(group)
        _assign(viewer_role, domain_folder, user_group=group)

        assert RoleAssignment.has_permission_anywhere(user, "view_riskassessment")

    def test_user_group_principal(self, domain_folder, viewer_role):
        group = UserGroup.objects.create(name="test group", folder=domain_folder)
        _assign(viewer_role, domain_folder, user_group=group)

        assert RoleAssignment.has_permission_anywhere(group, "view_riskassessment")
        assert not RoleAssignment.has_permission_anywhere(group, "add_riskassessment")

    def test_existential_not_scoped(self, domain_folder, viewer_role):
        """A permission held only on a sub-folder still counts "anywhere",
        while the scoped check on an unrelated folder must stay False."""
        user = User.objects.create_user(email="scoped@example.com")
        _assign(viewer_role, domain_folder, user=user)

        assert RoleAssignment.has_permission_anywhere(user, "view_riskassessment")
        # is_access_allowed on the root folder (outside the assignment perimeter)
        # is False: has_permission_anywhere must never be used as a substitute.
        perm = Permission.objects.get(codename="view_riskassessment")
        assert not RoleAssignment.is_access_allowed(
            user=user, perm=perm, folder=Folder.get_root_folder()
        )
