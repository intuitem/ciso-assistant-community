"""Tests for Framework publish endpoint."""

import pytest
from django.urls import reverse
from rest_framework import status

from core.models import (
    Framework,
    Question,
    QuestionChoice,
    RequirementNode,
)
from iam.models import Folder


@pytest.fixture
def draft_framework_with_valid_questions(app_config):
    """Create a draft framework with valid questions ready to publish."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Publishable Framework",
        folder=folder,
        status=Framework.Status.DRAFT,
        is_published=True,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:pub:req:001",
        ref_id="PUB-REQ-001",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    q = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:pub:q1",
        ref_id="PQ1",
        annotation="Pick one",
        type=Question.Type.SINGLE_CHOICE,
        order=0,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q,
        ref_id="PC1",
        annotation="Choice A",
        order=0,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q,
        ref_id="PC2",
        annotation="Choice B",
        order=1,
        folder=folder,
        is_published=True,
    )
    return fw


@pytest.mark.django_db
class TestFrameworkPublish:
    def test_publish_draft_framework(
        self, authenticated_client, draft_framework_with_valid_questions
    ):
        fw = draft_framework_with_valid_questions
        response = authenticated_client.post(
            reverse("frameworks-publish", args=[fw.id])
        )
        assert response.status_code == status.HTTP_200_OK
        fw.refresh_from_db()
        assert fw.status == Framework.Status.PUBLISHED

    def test_publish_already_published_returns_400(self, authenticated_client):
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Already Published",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
        )
        response = authenticated_client.post(
            reverse("frameworks-publish", args=[fw.id])
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_publish_fails_with_too_few_choices(self, authenticated_client):
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Bad Choices Framework",
            folder=folder,
            status=Framework.Status.DRAFT,
            is_published=True,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:badchoice:req:001",
            ref_id="BC-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:badchoice:q1",
            ref_id="BCQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        # Only 1 choice — should fail validation
        QuestionChoice.objects.create(
            question=q,
            ref_id="BC1",
            annotation="Only choice",
            order=0,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.post(
            reverse("frameworks-publish", args=[fw.id])
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_publish_fails_with_invalid_depends_on(self, authenticated_client):
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Bad DependsOn Framework",
            folder=folder,
            status=Framework.Status.DRAFT,
            is_published=True,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:baddep:req:001",
            ref_id="BD-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        Question.objects.create(
            requirement_node=rn,
            urn="urn:test:baddep:q1",
            ref_id="BDQ1",
            type=Question.Type.TEXT,
            depends_on={
                "question": "NONEXISTENT",
                "answers": ["x"],
                "condition": "any",
            },
            order=0,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.post(
            reverse("frameworks-publish", args=[fw.id])
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_publish_fails_missing_score_key(self, authenticated_client):
        """scores_definition scale entry missing 'score' key -> 400."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Missing Score Key FW",
            folder=folder,
            status=Framework.Status.DRAFT,
            is_published=True,
            scores_definition={"scale": [{"name": "Good"}]},
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:msk:req:001",
            ref_id="MSK-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:msk:q1",
            ref_id="MSKQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="MSKC1",
            annotation="A",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="MSKC2",
            annotation="B",
            order=1,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.post(
            reverse("frameworks-publish", args=[fw.id])
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_publish_fails_duplicate_scores(self, authenticated_client):
        """Two entries with the same 'score' value -> 400."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Duplicate Scores FW",
            folder=folder,
            status=Framework.Status.DRAFT,
            is_published=True,
            scores_definition={
                "scale": [
                    {"score": 1, "name": "Good"},
                    {"score": 1, "name": "Also Good"},
                ]
            },
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:dup:req:001",
            ref_id="DUP-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:dup:q1",
            ref_id="DUPQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="DUPC1",
            annotation="A",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="DUPC2",
            annotation="B",
            order=1,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.post(
            reverse("frameworks-publish", args=[fw.id])
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_publish_fails_invalid_aggregation(self, authenticated_client):
        """aggregation: 'max' (unsupported) -> 400."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Bad Agg FW",
            folder=folder,
            status=Framework.Status.DRAFT,
            is_published=True,
            scores_definition={"aggregation": "max"},
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:badagg:req:001",
            ref_id="BA-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:badagg:q1",
            ref_id="BAQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="BAC1",
            annotation="A",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="BAC2",
            annotation="B",
            order=1,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.post(
            reverse("frameworks-publish", args=[fw.id])
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_publish_succeeds_with_valid_scores_definition(self, authenticated_client):
        """Valid scale + aggregation: 'sum' -> 200."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Valid SD FW",
            folder=folder,
            status=Framework.Status.DRAFT,
            is_published=True,
            scores_definition={
                "scale": [
                    {"score": 0, "name": "Low"},
                    {"score": 1, "name": "Medium"},
                    {"score": 2, "name": "High"},
                ],
                "aggregation": "sum",
            },
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:validsd:req:001",
            ref_id="VSD-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:validsd:q1",
            ref_id="VSDQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="VSDC1",
            annotation="A",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="VSDC2",
            annotation="B",
            order=1,
            folder=folder,
            is_published=True,
        )
        response = authenticated_client.post(
            reverse("frameworks-publish", args=[fw.id])
        )
        assert response.status_code == status.HTTP_200_OK
        fw.refresh_from_db()
        assert fw.status == Framework.Status.PUBLISHED
