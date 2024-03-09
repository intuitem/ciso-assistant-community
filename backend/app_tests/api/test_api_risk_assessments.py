import pytest
from rest_framework.test import APIClient
from core.models import Project, RiskAssessment, RiskMatrix
from iam.models import Folder, User

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries

# Generic project data for tests
RISK_ASSESSMENT_NAME = "Test risk_assessment"
RISK_ASSESSMENT_DESCRIPTION = "Test Description"
RISK_ASSESSMENT_VERSION = "1.0"


@pytest.mark.django_db
class TestRiskAssessmentUnauthenticated:
    """Perform tests on Risk Assessment API endpoint without authentication"""

    client = APIClient()

    def test_get_risk_acceptances(self):
        """test to get risk assessments from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "description": RISK_ASSESSMENT_DESCRIPTION,
                "project": Project.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "risk_matrix": RiskMatrix.objects.create(
                    name="test", folder=Folder.objects.create(name="test2")
                ),
            },
        )

    def test_create_risk_assessments(self):
        """test to create risk assessments with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "description": RISK_ASSESSMENT_DESCRIPTION,
                "project": Project.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ).id,
            },
        )

    def test_update_risk_assessments(self):
        """test to update risk assessments with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "description": RISK_ASSESSMENT_DESCRIPTION,
                "project": Project.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "risk_matrix": RiskMatrix.objects.create(
                    name="test", folder=Folder.objects.create(name="test2")
                ),
            },
            {
                "name": "new " + RISK_ASSESSMENT_NAME,
                "description": "new " + RISK_ASSESSMENT_DESCRIPTION,
                "project": Project.objects.create(
                    name="test2", folder=Folder.objects.create(name="test3")
                ).id,
            },
        )

    def test_delete_risk_assessments(self):
        """test to delete risk assessments with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "project": Project.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "risk_matrix": RiskMatrix.objects.create(
                    name="test", folder=Folder.objects.create(name="test2")
                ),
            },
        )


@pytest.mark.django_db
class TestRiskAssessmentAuthenticated:
    """Perform tests on Risk Assessment API endpoint with authentication"""

    def test_get_risk_assessments(self, test):
        """test to get risk assessments from the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        project = Project.objects.create(name="test", folder=test.folder)
        risk_matrix = RiskMatrix.objects.all()[0]

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "description": RISK_ASSESSMENT_DESCRIPTION,
                "version": RISK_ASSESSMENT_VERSION,
                "project": project,
                "risk_matrix": risk_matrix,
            },
            {
                "project": {"id": str(project.id), "str": project.name},
                "risk_matrix": {"id": str(risk_matrix.id), "str": str(risk_matrix)},
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_create_risk_assessments(self, test):
        """test to create risk assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        project = Project.objects.create(name="test", folder=test.folder)
        risk_matrix = RiskMatrix.objects.all()[0]

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "description": RISK_ASSESSMENT_DESCRIPTION,
                "version": RISK_ASSESSMENT_VERSION,
                "project": str(project.id),
                "risk_matrix": str(risk_matrix.id),
            },
            {
                "project": {"id": str(project.id), "str": project.name},
                "risk_matrix": {"id": str(risk_matrix.id), "str": str(risk_matrix)},
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_risk_assessments(self, test):
        """test to update risk assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix2")
        project = Project.objects.create(name="test", folder=test.folder)
        project2 = Project.objects.create(
            name="test2", folder=Folder.objects.create(name="test2")
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        risk_matrix2 = RiskMatrix.objects.all()[1]

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "description": RISK_ASSESSMENT_DESCRIPTION,
                "version": RISK_ASSESSMENT_VERSION,
                "project": project,
                "risk_matrix": risk_matrix,
            },
            {
                "name": "new " + RISK_ASSESSMENT_NAME,
                "description": "new " + RISK_ASSESSMENT_DESCRIPTION,
                "version": RISK_ASSESSMENT_VERSION + ".1",
                "project": str(project2.id),
                "risk_matrix": str(risk_matrix2.id),
            },
            {
                "project": {"id": str(project.id), "str": project.name},
                "risk_matrix": {"id": str(risk_matrix.id), "str": str(risk_matrix)},
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_delete_risk_assessments(self, test):
        """test to delete risk assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        project = Project.objects.create(name="test", folder=test.folder)
        risk_matrix = RiskMatrix.objects.all()[0]

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "project": project,
                "risk_matrix": risk_matrix,
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    # TODO add option quality_check (endpoint /api/risk-assessments/quality_check/ not working)
    # def test_get_status_choice(self, test):
    #     """test to get risk assessments status choices from the API with authentication"""

    #     EndpointTestsQueries.get_object_options_auth(test.client, "Risk Assessment", "lc_status", Project.PRJ_LC_STATUS)
