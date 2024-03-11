import pytest
from rest_framework.test import APIClient
from core.models import User
from core.models import (
    Project,
    RiskAcceptance,
    RiskScenario,
    RiskMatrix,
    RiskAssessment,
)
from iam.models import Folder, UserGroup

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries

# Generic risk acceptance data for tests
RISK_ACCEPTANCE_NAME = "Test Risk Acceptance"
RISK_ACCEPTANCE_DESCRIPTION = "Test Description"
RISK_ACCEPTANCE_EXPIRY_DATE = "2024-01-01"
RISK_ACCEPTANCE_ACCEPTED_DATE = "2024-01-02"
RISK_ACCEPTANCE_REJECTED_DATE = "2024-01-02"
RISK_ACCEPTANCE_REVOKED_DATE = "2024-01-02"
RISK_ACCEPTANCE_JUSTIFICATION = "Test justification"
RISK_ACCEPTANCE_STATE = ("submitted", "Submitted")
RISK_ACCEPTANCE_STATE2 = ("accepted", "Accepted")


@pytest.mark.django_db
class TestRiskAcceptanceUnauthenticated:
    """Perform tests on Risk Acceptance API endpoint without authentication"""

    client = APIClient()

    def test_get_risk_acceptances(self):
        """test to get risk acceptances from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Risk Acceptances",
            RiskAcceptance,
            {
                "name": RISK_ACCEPTANCE_NAME,
                "description": RISK_ACCEPTANCE_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_risk_acceptances(self):
        """test to create risk acceptances with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Risk Acceptances",
            RiskAcceptance,
            {
                "name": RISK_ACCEPTANCE_NAME,
                "description": RISK_ACCEPTANCE_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_acceptances(self):
        """test to update risk acceptances with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Risk Acceptances",
            RiskAcceptance,
            {
                "name": RISK_ACCEPTANCE_NAME,
                "description": RISK_ACCEPTANCE_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + RISK_ACCEPTANCE_NAME,
                "description": "new " + RISK_ACCEPTANCE_DESCRIPTION,
            },
        )

    def test_delete_risk_acceptances(self):
        """test to delete risk acceptances with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Risk Acceptances",
            RiskAcceptance,
            {
                "name": RISK_ACCEPTANCE_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
class TestRiskAcceptanceAuthenticated:
    """Perform tests on Risk Acceptance API endpoint with authentication"""

    def test_get_risk_acceptances(self, test):
        """test to get risk acceptances from the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        approver = User.objects.create_user(email="approver@test.com")

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Risk Acceptances",
            RiskAcceptance,
            {
                "name": RISK_ACCEPTANCE_NAME,
                "description": RISK_ACCEPTANCE_DESCRIPTION,
                "expiry_date": RISK_ACCEPTANCE_EXPIRY_DATE,
                # 'accepted_date': RISK_ACCEPTANCE_ACCEPTED_DATE,
                # 'rejected_date': RISK_ACCEPTANCE_REJECTED_DATE,
                # 'revoked_date': RISK_ACCEPTANCE_REVOKED_DATE,
                "state": RISK_ACCEPTANCE_STATE[0],
                "folder": test.folder,
                "approver": approver,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "approver": {"id": str(approver.id), "str": approver.email},
                "state": RISK_ACCEPTANCE_STATE[1],
            },
            user_group=test.user_group,
        )

    def test_create_risk_acceptances(self, test):
        """test to create risk acceptances with the API with authentication"""

        approver = User.objects.create_user(email="approver@test.com")
        UserGroup.objects.get(name="BI-UG-GAP").user_set.add(approver)
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        risk_scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test description",
            risk_assessment=RiskAssessment.objects.create(
                name="test",
                project=Project.objects.create(name="test", folder=test.folder),
                risk_matrix=RiskMatrix.objects.create(name="test", folder=test.folder),
            ),
        )

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Risk Acceptances",
            RiskAcceptance,
            {
                "name": RISK_ACCEPTANCE_NAME,
                "description": RISK_ACCEPTANCE_DESCRIPTION,
                "expiry_date": RISK_ACCEPTANCE_EXPIRY_DATE,
                # 'accepted_date': RISK_ACCEPTANCE_ACCEPTED_DATE,
                # 'rejected_date': RISK_ACCEPTANCE_REJECTED_DATE,
                # 'revoked_date': RISK_ACCEPTANCE_REVOKED_DATE,
                # 'state': RISK_ACCEPTANCE_STATE[0],
                "folder": str(test.folder.id),
                "approver": str(approver.id),
                "risk_scenarios": [str(risk_scenario.id)],
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "approver": {"id": str(approver.id), "str": approver.email},
                "risk_scenarios": [
                    {"id": str(risk_scenario.id), "str": str(risk_scenario)}
                ],
                # 'state': RISK_ACCEPTANCE_STATE[1],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_risk_acceptances(self, test):
        """test to update risk acceptances with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        folder = Folder.objects.create(name="test2")
        approver = User.objects.create_user(email="approver@test.com")
        UserGroup.objects.get(name="BI-UG-GAP").user_set.add(approver)
        approver2 = User.objects.create_user(email="approver2@test.com")
        UserGroup.objects.get(name="BI-UG-GAP").user_set.add(approver2)
        risk_scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test description",
            risk_assessment=RiskAssessment.objects.create(
                name="test",
                project=Project.objects.create(name="test", folder=folder),
                risk_matrix=RiskMatrix.objects.create(name="test", folder=folder),
            ),
        )

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Risk Acceptances",
            RiskAcceptance,
            {
                "name": RISK_ACCEPTANCE_NAME,
                "description": RISK_ACCEPTANCE_DESCRIPTION,
                "expiry_date": RISK_ACCEPTANCE_EXPIRY_DATE,
                # 'state': RISK_ACCEPTANCE_STATE[0],
                "folder": test.folder,
                "approver": approver,
            },
            {
                "name": "new " + RISK_ACCEPTANCE_NAME,
                "description": "new " + RISK_ACCEPTANCE_DESCRIPTION,
                "expiry_date": "2024-05-05",
                "folder": str(folder.id),
                "approver": str(approver2.id),
                "risk_scenarios": [str(risk_scenario.id)],
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "approver": {"id": str(approver.id), "str": approver.email},
                # 'state': RISK_ACCEPTANCE_STATE[1],
            },
            user_group=test.user_group,
        )

    def test_delete_risk_acceptances(self, test):
        """test to delete risk acceptances with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Risk Acceptances",
            RiskAcceptance,
            {
                "name": RISK_ACCEPTANCE_NAME,
                "folder": test.folder,
            },
            user_group=test.user_group,
        )
