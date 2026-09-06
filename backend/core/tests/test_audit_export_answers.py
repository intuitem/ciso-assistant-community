"""Tests for the `answers` column shared by the audit CSV and XLSX exports,
exercised through the same model access the export views use."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

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
from core.utils import build_answers_dict, parse_answers_cell, render_answers_cell
from iam.models import Folder


def build_audit(name, requirement_count):
    """Framework with `requirement_count` requirements, each carrying a text and
    a single-choice question, plus an audit with one empty answer per question."""
    folder = Folder.get_root_folder()
    framework = Framework.objects.create(
        name=name, folder=folder, is_published=True, urn=f"urn:test:fw:{name}"
    )
    perimeter = Perimeter.objects.create(name=f"{name} perimeter", folder=folder)
    audit = ComplianceAssessment.objects.create(
        name=f"{name} audit",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        is_published=True,
    )

    for index in range(requirement_count):
        node = RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:{name}:req:{index}",
            ref_id=f"REQ-{index}",
            assessable=True,
            order_id=index,
            folder=folder,
            is_published=True,
        )
        q_text = Question.objects.create(
            requirement_node=node,
            urn=f"urn:test:{name}:q:text:{index}",
            ref_id=f"QT-{index}",
            text="Describe the control",
            type=Question.Type.TEXT,
            order=0,
            folder=folder,
            is_published=True,
        )
        q_choice = Question.objects.create(
            requirement_node=node,
            urn=f"urn:test:{name}:q:choice:{index}",
            ref_id=f"QC-{index}",
            text="Is it in place",
            type=Question.Type.UNIQUE_CHOICE,
            order=1,
            folder=folder,
            is_published=True,
        )
        for order, value in enumerate(("Yes", "No")):
            QuestionChoice.objects.create(
                question=q_choice,
                urn=f"urn:test:{name}:choice:{index}:{value}",
                ref_id=f"{value}-{index}",
                value=value,
                order=order,
                folder=folder,
                is_published=True,
            )
        assessment = RequirementAssessment.objects.create(
            compliance_assessment=audit,
            requirement=node,
            folder=folder,
        )
        for question in (q_text, q_choice):
            Answer.objects.create(
                requirement_assessment=assessment,
                question=question,
                folder=folder,
            )

    return audit


def render_all(audit):
    """The exact access pattern compliance_assessment_csv() uses per row."""
    return [
        render_answers_cell(
            req.requirement.get_questions_translated,
            build_answers_dict(req.answers.all()),
        )
        for req in audit.get_requirement_assessments(include_non_assessable=True)
    ]


@pytest.mark.django_db
class TestExportAnswersColumn:
    def test_unanswered_audit_renders_hints(self):
        audit = build_audit("hints", 1)
        (cell,) = render_all(audit)
        assert "Describe the control >> [free text]" in cell
        assert "Is it in place >> [Yes / No]" in cell
        assert cell.startswith("[urn:test:hints:q:text:0]")

    def test_answers_round_trip_through_the_cell(self):
        audit = build_audit("roundtrip", 1)
        assessment = audit.requirement_assessments.get()
        text_answer = assessment.answers.get(question__type=Question.Type.TEXT)
        text_answer.value = "Encrypted at rest\nand in transit"
        text_answer.save()
        choice_answer = assessment.answers.get(
            question__type=Question.Type.UNIQUE_CHOICE
        )
        choice_answer.selected_choices.set(
            [QuestionChoice.objects.get(urn="urn:test:roundtrip:choice:0:Yes")]
        )

        (cell,) = render_all(audit)
        questions = assessment.requirement.get_questions_translated
        parsed, warnings = parse_answers_cell(cell, questions)

        assert warnings == []
        assert parsed == {
            "urn:test:roundtrip:q:text:0": "Encrypted at rest\nand in transit",
            "urn:test:roundtrip:q:choice:0": "urn:test:roundtrip:choice:0:Yes",
        }

    def test_rendering_does_not_scale_with_requirement_count(self):
        """Guards the N+1 that would otherwise make a large audit's CSV export
        issue a query per requirement."""
        small = build_audit("small", 1)
        large = build_audit("large", 5)

        with CaptureQueriesContext(connection) as small_queries:
            render_all(small)
        with CaptureQueriesContext(connection) as large_queries:
            render_all(large)

        assert len(large_queries) == len(small_queries), (
            f"{len(small_queries)} queries for 1 requirement vs "
            f"{len(large_queries)} for 5: the per-requirement work is not prefetched"
        )
