"""Tests for build_questions_dict() and build_answers_dict() utility functions."""

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
from core.utils import build_answers_dict, build_questions_dict
from iam.models import Folder


@pytest.fixture
def node_with_questions(db):
    """RequirementNode with questions of various types and choices with all optional fields."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Dict Test FW",
        folder=folder,
        status=Framework.Status.PUBLISHED,
        is_published=True,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:dict:req:001",
        ref_id="DICT-REQ",
        assessable=True,
        folder=folder,
        is_published=True,
    )

    # Single-choice question
    q_sc = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:dict:q_sc",
        ref_id="QSC",
        annotation="Pick one color",
        type=Question.Type.SINGLE_CHOICE,
        order=0,
        folder=folder,
        is_published=True,
    )
    c_sc_1 = QuestionChoice.objects.create(
        question=q_sc,
        ref_id="SC1",
        annotation="Red",
        add_score=10,
        compute_result="true",
        order=0,
        description="A red choice",
        color="#FF0000",
        select_implementation_groups=["basic"],
        folder=folder,
        is_published=True,
    )
    c_sc_2 = QuestionChoice.objects.create(
        question=q_sc,
        ref_id="SC2",
        annotation="Blue",
        add_score=5,
        compute_result="false",
        order=1,
        folder=folder,
        is_published=True,
    )

    # Multiple-choice question
    q_mc = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:dict:q_mc",
        ref_id="QMC",
        annotation="Select all that apply",
        type=Question.Type.MULTIPLE_CHOICE,
        order=1,
        folder=folder,
        is_published=True,
    )
    c_mc_1 = QuestionChoice.objects.create(
        question=q_mc,
        ref_id="MC1",
        annotation="Option A",
        add_score=3,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    c_mc_2 = QuestionChoice.objects.create(
        question=q_mc,
        ref_id="MC2",
        annotation="Option B",
        add_score=2,
        compute_result="true",
        order=1,
        folder=folder,
        is_published=True,
    )

    # Text question
    q_text = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:dict:q_text",
        ref_id="QTXT",
        annotation="Describe your approach",
        type=Question.Type.TEXT,
        order=2,
        folder=folder,
        is_published=True,
    )

    # Question with depends_on
    q_dep = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:dict:q_dep",
        ref_id="QDEP",
        annotation="Follow-up",
        type=Question.Type.SINGLE_CHOICE,
        order=3,
        depends_on={"question": "QSC", "answers": ["SC1"], "condition": "any"},
        folder=folder,
        is_published=True,
    )
    c_dep_1 = QuestionChoice.objects.create(
        question=q_dep,
        ref_id="DEP1",
        annotation="Yes",
        add_score=1,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q_dep,
        ref_id="DEP2",
        annotation="No",
        add_score=0,
        compute_result="false",
        order=1,
        folder=folder,
        is_published=True,
    )

    perimeter = Perimeter.objects.create(name="Dict Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Dict CA",
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

    return {
        "rn": rn,
        "q_sc": q_sc,
        "c_sc_1": c_sc_1,
        "c_sc_2": c_sc_2,
        "q_mc": q_mc,
        "c_mc_1": c_mc_1,
        "c_mc_2": c_mc_2,
        "q_text": q_text,
        "q_dep": q_dep,
        "c_dep_1": c_dep_1,
        "ca": ca,
        "ra": ra,
        "folder": folder,
    }


@pytest.mark.django_db
class TestBuildQuestionsDict:
    def test_basic_single_choice(self, node_with_questions):
        d = node_with_questions
        result = build_questions_dict(d["rn"])

        assert result is not None
        sc_entry = result["urn:test:dict:q_sc"]
        assert sc_entry["type"] == "unique_choice"
        assert sc_entry["text"] == "Pick one color"
        assert len(sc_entry["choices"]) == 2
        assert sc_entry["choices"][0]["urn"] == "SC1"
        assert sc_entry["choices"][0]["value"] == "Red"

    def test_type_mapping(self, node_with_questions):
        d = node_with_questions
        result = build_questions_dict(d["rn"])

        assert result["urn:test:dict:q_sc"]["type"] == "unique_choice"
        assert result["urn:test:dict:q_mc"]["type"] == "multiple_choice"
        assert result["urn:test:dict:q_text"]["type"] == "text"

    def test_optional_fields_present(self, node_with_questions):
        d = node_with_questions
        result = build_questions_dict(d["rn"])

        sc_choices = result["urn:test:dict:q_sc"]["choices"]
        # First choice has description, color, select_implementation_groups
        first_choice = sc_choices[0]
        assert first_choice["description"] == "A red choice"
        assert first_choice["color"] == "#FF0000"
        assert first_choice["select_implementation_groups"] == ["basic"]

    def test_optional_fields_absent(self, node_with_questions):
        d = node_with_questions
        result = build_questions_dict(d["rn"])

        sc_choices = result["urn:test:dict:q_sc"]["choices"]
        # Second choice has no description, color, select_implementation_groups
        second_choice = sc_choices[1]
        assert "description" not in second_choice
        assert "color" not in second_choice
        assert "select_implementation_groups" not in second_choice

    def test_depends_on_included(self, node_with_questions):
        d = node_with_questions
        result = build_questions_dict(d["rn"])

        dep_entry = result["urn:test:dict:q_dep"]
        assert "depends_on" in dep_entry
        assert dep_entry["depends_on"]["question"] == "QSC"
        assert dep_entry["depends_on"]["answers"] == ["SC1"]
        assert dep_entry["depends_on"]["condition"] == "any"

    def test_returns_none_for_no_questions(self, db):
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Empty Q FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:noq:req:001",
            ref_id="NOQ-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        result = build_questions_dict(rn)
        assert result is None

    def test_compute_result_boolean_conversion(self, node_with_questions):
        d = node_with_questions
        result = build_questions_dict(d["rn"])

        sc_choices = result["urn:test:dict:q_sc"]["choices"]
        # compute_result="true" -> True
        assert sc_choices[0]["compute_result"] is True
        # compute_result="false" -> False
        assert sc_choices[1]["compute_result"] is False


@pytest.mark.django_db
class TestBuildAnswersDict:
    def test_single_choice_returns_string(self, node_with_questions):
        d = node_with_questions
        a = Answer.objects.create(
            requirement_assessment=d["ra"],
            question=d["q_sc"],
            folder=d["folder"],
        )
        a.selected_choices.set([d["c_sc_1"]])

        answers_qs = (
            d["ra"]
            .answers.select_related("question")
            .prefetch_related("selected_choices")
            .all()
        )
        result = build_answers_dict(answers_qs)

        # Single choice returns a string, not a list
        assert result[d["q_sc"].urn] == "SC1"

    def test_multiple_choice_returns_list(self, node_with_questions):
        d = node_with_questions
        a = Answer.objects.create(
            requirement_assessment=d["ra"],
            question=d["q_mc"],
            folder=d["folder"],
        )
        a.selected_choices.set([d["c_mc_1"], d["c_mc_2"]])

        answers_qs = (
            d["ra"]
            .answers.select_related("question")
            .prefetch_related("selected_choices")
            .all()
        )
        result = build_answers_dict(answers_qs)

        # Multiple choice returns a list
        assert isinstance(result[d["q_mc"].urn], list)
        assert set(result[d["q_mc"].urn]) == {"MC1", "MC2"}

    def test_text_type_returns_raw_value(self, node_with_questions):
        d = node_with_questions
        Answer.objects.create(
            requirement_assessment=d["ra"],
            question=d["q_text"],
            folder=d["folder"],
            value="some text",
        )

        answers_qs = (
            d["ra"]
            .answers.select_related("question")
            .prefetch_related("selected_choices")
            .all()
        )
        result = build_answers_dict(answers_qs)

        assert result[d["q_text"].urn] == "some text"

    def test_unanswered_single_choice_returns_none(self, node_with_questions):
        d = node_with_questions
        Answer.objects.create(
            requirement_assessment=d["ra"],
            question=d["q_sc"],
            folder=d["folder"],
        )
        # No selected_choices set

        answers_qs = (
            d["ra"]
            .answers.select_related("question")
            .prefetch_related("selected_choices")
            .all()
        )
        result = build_answers_dict(answers_qs)

        assert result[d["q_sc"].urn] is None
