"""Tests for scoring logic with the new relational Question/Answer models."""

import pytest
from core.models import (
    Answer,
    ComplianceAssessment,
    Framework,
    Question,
    QuestionChoice,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder


@pytest.fixture
def scoring_setup(db):
    """Set up a framework with scored questions for testing."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Scoring Test Framework",
        folder=folder,
        status=Framework.Status.PUBLISHED,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:score:req:001",
        ref_id="SCORE-REQ",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    q1 = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:score:q1",
        ref_id="SQ1",
        annotation="Question 1",
        type=Question.Type.SINGLE_CHOICE,
        order=0,
        weight=1,
        folder=folder,
        is_published=True,
    )
    choice_good = QuestionChoice.objects.create(
        question=q1,
        ref_id="SC1A",
        annotation="Good",
        add_score=10,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    choice_bad = QuestionChoice.objects.create(
        question=q1,
        ref_id="SC1B",
        annotation="Bad",
        add_score=0,
        compute_result="false",
        order=1,
        folder=folder,
        is_published=True,
    )

    from core.models import Perimeter

    perimeter = Perimeter.objects.create(name="Score Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Score CA",
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
        "question": q1,
        "choice_good": choice_good,
        "choice_bad": choice_bad,
        "ca": ca,
        "ra": ra,
        "folder": folder,
    }


@pytest.mark.django_db
class TestScoring:
    def test_single_choice_scoring_compliant(self, scoring_setup):
        data = scoring_setup
        ra = data["ra"]
        q = data["question"]
        folder = data["folder"]

        Answer.objects.create(
            requirement_assessment=ra,
            question=q,
            selected_choice=data["choice_good"],  # score=10, result=true
            folder=folder,
        )

        ra.compute_score_and_result()
        ra.refresh_from_db()

        assert ra.score == 10
        assert ra.result == "compliant"
        assert ra.is_scored is True

    def test_single_choice_scoring_non_compliant(self, scoring_setup):
        data = scoring_setup
        ra = data["ra"]
        q = data["question"]
        folder = data["folder"]

        Answer.objects.create(
            requirement_assessment=ra,
            question=q,
            selected_choice=data["choice_bad"],  # score=0, result=false
            folder=folder,
        )

        ra.compute_score_and_result()
        ra.refresh_from_db()

        assert ra.score == 0
        assert ra.result == "non_compliant"

    def test_no_visible_questions_gives_not_applicable(self, db):
        """A requirement node with no questions -> not_applicable."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Empty Q FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:empty:req:001",
            ref_id="EMP-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )

        from core.models import Perimeter

        perimeter = Perimeter.objects.create(name="Empty Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Empty CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "not_applicable"

    def test_unanswered_questions_gives_not_assessed(self, scoring_setup):
        """When not all visible questions are answered -> not_assessed."""
        data = scoring_setup
        ra = data["ra"]
        q = data["question"]
        folder = data["folder"]

        # Create answer with no selected_choice (unanswered single choice)
        Answer.objects.create(
            requirement_assessment=ra,
            question=q,
            folder=folder,
        )

        ra.compute_score_and_result()
        ra.refresh_from_db()
        assert ra.result == "not_assessed"

    def test_weight_aware_scoring(self, db):
        """Test that scoring respects question weights."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Weight FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:weight:req:001",
            ref_id="W-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )

        # Question with weight=3
        q1 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:weight:q1",
            ref_id="WQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            weight=3,
            folder=folder,
            is_published=True,
        )
        choice_yes = QuestionChoice.objects.create(
            question=q1,
            ref_id="WC1A",
            annotation="Yes",
            add_score=10,
            compute_result="true",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="WC1B",
            annotation="No",
            add_score=0,
            compute_result="false",
            order=1,
            folder=folder,
            is_published=True,
        )

        from core.models import Perimeter

        perimeter = Perimeter.objects.create(name="Weight Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Weight CA",
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

        Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            selected_choice=choice_yes,  # score=10, weight=3 -> total_score=30
            folder=folder,
        )

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # With mean aggregation: 30 / 3 = 10
        assert ra.score == 10

    def test_depends_on_visibility(self, db):
        """Test depends_on hides questions correctly."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Depends FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:depends:req:001",
            ref_id="DEP-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )

        # Q1: single_choice
        q1 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:depends:q1",
            ref_id="DQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1, ref_id="DC1A", annotation="Yes",
            add_score=10, compute_result="true", order=0,
            folder=folder, is_published=True,
        )
        choice_no = QuestionChoice.objects.create(
            question=q1, ref_id="DC1B", annotation="No",
            add_score=0, compute_result="true", order=1,
            folder=folder, is_published=True,
        )

        # Q2: depends on Q1 answer being "DC1A"
        q2 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:depends:q2",
            ref_id="DQ2",
            type=Question.Type.SINGLE_CHOICE,
            depends_on={
                "question": "DQ1",
                "answers": ["DC1A"],
                "condition": "any",
            },
            order=1,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2, ref_id="DC2A", annotation="Sub-Yes",
            add_score=5, compute_result="true", order=0,
            folder=folder, is_published=True,
        )
        QuestionChoice.objects.create(
            question=q2, ref_id="DC2B", annotation="Sub-No",
            add_score=0, compute_result="false", order=1,
            folder=folder, is_published=True,
        )

        from core.models import Perimeter

        perimeter = Perimeter.objects.create(name="Dep Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Dep CA",
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

        # Answer Q1 with "DC1B" -> Q2 should be hidden
        Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            selected_choice=choice_no,
            folder=folder,
        )

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Only Q1 is visible (answered "No"), Q2 is hidden
        # result = compliant (Q1 compute_result is true)
        assert ra.result == "compliant"

    def test_multiple_choice_scoring(self, db):
        """Test scoring with multiple choice questions using M2M."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Multi FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:multi:req:001",
            ref_id="MULTI-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:multi:q1",
            ref_id="MQ1",
            type=Question.Type.MULTIPLE_CHOICE,
            order=0,
            weight=1,
            folder=folder,
            is_published=True,
        )
        c1 = QuestionChoice.objects.create(
            question=q, ref_id="MC1", annotation="A",
            add_score=5, compute_result="true", order=0,
            folder=folder, is_published=True,
        )
        c2 = QuestionChoice.objects.create(
            question=q, ref_id="MC2", annotation="B",
            add_score=3, compute_result="true", order=1,
            folder=folder, is_published=True,
        )

        from core.models import Perimeter

        perimeter = Perimeter.objects.create(name="Multi Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Multi CA",
            framework=fw, folder=folder, perimeter=perimeter,
            is_published=True, min_score=0, max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn, folder=folder,
        )

        answer = Answer.objects.create(
            requirement_assessment=ra, question=q, folder=folder,
        )
        answer.selected_choices.set([c1, c2])

        ra.compute_score_and_result()
        ra.refresh_from_db()

        # Both choices selected: add_score 5 + 3 = 8 total, weight 1+1=2
        # But weight is per-question, not per-choice. Each choice adds
        # score * weight, but total_weight only increments once per choice match.
        # Actually looking at the code: each choice match adds score*weight and weight.
        # So total_score = 5*1 + 3*1 = 8, total_weight = 1+1 = 2, mean = 4
        assert ra.score == 4
        assert ra.result == "compliant"
