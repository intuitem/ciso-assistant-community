"""Extended tests for scoring logic and visibility (depends_on) edge cases."""

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
def scoring_setup(db):
    """Set up a framework with two scored questions for testing edge cases."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Extended Scoring FW",
        folder=folder,
        status=Framework.Status.PUBLISHED,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:extscore:req:001",
        ref_id="EXT-REQ",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    # Q1: single choice
    q1 = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:extscore:q1",
        ref_id="EQ1",
        annotation="Question 1",
        type=Question.Type.SINGLE_CHOICE,
        order=0,
        weight=1,
        folder=folder,
        is_published=True,
    )
    q1_good = QuestionChoice.objects.create(
        question=q1,
        ref_id="EC1A",
        annotation="Good",
        add_score=10,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    q1_bad = QuestionChoice.objects.create(
        question=q1,
        ref_id="EC1B",
        annotation="Bad",
        add_score=0,
        compute_result="false",
        order=1,
        folder=folder,
        is_published=True,
    )

    # Q2: single choice
    q2 = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:extscore:q2",
        ref_id="EQ2",
        annotation="Question 2",
        type=Question.Type.SINGLE_CHOICE,
        order=1,
        weight=1,
        folder=folder,
        is_published=True,
    )
    q2_good = QuestionChoice.objects.create(
        question=q2,
        ref_id="EC2A",
        annotation="Good",
        add_score=10,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    q2_bad = QuestionChoice.objects.create(
        question=q2,
        ref_id="EC2B",
        annotation="Bad",
        add_score=0,
        compute_result="false",
        order=1,
        folder=folder,
        is_published=True,
    )

    perimeter = Perimeter.objects.create(name="Ext Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Ext CA",
        framework=fw,
        folder=folder,
        perimeter=perimeter,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    ra = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=rn,
        folder=folder,
    )
    return {
        "framework": fw,
        "requirement_node": rn,
        "q1": q1,
        "q1_good": q1_good,
        "q1_bad": q1_bad,
        "q2": q2,
        "q2_good": q2_good,
        "q2_bad": q2_bad,
        "ca": ca,
        "ra": ra,
        "folder": folder,
        "perimeter": perimeter,
    }


@pytest.mark.django_db
class TestScoringExtended:
    def test_partially_compliant_result(self, scoring_setup):
        """Two questions: one true, one false -> partially_compliant."""
        d = scoring_setup
        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # compute_result="true"

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_bad"]])  # compute_result="false"

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        assert d["ra"].result == "partially_compliant"

    def test_sum_aggregation_mode(self, scoring_setup):
        """SUM calculation method: score = raw sum, not divided by weight."""
        d = scoring_setup
        d["ca"].score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        d["ca"].save(update_fields=["score_calculation_method"])

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # add_score=10, weight=1

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])  # add_score=10, weight=1

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        # SUM: total_score = 10*1 + 10*1 = 20 (not divided by weight)
        assert d["ra"].score == 20

    def test_sum_aggregation_via_scores_definition(self, scoring_setup):
        """scores_definition.aggregation takes precedence over score_calculation_method."""
        d = scoring_setup
        # Set calculation method to AVG, but scores_definition overrides to sum
        d["ca"].score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        d["ca"].scores_definition = {"aggregation": "sum"}
        d["ca"].save(update_fields=["score_calculation_method", "scores_definition"])

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # add_score=10

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])  # add_score=10

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        # scores_definition aggregation "sum" overrides AVG -> raw sum = 20
        assert d["ra"].score == 20

    def test_score_clamped_to_min_max(self, db):
        """Score clamped to max_score and min_score."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Clamp FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
            min_score=0,
            max_score=50,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:clamp:req:001",
            ref_id="CL-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:clamp:q1",
            ref_id="CLQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            weight=1,
            folder=folder,
            is_published=True,
        )
        c_high = QuestionChoice.objects.create(
            question=q,
            ref_id="CLC1",
            annotation="Very high",
            add_score=100,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="CLC2",
            annotation="Placeholder",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Clamp Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Clamp CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=50,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn, folder=folder
        )

        answer = Answer.objects.create(
            requirement_assessment=ra, question=q, folder=folder
        )
        answer.selected_choices.set([c_high])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        assert ra.score == 50  # clamped to max_score

    def test_answered_question_with_no_score_no_result(self, scoring_setup):
        """Choice with add_score=None, compute_result=None -> no crash."""
        d = scoring_setup
        # Remove score/result from q1's choices
        d["q1_good"].add_score = None
        d["q1_good"].compute_result = None
        d["q1_good"].save()
        d["q1_bad"].add_score = None
        d["q1_bad"].compute_result = None
        d["q1_bad"].save()
        # Also for q2
        d["q2_good"].add_score = None
        d["q2_good"].compute_result = None
        d["q2_good"].save()
        d["q2_bad"].add_score = None
        d["q2_bad"].compute_result = None
        d["q2_bad"].save()

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        # No crash; results list empty -> not_assessed
        assert d["ra"].result == "not_assessed"
        assert d["ra"].is_scored is False

    def test_score_only_no_result_fields(self, scoring_setup):
        """Choices with add_score but compute_result=None -> only score+is_scored saved."""
        d = scoring_setup
        # Set choices to score-only
        for c in [d["q1_good"], d["q1_bad"], d["q2_good"], d["q2_bad"]]:
            c.compute_result = None
            c.save()

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # add_score=10

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])  # add_score=10

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        assert d["ra"].is_scored is True
        assert d["ra"].score == 10  # mean: (10+10)/2

    def test_result_only_no_score_fields(self, scoring_setup):
        """Choices with compute_result but add_score=None -> only result saved."""
        d = scoring_setup
        for c in [d["q1_good"], d["q1_bad"], d["q2_good"], d["q2_bad"]]:
            c.add_score = None
            c.save()

        a1 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q1"], folder=d["folder"]
        )
        a1.selected_choices.set([d["q1_good"]])  # compute_result="true"

        a2 = Answer.objects.create(
            requirement_assessment=d["ra"], question=d["q2"], folder=d["folder"]
        )
        a2.selected_choices.set([d["q2_good"]])  # compute_result="true"

        d["ra"].compute_score_and_result()
        d["ra"].refresh_from_db()

        assert d["ra"].result == "compliant"
        assert d["ra"].is_scored is False


@pytest.mark.django_db
class TestVisibilityEdgeCases:
    def _make_visibility_setup(self, folder, q1_type, q2_depends_on):
        """Helper to create framework with Q1->Q2 depends_on chain."""
        fw = Framework.objects.create(
            name=f"Vis FW {q2_depends_on}",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:test:vis:{id(q2_depends_on)}:req:001",
            ref_id="VIS-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q1 = Question.objects.create(
            requirement_node=rn,
            urn=f"urn:test:vis:{id(q2_depends_on)}:q1",
            ref_id="VQ1",
            type=q1_type,
            order=0,
            folder=folder,
            is_published=True,
        )
        q2 = Question.objects.create(
            requirement_node=rn,
            urn=f"urn:test:vis:{id(q2_depends_on)}:q2",
            ref_id="VQ2",
            type=Question.Type.SINGLE_CHOICE,
            depends_on=q2_depends_on,
            order=1,
            folder=folder,
            is_published=True,
        )
        return fw, rn, q1, q2

    def test_depends_on_condition_all_with_multiple_choice(self, db):
        """Q1 multi-choice answered ["A","B"], Q2 depends_on condition=all answers=["A","B"] -> visible."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.MULTIPLE_CHOICE,
            {"question": "VQ1", "answers": ["VA", "VB"], "condition": "all"},
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            ref_id="VA",
            annotation="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        c_b = QuestionChoice.objects.create(
            question=q1,
            ref_id="VB",
            annotation="B",
            add_score=5,
            compute_result="true",
            order=1,
            folder=folder,
            is_published=True,
        )
        # Q2 choices
        q2_c = QuestionChoice.objects.create(
            question=q2,
            ref_id="VQ2A",
            annotation="X",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="VQ2B",
            annotation="Y",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim All", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA All",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer Q1 with both ["VA","VB"] - Q2 should be visible
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a, c_b])

        a2 = Answer.objects.create(
            requirement_assessment=ra,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([q2_c])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Both Q1 and Q2 visible and answered -> result from both
        assert ra.result == "compliant"

    def test_depends_on_condition_all_partial_answer_hides(self, db):
        """Q1 multi-choice answered ["A"] only, Q2 depends_on condition=all answers=["A","B"] -> hidden."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.MULTIPLE_CHOICE,
            {"question": "VQ1", "answers": ["VA2", "VB2"], "condition": "all"},
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            ref_id="VA2",
            annotation="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="VB2",
            annotation="B",
            add_score=5,
            compute_result="true",
            order=1,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="VQ2C",
            annotation="X",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="VQ2D",
            annotation="Y",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim All2", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA All2",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer Q1 with only ["VA2"] - Q2 should be hidden (condition=all needs both)
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Only Q1 visible and answered -> compliant
        assert ra.result == "compliant"

    def test_depends_on_condition_all_with_single_choice(self, db):
        """Single-choice 'A', depends_on condition=all answers=['A'] -> visible."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.SINGLE_CHOICE,
            {"question": "VQ1", "answers": ["VSA"], "condition": "all"},
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            ref_id="VSA",
            annotation="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="VSB",
            annotation="B",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )
        q2_c = QuestionChoice.objects.create(
            question=q2,
            ref_id="VSQ2A",
            annotation="X",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="VSQ2B",
            annotation="Y",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim SC", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA SC",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a])

        a2 = Answer.objects.create(
            requirement_assessment=ra,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([q2_c])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        assert ra.result == "compliant"

    def test_chained_depends_on(self, db):
        """Q1->Q2->Q3 chain. Q3 visible only if Q2 is answered."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Chain FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:chain:req:001",
            ref_id="CH-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q1 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:chain:q1",
            ref_id="CHQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        q1_c = QuestionChoice.objects.create(
            question=q1,
            ref_id="CHC1A",
            annotation="Yes",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="CHC1B",
            annotation="No",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        q2 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:chain:q2",
            ref_id="CHQ2",
            type=Question.Type.SINGLE_CHOICE,
            order=1,
            depends_on={"question": "CHQ1", "answers": ["CHC1A"], "condition": "any"},
            folder=folder,
            is_published=True,
        )
        q2_c = QuestionChoice.objects.create(
            question=q2,
            ref_id="CHC2A",
            annotation="Sub-Yes",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="CHC2B",
            annotation="Sub-No",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        q3 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:chain:q3",
            ref_id="CHQ3",
            type=Question.Type.SINGLE_CHOICE,
            order=2,
            depends_on={"question": "CHQ2", "answers": ["CHC2A"], "condition": "any"},
            folder=folder,
            is_published=True,
        )
        q3_c = QuestionChoice.objects.create(
            question=q3,
            ref_id="CHC3A",
            annotation="Deep-Yes",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q3,
            ref_id="CHC3B",
            annotation="Deep-No",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Chain Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Chain CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer all three in chain
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([q1_c])
        a2 = Answer.objects.create(
            requirement_assessment=ra,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([q2_c])
        a3 = Answer.objects.create(
            requirement_assessment=ra,
            question=q3,
            folder=folder,
        )
        a3.selected_choices.set([q3_c])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # All 3 visible and answered -> compliant
        assert ra.result == "compliant"

    def test_depends_on_with_unanswered_dependency(self, db):
        """Q2 depends on Q1, Q1 not answered -> Q2 hidden."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.SINGLE_CHOICE,
            {"question": "VQ1", "answers": ["VUA"], "condition": "any"},
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="VUA",
            annotation="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="VUB",
            annotation="B",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="VUQ2A",
            annotation="X",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="VUQ2B",
            annotation="Y",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim UA", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA UA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Don't answer Q1 at all -> Q2 hidden, only Q1 is visible but unanswered
        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Q1 visible but unanswered -> not_assessed
        assert ra.result == "not_assessed"

    def test_depends_on_with_empty_answers_list(self, db):
        """depends_on.answers=[] -> always hidden."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.SINGLE_CHOICE,
            {"question": "VQ1", "answers": [], "condition": "any"},
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            ref_id="VEA",
            annotation="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="VEB",
            annotation="B",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="VEQ2A",
            annotation="X",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="VEQ2B",
            annotation="Y",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim Empty", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA Empty",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer Q1 -> Q2 still hidden because answers=[]
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Only Q1 visible and answered -> compliant (from Q1's result)
        assert ra.result == "compliant"

    def test_depends_on_with_unknown_condition(self, db):
        """condition='foo' -> fallback returns True (visible)."""
        folder = Folder.get_root_folder()
        fw, rn, q1, q2 = self._make_visibility_setup(
            folder,
            Question.Type.SINGLE_CHOICE,
            {"question": "VQ1", "answers": ["VFA"], "condition": "foo"},
        )
        c_a = QuestionChoice.objects.create(
            question=q1,
            ref_id="VFA",
            annotation="A",
            add_score=5,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="VFB",
            annotation="B",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )
        q2_c = QuestionChoice.objects.create(
            question=q2,
            ref_id="VFQ2A",
            annotation="X",
            add_score=1,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="VFQ2B",
            annotation="Y",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="Vis Perim Foo", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Vis CA Foo",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer Q1 -> Q2 is visible (unknown condition falls through to True)
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_a])
        a2 = Answer.objects.create(
            requirement_assessment=ra,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([q2_c])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Both visible and answered -> compliant
        assert ra.result == "compliant"
