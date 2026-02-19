"""Tests for Question and QuestionChoice API endpoints."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Framework,
    RequirementNode,
    Question,
    QuestionChoice,
)
from iam.models import Folder


@pytest.fixture
def draft_framework(app_config):
    """Create a draft framework with a requirement node."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Test Framework",
        folder=folder,
        status=Framework.Status.DRAFT,
        is_published=True,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:framework:req:001",
        ref_id="REQ-001",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    return fw, rn


@pytest.fixture
def published_framework(app_config):
    """Create a published framework with a requirement node."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Published Framework",
        folder=folder,
        status=Framework.Status.PUBLISHED,
        is_published=True,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:published:req:001",
        ref_id="REQ-P001",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    return fw, rn


@pytest.mark.django_db
class TestQuestionEndpoints:
    """Test Question API endpoints."""

    def test_unauthenticated_list_returns_401(self):
        client = APIClient()
        response = client.get(reverse("questions-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_create_returns_401(self):
        client = APIClient()
        response = client.post(reverse("questions-list"), {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_questions(self, authenticated_client, draft_framework):
        fw, rn = draft_framework
        folder = Folder.get_root_folder()
        Question.objects.create(
            requirement_node=rn,
            urn="urn:test:q1",
            ref_id="Q1",
            annotation="What is your name?",
            type=Question.Type.TEXT,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.get(reverse("questions-list"))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] >= 1

    def test_create_question_on_draft_framework(
        self, authenticated_client, draft_framework
    ):
        fw, rn = draft_framework
        data = {
            "requirement_node": str(rn.id),
            "urn": "urn:test:new:q1",
            "ref_id": "NQ1",
            "annotation": "New question?",
            "type": "text",
            "order": 0,
            "folder": str(Folder.get_root_folder().id),
        }
        response = authenticated_client.post(
            reverse("questions-list"), data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Question.objects.filter(urn="urn:test:new:q1").exists()

    def test_create_question_on_published_framework_rejected(
        self, authenticated_client, published_framework
    ):
        fw, rn = published_framework
        data = {
            "requirement_node": str(rn.id),
            "urn": "urn:test:pub:q1",
            "ref_id": "PQ1",
            "annotation": "Should fail?",
            "type": "text",
            "order": 0,
            "folder": str(Folder.get_root_folder().id),
        }
        response = authenticated_client.post(
            reverse("questions-list"), data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_question_on_draft_framework(
        self, authenticated_client, draft_framework
    ):
        fw, rn = draft_framework
        folder = Folder.get_root_folder()
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:upd:q1",
            ref_id="UQ1",
            annotation="Original?",
            type=Question.Type.TEXT,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.patch(
            reverse("questions-detail", args=[q.id]),
            {"annotation": "Updated?"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        q.refresh_from_db()
        assert q.annotation == "Updated?"

    def test_delete_question_on_draft_framework(
        self, authenticated_client, draft_framework
    ):
        fw, rn = draft_framework
        folder = Folder.get_root_folder()
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:del:q1",
            ref_id="DQ1",
            annotation="Delete me?",
            type=Question.Type.TEXT,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.delete(
            reverse("questions-detail", args=[q.id])
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Question.objects.filter(id=q.id).exists()


@pytest.mark.django_db
class TestQuestionChoiceEndpoints:
    """Test QuestionChoice API endpoints."""

    def test_unauthenticated_list_returns_401(self):
        client = APIClient()
        response = client.get(reverse("question-choices-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_choice_on_draft_framework(
        self, authenticated_client, draft_framework
    ):
        fw, rn = draft_framework
        folder = Folder.get_root_folder()
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:choice:q1",
            ref_id="CQ1",
            type=Question.Type.SINGLE_CHOICE,
            folder=folder,
            is_published=True,
        )
        data = {
            "question": str(q.id),
            "ref_id": "C1",
            "annotation": "Choice A",
            "add_score": 10,
            "order": 0,
            "folder": str(folder.id),
        }
        response = authenticated_client.post(
            reverse("question-choices-list"), data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_choice_on_published_framework_rejected(
        self, authenticated_client, published_framework
    ):
        fw, rn = published_framework
        folder = Folder.get_root_folder()
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:pubchoice:q1",
            ref_id="PCQ1",
            type=Question.Type.SINGLE_CHOICE,
            folder=folder,
            is_published=True,
        )
        data = {
            "question": str(q.id),
            "ref_id": "PC1",
            "annotation": "Should fail",
            "order": 0,
            "folder": str(folder.id),
        }
        response = authenticated_client.post(
            reverse("question-choices-list"), data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
