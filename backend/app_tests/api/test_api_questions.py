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
def framework_with_node(app_config):
    """Create a draft framework with a requirement node."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Test Framework",
        folder=folder,
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

    def test_list_questions(self, authenticated_client, framework_with_node):
        fw, rn = framework_with_node
        folder = Folder.get_root_folder()
        Question.objects.create(
            requirement_node=rn,
            urn="urn:test:q1",
            ref_id="Q1",
            text="What is your name?",
            type=Question.Type.TEXT,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.get(reverse("questions-list"))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] >= 1

    def test_create_question_on_framework_with_node(
        self, authenticated_client, framework_with_node
    ):
        fw, rn = framework_with_node
        data = {
            "requirement_node": str(rn.id),
            "urn": "urn:test:new:q1",
            "ref_id": "NQ1",
            "text": "New question?",
            "type": "text",
            "order": 0,
            "folder": str(Folder.get_root_folder().id),
        }
        response = authenticated_client.post(
            reverse("questions-list"), data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Question.objects.filter(urn="urn:test:new:q1").exists()


@pytest.mark.django_db
class TestRequirementNodeEndpoints:
    """Test RequirementNode API endpoints for published-framework guards."""

    def test_create_requirement_node_on_framework_with_node(
        self, authenticated_client, framework_with_node
    ):
        fw, rn = framework_with_node
        folder = Folder.get_root_folder()
        data = {
            "framework": str(fw.id),
            "ref_id": "REQ-NEW",
            "assessable": True,
            "folder": str(folder.id),
        }
        response = authenticated_client.post(
            reverse("requirement-nodes-list"), data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestQuestionChoiceEndpoints:
    """Test QuestionChoice API endpoints."""

    def test_unauthenticated_list_returns_401(self):
        client = APIClient()
        response = client.get(reverse("question-choices-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_choice_on_framework_with_node(
        self, authenticated_client, framework_with_node
    ):
        fw, rn = framework_with_node
        folder = Folder.get_root_folder()
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:choice:q1",
            ref_id="CQ1",
            type=Question.Type.UNIQUE_CHOICE,
            folder=folder,
            is_published=True,
        )
        data = {
            "question": str(q.id),
            "ref_id": "C1",
            "value": "Choice A",
            "add_score": 10,
            "order": 0,
            "folder": str(folder.id),
        }
        response = authenticated_client.post(
            reverse("question-choices-list"), data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
