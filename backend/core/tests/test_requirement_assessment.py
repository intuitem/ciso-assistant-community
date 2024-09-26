import pytest
from django.contrib.auth import get_user_model
from core.models import (
    StoredLibrary,
    Framework,
    ComplianceAssessment,
    Project,
    RequirementAssessment,
)
from iam.models import Folder

from .fixtures import *

User = get_user_model()


@pytest.fixture
def enisa_5g_scm_framework_fixture():
    enisa_5g_scm_library = StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:enisa-5g-scm-v1.3", locale="en"
    )
    assert enisa_5g_scm_library is not None
    enisa_5g_scm_library.load()


@pytest.mark.django_db
class TestRequirementAssessment:
    @pytest.mark.usefixtures("domain_project_fixture", "enisa_5g_scm_framework_fixture")
    def test_create_applied_controls_from_suggestions(self):
        enisa_5g_scm = Framework.objects.first()
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test compliance assessment",
            framework=enisa_5g_scm,
            folder=Folder.objects.filter(
                content_type=Folder.ContentType.DOMAIN
            ).first(),
            project=Project.objects.first(),
        )

        requirement_assessments: list[
            RequirementAssessment
        ] = compliance_assessment.create_requirement_assessments()
        assert requirement_assessments is not None
        assert len(requirement_assessments) > 0

        for requirement_assessment in requirement_assessments:
            requirement_assessment.create_applied_controls_from_suggestions()
            if len(requirement_assessment.requirement.reference_controls.all()) > 0:
                assert requirement_assessment.applied_controls.all() is not None
                assert len(requirement_assessment.applied_controls.all()) > 0
                for control in requirement_assessment.applied_controls.all():
                    assert (
                        control.reference_control
                        in requirement_assessment.requirement.reference_controls.all()
                    )
