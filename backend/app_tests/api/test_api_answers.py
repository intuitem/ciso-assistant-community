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


@pytest.mark.django_db
class TestAnswerEndpoints:
    def test_unauthenticated_list_returns_401(self):
        client = APIClient()
        response = client.get(reverse("answers-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_answer(self, authenticated_client, framework_with_questions):
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
        assert Answer.objects.filter(
            requirement_assessment=ra, question=q
        ).exists()

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
            value="AC1",
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
            value="AC1",
            folder=folder,
        )

        response = authenticated_client.patch(
            reverse("answers-detail", args=[answer.id]),
            {"value": "AC2"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        answer.refresh_from_db()
        assert answer.value == "AC2"

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
