import pytest
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.test import APIClient
from core.models import (
    ComplianceAssessment,
    RequirementNode,
    RequirementAssessment,
    Framework,
)
from core.models import Project, SecurityMeasure
from iam.models import Folder

from test_api import EndpointTestsQueries

# Generic requirement assessment data for tests
REQUIREMENT_ASSESSMENT_STATUS = "partially_compliant"
REQUIREMENT_ASSESSMENT_STATUS2 = "non_compliant"
REQUIREMENT_ASSESSMENT_OBSERVATION = "Test observation"


@pytest.mark.django_db
class TestRequirementAssessmentsUnauthenticated:
    """Perform tests on Requirement Assessments API endpoint without authentication"""

    client = APIClient()

    def test_get_requirement_assessments(self, authenticated_client):
        """test to get requirement assessments from the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.get_object(
            self.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "folder": folder,
                "compliance_assessment": ComplianceAssessment.objects.create(
                    name="test",
                    project=Project.objects.create(name="test", folder=folder),
                    framework=Framework.objects.all()[0],
                ),
                "requirement": RequirementNode.objects.create(
                    name="test", folder=folder, assessable=False
                ),
            },
        )

    def test_create_requirement_assessments(self):
        """test to create requirement assessments with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_requirement_assessments(self, authenticated_client):
        """test to update requirement assessments with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.update_object(
            self.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "folder": folder,
                "compliance_assessment": ComplianceAssessment.objects.create(
                    name="test",
                    project=Project.objects.create(name="test", folder=folder),
                    framework=Framework.objects.all()[0],
                ),
                "requirement": RequirementNode.objects.create(
                    name="test", folder=folder, assessable=False
                ),
            },
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS2,
                "folder": Folder.objects.create(name="test2").id,
            },
        )


@pytest.mark.django_db
class TestRequirementAssessmentsAuthenticated:
    """Perform tests on Requirement Assessments API endpoint with authentication"""

    def test_get_requirement_assessments(self, authenticated_client):
        """test to get requirement assessments from the API with authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        folder = Folder.objects.create(name="test")
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test",
            project=Project.objects.create(name="test", folder=folder),
            framework=Framework.objects.all()[0],
        )

        EndpointTestsQueries.Auth.get_object(
            authenticated_client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "observation": REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": folder,
                "compliance_assessment": compliance_assessment,
                "requirement": RequirementNode.objects.all()[0],
            },
            {
                "folder": str(folder.id),
                "compliance_assessment": {
                    "id": str(compliance_assessment.id),
                    "str": compliance_assessment.name,
                },
                "requirement": str(RequirementNode.objects.all()[0].id),
            },
            -1,
        )

    def test_create_requirement_assessments(self, authenticated_client):
        """test to create requirement assessments with the API with authentication"""
        """nobody has permission to do that, so it will fail"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        folder = Folder.objects.create(name="test")
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test",
            project=Project.objects.create(name="test", folder=folder),
            framework=Framework.objects.all()[0],
        )
        security_measure = SecurityMeasure.objects.create(name="test", folder=folder)

        EndpointTestsQueries.Auth.create_object(
            authenticated_client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "observation": REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": str(folder.id),
                "compliance_assessment": str(compliance_assessment.id),
                "requirement": str(RequirementNode.objects.all()[0].id),
                "security_measures": [str(security_measure.id)],
            },
            {
                "compliance_assessment": {
                    "id": str(compliance_assessment.id),
                    "str": compliance_assessment.name,
                }
            },
            base_count=-1,
            fails=True,
            expected_status=HTTP_400_BAD_REQUEST
        )

    def test_update_requirement_assessments(self, authenticated_client):
        """test to update requirement assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        folder = Folder.objects.create(name="test")
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test",
            project=Project.objects.create(
                name="test", folder=Folder.get_root_folder()
            ),
            framework=Framework.objects.all()[0],
        )
        compliance_assessment2 = ComplianceAssessment.objects.create(
            name="test2",
            project=Project.objects.create(name="test2", folder=folder),
            framework=Framework.objects.all()[0],
        )
        security_measure = SecurityMeasure.objects.create(name="test", folder=folder)

        EndpointTestsQueries.Auth.update_object(
            authenticated_client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "observation": REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": Folder.get_root_folder(),
                "compliance_assessment": compliance_assessment,
                "requirement": RequirementNode.objects.all()[0],
            },
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS2,
                "observation": "new " + REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": str(folder.id),
                "compliance_assessment": str(compliance_assessment2.id),
                "requirement": str(RequirementNode.objects.all()[1].id),
                "security_measures": [str(security_measure.id)],
            },
            {
                "folder": str(Folder.get_root_folder().id),
                "compliance_assessment": {
                    "id": str(compliance_assessment.id),
                    "str": compliance_assessment.name,
                },
                "requirement": str(RequirementNode.objects.all()[0].id),
            },
        )

    def test_get_status_choices(self, authenticated_client):
        """test to get requirement assessments status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            authenticated_client,
            "Requirement Assessments",
            "status",
            RequirementAssessment.Status.choices,
        )
