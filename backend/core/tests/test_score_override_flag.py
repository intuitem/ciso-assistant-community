"""Focused tests for is_score_overridden.

Covers:
- recompute_assessment honours the flag (pinned RA stays untouched).
- Clearing the flag lets recompute pick up new answers.
- Baseline copy propagates the flag on assessment clone.
"""

import pytest

from core.models import (
    Answer,
    ComplianceAssessment,
    Framework,
    Perimeter,
    Question,
    QuestionChoice,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder


@pytest.fixture
def question_driven_setup():
    folder = Folder.get_root_folder()
    perimeter = Perimeter.objects.create(name="p-override", folder=folder)
    fw = Framework.objects.create(
        name="FW override",
        urn="urn:test:fw-override",
        min_score=0,
        max_score=5,
        folder=folder,
    )
    rn = RequirementNode.objects.create(
        urn="urn:test:rn-override",
        framework=fw,
        assessable=True,
        folder=folder,
    )
    q = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:q-override",
        ref_id="Q",
        text="Q",
        type=Question.Type.UNIQUE_CHOICE,
        order=0,
        weight=1,
        folder=folder,
    )
    choice = QuestionChoice.objects.create(
        question=q,
        urn="urn:test:c-override",
        value="ok",
        add_score=3,
        order=0,
        folder=folder,
    )
    ca = ComplianceAssessment.objects.create(
        name="CA override",
        framework=fw,
        folder=folder,
        perimeter=perimeter,
        min_score=0,
        max_score=5,
    )
    ra = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=rn,
        folder=folder,
    )
    return {"ca": ca, "ra": ra, "question": q, "choice": choice, "folder": folder}


def _answer(ra, question, choice, folder):
    answer = Answer.objects.create(
        requirement_assessment=ra, question=question, folder=folder
    )
    answer.selected_choices.set([choice])
    return answer


@pytest.mark.django_db
class TestRecomputeHonoursOverride:
    def test_pinned_ra_ignores_answers(self, question_driven_setup):
        ctx = question_driven_setup
        ra = ctx["ra"]
        ra.score = 5
        ra.is_scored = True
        ra.is_score_overridden = True
        ra.save()
        _answer(ra, ctx["question"], ctx["choice"], ctx["folder"])

        ra.recompute_assessment()
        assert ra.score == 5
        assert ra.is_scored is True

    def test_clearing_flag_reopens_recompute(self, question_driven_setup):
        ctx = question_driven_setup
        ra = ctx["ra"]
        ra.score = None
        ra.is_scored = False
        ra.is_score_overridden = True
        ra.save()
        _answer(ra, ctx["question"], ctx["choice"], ctx["folder"])

        ra.recompute_assessment()
        assert ra.score is None  # still pinned

        ra.is_score_overridden = False
        ra.recompute_assessment()
        assert ra.score == 3
        assert ra.is_scored is True


@pytest.mark.django_db
class TestBaselineCloneCopiesFlag:
    def test_pinned_baseline_carries_over_to_clone(self, question_driven_setup):
        ctx = question_driven_setup
        baseline = ctx["ca"]
        ra = ctx["ra"]
        ra.score = 4
        ra.is_scored = True
        ra.is_score_overridden = True
        ra.save()

        clone = ComplianceAssessment.objects.create(
            name="CA clone",
            framework=baseline.framework,
            folder=baseline.folder,
            perimeter=baseline.perimeter,
            min_score=0,
            max_score=5,
        )
        clone.create_requirement_assessments(baseline=baseline)
        cloned_ra = RequirementAssessment.objects.get(
            compliance_assessment=clone, requirement=ra.requirement
        )
        assert cloned_ra.score == 4
        assert cloned_ra.is_score_overridden is True
