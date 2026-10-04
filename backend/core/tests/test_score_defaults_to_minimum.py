"""score_defaults_to_minimum: applicable requirements always have a score, the
scale minimum until assessed, as in the CCB CyFun tools."""

import pytest

from core.models import (
    ComplianceAssessment,
    Framework,
    Question,
    RequirementAssessment,
    RequirementNode,
)
from core.serializers import ComplianceAssessmentWriteSerializer
from core.utils import EVERYONE_EDIT
from iam.models import Folder

NA = RequirementAssessment.Result.NOT_APPLICABLE
SCORES_VISIBLE = {
    field: EVERYONE_EDIT for field in ("score", "is_scored", "documentation_score")
}


@pytest.fixture
def framework():
    folder = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="Defaults",
        urn="urn:test:framework:score-defaults",
        folder=folder,
        min_score=1,
        max_score=5,
        field_visibility=SCORES_VISIBLE,
        score_defaults_to_minimum=True,
    )
    for ref_id, min_score in (("plain", None), ("offset", 2), ("asked", None)):
        RequirementNode.objects.create(
            urn=f"urn:test:score-defaults:{ref_id}",
            ref_id=ref_id,
            framework=framework,
            assessable=True,
            folder=folder,
            min_score=min_score,
            max_score=5 if min_score else None,
        )
    Question.objects.create(
        requirement_node=RequirementNode.objects.get(ref_id="asked"),
        urn="urn:test:score-defaults:asked:question",
        ref_id="Q",
        text="Q",
        type=Question.Type.UNIQUE_CHOICE,
        order=0,
        weight=1,
        folder=folder,
    )
    return framework


def _audit(framework, **data):
    serializer = ComplianceAssessmentWriteSerializer(
        data={
            "name": "Audit",
            "folder": str(Folder.get_root_folder().id),
            "framework": str(framework.id),
            **data,
        }
    )
    assert serializer.is_valid(), serializer.errors
    audit = serializer.save()
    audit.create_requirement_assessments()
    return audit


def _ra(audit, ref_id):
    return RequirementAssessment.objects.get(
        compliance_assessment=audit, requirement__ref_id=ref_id
    )


def _scores(ra):
    ra.refresh_from_db()
    return ra.is_scored, ra.score, ra.documentation_score


@pytest.mark.django_db
class TestScoreDefaultsToMinimum:
    def test_proposed_by_the_framework(self, framework):
        assert framework.default_scoring["score_defaults_to_minimum"] is True
        assert _audit(framework).score_defaults_to_minimum is True

    def test_new_audit_starts_at_the_minimum(self, framework):
        audit = _audit(framework)
        assert _scores(_ra(audit, "plain")) == (True, 1, 1)
        # The requirement's own scale.
        assert _scores(_ra(audit, "offset")) == (True, 2, 2)
        # Answers compute this one.
        assert _scores(_ra(audit, "asked"))[1] is None

    def test_returned_requirement_assessments_match_the_database(self, framework):
        audit = _audit(framework)
        audit.requirement_assessments.all().delete()
        created = audit.create_requirement_assessments()
        plain = next(ra for ra in created if ra.requirement.ref_id == "plain")
        assert (plain.is_scored, plain.score, plain.documentation_score) == (True, 1, 1)

    def test_not_applicable_requirements_are_left_alone(self, framework):
        audit = _audit(framework)
        RequirementAssessment.objects.filter(compliance_assessment=audit).update(
            result=NA, is_scored=False, score=None, documentation_score=None
        )
        ra = _ra(audit, "plain")
        ra.observation = "excluded"
        ra.save()
        assert _scores(ra) == (False, None, None)

        # Applicable again: the minimum, even when saving only the result.
        ra.result = RequirementAssessment.Result.COMPLIANT
        ra.save(update_fields=["result"])
        assert _scores(ra) == (True, 1, 1)

    def test_switched_off_scores_start_over_at_the_minimum(self, framework):
        audit = _audit(framework)
        ra = _ra(audit, "plain")
        ra.is_scored, ra.score, ra.documentation_score = False, 4, 3
        ra.save()
        assert _scores(ra) == (True, 1, 1)

    def test_entered_scores_are_kept(self, framework):
        audit = _audit(framework)
        ra = _ra(audit, "plain")
        ra.score, ra.documentation_score = 4, 3
        ra.save()
        assert _scores(ra) == (True, 4, 3)

    def test_turning_it_on_fills_an_existing_audit(self, framework):
        audit = _audit(framework, score_defaults_to_minimum=False)
        assert _scores(_ra(audit, "plain"))[2] is None
        audit = ComplianceAssessment.objects.get(pk=audit.pk)
        audit.score_defaults_to_minimum = True
        audit.save()
        assert _scores(_ra(audit, "plain")) == (True, 1, 1)

    def test_turning_it_off_keeps_the_scores(self, framework):
        audit = _audit(framework)
        audit.score_defaults_to_minimum = False
        audit.save()
        assert _scores(_ra(audit, "plain")) == (True, 1, 1)

    def test_scoring_disabled_leaves_scores_unset(self, framework):
        audit = _audit(framework, field_visibility={"score": {"auditor": "hidden"}})
        assert _scores(_ra(audit, "plain"))[1] is None
