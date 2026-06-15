"""Tests for the `recompute_assessment_results` management command.

The command realigns stored RequirementAssessment.result/score for audits
built before the semantic compute_result aggregation. These tests cover the
behaviours that matter operationally: it fixes stale results, honours
--dry-run, is idempotent, and never touches requirements that are not
compute_result-driven (so a manually set result is preserved).
"""

from io import StringIO

import pytest
from django.core.management import call_command

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


def _answer(ra, question, choice, folder):
    answer = Answer.objects.create(
        requirement_assessment=ra, question=question, folder=folder
    )
    answer.selected_choices.set([choice])
    return answer


def _set_stored(ra, **fields):
    """Force stored columns without going through save() (no recompute)."""
    RequirementAssessment.objects.filter(pk=ra.pk).update(**fields)


@pytest.fixture
def command_setup(db):
    """One CA with two requirements:

    - rn_result: result-driven (choices carry compute_result), in command scope
    - rn_score: score-only (choices carry add_score but no compute_result),
      out of command scope
    """
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Recompute FW",
        folder=folder,
        is_published=True,
        min_score=0,
        max_score=100,
    )

    # --- result-driven requirement ---
    rn_result = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:recompute:req:result",
        ref_id="REQ-RESULT",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    q1 = Question.objects.create(
        requirement_node=rn_result,
        urn="urn:test:recompute:q1",
        ref_id="Q1",
        text="Q1",
        type=Question.Type.UNIQUE_CHOICE,
        order=0,
        weight=1,
        folder=folder,
        is_published=True,
    )
    q1_good = QuestionChoice.objects.create(
        question=q1,
        urn="urn:test:recompute:q1:good",
        ref_id="Q1A",
        value="Good",
        add_score=10,
        compute_result="compliant",
        order=0,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q1,
        urn="urn:test:recompute:q1:bad",
        ref_id="Q1B",
        value="Bad",
        add_score=0,
        compute_result="non_compliant",
        order=1,
        folder=folder,
        is_published=True,
    )
    q2 = Question.objects.create(
        requirement_node=rn_result,
        urn="urn:test:recompute:q2",
        ref_id="Q2",
        text="Q2",
        type=Question.Type.UNIQUE_CHOICE,
        order=1,
        weight=1,
        folder=folder,
        is_published=True,
    )
    q2_good = QuestionChoice.objects.create(
        question=q2,
        urn="urn:test:recompute:q2:good",
        ref_id="Q2A",
        value="Good",
        add_score=10,
        compute_result="compliant",
        order=0,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q2,
        urn="urn:test:recompute:q2:bad",
        ref_id="Q2B",
        value="Bad",
        add_score=0,
        compute_result="non_compliant",
        order=1,
        folder=folder,
        is_published=True,
    )

    # --- score-only requirement (no compute_result anywhere) ---
    rn_score = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:recompute:req:score",
        ref_id="REQ-SCORE",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    q3 = Question.objects.create(
        requirement_node=rn_score,
        urn="urn:test:recompute:q3",
        ref_id="Q3",
        text="Q3",
        type=Question.Type.UNIQUE_CHOICE,
        order=0,
        weight=1,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q3,
        urn="urn:test:recompute:q3:a",
        ref_id="Q3A",
        value="A",
        add_score=5,
        order=0,
        folder=folder,
        is_published=True,
    )

    perimeter = Perimeter.objects.create(name="Recompute Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Recompute CA",
        framework=fw,
        folder=folder,
        perimeter=perimeter,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    ra_result = RequirementAssessment.objects.create(
        compliance_assessment=ca, requirement=rn_result, folder=folder
    )
    ra_score = RequirementAssessment.objects.create(
        compliance_assessment=ca, requirement=rn_score, folder=folder
    )

    return {
        "folder": folder,
        "ca": ca,
        "rn_result": rn_result,
        "rn_score": rn_score,
        "q1": q1,
        "q1_good": q1_good,
        "q2": q2,
        "q2_good": q2_good,
        "ra_result": ra_result,
        "ra_score": ra_score,
    }


@pytest.mark.django_db
class TestRecomputeAssessmentResultsCommand:
    def _run(self, ca, *extra):
        out = StringIO()
        call_command(
            "recompute_assessment_results",
            "--compliance-assessment",
            str(ca.id),
            "--skip-post-hooks",
            *extra,
            stdout=out,
        )
        return out.getvalue()

    def test_fixes_stale_result(self, command_setup):
        """Both questions answered compliant -> stored non_compliant gets corrected."""
        d = command_setup
        _answer(d["ra_result"], d["q1"], d["q1_good"], d["folder"])
        _answer(d["ra_result"], d["q2"], d["q2_good"], d["folder"])
        # Simulate a stale boolean-collapse result.
        _set_stored(
            d["ra_result"],
            result=RequirementAssessment.Result.NON_COMPLIANT,
            score=None,
            is_scored=False,
        )

        self._run(d["ca"])

        d["ra_result"].refresh_from_db()
        assert d["ra_result"].result == RequirementAssessment.Result.COMPLIANT
        assert d["ra_result"].is_scored is True

    def test_dry_run_does_not_write(self, command_setup):
        d = command_setup
        _answer(d["ra_result"], d["q1"], d["q1_good"], d["folder"])
        _answer(d["ra_result"], d["q2"], d["q2_good"], d["folder"])
        _set_stored(d["ra_result"], result=RequirementAssessment.Result.NON_COMPLIANT)

        output = self._run(d["ca"], "--dry-run")

        d["ra_result"].refresh_from_db()
        # DB untouched...
        assert d["ra_result"].result == RequirementAssessment.Result.NON_COMPLIANT
        # ...but the run reports the change it would make.
        assert "DRY RUN" in output
        assert "changed=1" in output

    def test_idempotent_second_run_is_noop(self, command_setup):
        d = command_setup
        _answer(d["ra_result"], d["q1"], d["q1_good"], d["folder"])
        _answer(d["ra_result"], d["q2"], d["q2_good"], d["folder"])
        _set_stored(d["ra_result"], result=RequirementAssessment.Result.NON_COMPLIANT)

        first = self._run(d["ca"])
        assert "changed=1" in first

        second = self._run(d["ca"])
        assert "changed=0" in second

    def test_score_only_requirement_is_untouched(self, command_setup):
        """A score-only requirement is out of scope: a manual result is preserved."""
        d = command_setup
        _set_stored(d["ra_score"], result=RequirementAssessment.Result.COMPLIANT)

        self._run(d["ca"])

        d["ra_score"].refresh_from_db()
        assert d["ra_score"].result == RequirementAssessment.Result.COMPLIANT
