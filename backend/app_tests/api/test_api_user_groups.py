import pytest
from core.models import User
from core.models import (
    Project,
    RiskAcceptance,
    RiskScenario,
    RiskMatrix,
    RiskAssessment,
)
from iam.models import Folder, UserGroup, RoleAssignment
from test_api import EndpointTestsQueries

@pytest.mark.django_db
class TestUserGroupsAuthenticated:
    """Perform tests on User Groups API endpoint with authentication"""

    @pytest.mark.django_db
    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client):
        EndpointTestsQueries.Auth.create_object(authenticated_client, "Folders", Folder, {"name": "test"}) # TODO create the folder using the DB directly instead of the API

    @pytest.mark.parametrize("authenticated_client_with_role", [{"role": "BI-UG-AUD", "folder": "test"}], indirect=True)
    def test_group_auditor(self, authenticated_client_with_role):
        """test that a user with the role auditor has the correct permissions"""

        user_permissions = RoleAssignment.get_permissions(User.objects.get(email="user@tests.com"))
        for perm in [
            "view_project",
            "view_riskassessment",
            "view_securitymeasure",
            "view_policy",
            "view_riskscenario",
            "view_riskacceptance",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "view_usergroup",
            "view_riskmatrix",
            "view_complianceassessment",
            "view_requirementassessment",
            "view_requirement",
            "view_evidence",
            "view_framework",
        ]:
            assert perm in user_permissions.keys(), f"Permission {perm} not found in auditor user permissions"
