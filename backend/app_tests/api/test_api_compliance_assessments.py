import pytest
from rest_framework.test import APIClient
from core.models import ComplianceAssessment, Framework
from core.models import Perimeter
from iam.models import Folder

from test_utils import EndpointTestsQueries

# Generic compliance assessment data for tests
COMPLIANCE_ASSESSMENT_NAME = "Test Compliance Assessment"
COMPLIANCE_ASSESSMENT_DESCRIPTION = "Test Description"
COMPLIANCE_ASSESSMENT_VERSION = "1.0"


@pytest.mark.django_db
class TestComplianceAssessmentsUnauthenticated:
    """Perform tests on ComplianceAssessments API endpoint without authentication"""

    client = APIClient()

    def test_get_compliance_assessments(self, authenticated_client):
        """test to get compliance assessments from the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.get_object(
            self.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "perimeter": Perimeter.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "framework": Framework.objects.all()[0],
            },
        )

    def test_create_compliance_assessments(self):
        """test to create compliance assessments with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "perimeter": Perimeter.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ).id,
            },
        )

    def test_update_compliance_assessments(self, authenticated_client):
        """test to update compliance assessments with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.update_object(
            self.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "perimeter": Perimeter.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "framework": Framework.objects.all()[0],
            },
            {
                "name": "new " + COMPLIANCE_ASSESSMENT_NAME,
                "description": "new " + COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "perimeter": Perimeter.objects.create(
                    name="test2", folder=Folder.objects.create(name="test2")
                ).id,
            },
        )

    def test_delete_compliance_assessments(self, authenticated_client):
        """test to delete compliance assessments with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.delete_object(
            self.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "perimeter": Perimeter.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "framework": Framework.objects.all()[0],
            },
        )


@pytest.mark.django_db
class TestComplianceAssessmentsAuthenticated:
    """Perform tests on ComplianceAssessments API endpoint with authentication"""

    def test_get_compliance_assessments(self, test):
        """test to get compliance assessments from the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION,
                "perimeter": perimeter,
                "framework": Framework.objects.all()[0],
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
                "framework": {
                    "id": str(Framework.objects.all()[0].id),
                    "str": str(Framework.objects.all()[0]),
                    "implementation_groups_definition": None,
                    "reference_controls": [],
                    "min_score": 1,
                    "max_score": 4,
                    "ref_id": str(Framework.objects.all()[0].ref_id),
                },
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_create_compliance_assessments(self, test):
        """test to create compliance assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION,
                "perimeter": str(perimeter.id),
                "framework": str(Framework.objects.all()[0].id),
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
                "framework": {
                    "id": str(Framework.objects.all()[0].id),
                    "str": str(Framework.objects.all()[0]),
                    "implementation_groups_definition": None,
                    "reference_controls": [],
                    "min_score": Framework.objects.all()[0].min_score,
                    "max_score": Framework.objects.all()[0].max_score,
                    "ref_id": str(Framework.objects.all()[0].ref_id),
                },
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_compliance_assessments(self, test):
        """test to update compliance assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Documents")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework2")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)
        perimeter2 = Perimeter.objects.create(name="test2", folder=test.folder)

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION,
                "perimeter": perimeter,
                "framework": Framework.objects.all()[0],
            },
            {
                "name": "new " + COMPLIANCE_ASSESSMENT_NAME,
                "description": "new " + COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION + ".1",
                "perimeter": str(perimeter2.id),
                "framework": str(Framework.objects.all()[1].id),
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
                "framework": {
                    "id": str(Framework.objects.all()[0].id),
                    "str": str(Framework.objects.all()[0]),
                    "implementation_groups_definition": None,
                    "reference_controls": [],
                    "min_score": Framework.objects.all()[0].min_score,
                    "max_score": Framework.objects.all()[0].max_score,
                    "ref_id": str(Framework.objects.all()[0].ref_id),
                },
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    """def test_update_compliance_assessments_fails_with_out_of_scope_object(self, test):

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Documents")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework2")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)
        perimeter2 = Perimeter.objects.create(
            name="test2", folder=Folder.objects.create(name="test2")
        )

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION,
                "perimeter": perimeter,
                "framework": Framework.objects.all()[0],
            },
            {
                "name": "new " + COMPLIANCE_ASSESSMENT_NAME,
                "description": "new " + COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION + ".1",
                "perimeter": str(perimeter2.id),
                "framework": str(Framework.objects.all()[1].id),
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
                "framework": {
                    "id": str(Framework.objects.all()[0].id),
                    "str": str(Framework.objects.all()[0]),
                    "implementation_groups_definition": None,
                    "reference_controls": [],
                    "min_score": Framework.objects.all()[0].min_score,
                    "max_score": Framework.objects.all()[0].max_score,
                    "ref_id": str(Framework.objects.all()[0].ref_id),
                },
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )"""

    def test_delete_compliance_assessments(self, test):
        """test to delete compliance assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "perimeter": perimeter,
                "framework": Framework.objects.all()[0],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )
