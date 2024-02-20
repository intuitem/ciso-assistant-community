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

groups_permissions = {
    "BI-UG-AUD": [
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
        # "view_requirement",
        "view_evidence",
        "view_framework",
    ],
    "BI-UG-VAL": [
        "view_project",
        "view_riskassessment",
        "view_securitymeasure",
        "view_policy",
        "view_riskscenario",
        "view_riskacceptance",
        "approve_riskacceptance",
        "view_asset",
        "view_threat",
        "view_securityfunction",
        "view_folder",
        "view_usergroup",
        "view_riskmatrix",
        "view_complianceassessment",
        "view_requirementassessment",
        # "view_requirement",
        "view_evidence",
        "view_framework",
    ],
    "BI-UG-ANA": [
        "add_project",
        "view_project",
        "change_project",
        "delete_project",
        "add_riskassessment",
        "view_riskassessment",
        "change_riskassessment",
        "delete_riskassessment",
        "add_securitymeasure",
        "view_securitymeasure",
        "change_securitymeasure",
        "delete_securitymeasure",
        "add_policy",
        "view_policy",
        "change_policy",
        "delete_policy",
        "add_riskscenario",
        "view_riskscenario",
        "change_riskscenario",
        "delete_riskscenario",
        "add_riskacceptance",
        "view_riskacceptance",
        "change_riskacceptance",
        "delete_riskacceptance",
        "add_complianceassessment",
        "view_complianceassessment",
        "change_complianceassessment",
        "delete_complianceassessment",
        "view_requirementassessment",
        "change_requirementassessment",
        "add_evidence",
        "view_evidence",
        "change_evidence",
        "delete_evidence",
        "view_asset",
        "view_threat",
        "view_securityfunction",
        "view_folder",
        "view_usergroup",
        "view_riskmatrix",
        # "view_requirement",
        "view_framework",
    ],
    "BI-UG-DMA": [
        "change_usergroup",
        "view_usergroup",
        "add_project",
        "change_project",
        "delete_project",
        "view_project",
        "add_riskassessment",
        "view_riskassessment",
        "change_riskassessment",
        "delete_riskassessment",
        "add_securitymeasure",
        "view_securitymeasure",
        "change_securitymeasure",
        "delete_securitymeasure",
        "add_policy",
        "view_policy",
        "change_policy",
        "delete_policy",
        "add_riskscenario",
        "view_riskscenario",
        "change_riskscenario",
        "delete_riskscenario",
        "add_riskacceptance",
        "view_riskacceptance",
        "change_riskacceptance",
        "delete_riskacceptance",
        "view_asset",
        "view_threat",
        "view_securityfunction",
        "view_folder",
        "change_folder",
        "add_riskmatrix",
        "view_riskmatrix",
        "change_riskmatrix",
        "delete_riskmatrix",
        "add_complianceassessment",
        "view_complianceassessment",
        "change_complianceassessment",
        "delete_complianceassessment",
        "view_requirementassessment",
        "change_requirementassessment",
        "add_evidence",
        "view_evidence",
        "change_evidence",
        "delete_evidence",
        # "view_requirement",
        "view_framework",
    ]
}

@pytest.mark.django_db
class TestUserGroupsAuthenticated:
    """Perform tests on User Groups API endpoint with authentication"""

    @pytest.mark.django_db
    @pytest.fixture(autouse=True)
    def setup(self, authenticated_client):
        EndpointTestsQueries.Auth.create_object(authenticated_client, "Folders", Folder, {"name": "test"}) # TODO create the folder using the DB directly instead of the API

    @pytest.mark.parametrize("authenticated_client_with_role", [{"role": "BI-UG-AUD", "folder": "test"}, {"role": "BI-UG-VAL", "folder": "test"}, {"role": "BI-UG-ANA", "folder": "test"}, {"role": "BI-UG-DMA", "folder": "test"}], indirect=True, ids=["BI-UG-AUD", "BI-UG-VAL", "BI-UG-ANA", "BI-UG-DMA"])
    def test_group_permissions(self, authenticated_client_with_role):
        """test that a user with a specific role has the correct permissions"""
        
        authenticated_client, params = authenticated_client_with_role
        user_permissions = RoleAssignment.get_permissions(User.objects.get(email="user@tests.com"))
        for perm in groups_permissions[params["role"]]:
            assert perm in user_permissions.keys(), f"Permission {perm} not found in user permissions (group: {params['role']})"
