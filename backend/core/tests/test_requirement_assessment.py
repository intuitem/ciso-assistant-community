import pytest
from django.contrib.auth import get_user_model
from django.utils.translation import override
from core.models import (
    StoredLibrary,
    Framework,
    ComplianceAssessment,
    Perimeter,
    ReferenceControl,
    RequirementAssessment,
    RequirementNode,
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
    @pytest.mark.usefixtures(
        "domain_perimeter_fixture", "enisa_5g_scm_framework_fixture"
    )
    def test_create_applied_controls_from_suggestions(self):
        enisa_5g_scm = Framework.objects.first()
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test compliance assessment",
            framework=enisa_5g_scm,
            folder=Folder.objects.filter(
                content_type=Folder.ContentType.DOMAIN
            ).first(),
            perimeter=Perimeter.objects.first(),
        )

        requirement_assessments: list[RequirementAssessment] = (
            compliance_assessment.create_requirement_assessments()
        )
        assert requirement_assessments is not None
        assert len(requirement_assessments) > 0

        for requirement_assessment in requirement_assessments:
            requirement_assessment.create_applied_controls_from_suggestions()

            if len(requirement_assessment.requirement.reference_controls.all()) == 0:
                assert requirement_assessment.applied_controls.all().count() == 0
                return

            assert requirement_assessment.applied_controls.all() is not None
            assert len(requirement_assessment.applied_controls.all()) > 0
            for control in requirement_assessment.applied_controls.all():
                assert (
                    control.reference_control
                    in requirement_assessment.requirement.reference_controls.all()
                )

            # NOTE: running create_applied_controls_from_suggestions agani MUST not create
            # any new applied control.

            applied_controls_count: int = (
                requirement_assessment.applied_controls.all().count()
            )
            requirement_assessment.create_applied_controls_from_suggestions()
            assert (
                requirement_assessment.applied_controls.all().count()
                == applied_controls_count
            )

    @pytest.mark.usefixtures("domain_perimeter_fixture")
    def test_suggested_applied_control_description_is_translated(self):
        folder = Folder.objects.get(name="test folder")
        framework = Framework.objects.create(name="test framework", folder=folder)
        reference_control = ReferenceControl.objects.create(
            name="Monitor supplier services",
            description="This control ensures supplier services are monitored.",
            ref_id="A.5.22",
            category="process",
            folder=folder,
            translations={
                "es": {
                    "description": "Este control garantiza que los servicios de los proveedores se supervisen.",
                }
            },
        )
        requirement = RequirementNode.objects.create(
            framework=framework,
            urn="urn:test:a522",
            ref_id="A.5.22",
            name="Supplier services",
            assessable=True,
            folder=folder,
        )
        requirement.reference_controls.add(reference_control)
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test compliance assessment",
            framework=framework,
            folder=folder,
            perimeter=Perimeter.objects.get(name="test perimeter"),
        )
        requirement_assessment = RequirementAssessment.objects.create(
            requirement=requirement,
            compliance_assessment=compliance_assessment,
            folder=folder,
        )

        with override("es"):
            preview = requirement_assessment.preview_suggested_applied_controls()
            assert (
                preview[0]["applied_control"].description
                == "Este control garantiza que los servicios de los proveedores se supervisen."
            )
            created = requirement_assessment.create_applied_controls_from_suggestions()
            assert (
                created[0].description
                == "Este control garantiza que los servicios de los proveedores se supervisen."
            )
