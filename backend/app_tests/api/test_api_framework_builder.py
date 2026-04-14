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
    Framework,
    RequirementNode,
    Question,
    QuestionChoice,
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
