"""Tests for Answer API endpoints."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

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
def framework_with_questions(app_config):
    """Create a published framework with questions, choices, and a compliance assessment."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Answer Test Framework",
        folder=folder,
        status=Framework.Status.PUBLISHED,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:ans:req:001",
        ref_id="ANS-REQ-001",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    q = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:ans:q1",
        ref_id="AQ1",
        annotation="Pick one",
        type=Question.Type.SINGLE_CHOICE,
        order=0,
        folder=folder,
        is_published=True,
    )
    c1 = QuestionChoice.objects.create(
        question=q,
        ref_id="AC1",
        annotation="Choice A",
        add_score=10,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    c2 = QuestionChoice.objects.create(
        question=q,
        ref_id="AC2",
        annotation="Choice B",
        add_score=0,
        compute_result="false",
        order=1,
        folder=folder,
        is_published=True,
    )

    from core.models import Perimeter

    perimeter = Perimeter.objects.create(
        name="Test Perimeter",
        folder=folder,
    )
    ca = ComplianceAssessment.objects.create(
        name="Test CA",
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
        "framework": fw,
        "requirement_node": rn,
        "question": q,
        "choice_a": c1,
        "choice_b": c2,
        "compliance_assessment": ca,
        "requirement_assessment": ra,
    }


@pytest.fixture
def framework_with_multi_choice(app_config):
    """Create a framework with a multiple-choice question."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Multi Choice FW",
        folder=folder,
        status=Framework.Status.PUBLISHED,
        is_published=True,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:multi:req:001",
        ref_id="MC-REQ",
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
        folder=folder,
        is_published=True,
    )
    c1 = QuestionChoice.objects.create(
        question=q,
        ref_id="MC1",
        annotation="A",
        order=0,
        folder=folder,
        is_published=True,
    )
    c2 = QuestionChoice.objects.create(
        question=q,
        ref_id="MC2",
        annotation="B",
        order=1,
        folder=folder,
        is_published=True,
    )
    c3 = QuestionChoice.objects.create(
        question=q,
        ref_id="MC3",
        annotation="C",
        order=2,
        folder=folder,
        is_published=True,
    )

    from core.models import Perimeter

    perimeter = Perimeter.objects.create(name="MC Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="MC CA",
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
        "question": q,
        "choice_a": c1,
        "choice_b": c2,
        "choice_c": c3,
        "requirement_assessment": ra,
    }


@pytest.mark.django_db
class TestAnswerEndpoints:
    def test_unauthenticated_list_returns_401(self):
        client = APIClient()
        response = client.get(reverse("answers-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_answer_legacy_value(
        self, authenticated_client, framework_with_questions
    ):
        """Legacy: create single-choice answer using value (ref_id string)."""
        data = framework_with_questions
        ra = data["requirement_assessment"]
        q = data["question"]
        folder = Folder.get_root_folder()

        response = authenticated_client.post(
            reverse("answers-list"),
            {
                "requirement_assessment": str(ra.id),
                "question": str(q.id),
                "value": "AC1",
                "folder": str(folder.id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        answer = Answer.objects.get(requirement_assessment=ra, question=q)
        # Legacy value is resolved to FK
        assert answer.selected_choice == data["choice_a"]
        assert answer.value is None

    def test_create_answer_with_selected_choice(
        self, authenticated_client, framework_with_questions
    ):
        """Create single-choice answer using selected_choice FK (UUID)."""
        data = framework_with_questions
        ra = data["requirement_assessment"]
        q = data["question"]
        folder = Folder.get_root_folder()

        response = authenticated_client.post(
            reverse("answers-list"),
            {
                "requirement_assessment": str(ra.id),
                "question": str(q.id),
                "selected_choice": str(data["choice_b"].id),
                "folder": str(folder.id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        answer = Answer.objects.get(requirement_assessment=ra, question=q)
        assert answer.selected_choice == data["choice_b"]

    def test_unique_together_constraint(
        self, authenticated_client, framework_with_questions
    ):
        data = framework_with_questions
        ra = data["requirement_assessment"]
        q = data["question"]
        folder = Folder.get_root_folder()

        # Create first answer
        Answer.objects.create(
            requirement_assessment=ra,
            question=q,
            selected_choice=data["choice_a"],
            folder=folder,
        )

        # Try to create duplicate
        response = authenticated_client.post(
            reverse("answers-list"),
            {
                "requirement_assessment": str(ra.id),
                "question": str(q.id),
                "value": "AC2",
                "folder": str(folder.id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_answer(self, authenticated_client, framework_with_questions):
        data = framework_with_questions
        ra = data["requirement_assessment"]
        q = data["question"]
        folder = Folder.get_root_folder()

        answer = Answer.objects.create(
            requirement_assessment=ra,
            question=q,
            selected_choice=data["choice_a"],
            folder=folder,
        )

        response = authenticated_client.patch(
            reverse("answers-detail", args=[answer.id]),
            {"value": "AC2"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        answer.refresh_from_db()
        # Legacy value update resolves to FK
        assert answer.selected_choice == data["choice_b"]
        assert answer.value is None

    def test_answer_validation_single_choice_rejects_list(
        self, authenticated_client, framework_with_questions
    ):
        data = framework_with_questions
        ra = data["requirement_assessment"]
        q = data["question"]
        folder = Folder.get_root_folder()

        response = authenticated_client.post(
            reverse("answers-list"),
            {
                "requirement_assessment": str(ra.id),
                "question": str(q.id),
                "value": ["AC1", "AC2"],
                "folder": str(folder.id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_answer_validation_invalid_choice(
        self, authenticated_client, framework_with_questions
    ):
        data = framework_with_questions
        ra = data["requirement_assessment"]
        q = data["question"]
        folder = Folder.get_root_folder()

        response = authenticated_client.post(
            reverse("answers-list"),
            {
                "requirement_assessment": str(ra.id),
                "question": str(q.id),
                "value": "INVALID_CHOICE",
                "folder": str(folder.id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_selected_choice_must_belong_to_question(
        self, authenticated_client, framework_with_questions
    ):
        """selected_choice FK must reference a choice that belongs to the answer's question."""
        data = framework_with_questions
        ra = data["requirement_assessment"]
        q = data["question"]
        folder = Folder.get_root_folder()

        # Create another question with its own choice
        rn = data["requirement_node"]
        other_q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:ans:q_other",
            ref_id="AQ_OTHER",
            type=Question.Type.SINGLE_CHOICE,
            order=1,
            folder=folder,
            is_published=True,
        )
        other_choice = QuestionChoice.objects.create(
            question=other_q,
            ref_id="OC1",
            annotation="Other",
            order=0,
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("answers-list"),
            {
                "requirement_assessment": str(ra.id),
                "question": str(q.id),
                "selected_choice": str(other_choice.id),
                "folder": str(folder.id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_multiple_choice_legacy_value(
        self, authenticated_client, framework_with_multi_choice
    ):
        """Legacy: create multiple-choice answer using value (list of ref_id strings)."""
        data = framework_with_multi_choice
        ra = data["requirement_assessment"]
        q = data["question"]
        folder = Folder.get_root_folder()

        response = authenticated_client.post(
            reverse("answers-list"),
            {
                "requirement_assessment": str(ra.id),
                "question": str(q.id),
                "value": ["MC1", "MC3"],
                "folder": str(folder.id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        answer = Answer.objects.get(requirement_assessment=ra, question=q)
        assert answer.value is None
        selected = set(answer.selected_choices.values_list("ref_id", flat=True))
        assert selected == {"MC1", "MC3"}

    def test_create_multiple_choice_with_selected_choices(
        self, authenticated_client, framework_with_multi_choice
    ):
        """Create multiple-choice answer using selected_choices (list of UUIDs)."""
        data = framework_with_multi_choice
        ra = data["requirement_assessment"]
        q = data["question"]
        folder = Folder.get_root_folder()

        response = authenticated_client.post(
            reverse("answers-list"),
            {
                "requirement_assessment": str(ra.id),
                "question": str(q.id),
                "selected_choices": [
                    str(data["choice_a"].id),
                    str(data["choice_b"].id),
                ],
                "folder": str(folder.id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        answer = Answer.objects.get(requirement_assessment=ra, question=q)
        assert set(answer.selected_choices.values_list("id", flat=True)) == {
            data["choice_a"].id,
            data["choice_b"].id,
        }
