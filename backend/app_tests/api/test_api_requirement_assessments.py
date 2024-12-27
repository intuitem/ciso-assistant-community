import pytest
from rest_framework.status import HTTP_403_FORBIDDEN
from rest_framework.test import APIClient
from core.models import (
    ComplianceAssessment,
    RequirementNode,
    RequirementAssessment,
    Framework,
)
from core.models import Project, AppliedControl
from iam.models import Folder

from test_utils import EndpointTestsQueries

# Generic requirement assessment data for tests
REQUIREMENT_ASSESSMENT_STATUS = "to_do"
REQUIREMENT_ASSESSMENT_STATUS2 = "in_progress"
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
                "score": None,
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
                "score": None,
            },
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS2,
                "folder": Folder.objects.create(name="test2").id,
            },
        )


@pytest.mark.django_db
class TestRequirementAssessmentsAuthenticated:
    """Perform tests on Requirement Assessments API endpoint with authentication"""

    def test_get_requirement_assessments(self, test):
        """test to get requirement assessments from the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test",
            project=Project.objects.create(name="test", folder=test.folder),
            framework=Framework.objects.all()[0],
        )

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "observation": REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": test.folder,
                "compliance_assessment": compliance_assessment,
                "requirement": RequirementNode.objects.all()[0],
                "score": None,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "compliance_assessment": {
                    "id": str(compliance_assessment.id),
                    "str": compliance_assessment.name,
                },
                "requirement": {
                    "id": str(RequirementNode.objects.all()[0].id),
                    "urn": RequirementNode.objects.all()[0].urn,
                    "annotation": RequirementNode.objects.all()[0].annotation,
                    "name": RequirementNode.objects.all()[0].name,
                    "description": RequirementNode.objects.all()[0].description,
                    "typical_evidence": RequirementNode.objects.all()[
                        0
                    ].typical_evidence,
                    "ref_id": RequirementNode.objects.all()[0].ref_id,
                    "associated_reference_controls": RequirementNode.objects.all()[
                        0
                    ].associated_reference_controls,
                    "associated_threats": RequirementNode.objects.all()[
                        0
                    ].associated_threats,
                    "parent_requirement": {
                        "str": RequirementNode.objects.all()[0].parent_requirement.get(
                            "str"
                        ),
                        "urn": RequirementNode.objects.all()[0].parent_requirement.get(
                            "urn"
                        ),
                        "id": str(
                            RequirementNode.objects.all()[0].parent_requirement.get(
                                "id"
                            )
                        ),
                        "ref_id": RequirementNode.objects.all()[
                            0
                        ].parent_requirement.get("ref_id"),
                        "name": RequirementNode.objects.all()[0].parent_requirement.get(
                            "name"
                        ),
                        "description": RequirementNode.objects.all()[
                            0
                        ].parent_requirement.get("description"),
                    }
                    if RequirementNode.objects.all()[0].parent_requirement
                    else None,
                },
            },
            base_count=-1,
            user_group=test.user_group,
        )

    def test_create_requirement_assessments(self, test):
        """test to create requirement assessments with the API with authentication"""
        """nobody has permission to do that, so it will fail"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test",
            project=Project.objects.create(name="test", folder=test.folder),
            framework=Framework.objects.all()[0],
        )
        applied_control = AppliedControl.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "observation": REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": str(test.folder.id),
                "compliance_assessment": str(compliance_assessment.id),
                "requirement": str(RequirementNode.objects.all()[0].id),
                "applied_controls": [str(applied_control.id)],
                "score": None,
            },
            {
                "compliance_assessment": {
                    "id": str(compliance_assessment.id),
                    "str": compliance_assessment.name,
                }
            },
            base_count=-1,
            fails=True,
            expected_status=HTTP_403_FORBIDDEN,
        )

    def test_update_requirement_assessments(self, test):
        """test to update requirement assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        folder = Folder.objects.create(name="test2")
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test",
            project=Project.objects.create(name="test", folder=test.folder),
            framework=Framework.objects.all()[0],
        )
        compliance_assessment2 = ComplianceAssessment.objects.create(
            name="test2",
            project=Project.objects.create(name="test2", folder=folder),
            framework=Framework.objects.all()[0],
        )
        applied_control = AppliedControl.objects.create(name="test", folder=folder)

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "observation": REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": test.folder,
                "compliance_assessment": compliance_assessment,
                "requirement": RequirementNode.objects.all()[0],
                "score": None,
            },
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS2,
                "observation": "new " + REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": str(folder.id),
                "compliance_assessment": str(compliance_assessment2.id),
                "requirement": str(RequirementNode.objects.all()[1].id),
                "applied_controls": [str(applied_control.id)],
                "score": 3,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "compliance_assessment": {
                    "id": str(compliance_assessment.id),
                    "str": compliance_assessment.name,
                },
                "requirement": {
                    "id": str(RequirementNode.objects.all()[0].id),
                    "urn": RequirementNode.objects.all()[0].urn,
                    "annotation": RequirementNode.objects.all()[0].annotation,
                    "name": RequirementNode.objects.all()[0].name,
                    "description": RequirementNode.objects.all()[0].description,
                    "typical_evidence": RequirementNode.objects.all()[
                        0
                    ].typical_evidence,
                    "ref_id": RequirementNode.objects.all()[0].ref_id,
                    "associated_reference_controls": RequirementNode.objects.all()[
                        0
                    ].associated_reference_controls,
                    "associated_threats": RequirementNode.objects.all()[
                        0
                    ].associated_threats,
                    "parent_requirement": {
                        "str": RequirementNode.objects.all()[0].parent_requirement.get(
                            "str"
                        ),
                        "urn": RequirementNode.objects.all()[0].parent_requirement.get(
                            "urn"
                        ),
                        "id": str(
                            RequirementNode.objects.all()[0].parent_requirement.get(
                                "id"
                            )
                        ),
                        "ref_id": RequirementNode.objects.all()[
                            0
                        ].parent_requirement.get("ref_id"),
                        "name": RequirementNode.objects.all()[0].parent_requirement.get(
                            "name"
                        ),
                        "description": RequirementNode.objects.all()[
                            0
                        ].parent_requirement.get("description"),
                    }
                    if RequirementNode.objects.all()[0].parent_requirement
                    else None,
                },
            },
            user_group=test.user_group,
        )

    def test_get_status_choices(self, test):
        """test to get requirement assessments status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Requirement Assessments",
            "status",
            RequirementAssessment.Status.choices,
            user_group=test.user_group,
        )
