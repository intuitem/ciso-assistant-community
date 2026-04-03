"""Tests for framework builder security hardening."""

import io
import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Framework,
    RequirementNode,
    Question,
    QuestionChoice,
    RequirementNodeAttachment,
)
from iam.models import Folder


# --- Helpers ---

# Minimal 1x1 PNG (67 bytes)
REAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal WebP (30 bytes)
REAL_WEBP = (
    b"RIFF\x1a\x00\x00\x00WEBPVP8 "
    b"\x0e\x00\x00\x000\x01\x00\x9d\x01\x2a"
    b"\x01\x00\x01\x00\x01\x00\x03p\x00\xfe"
    b"\xfb\x94\x00\x00"
)

PDF_CONTENT = b"%PDF-1.4 fake pdf content"


def _upload_file(client, url, content, filename, content_type):
    f = io.BytesIO(content)
    f.name = filename
    return client.post(
        url, {"file": f}, format="multipart", HTTP_CONTENT_TYPE=content_type
    )


# --- Fixtures ---


@pytest.fixture
def framework_with_node(app_config):
    """Create a framework with a requirement node for builder tests."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Builder Test FW",
        folder=folder,
        is_published=True,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:builder:test:001",
        ref_id="BT-001",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    return fw, rn, folder


@pytest.fixture
def second_framework(app_config):
    """Create a second framework for cross-framework tests."""
    folder = Folder.get_root_folder()
    fw2 = Framework.objects.create(
        name="Other Framework",
        folder=folder,
        is_published=True,
    )
    rn2 = RequirementNode.objects.create(
        framework=fw2,
        urn="urn:other:test:001",
        ref_id="OT-001",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    q2 = Question.objects.create(
        requirement_node=rn2,
        urn="urn:other:q1",
        ref_id="OQ1",
        text="Other question",
        type=Question.Type.TEXT,
        folder=folder,
        is_published=True,
    )
    return fw2, rn2, q2


# --- Test class ---


@pytest.mark.django_db
class TestFrameworkBuilderSecurity:
    """Security tests for framework builder endpoints."""

    # --- Finding 1: MIME validation ---

    def test_upload_image_rejects_fake_mime(
        self, authenticated_client, framework_with_node
    ):
        """Upload file with image/png content-type but PDF content → 400."""
        fw, rn, folder = framework_with_node
        url = reverse("frameworks-upload-image", args=[fw.id])
        f = io.BytesIO(PDF_CONTENT)
        f.name = "evil.png"
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile("evil.png", PDF_CONTENT, content_type="image/png")
        response = authenticated_client.post(
            url, {"file": uploaded}, format="multipart"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not an allowed image type" in response.data["error"]

    def test_upload_real_png_succeeds(self, authenticated_client, framework_with_node):
        """Upload a real PNG → 201."""
        fw, rn, folder = framework_with_node
        url = reverse("frameworks-upload-image", args=[fw.id])
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile("test.png", REAL_PNG, content_type="image/png")
        response = authenticated_client.post(
            url, {"file": uploaded}, format="multipart"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data

    def test_upload_disallowed_extension_rejected(
        self, authenticated_client, framework_with_node
    ):
        """Framework upload_image runs full_clean → disallowed extension rejected."""
        fw, rn, folder = framework_with_node
        url = reverse("frameworks-upload-image", args=[fw.id])
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile("test.exe", REAL_PNG, content_type="image/png")
        response = authenticated_client.post(
            url, {"file": uploaded}, format="multipart"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_serve_image_basename_only(self, authenticated_client, framework_with_node):
        """Serve image returns basename in Content-Disposition, no path separators."""
        fw, rn, folder = framework_with_node
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile("safe.png", REAL_PNG, content_type="image/png")
        upload_url = reverse("frameworks-upload-image", args=[fw.id])
        resp = authenticated_client.post(
            upload_url, {"file": uploaded}, format="multipart"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        att_id = resp.data["id"]

        serve_url = reverse("frameworks-serve-image", args=[fw.id, att_id])
        response = authenticated_client.get(serve_url)
        assert response.status_code == 200
        disposition = response["Content-Disposition"]
        # Should not contain path separators
        assert "/" not in disposition.split("filename=")[1]

    # --- Finding 1: RequirementNode upload_image MIME validation ---

    def test_requirement_upload_rejects_fake_mime(
        self, authenticated_client, framework_with_node
    ):
        """RequirementNode upload_image rejects fake MIME."""
        fw, rn, folder = framework_with_node
        url = reverse("requirement-nodes-upload-image", args=[rn.id])
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile("evil.png", PDF_CONTENT, content_type="image/png")
        response = authenticated_client.post(
            url, {"file": uploaded}, format="multipart"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not an allowed image type" in response.data["error"]

    # --- Finding 2: Cross-framework reparenting ---

    def test_publish_rejects_cross_framework_node_ref(
        self, authenticated_client, framework_with_node, second_framework
    ):
        """publish_draft rejects question referencing a node from another framework."""
        fw, rn, folder = framework_with_node
        fw2, rn2, q2 = second_framework

        node_id = str(rn.id)
        q_id = str(uuid.uuid4())

        # Start editing
        start_url = reverse("frameworks-start-editing", args=[fw.id])
        authenticated_client.post(start_url)

        # Build a draft that references the other framework's node
        draft = {
            "framework_meta": {"name": fw.name},
            "nodes": [
                {
                    "id": node_id,
                    "urn": rn.urn,
                    "ref_id": rn.ref_id,
                    "assessable": True,
                    "order_id": 0,
                    "weight": 1,
                    "importance": "undefined",
                    "display_mode": "default",
                }
            ],
            "questions": [
                {
                    "id": q_id,
                    "requirement_node_id": str(rn2.id),  # CROSS-FRAMEWORK!
                    "type": "text",
                    "text": "evil question",
                    "order": 0,
                    "weight": 1,
                }
            ],
            "choices": [],
        }

        # Save draft then publish
        save_url = reverse("frameworks-save-draft", args=[fw.id])
        authenticated_client.patch(save_url, {"editing_draft": draft}, format="json")

        publish_url = reverse("frameworks-publish-draft", args=[fw.id])
        response = authenticated_client.post(publish_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "requirement_node not in this framework" in response.data["error"]

    def test_publish_rejects_cross_framework_question_ref(
        self, authenticated_client, framework_with_node, second_framework
    ):
        """publish_draft rejects choice referencing a question from another framework."""
        fw, rn, folder = framework_with_node
        fw2, rn2, q2 = second_framework

        node_id = str(rn.id)
        q_id = str(uuid.uuid4())
        c_id = str(uuid.uuid4())

        start_url = reverse("frameworks-start-editing", args=[fw.id])
        authenticated_client.post(start_url)

        draft = {
            "framework_meta": {"name": fw.name},
            "nodes": [
                {
                    "id": node_id,
                    "urn": rn.urn,
                    "ref_id": rn.ref_id,
                    "assessable": True,
                    "order_id": 0,
                    "weight": 1,
                    "importance": "undefined",
                    "display_mode": "default",
                }
            ],
            "questions": [
                {
                    "id": q_id,
                    "urn": f"urn:builder:test:q:{q_id}",
                    "requirement_node_id": node_id,
                    "type": "unique_choice",
                    "text": "legit question",
                    "order": 0,
                    "weight": 1,
                }
            ],
            "choices": [
                {
                    "id": c_id,
                    "question_id": str(q2.id),  # CROSS-FRAMEWORK!
                    "value": "evil",
                    "order": 0,
                }
            ],
        }

        save_url = reverse("frameworks-save-draft", args=[fw.id])
        authenticated_client.patch(save_url, {"editing_draft": draft}, format="json")

        publish_url = reverse("frameworks-publish-draft", args=[fw.id])
        response = authenticated_client.post(publish_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "question not in this framework" in response.data["error"]

    # --- Finding 3: folder_id injection ---

    def test_publish_ignores_injected_folder_id(
        self, authenticated_client, framework_with_node
    ):
        """folder_id from draft JSON is ignored; always uses framework.folder_id."""
        fw, rn, folder = framework_with_node
        fake_folder_id = str(uuid.uuid4())

        node_id = str(rn.id)

        start_url = reverse("frameworks-start-editing", args=[fw.id])
        authenticated_client.post(start_url)

        draft = {
            "framework_meta": {"name": fw.name},
            "nodes": [
                {
                    "id": node_id,
                    "urn": rn.urn,
                    "ref_id": rn.ref_id,
                    "assessable": True,
                    "order_id": 0,
                    "weight": 1,
                    "importance": "undefined",
                    "display_mode": "default",
                    "folder_id": fake_folder_id,  # INJECTED!
                }
            ],
            "questions": [],
            "choices": [],
        }

        save_url = reverse("frameworks-save-draft", args=[fw.id])
        authenticated_client.patch(save_url, {"editing_draft": draft}, format="json")

        publish_url = reverse("frameworks-publish-draft", args=[fw.id])
        response = authenticated_client.post(publish_url)
        assert response.status_code == 200

        rn.refresh_from_db()
        assert str(rn.folder_id) == str(fw.folder_id)

    # --- Finding 4: save_draft schema validation ---

    def test_save_draft_rejects_missing_nodes(
        self, authenticated_client, framework_with_node
    ):
        """save_draft rejects draft missing required 'nodes' key."""
        fw, rn, folder = framework_with_node

        start_url = reverse("frameworks-start-editing", args=[fw.id])
        authenticated_client.post(start_url)

        url = reverse("frameworks-save-draft", args=[fw.id])
        response = authenticated_client.patch(
            url,
            {"editing_draft": {"framework_meta": {}, "questions": [], "choices": []}},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "missing required keys" in response.data["error"]

    def test_save_draft_rejects_non_dict(
        self, authenticated_client, framework_with_node
    ):
        """save_draft rejects non-dict editing_draft."""
        fw, rn, folder = framework_with_node

        start_url = reverse("frameworks-start-editing", args=[fw.id])
        authenticated_client.post(start_url)

        url = reverse("frameworks-save-draft", args=[fw.id])
        response = authenticated_client.patch(
            url, {"editing_draft": "not a dict"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be a JSON object" in response.data["error"]

    # --- Field length validation ---

    def test_publish_rejects_node_name_over_200_chars(
        self, authenticated_client, framework_with_node
    ):
        """publish_draft rejects a node with name > 200 chars via DraftValidationError."""
        fw, rn, folder = framework_with_node
        node_id = str(rn.id)

        start_url = reverse("frameworks-start-editing", args=[fw.id])
        authenticated_client.post(start_url)

        long_name = "A" * 201

        draft = {
            "framework_meta": {"name": fw.name},
            "nodes": [
                {
                    "id": node_id,
                    "urn": rn.urn,
                    "ref_id": rn.ref_id,
                    "name": long_name,
                    "assessable": True,
                    "order_id": 0,
                    "weight": 1,
                    "importance": "undefined",
                    "display_mode": "default",
                }
            ],
            "questions": [],
            "choices": [],
        }

        save_url = reverse("frameworks-save-draft", args=[fw.id])
        authenticated_client.patch(save_url, {"editing_draft": draft}, format="json")

        publish_url = reverse("frameworks-publish-draft", args=[fw.id])
        response = authenticated_client.post(publish_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name is 201 characters (max 200)" in response.data["error"]
