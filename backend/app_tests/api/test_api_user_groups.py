import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import User

from iam.models import RoleAssignment, UserGroup
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
        """test that a builtin user group cannot be deleted via the API"""

        builtin_group = UserGroup.objects.filter(builtin=True).first()
        assert builtin_group is not None, "No builtin user group found in DB"

        url = reverse("user-groups-detail", args=[builtin_group.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data.get("error") == "attemptToDeleteBuiltinUserGroup"
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
