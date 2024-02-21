import pytest
from core.models import User

from iam.models import Folder, UserGroup, RoleAssignment
from test_vars import GROUPS_PERMISSIONS
from test_api import EndpointTestsQueries

@pytest.mark.django_db
class TestUserGroups:
    """Perform tests on User Groups API endpoint with authentication"""

    @pytest.mark.django_db
    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client):
        EndpointTestsQueries.Auth.create_object(authenticated_client, "Folders", Folder, {"name": "test"})

    @pytest.mark.parametrize("authenticated_client_with_role", [{"role": "BI-UG-AUD", "folder": "test"}, {"role": "BI-UG-VAL", "folder": "test"}, {"role": "BI-UG-ANA", "folder": "test"}, {"role": "BI-UG-DMA", "folder": "test"}], indirect=True, ids=["BI-UG-AUD", "BI-UG-VAL", "BI-UG-ANA", "BI-UG-DMA"])
    def test_group_permissions(self, authenticated_client_with_role):
        """test that a user with a specific role has the correct permissions"""
        
        authenticated_client, params = authenticated_client_with_role
        user_permissions = RoleAssignment.get_permissions(User.objects.get(email="user@tests.com"))
        for perm in GROUPS_PERMISSIONS[params["role"]]:
            assert perm in user_permissions.keys(), f"Permission {perm} not found in user permissions (group: {params['role']})"

@pytest.mark.django_db
class TestUserPermissions:
    pass