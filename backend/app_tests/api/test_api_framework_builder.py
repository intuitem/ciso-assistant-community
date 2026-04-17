"""Tests for framework builder security hardening and URN generation."""

import io
import uuid

import pytest
import yaml
from django.urls import reverse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Answer,
    ComplianceAssessment,
    Framework,
    Perimeter,
    Question,
    QuestionChoice,
    RequirementAssessment,
    RequirementNode,
    RequirementNodeAttachment,
    StoredLibrary,
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


# --- Fixtures for URN generation tests ---


@pytest.fixture
def framework_with_tree(app_config):
    """Create a framework with nodes, questions, and choices for duplication tests."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="My SOC2 Framework",
        folder=folder,
        is_published=True,
    )
    sec = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:req_node:section1",
        ref_id="1",
        name="Section 1",
        assessable=False,
        folder=folder,
        is_published=True,
    )
    req = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:req_node:req1",
        ref_id="1.1",
        name="Requirement 1.1",
        parent_urn="urn:test:req_node:section1",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    q = Question.objects.create(
        requirement_node=req,
        urn="urn:test:question:q1",
        ref_id="1.1-q1",
        text="Test question",
        type=Question.Type.UNIQUE_CHOICE,
        folder=folder,
        is_published=True,
    )
    c = QuestionChoice.objects.create(
        question=q,
        urn="urn:test:choice:c1",
        ref_id="1.1-q1-c1",
        value="Yes",
        folder=folder,
        is_published=True,
    )
    return fw, sec, req, q, c, folder


# --- URN Generation tests ---


@pytest.mark.django_db
class TestFrameworkBuilderURNGeneration:
    """Tests for readable URN generation in duplicate and publish flows."""

    def test_duplicate_urn_format(self, authenticated_client, framework_with_tree):
        """Duplicated framework nodes get slug-based URNs, not UUIDs."""
        fw, sec, req, q, c, folder = framework_with_tree
        url = reverse("frameworks-duplicate", args=[fw.id])
        response = authenticated_client.post(
            url, {"name": "My SOC2 Copy"}, format="json"
        )
        assert response.status_code == 201
        new_fw_id = response.data["id"]

        nodes = RequirementNode.objects.filter(framework_id=new_fw_id)
        for node in nodes:
            assert node.urn is not None
            assert "my-soc2-copy" in node.urn
            assert "req_node" in node.urn
            # Should NOT contain a UUID pattern
            try:
                # Extract the part after the last colon (ref_id portion)
                parts = node.urn.split(":")
                uuid.UUID(parts[-1])
                # If parsing as UUID succeeds, that's wrong
                assert False, f"URN contains UUID: {node.urn}"
            except ValueError:
                pass  # Good, it's not a UUID

    def test_duplicate_choice_prefix(self, authenticated_client, framework_with_tree):
        """Duplicated choices use 'question_choice:' prefix, not 'choice:'."""
        fw, sec, req, q, c, folder = framework_with_tree
        url = reverse("frameworks-duplicate", args=[fw.id])
        response = authenticated_client.post(
            url, {"name": "Choice Prefix Test"}, format="json"
        )
        assert response.status_code == 201
        new_fw_id = response.data["id"]

        choices = QuestionChoice.objects.filter(
            question__requirement_node__framework_id=new_fw_id
        )
        for choice in choices:
            if choice.urn:
                assert "question_choice:" in choice.urn
                assert "choice:" not in choice.urn.replace("question_choice:", "")

    def test_duplicate_ref_id_preservation(
        self, authenticated_client, framework_with_tree
    ):
        """Duplicated framework preserves original ref_ids."""
        fw, sec, req, q, c, folder = framework_with_tree
        url = reverse("frameworks-duplicate", args=[fw.id])
        response = authenticated_client.post(
            url, {"name": "Ref ID Test"}, format="json"
        )
        assert response.status_code == 201
        new_fw_id = response.data["id"]

        new_nodes = RequirementNode.objects.filter(framework_id=new_fw_id).order_by(
            "order_id"
        )
        assert new_nodes[0].ref_id == "1"
        assert new_nodes[1].ref_id == "1.1"

        new_questions = Question.objects.filter(
            requirement_node__framework_id=new_fw_id
        )
        assert new_questions[0].ref_id == "1.1-q1"

    def test_reconcile_draft_no_collision(
        self, authenticated_client, framework_with_node
    ):
        """Publishing a draft with unique URNs succeeds without warnings."""
        fw, rn, folder = framework_with_node
        node_id = str(rn.id)
        new_node_id = str(uuid.uuid4())

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
                },
                {
                    "id": new_node_id,
                    "urn": f"urn:intuitem:risk:req_node:unique-test-slug:{uuid.uuid4().hex[:8]}",
                    "ref_id": "2",
                    "assessable": False,
                    "order_id": 100,
                    "weight": 1,
                    "importance": "undefined",
                    "display_mode": "default",
                },
            ],
            "questions": [],
            "choices": [],
        }

        save_url = reverse("frameworks-save-draft", args=[fw.id])
        authenticated_client.patch(save_url, {"editing_draft": draft}, format="json")

        publish_url = reverse("frameworks-publish-draft", args=[fw.id])
        response = authenticated_client.post(publish_url)
        assert response.status_code == 200
        assert "warnings" not in response.data

    def test_reconcile_draft_collision_disambiguation(
        self, authenticated_client, framework_with_node
    ):
        """Publishing a draft with colliding URNs triggers disambiguation."""
        fw, rn, folder = framework_with_node
        node_id = str(rn.id)
        new_node_id = str(uuid.uuid4())

        # Create a conflicting node in another framework with a standard-format URN
        fw_other = Framework.objects.create(
            name="Conflict FW",
            folder=folder,
            is_published=True,
        )
        colliding_urn = "urn:intuitem:risk:req_node:my-slug:2"
        RequirementNode.objects.create(
            framework=fw_other,
            urn=colliding_urn,
            ref_id="2",
            assessable=False,
            folder=folder,
            is_published=True,
        )

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
                },
                {
                    "id": new_node_id,
                    "urn": colliding_urn,
                    "ref_id": "2",
                    "assessable": False,
                    "order_id": 100,
                    "weight": 1,
                    "importance": "undefined",
                    "display_mode": "default",
                },
            ],
            "questions": [],
            "choices": [],
        }

        save_url = reverse("frameworks-save-draft", args=[fw.id])
        authenticated_client.patch(save_url, {"editing_draft": draft}, format="json")

        publish_url = reverse("frameworks-publish-draft", args=[fw.id])
        response = authenticated_client.post(publish_url)
        assert response.status_code == 200
        assert "warnings" in response.data
        assert any("disambiguated" in w for w in response.data["warnings"])

        # Verify the new node got a disambiguated URN
        new_node = RequirementNode.objects.get(id=new_node_id)
        assert new_node.urn != colliding_urn
        assert "my-slug-2" in new_node.urn

    def test_slug_parity_with_frontend(self, app_config):
        """Backend slugify produces the same results as the frontend slugifyFrameworkName."""
        # Shared test fixtures matching frontend tests
        test_cases = [
            ("My Custom SOC2 Framework!", "my-custom-soc2-framework"),
            ("Cadre de Conformit\u00e9 ISO", "cadre-de-conformite-iso"),
        ]
        for name, expected in test_cases:
            result = slugify(name, allow_unicode=False)[:60]
            assert result == expected, (
                f"Slug mismatch for '{name}': got '{result}', expected '{expected}'"
            )

        # CJK should produce empty slug (frontend falls back to UUID)
        result = slugify(
            "\u60c5\u5831\u30bb\u30ad\u30e5\u30ea\u30c6\u30a3", allow_unicode=False
        )
        assert result == "", f"CJK should produce empty slug, got '{result}'"

        # Empty string should produce empty slug
        result = slugify("", allow_unicode=False)
        assert result == ""

    def test_duplicate_long_name_slug_collision(self, authenticated_client, app_config):
        """Duplicating a framework whose slug fills the 60-char limit should not
        collide with the source's URNs (regression test for slug truncation bug)."""
        folder = Folder.get_root_folder()
        # Name whose slug exceeds 55 chars so "(copy)" gets truncated away
        long_name = "NIST Cybersecurity Framework 2.0 - Information Security Controls"
        slug = slugify(long_name, allow_unicode=False)[:60]
        assert len(slug) == 60, "Test requires a slug that fills the 60-char limit"

        fw = Framework.objects.create(
            name=long_name,
            folder=folder,
            is_published=True,
        )
        # Create nodes with URNs that use the full-length slug
        RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:custom:risk:req_node:{slug}:1",
            ref_id="1",
            name="Section 1",
            assessable=False,
            folder=folder,
            is_published=True,
        )
        RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:custom:risk:req_node:{slug}:1.1",
            ref_id="1.1",
            name="Requirement 1.1",
            parent_urn=f"urn:custom:risk:req_node:{slug}:1",
            assessable=True,
            folder=folder,
            is_published=True,
        )

        url = reverse("frameworks-duplicate", args=[fw.id])
        response = authenticated_client.post(
            url, {"name": f"{long_name} (copy)"}, format="json"
        )
        assert response.status_code == 201, (
            f"Duplicate should succeed, got {response.status_code}: {response.data}"
        )

        new_fw_id = response.data["id"]
        new_nodes = RequirementNode.objects.filter(framework_id=new_fw_id)
        assert new_nodes.count() == 2
        # New URNs must differ from source URNs
        source_urns = set(
            RequirementNode.objects.filter(framework=fw).values_list("urn", flat=True)
        )
        new_urns = set(new_nodes.values_list("urn", flat=True))
        assert not source_urns & new_urns, "Copy URNs must not collide with source URNs"

    def test_duplicate_library_shape_question_ref_ids(
        self, authenticated_client, app_config
    ):
        """Duplicating a framework whose questions share bare positional ref_ids
        across nodes (the shape produced by the library loader, e.g.
        ``urn:...:req_node:X:question:1`` → ref_id="1") must not collide on
        Question.urn (regression for library-imported duplicate failure)."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Library-Shaped FW",
            folder=folder,
            is_published=True,
        )
        # Two requirement nodes, each with two questions whose ref_ids repeat
        # across nodes — the shape generated by _create_questions_from_data.
        for node_ref in ("a-01", "a-02"):
            rn = RequirementNode.objects.create(
                framework=fw,
                urn=f"urn:test:risk:req_node:lib:{node_ref}",
                ref_id=node_ref,
                assessable=True,
                folder=folder,
                is_published=True,
            )
            for q_pos in ("1", "2"):
                Question.objects.create(
                    requirement_node=rn,
                    urn=f"urn:test:risk:req_node:lib:{node_ref}:question:{q_pos}",
                    ref_id=q_pos,  # library loader sets this to the URN's last segment
                    text=f"Question {q_pos} for {node_ref}",
                    type=Question.Type.UNIQUE_CHOICE,
                    folder=folder,
                    is_published=True,
                )

        url = reverse("frameworks-duplicate", args=[fw.id])
        response = authenticated_client.post(
            url, {"name": "Library-Shaped FW (copy)"}, format="json"
        )
        assert response.status_code == 201, (
            f"Duplicate should succeed, got {response.status_code}: {response.data}"
        )

        new_fw_id = response.data["id"]
        new_questions = Question.objects.filter(
            requirement_node__framework_id=new_fw_id
        )
        assert new_questions.count() == 4
        new_urns = list(new_questions.values_list("urn", flat=True))
        assert len(set(new_urns)) == len(new_urns), (
            f"Duplicated question URNs must be unique, got: {new_urns}"
        )

        # node_id (the part after urn:{org}:risk:{type}:{slug}:) must be
        # preserved from source so CEL expressions referencing
        # answers.<q_node_id> still evaluate on the copy.
        from core.utils import extract_node_id

        source_node_ids = {
            extract_node_id(f"urn:test:risk:req_node:lib:{n}:question:{q}")
            for n in ("a-01", "a-02")
            for q in ("1", "2")
        }
        copy_node_ids = {extract_node_id(u) for u in new_urns}
        assert source_node_ids == copy_node_ids, (
            f"Question node_ids must be preserved, source={source_node_ids}, "
            f"copy={copy_node_ids}"
        )

    def test_duplicate_preserves_question_and_choice_node_ids(
        self, authenticated_client, app_config
    ):
        """Question and choice node_ids (the URN suffix after the slug) must
        survive duplication. CEL expressions in outcomes_definition and
        visibility_expression reference answers.<q_node_id> and
        selected_choices by choice node_id — they only work on the copy when
        those node_ids match the source's."""
        from core.utils import extract_node_id

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Node ID FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:node-id-fw:governance",
            ref_id="governance",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q_source_urn = "urn:intuitem:risk:question:node-id-fw:policy-exists"
        c_source_urn = "urn:intuitem:risk:question_choice:node-id-fw:policy-yes"
        q = Question.objects.create(
            requirement_node=rn,
            urn=q_source_urn,
            ref_id="policy-exists",
            text="Is there a policy?",
            type=Question.Type.UNIQUE_CHOICE,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            urn=c_source_urn,
            ref_id="policy-yes",
            value="Yes",
            folder=folder,
            is_published=True,
        )

        url = reverse("frameworks-duplicate", args=[fw.id])
        response = authenticated_client.post(
            url, {"name": "Node ID FW (copy)"}, format="json"
        )
        assert response.status_code == 201

        new_fw_id = response.data["id"]
        new_q = Question.objects.get(requirement_node__framework_id=new_fw_id)
        new_c = QuestionChoice.objects.get(question=new_q)

        assert extract_node_id(new_q.urn) == extract_node_id(q_source_urn)
        assert extract_node_id(new_c.urn) == extract_node_id(c_source_urn)
        # URN itself must still differ (different slug)
        assert new_q.urn != q_source_urn
        assert new_c.urn != c_source_urn

    def test_duplicate_preserves_library_shape_node_ids(
        self, authenticated_client, app_config
    ):
        """Library-imported questions carry URNs of the form
        urn:{org}:risk:req_node:{slug}:{parent}:question:{N}. Their node_id
        (e.g. 'governance:question:1') must be preserved on the copy so the
        copied outcomes_definition and visibility_expression CEL still work."""
        from core.utils import extract_node_id

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Lib Shape FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:lib-shape-fw:governance",
            ref_id="governance",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q_source_urn = "urn:intuitem:risk:req_node:lib-shape-fw:governance:question:1"
        c_source_urn = (
            "urn:intuitem:risk:req_node:lib-shape-fw:governance:question:1:choice:1"
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn=q_source_urn,
            ref_id="1",  # library loader sets ref_id to parts[-1]
            text="First question",
            type=Question.Type.UNIQUE_CHOICE,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            urn=c_source_urn,
            ref_id="1",
            value="Yes",
            folder=folder,
            is_published=True,
        )

        url = reverse("frameworks-duplicate", args=[fw.id])
        response = authenticated_client.post(
            url, {"name": "Lib Shape FW (copy)"}, format="json"
        )
        assert response.status_code == 201

        new_fw_id = response.data["id"]
        new_q = Question.objects.get(requirement_node__framework_id=new_fw_id)
        new_c = QuestionChoice.objects.get(question=new_q)

        assert extract_node_id(new_q.urn) == "governance:question:1"
        assert extract_node_id(new_c.urn) == "governance:question:1:choice:1"

    def test_duplicate_remaps_depends_on_urns(self, authenticated_client, app_config):
        """Copied questions with depends_on must reference the copy's own
        question/choice URNs, not the source's."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Depends On FW",
            folder=folder,
            is_published=True,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:req_node:dep:1",
            ref_id="1",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q1 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:req_node:dep:1:question:1",
            ref_id="1",
            text="Parent question",
            type=Question.Type.UNIQUE_CHOICE,
            folder=folder,
            is_published=True,
        )
        c1 = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:req_node:dep:1:question:1:choice:1",
            ref_id="1",
            value="Yes",
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:req_node:dep:1:question:1:choice:2",
            ref_id="2",
            value="No",
            folder=folder,
            is_published=True,
        )
        # Q2 depends on Q1 = "Yes"
        Question.objects.create(
            requirement_node=rn,
            urn="urn:test:req_node:dep:1:question:2",
            ref_id="2",
            text="Child question",
            type=Question.Type.TEXT,
            depends_on={
                "question": q1.urn,
                "answers": [c1.urn],
                "condition": "any",
            },
            folder=folder,
            is_published=True,
        )

        url = reverse("frameworks-duplicate", args=[fw.id])
        response = authenticated_client.post(
            url, {"name": "Depends On FW (copy)"}, format="json"
        )
        assert response.status_code == 201, (
            f"Duplicate should succeed, got {response.status_code}: {response.data}"
        )

        new_fw_id = response.data["id"]
        new_questions = Question.objects.filter(
            requirement_node__framework_id=new_fw_id
        ).order_by("order")
        assert new_questions.count() == 2
        new_q1, new_q2 = new_questions[0], new_questions[1]

        # depends_on on the copy must point at the copy's own URNs, not source's
        assert new_q2.depends_on is not None
        assert new_q2.depends_on["question"] == new_q1.urn, (
            f"depends_on.question must be remapped to copy's URN, "
            f"got {new_q2.depends_on['question']} vs {new_q1.urn}"
        )
        new_c1 = new_q1.choices.get(ref_id="1")
        assert new_q2.depends_on["answers"] == [new_c1.urn], (
            f"depends_on.answers must be remapped to copy's choice URNs, "
            f"got {new_q2.depends_on['answers']} vs [{new_c1.urn}]"
        )
        assert new_q2.depends_on["condition"] == "any"

    def test_duplicate_preserves_foreign_depends_on_urns(
        self, authenticated_client, app_config
    ):
        """depends_on URNs not found in the framework (e.g. stale/cross-framework
        refs) must be left untouched rather than silently dropped."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Foreign Dep FW",
            folder=folder,
            is_published=True,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:req_node:foreign:1",
            ref_id="1",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        foreign_q_urn = "urn:other:framework:question:x"
        foreign_c_urn = "urn:other:framework:question:x:choice:1"
        Question.objects.create(
            requirement_node=rn,
            urn="urn:test:req_node:foreign:1:question:1",
            ref_id="1",
            text="Question with foreign dependency",
            type=Question.Type.TEXT,
            depends_on={
                "question": foreign_q_urn,
                "answers": [foreign_c_urn],
                "condition": "any",
            },
            folder=folder,
            is_published=True,
        )

        url = reverse("frameworks-duplicate", args=[fw.id])
        response = authenticated_client.post(
            url, {"name": "Foreign Dep FW (copy)"}, format="json"
        )
        assert response.status_code == 201

        new_fw_id = response.data["id"]
        new_q = Question.objects.get(requirement_node__framework_id=new_fw_id)
        assert new_q.depends_on["question"] == foreign_q_urn
        assert new_q.depends_on["answers"] == [foreign_c_urn]


# --- YAML Export tests ---


@pytest.mark.django_db
class TestFrameworkExportYaml:
    """Tests for the export-yaml endpoint on FrameworkViewSet."""

    def test_export_yaml_basic(self, authenticated_client, framework_with_tree):
        """Export produces valid YAML with correct structure."""
        fw, sec, req, q, c, folder = framework_with_tree
        url = reverse("frameworks-export-yaml", args=[fw.id])
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/x-yaml"
        assert "attachment" in response["Content-Disposition"]
        assert ".yaml" in response["Content-Disposition"]

        data = yaml.safe_load(response.content)

        # Library-level fields
        assert "urn:custom:risk:library:" in data["urn"]
        assert data["name"] == fw.name
        assert data["version"] == 1
        assert data["packager"] == "custom"

        # Framework object
        fw_obj = data["objects"]["framework"]
        assert "urn:custom:risk:framework:" in fw_obj["urn"]
        assert fw_obj["name"] == fw.name

        # Requirement nodes
        nodes = fw_obj["requirement_nodes"]
        assert len(nodes) == 2  # sec + req

        # assessable MUST be present on every node (both true and false)
        for node in nodes:
            assert "assessable" in node, f"assessable missing on node {node.get('urn')}"

        # field_visibility must NOT be present anywhere
        assert "field_visibility" not in str(data)

        # Check parent/child depth
        section_node = next(n for n in nodes if n["urn"] == sec.urn)
        req_node = next(n for n in nodes if n["urn"] == req.urn)
        assert section_node["depth"] == 1
        assert req_node["depth"] == 2
        assert section_node["assessable"] is False
        assert req_node["assessable"] is True

    def test_export_yaml_questions_dict_keyed_by_urn(
        self, authenticated_client, framework_with_tree
    ):
        """Questions are exported as a dict keyed by URN, not a list."""
        fw, sec, req, q, c, folder = framework_with_tree
        url = reverse("frameworks-export-yaml", args=[fw.id])
        response = authenticated_client.get(url)
        data = yaml.safe_load(response.content)

        nodes = data["objects"]["framework"]["requirement_nodes"]
        req_node = next(n for n in nodes if n.get("questions"))

        questions = req_node["questions"]
        assert isinstance(questions, dict)
        assert q.urn in questions

        q_data = questions[q.urn]
        assert q_data["type"] == "unique_choice"
        assert q_data["text"] == "Test question"

        # Choices should be a list
        assert "choices" in q_data
        assert isinstance(q_data["choices"], list)
        assert len(q_data["choices"]) == 1
        assert q_data["choices"][0]["value"] == "Yes"

    def test_export_yaml_round_trip_importable(
        self, authenticated_client, framework_with_tree
    ):
        """Exported YAML passes the stored-library import validation (dry-run).

        This is the strongest guarantee that the export format stays in sync
        with what the importer expects. If this test fails, the export is
        producing YAML that users can't re-import.
        """
        fw, sec, req, q, c, folder = framework_with_tree
        url = reverse("frameworks-export-yaml", args=[fw.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200

        yaml_bytes = response.content
        # Dry-run through the actual import path
        result, error = StoredLibrary.store_library_content(yaml_bytes, dry_run=True)
        assert error is None, f"Exported YAML failed import validation: {error}"
        assert result is not None
        assert result["name"] == fw.name

    def test_export_yaml_nodes_only_no_questions(
        self, authenticated_client, app_config
    ):
        """Framework with only nodes (no questions) round-trips successfully."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Nodes Only FW", folder=folder, is_published=True
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:req_node:no-q:1",
            ref_id="1",
            name="Section",
            assessable=False,
            order_id=0,
            folder=folder,
            is_published=True,
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:req_node:no-q:1.1",
            ref_id="1.1",
            assessable=True,
            parent_urn="urn:test:req_node:no-q:1",
            order_id=1,
            folder=folder,
            is_published=True,
        )
        url = reverse("frameworks-export-yaml", args=[fw.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        result, error = StoredLibrary.store_library_content(
            response.content, dry_run=True
        )
        assert error is None, f"Round-trip failed: {error}"

    def test_export_yaml_deep_nesting(self, authenticated_client, app_config):
        """Framework with 4 levels of nesting round-trips successfully."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Deep Nesting FW", folder=folder, is_published=True
        )
        urns = []
        for depth, (ref, parent_idx) in enumerate(
            [("1", None), ("1.1", 0), ("1.1.1", 1), ("1.1.1.1", 2)]
        ):
            urn = f"urn:test:req_node:deep:{ref}"
            urns.append(urn)
            RequirementNode.objects.create(
                framework=fw,
                urn=urn,
                ref_id=ref,
                assessable=(depth > 0),
                parent_urn=urns[parent_idx] if parent_idx is not None else None,
                order_id=depth,
                folder=folder,
                is_published=True,
            )
        url = reverse("frameworks-export-yaml", args=[fw.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        data = yaml.safe_load(response.content)
        depths = [n["depth"] for n in data["objects"]["framework"]["requirement_nodes"]]
        assert depths == [1, 2, 3, 4]
        result, error = StoredLibrary.store_library_content(
            response.content, dry_run=True
        )
        assert error is None, f"Round-trip failed: {error}"

    def test_export_yaml_with_translations(self, authenticated_client, app_config):
        """Framework with translations round-trips successfully."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Translated FW",
            folder=folder,
            locale="en",
            translations={"fr": {"name": "Cadre traduit", "description": "Desc FR"}},
            is_published=True,
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:req_node:trans:1",
            ref_id="1",
            name="Section EN",
            assessable=False,
            order_id=0,
            translations={"fr": {"name": "Section FR"}},
            folder=folder,
            is_published=True,
        )
        url = reverse("frameworks-export-yaml", args=[fw.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        data = yaml.safe_load(response.content)
        assert "translations" in data
        assert "fr" in data["translations"]
        node = data["objects"]["framework"]["requirement_nodes"][0]
        assert node["translations"]["fr"]["name"] == "Section FR"
        result, error = StoredLibrary.store_library_content(
            response.content, dry_run=True
        )
        assert error is None, f"Round-trip failed: {error}"

    def test_export_yaml_special_chars_in_name(self, authenticated_client, app_config):
        """Framework with accented/special characters round-trips successfully."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Cadre de Conformit\u00e9 ISO 27001!",
            description="R\u00e9f\u00e9rentiel avec des caract\u00e8res sp\u00e9ciaux: <>&\"'",
            folder=folder,
            is_published=True,
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:req_node:special:1",
            ref_id="1",
            name="S\u00e9curit\u00e9 de l'information",
            description='Contr\u00f4les d\'acc\u00e8s: v\u00e9rifier les "droits"',
            assessable=True,
            order_id=0,
            folder=folder,
            is_published=True,
        )
        url = reverse("frameworks-export-yaml", args=[fw.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        result, error = StoredLibrary.store_library_content(
            response.content, dry_run=True
        )
        assert error is None, f"Round-trip failed: {error}"

    def test_export_yaml_multiple_question_types(
        self, authenticated_client, app_config
    ):
        """Framework with text, boolean, and multiple_choice questions round-trips."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Multi Question Types", folder=folder, is_published=True
        )
        req = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:req_node:multi-q:1",
            ref_id="1",
            assessable=True,
            order_id=0,
            folder=folder,
            is_published=True,
        )
        Question.objects.create(
            requirement_node=req,
            urn="urn:test:question:multi-q:1-q1",
            text="Free text question",
            type="text",
            order=0,
            folder=folder,
            is_published=True,
        )
        Question.objects.create(
            requirement_node=req,
            urn="urn:test:question:multi-q:1-q2",
            text="Yes or no?",
            type="boolean",
            order=100,
            folder=folder,
            is_published=True,
        )
        mc = Question.objects.create(
            requirement_node=req,
            urn="urn:test:question:multi-q:1-q3",
            text="Select all that apply",
            type="multiple_choice",
            order=200,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=mc,
            urn="urn:test:choice:multi-q:1-q3-c1",
            value="Option A",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=mc,
            urn="urn:test:choice:multi-q:1-q3-c2",
            value="Option B",
            order=100,
            folder=folder,
            is_published=True,
        )
        url = reverse("frameworks-export-yaml", args=[fw.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        data = yaml.safe_load(response.content)
        questions = data["objects"]["framework"]["requirement_nodes"][0]["questions"]
        types = {q["type"] for q in questions.values()}
        assert types == {"text", "boolean", "multiple_choice"}
        result, error = StoredLibrary.store_library_content(
            response.content, dry_run=True
        )
        assert error is None, f"Round-trip failed: {error}"

    def test_export_yaml_with_implementation_groups_and_scores(
        self, authenticated_client, app_config
    ):
        """Framework with scores_definition and implementation_groups round-trips."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Scored FW",
            folder=folder,
            min_score=0,
            max_score=10,
            scores_definition=[
                {"score": 0, "name": "Not implemented"},
                {"score": 5, "name": "Partial"},
                {"score": 10, "name": "Full"},
            ],
            implementation_groups_definition=[
                {"ref_id": "IG1", "name": "Basic"},
                {"ref_id": "IG2", "name": "Advanced"},
            ],
            is_published=True,
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:req_node:scored:1",
            ref_id="1",
            assessable=True,
            implementation_groups=["IG1", "IG2"],
            order_id=0,
            folder=folder,
            is_published=True,
        )
        url = reverse("frameworks-export-yaml", args=[fw.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        data = yaml.safe_load(response.content)
        fw_obj = data["objects"]["framework"]
        assert fw_obj["scores_definition"] is not None
        assert fw_obj["implementation_groups_definition"] is not None
        assert data["objects"]["framework"]["requirement_nodes"][0][
            "implementation_groups"
        ] == ["IG1", "IG2"]
        result, error = StoredLibrary.store_library_content(
            response.content, dry_run=True
        )
        assert error is None, f"Round-trip failed: {error}"

    def test_export_yaml_empty_framework(self, authenticated_client, app_config):
        """Export of a framework with no nodes returns 400."""
        folder = Folder.get_root_folder()
        empty_fw = Framework.objects.create(
            name="Empty Framework",
            folder=folder,
            is_published=True,
        )
        url = reverse("frameworks-export-yaml", args=[empty_fw.id])
        response = authenticated_client.get(url)
        assert response.status_code == 400


# --- Framework duplicate behavior tests ---


@pytest.mark.django_db
class TestFrameworkDuplicateBehavior:
    """Higher-level behavior tests for Framework duplicate action beyond URN
    generation: CEL evaluation on copies, depends_on edges, scalar
    round-trip, folder placement, structural edges, and copy boundaries."""

    # --- CEL end-to-end on a duplicated framework ---

    def test_duplicate_outcomes_definition_evaluates_on_copy(
        self, authenticated_client, app_config
    ):
        """outcomes_definition CEL that references answers.<q_node_id> must
        evaluate correctly on the duplicated framework's ComplianceAssessment."""
        from core.cel_service import evaluate_outcomes

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Outcomes FW",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
            urn_namespace="intuitem",
            outcomes_definition=[
                {
                    "ref_id": "compliant",
                    "expression": 'answers["policy-exists"].value == "yes"',
                    "result": "pass",
                    "label": "Compliant",
                },
            ],
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:outcomes-fw:governance",
            ref_id="governance",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:outcomes-fw:policy-exists",
            ref_id="policy-exists",
            text="Is there a policy?",
            type=Question.Type.TEXT,
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Outcomes FW (copy)"},
            format="json",
        )
        assert response.status_code == 201
        new_fw = Framework.objects.get(id=response.data["id"])

        perimeter = Perimeter.objects.create(name="Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="CA",
            framework=new_fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        new_rn = RequirementNode.objects.get(framework=new_fw)
        new_q = Question.objects.get(requirement_node=new_rn)
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=new_rn, folder=folder
        )
        Answer.objects.create(
            requirement_assessment=ra,
            question=new_q,
            value="yes",
            folder=folder,
        )

        evaluate_outcomes(ca)
        ca.refresh_from_db()
        assert ca.computed_outcome == {
            "compliant": {"result": "pass", "label": "Compliant"}
        }

    def test_duplicate_visibility_expression_with_answer_reference(
        self, authenticated_client, app_config
    ):
        """A node's visibility_expression that references answers.<q_node_id>
        must still hide/reveal correctly on the duplicated framework."""
        from core.cel_service import build_cel_context

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Vis Answer FW",
            folder=folder,
            is_published=True,
            min_score=0,
            max_score=100,
            urn_namespace="intuitem",
        )
        rn_trigger = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:vis-answer-fw:trigger",
            ref_id="trigger",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        rn_dependent = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:vis-answer-fw:dependent",
            ref_id="dependent",
            assessable=True,
            # has() guards against the "no answer yet" path (where evaluating
            # answers["toggle"] raises and CEL fails-open, masking the test).
            visibility_expression=(
                'has(answers.toggle) && answers.toggle.value == "show"'
            ),
            folder=folder,
            is_published=True,
        )
        Question.objects.create(
            requirement_node=rn_trigger,
            urn="urn:intuitem:risk:question:vis-answer-fw:toggle",
            ref_id="toggle",
            text="Show dependent?",
            type=Question.Type.TEXT,
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Vis Answer FW (copy)"},
            format="json",
        )
        assert response.status_code == 201
        new_fw = Framework.objects.get(id=response.data["id"])

        perimeter = Perimeter.objects.create(name="Perim2", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="CA2",
            framework=new_fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        new_trigger = RequirementNode.objects.get(framework=new_fw, ref_id="trigger")
        new_dependent = RequirementNode.objects.get(
            framework=new_fw, ref_id="dependent"
        )
        new_q = Question.objects.get(requirement_node=new_trigger)
        ra_trigger = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=new_trigger, folder=folder
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=new_dependent, folder=folder
        )

        # Without an answer, has() is false → expression false → hidden
        _ctx, hidden = build_cel_context(ca)
        assert new_dependent.urn in hidden, (
            "Without an answer, visibility_expression should evaluate false "
            "and hide the dependent requirement"
        )

        # Answer "show" → expression true → visible
        answer = Answer.objects.create(
            requirement_assessment=ra_trigger,
            question=new_q,
            value="show",
            folder=folder,
        )
        _ctx, hidden = build_cel_context(ca)
        assert new_dependent.urn not in hidden

        # Change answer to "hide" → expression false → hidden
        answer.value = "hide"
        answer.save(update_fields=["value"])
        _ctx, hidden = build_cel_context(ca)
        assert new_dependent.urn in hidden

    # --- depends_on edge cases ---

    def test_duplicate_depends_on_multihop_chain(
        self, authenticated_client, app_config
    ):
        """Q3 → Q2 → Q1 depends_on chain: all three question URNs and their
        answer choice URNs must be remapped consistently on the copy."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Chain FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:chain-fw:node1",
            ref_id="node1",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q1 = Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:chain-fw:q1",
            ref_id="q1",
            type=Question.Type.UNIQUE_CHOICE,
            folder=folder,
            is_published=True,
        )
        c1 = QuestionChoice.objects.create(
            question=q1,
            urn="urn:intuitem:risk:question_choice:chain-fw:q1-yes",
            ref_id="q1-yes",
            value="Yes",
            folder=folder,
            is_published=True,
        )
        q2 = Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:chain-fw:q2",
            ref_id="q2",
            type=Question.Type.UNIQUE_CHOICE,
            depends_on={
                "question": q1.urn,
                "answers": [c1.urn],
                "condition": "any",
            },
            folder=folder,
            is_published=True,
        )
        c2 = QuestionChoice.objects.create(
            question=q2,
            urn="urn:intuitem:risk:question_choice:chain-fw:q2-yes",
            ref_id="q2-yes",
            value="Yes",
            folder=folder,
            is_published=True,
        )
        Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:chain-fw:q3",
            ref_id="q3",
            type=Question.Type.TEXT,
            depends_on={
                "question": q2.urn,
                "answers": [c2.urn],
                "condition": "any",
            },
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Chain FW (copy)"},
            format="json",
        )
        assert response.status_code == 201

        new_fw_id = response.data["id"]
        qs = {
            q.ref_id: q
            for q in Question.objects.filter(requirement_node__framework_id=new_fw_id)
        }
        assert qs["q2"].depends_on["question"] == qs["q1"].urn
        assert qs["q2"].depends_on["answers"] == [
            qs["q1"].choices.get(ref_id="q1-yes").urn
        ]
        assert qs["q3"].depends_on["question"] == qs["q2"].urn
        assert qs["q3"].depends_on["answers"] == [
            qs["q2"].choices.get(ref_id="q2-yes").urn
        ]

    def test_duplicate_depends_on_all_condition(self, authenticated_client, app_config):
        """depends_on condition='all' with multiple answer URNs must have all
        choice URNs remapped and the condition preserved."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="All Cond FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:all-cond-fw:node1",
            ref_id="node1",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q1 = Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:all-cond-fw:q1",
            ref_id="q1",
            type=Question.Type.MULTIPLE_CHOICE,
            folder=folder,
            is_published=True,
        )
        ca = QuestionChoice.objects.create(
            question=q1,
            urn="urn:intuitem:risk:question_choice:all-cond-fw:q1-a",
            ref_id="a",
            value="A",
            folder=folder,
            is_published=True,
        )
        cb = QuestionChoice.objects.create(
            question=q1,
            urn="urn:intuitem:risk:question_choice:all-cond-fw:q1-b",
            ref_id="b",
            value="B",
            folder=folder,
            is_published=True,
        )
        Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:all-cond-fw:q2",
            ref_id="q2",
            type=Question.Type.TEXT,
            depends_on={
                "question": q1.urn,
                "answers": [ca.urn, cb.urn],
                "condition": "all",
            },
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "All Cond FW (copy)"},
            format="json",
        )
        assert response.status_code == 201

        new_fw_id = response.data["id"]
        new_q2 = Question.objects.get(
            requirement_node__framework_id=new_fw_id, ref_id="q2"
        )
        new_q1 = Question.objects.get(
            requirement_node__framework_id=new_fw_id, ref_id="q1"
        )
        new_ca = new_q1.choices.get(ref_id="a")
        new_cb = new_q1.choices.get(ref_id="b")
        assert new_q2.depends_on["condition"] == "all"
        assert new_q2.depends_on["question"] == new_q1.urn
        assert set(new_q2.depends_on["answers"]) == {new_ca.urn, new_cb.urn}

    def test_duplicate_depends_on_cross_node(self, authenticated_client, app_config):
        """A question on node B depending on a question on node A must still
        resolve correctly after duplicate (cross-node reference)."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="XNode FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn_a = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:xnode-fw:a",
            ref_id="a",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        rn_b = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:xnode-fw:b",
            ref_id="b",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q_a = Question.objects.create(
            requirement_node=rn_a,
            urn="urn:intuitem:risk:question:xnode-fw:qa",
            ref_id="qa",
            type=Question.Type.UNIQUE_CHOICE,
            folder=folder,
            is_published=True,
        )
        c_a = QuestionChoice.objects.create(
            question=q_a,
            urn="urn:intuitem:risk:question_choice:xnode-fw:qa-yes",
            ref_id="qa-yes",
            value="Yes",
            folder=folder,
            is_published=True,
        )
        Question.objects.create(
            requirement_node=rn_b,
            urn="urn:intuitem:risk:question:xnode-fw:qb",
            ref_id="qb",
            type=Question.Type.TEXT,
            depends_on={
                "question": q_a.urn,
                "answers": [c_a.urn],
                "condition": "any",
            },
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "XNode FW (copy)"},
            format="json",
        )
        assert response.status_code == 201

        new_fw_id = response.data["id"]
        new_qb = Question.objects.get(
            requirement_node__framework_id=new_fw_id, ref_id="qb"
        )
        new_qa = Question.objects.get(
            requirement_node__framework_id=new_fw_id, ref_id="qa"
        )
        new_ca = new_qa.choices.get(ref_id="qa-yes")
        assert new_qb.depends_on["question"] == new_qa.urn
        assert new_qb.depends_on["answers"] == [new_ca.urn]

    # --- Scalar field round-trip ---

    def test_duplicate_preserves_all_scalar_fields(
        self, authenticated_client, app_config
    ):
        """Every carried scalar field on Node/Question/Choice must round-trip
        through duplicate. Guards against silent field drops in future edits."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Scalar FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:scalar-fw:n1",
            ref_id="n1",
            name="Node name",
            description="Node desc",
            annotation="Node annotation",
            assessable=True,
            order_id=7,
            weight=3,
            importance="high",
            implementation_groups=["base", "advanced"],
            typical_evidence="Some evidence",
            visibility_expression='requirements["n1"].score >= 0',
            locale="en",
            default_locale=True,
            translations={"fr": {"name": "Nom FR"}},
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:scalar-fw:q1",
            ref_id="q1",
            text="Question text",
            annotation="Question annotation",
            type=Question.Type.UNIQUE_CHOICE,
            config={"foo": "bar"},
            order=5,
            weight=2,
            translations={"fr": {"text": "Texte FR"}},
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            urn="urn:intuitem:risk:question_choice:scalar-fw:c1",
            ref_id="c1",
            value="Yes",
            annotation="Choice annotation",
            add_score=42,
            compute_result="true",
            order=1,
            description="Choice desc",
            color="#00ff00",
            select_implementation_groups=["base"],
            translations={"fr": {"value": "Oui"}},
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Scalar FW (copy)"},
            format="json",
        )
        assert response.status_code == 201

        new_fw_id = response.data["id"]
        new_rn = RequirementNode.objects.get(framework_id=new_fw_id)
        new_q = Question.objects.get(requirement_node=new_rn)
        new_c = QuestionChoice.objects.get(question=new_q)

        for attr in (
            "ref_id",
            "name",
            "description",
            "annotation",
            "assessable",
            "order_id",
            "weight",
            "importance",
            "implementation_groups",
            "typical_evidence",
            "visibility_expression",
            "locale",
            "default_locale",
            "translations",
        ):
            assert getattr(new_rn, attr) == getattr(rn, attr), (
                f"RequirementNode.{attr} dropped: "
                f"{getattr(new_rn, attr)!r} != {getattr(rn, attr)!r}"
            )
        for attr in (
            "ref_id",
            "text",
            "annotation",
            "type",
            "config",
            "order",
            "weight",
            "translations",
        ):
            assert getattr(new_q, attr) == getattr(q, attr), f"Question.{attr} dropped"
        source_c = QuestionChoice.objects.get(question=q)
        for attr in (
            "ref_id",
            "value",
            "annotation",
            "add_score",
            "compute_result",
            "order",
            "description",
            "color",
            "select_implementation_groups",
            "translations",
        ):
            assert getattr(new_c, attr) == getattr(source_c, attr), (
                f"QuestionChoice.{attr} dropped"
            )

    # --- Folder placement ---

    def test_duplicate_uses_source_folder_when_not_specified(
        self, authenticated_client, app_config
    ):
        """Without a folder parameter, the copy lands in the source's folder."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Folder FW", folder=folder, is_published=True
        )
        RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:folder-fw:n1",
            ref_id="n1",
            assessable=True,
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Folder FW (copy)"},
            format="json",
        )
        assert response.status_code == 201
        assert Framework.objects.get(id=response.data["id"]).folder_id == folder.id

    def test_duplicate_places_nodes_in_requested_folder(
        self, authenticated_client, app_config
    ):
        """With a folder parameter, the copy and its children land there."""
        root = Folder.get_root_folder()
        target = Folder.objects.create(name="Target Folder", parent_folder=root)
        fw = Framework.objects.create(
            name="Folder Target FW", folder=root, is_published=True
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:risk:req_node:folder-target-fw:n1",
            ref_id="n1",
            assessable=True,
            folder=root,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:risk:question:folder-target-fw:q1",
            ref_id="q1",
            type=Question.Type.UNIQUE_CHOICE,
            folder=root,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            urn="urn:test:risk:question_choice:folder-target-fw:c1",
            ref_id="c1",
            value="Yes",
            folder=root,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Folder Target FW (copy)", "folder": str(target.id)},
            format="json",
        )
        assert response.status_code == 201
        new_fw = Framework.objects.get(id=response.data["id"])
        assert new_fw.folder_id == target.id
        for new_node in RequirementNode.objects.filter(framework=new_fw):
            assert new_node.folder_id == target.id
        for new_q in Question.objects.filter(requirement_node__framework=new_fw):
            assert new_q.folder_id == target.id
        for new_c in QuestionChoice.objects.filter(
            question__requirement_node__framework=new_fw
        ):
            assert new_c.folder_id == target.id

    # --- Structural edges ---

    def test_duplicate_framework_with_no_requirement_nodes(
        self, authenticated_client, app_config
    ):
        """Empty framework duplicates successfully with zero children."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Empty Dup FW", folder=folder, is_published=True
        )
        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Empty Dup FW (copy)"},
            format="json",
        )
        assert response.status_code == 201
        new_fw_id = response.data["id"]
        assert RequirementNode.objects.filter(framework_id=new_fw_id).count() == 0
        assert (
            Question.objects.filter(requirement_node__framework_id=new_fw_id).count()
            == 0
        )

    def test_duplicate_copy_of_copy_has_unique_urns(
        self, authenticated_client, app_config
    ):
        """Duplicating a duplicate: URNs across all three generations differ."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Gen0 FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:gen0-fw:n1",
            ref_id="n1",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:gen0-fw:q1",
            ref_id="q1",
            type=Question.Type.TEXT,
            folder=folder,
            is_published=True,
        )

        r1 = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Gen1 FW"},
            format="json",
        )
        assert r1.status_code == 201
        gen1_id = r1.data["id"]
        r2 = authenticated_client.post(
            reverse("frameworks-duplicate", args=[gen1_id]),
            {"name": "Gen2 FW"},
            format="json",
        )
        assert r2.status_code == 201
        gen2_id = r2.data["id"]

        gen0_urns = set(
            Question.objects.filter(requirement_node__framework=fw).values_list(
                "urn", flat=True
            )
        )
        gen1_urns = set(
            Question.objects.filter(requirement_node__framework_id=gen1_id).values_list(
                "urn", flat=True
            )
        )
        gen2_urns = set(
            Question.objects.filter(requirement_node__framework_id=gen2_id).values_list(
                "urn", flat=True
            )
        )
        assert gen0_urns.isdisjoint(gen1_urns)
        assert gen0_urns.isdisjoint(gen2_urns)
        assert gen1_urns.isdisjoint(gen2_urns)
        assert len(gen0_urns) == len(gen1_urns) == len(gen2_urns) == 1

    def test_duplicate_node_with_null_urn(self, authenticated_client, app_config):
        """A RequirementNode with urn=None (builder draft state) duplicates
        without crashing; the copy also has urn=None."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Null URN FW", folder=folder, is_published=True
        )
        RequirementNode.objects.create(
            framework=fw,
            urn=None,
            ref_id="no-urn",
            assessable=True,
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Null URN FW (copy)"},
            format="json",
        )
        assert response.status_code == 201
        new_node = RequirementNode.objects.get(framework_id=response.data["id"])
        assert new_node.urn is None
        assert new_node.ref_id == "no-urn"

    def test_duplicate_choice_with_null_urn(self, authenticated_client, app_config):
        """A QuestionChoice with urn=None must duplicate without crashing;
        the copy also has urn=None but retains other fields."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Null Choice URN FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:null-choice-urn-fw:n1",
            ref_id="n1",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:null-choice-urn-fw:q1",
            ref_id="q1",
            type=Question.Type.UNIQUE_CHOICE,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            urn=None,
            ref_id="c1",
            value="NoURN",
            folder=folder,
            is_published=True,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Null Choice URN FW (copy)"},
            format="json",
        )
        assert response.status_code == 201
        new_c = QuestionChoice.objects.get(
            question__requirement_node__framework_id=response.data["id"]
        )
        assert new_c.urn is None
        assert new_c.value == "NoURN"

    def test_duplicate_multi_level_parent_urn_chain(
        self, authenticated_client, app_config
    ):
        """parent_urn chain 4 levels deep must all re-point at the copy's
        nodes, not the source's."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Deep FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        levels = [("1", None), ("1.1", 0), ("1.1.1", 1), ("1.1.1.1", 2)]
        urns = []
        for _depth, (ref, parent_idx) in enumerate(levels):
            urn = f"urn:intuitem:risk:req_node:deep-fw:{ref}"
            urns.append(urn)
            RequirementNode.objects.create(
                framework=fw,
                urn=urn,
                ref_id=ref,
                assessable=True,
                parent_urn=urns[parent_idx] if parent_idx is not None else None,
                order_id=_depth,
                folder=folder,
                is_published=True,
            )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Deep FW (copy)"},
            format="json",
        )
        assert response.status_code == 201

        new_fw_id = response.data["id"]
        new_urns = set(
            RequirementNode.objects.filter(framework_id=new_fw_id).values_list(
                "urn", flat=True
            )
        )
        for node in RequirementNode.objects.filter(framework_id=new_fw_id):
            if node.parent_urn is not None:
                assert node.parent_urn in new_urns, (
                    f"parent_urn {node.parent_urn} points outside copy framework"
                )
                assert node.parent_urn not in urns, (
                    "parent_urn still points at source URN"
                )

    # --- Negative boundaries (what duplicate must NOT copy) ---

    def test_duplicate_does_not_copy_compliance_assessments(
        self, authenticated_client, app_config
    ):
        """The duplicated framework must start empty of ComplianceAssessments
        even if the source has assessments + answers."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="CA Boundary FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:ca-boundary-fw:n1",
            ref_id="n1",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:intuitem:risk:question:ca-boundary-fw:q1",
            ref_id="q1",
            type=Question.Type.TEXT,
            folder=folder,
            is_published=True,
        )
        perimeter = Perimeter.objects.create(name="Boundary Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Source CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
            min_score=0,
            max_score=100,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=rn, folder=folder
        )
        Answer.objects.create(
            requirement_assessment=ra, question=q, value="something", folder=folder
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "CA Boundary FW (copy)"},
            format="json",
        )
        assert response.status_code == 201
        new_fw_id = response.data["id"]
        assert not ComplianceAssessment.objects.filter(framework_id=new_fw_id).exists()
        assert not RequirementAssessment.objects.filter(
            requirement__framework_id=new_fw_id
        ).exists()
        assert not Answer.objects.filter(
            question__requirement_node__framework_id=new_fw_id
        ).exists()

    def test_duplicate_does_not_copy_attachments_or_m2m_today(
        self, authenticated_client, app_config
    ):
        """Documents current behavior: attachments, threats, and
        reference_controls are NOT carried over by the duplicate action.
        If this test ever fails, the scope of duplicate changed — audit
        whether the new behavior is intended and update accordingly."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Attach FW",
            folder=folder,
            is_published=True,
            urn_namespace="intuitem",
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:intuitem:risk:req_node:attach-fw:n1",
            ref_id="n1",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        from django.core.files.uploadedfile import SimpleUploadedFile

        RequirementNodeAttachment.objects.create(
            requirement_node=rn,
            file=SimpleUploadedFile("x.png", REAL_PNG, content_type="image/png"),
            folder=folder,
        )

        response = authenticated_client.post(
            reverse("frameworks-duplicate", args=[fw.id]),
            {"name": "Attach FW (copy)"},
            format="json",
        )
        assert response.status_code == 201
        new_rn = RequirementNode.objects.get(framework_id=response.data["id"])
        assert new_rn.attachments.count() == 0
