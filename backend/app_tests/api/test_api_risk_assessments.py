import pytest
from rest_framework.test import APIClient
from core.models import Perimeter, RiskAssessment, RiskMatrix
from iam.models import Folder

from test_utils import EndpointTestsQueries

# Generic perimeter data for tests
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
                "perimeter": Perimeter.objects.create(
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
                "perimeter": Perimeter.objects.create(
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
                "perimeter": Perimeter.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "risk_matrix": RiskMatrix.objects.create(
                    name="test", folder=Folder.objects.create(name="test2")
                ),
            },
            {
                "name": "new " + RISK_ASSESSMENT_NAME,
                "description": "new " + RISK_ASSESSMENT_DESCRIPTION,
                "perimeter": Perimeter.objects.create(
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
                "perimeter": Perimeter.objects.create(
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
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)
        risk_matrix = RiskMatrix.objects.all()[0]

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "description": RISK_ASSESSMENT_DESCRIPTION,
                "version": RISK_ASSESSMENT_VERSION,
                "perimeter": perimeter,
                "risk_matrix": risk_matrix,
            },
            {
                "perimeter": {
                    "id": str(perimeter.id),
                    "str": perimeter.folder.name + "/" + perimeter.name,
                    "folder": {
                        "id": str(perimeter.folder.id),
                        "str": perimeter.folder.name,
                    },
                },
                "risk_matrix": {"id": str(risk_matrix.id), "str": str(risk_matrix)},
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_create_risk_assessments(self, test):
        """test to create risk assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)
        risk_matrix = RiskMatrix.objects.all()[0]

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "description": RISK_ASSESSMENT_DESCRIPTION,
                "version": RISK_ASSESSMENT_VERSION,
                "perimeter": str(perimeter.id),
                "risk_matrix": str(risk_matrix.id),
            },
            {
                "perimeter": {
                    "id": str(perimeter.id),
                    "str": perimeter.folder.name + "/" + perimeter.name,
                    "folder": {
                        "id": str(perimeter.folder.id),
                        "str": perimeter.folder.name,
                    },
                },
                "risk_matrix": {"id": str(risk_matrix.id), "str": str(risk_matrix)},
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_risk_assessments(self, test):
        """test to update risk assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix2")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)
        perimeter2 = Perimeter.objects.create(name="test2", folder=test.folder)
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
                "perimeter": perimeter,
                "risk_matrix": risk_matrix,
            },
            {
                "name": "new " + RISK_ASSESSMENT_NAME,
                "description": "new " + RISK_ASSESSMENT_DESCRIPTION,
                "version": RISK_ASSESSMENT_VERSION + ".1",
                "perimeter": str(perimeter2.id),
                "risk_matrix": str(risk_matrix2.id),
            },
            {
                "perimeter": {
                    "id": str(perimeter.id),
                    "str": perimeter.folder.name + "/" + perimeter.name,
                    "folder": {
                        "id": str(perimeter.folder.id),
                        "str": perimeter.folder.name,
                    },
                },
                "risk_matrix": {"id": str(risk_matrix.id), "str": str(risk_matrix)},
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    """def test_update_risk_assessments(self, test):

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix2")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)
        perimeter2 = Perimeter.objects.create(
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
                "perimeter": perimeter,
                "risk_matrix": risk_matrix,
            },
            {
                "name": "new " + RISK_ASSESSMENT_NAME,
                "description": "new " + RISK_ASSESSMENT_DESCRIPTION,
                "version": RISK_ASSESSMENT_VERSION + ".1",
                "perimeter": str(perimeter2.id),
                "risk_matrix": str(risk_matrix2.id),
            },
            {
                "perimeter": {
                    "id": str(perimeter.id),
                    "str": perimeter.folder.name + "/" + perimeter.name,
                    "folder": {
                        "id": str(perimeter.folder.id),
                        "str": perimeter.folder.name,
                    },
                },
                "risk_matrix": {"id": str(risk_matrix.id), "str": str(risk_matrix)},
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )"""

    def test_delete_risk_assessments(self, test):
        """test to delete risk assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)
        risk_matrix = RiskMatrix.objects.all()[0]

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Risk Assessment",
            RiskAssessment,
            {
                "name": RISK_ASSESSMENT_NAME,
                "perimeter": perimeter,
                "risk_matrix": risk_matrix,
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    # TODO add option quality_check (endpoint /api/risk-assessments/quality_check/ not working)
    # def test_get_status_choice(self, test):
    #     """test to get risk assessments status choices from the API with authentication"""

    #     EndpointTestsQueries.get_object_options_auth(test.client, "Risk Assessment", "lc_status", Perimeter.PRJ_LC_STATUS)
