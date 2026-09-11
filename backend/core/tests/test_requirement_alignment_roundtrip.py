"""The respondent_alignment auto-map must not fire on an unchanged empty value.

The requirement edit form round-trips every field. When `result` is hidden the
frontend strips it from the PATCH, so the auto-map block is reached with a
`respondent_alignment` that was never set, and used to wipe result and scores.
"""

import pytest

from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from core.serializers import RequirementAssessmentWriteSerializer
from iam.models import Folder


@pytest.fixture
def requirement_assessment():
    root = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="Alignment Framework",
        urn="urn:test:fw-alignment",
        min_score=0,
        max_score=100,
        folder=root,
    )
    folder = Folder.objects.create(parent_folder=root, name="alignment folder")
    perimeter = Perimeter.objects.create(name="alignment perimeter", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Alignment CA",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        min_score=0,
        max_score=100,
    )
    ca.scoring_enabled = True
    ca.save()
    node = RequirementNode.objects.create(
        urn="urn:test:r-alignment",
        framework=framework,
        assessable=True,
        folder=root,
    )
    return RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=node,
        folder=folder,
        result=RequirementAssessment.Result.COMPLIANT,
        is_scored=True,
        score=80,
        documentation_score=60,
    )


def _update(ra, data):
    serializer = RequirementAssessmentWriteSerializer(ra, data=data, partial=True)
    assert serializer.is_valid(), serializer.errors
    serializer.save()
    ra.refresh_from_db()


@pytest.mark.django_db
class TestRespondentAlignmentRoundtrip:
    def test_empty_alignment_roundtrip_keeps_score_and_result(
        self, requirement_assessment
    ):
        _update(
            requirement_assessment,
            {"respondent_alignment": None, "observation": "saved without result"},
        )
        assert requirement_assessment.score == 80
        assert requirement_assessment.documentation_score == 60
        assert requirement_assessment.result == RequirementAssessment.Result.COMPLIANT

    def test_real_deselection_still_resets(self, requirement_assessment):
        _update(requirement_assessment, {"respondent_alignment": "yes"})
        assert requirement_assessment.result == RequirementAssessment.Result.COMPLIANT

        _update(requirement_assessment, {"respondent_alignment": None})
        assert requirement_assessment.score is None
        assert requirement_assessment.documentation_score is None
        assert (
            requirement_assessment.result == RequirementAssessment.Result.NOT_ASSESSED
        )

    def test_alignment_still_maps_to_result(self, requirement_assessment):
        _update(requirement_assessment, {"respondent_alignment": "no"})
        assert (
            requirement_assessment.result == RequirementAssessment.Result.NON_COMPLIANT
        )
