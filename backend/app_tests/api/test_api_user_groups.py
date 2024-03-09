import pytest
from core.models import User

from iam.models import Folder, UserGroup, RoleAssignment
from test_vars import GROUPS_PERMISSIONS, TEST_USER_EMAIL
from test_utils import EndpointTestsQueries


@pytest.mark.django_db
class TestUserGroups:
    """Perform tests on User Groups API endpoint with authentication"""

    def test_group_permissions(self, test):
        """test that a user with a specific role has the correct permissions"""

        user_permissions = RoleAssignment.get_permissions(
            User.objects.get(email=TEST_USER_EMAIL)
        )
        for perm in GROUPS_PERMISSIONS[test.user_group]["perms"]:
            assert (
                perm in user_permissions.keys()
            ), f"Permission {perm} not found in user permissions (group: {test.user_group})"
