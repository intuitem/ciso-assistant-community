"""Tests for the Preset editor endpoints (draft/publish/duplicate)."""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import (
    Framework,
    LoadedLibrary,
    Preset,
    PresetJourney,
    PresetJourneyStep,
    RiskMatrix,
)
from core.startup import startup
from iam.models import Folder, User, UserGroup


@pytest.fixture
def app_config():
    startup(sender=None, **{})


@pytest.fixture
def admin_client(app_config):
    admin = User.objects.create_superuser(
        "admin@preset-editor-tests.com", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def loaded_libs(app_config):
    """Create a loaded framework + risk matrix so CA/RA scaffolds can resolve."""
    root = Folder.get_root_folder()
    fw_lib = LoadedLibrary.objects.create(
        urn="urn:test:editor:framework",
        locale="en",
        version=1,
        name="Editor Framework Library",
        folder=root,
        objects_meta={},
    )
    Framework.objects.create(name="Editor Framework", folder=root, library=fw_lib)
    mtx_lib = LoadedLibrary.objects.create(
        urn="urn:test:editor:matrix",
        locale="en",
        version=1,
        name="Editor Matrix Library",
        folder=root,
        objects_meta={},
    )
    RiskMatrix.objects.create(
        name="Editor Matrix",
        folder=root,
        library=mtx_lib,
        json_definition={
            "probability": [{"abbreviation": "L", "name": "Low"}],
            "impact": [{"abbreviation": "L", "name": "Low"}],
            "risk": [{"abbreviation": "L", "name": "Low"}],
            "grid": [[0]],
        },
    )
    return {"framework_urn": fw_lib.urn, "matrix_urn": mtx_lib.urn}


def _create_blank(client, name="Test preset"):
    r = client.post("/api/presets/create-blank/", {"name": name}, format="json")
    assert r.status_code == 201, r.data
    return r.data["id"]


@pytest.mark.django_db
class TestEditorEndpoints:
    def test_create_blank_returns_user_authored(self, admin_client):
        r = admin_client.post(
            "/api/presets/create-blank/", {"name": "Blank A"}, format="json"
        )
        assert r.status_code == 201
        assert r.data["is_user_authored"] is True
        assert r.data["urn"] is None
        assert r.data["name"] == "Blank A"
        # default-named when omitted
        r2 = admin_client.post("/api/presets/create-blank/", {}, format="json")
        assert r2.status_code == 201
        assert r2.data["name"] == "Untitled preset"

    def test_start_editing_seeds_draft_and_is_idempotent(self, admin_client):
        pid = _create_blank(admin_client)
        r1 = admin_client.post(f"/api/presets/{pid}/start-editing/")
        assert r1.status_code == 200
        d1 = r1.data["editing_draft"]
        assert d1["journey_meta"]["name"] == "Test preset"
        assert d1["scaffolded_objects"] == []
        assert d1["steps"] == []
        # Second call returns the same draft (no regeneration)
        r2 = admin_client.post(f"/api/presets/{pid}/start-editing/")
        assert r2.status_code == 200
        assert r2.data["editing_draft"] == d1

    def test_save_draft_lenient_accepts_empty_framework(self, admin_client):
        pid = _create_blank(admin_client)
        admin_client.post(f"/api/presets/{pid}/start-editing/")
        draft = {
            "journey_meta": {"name": "WIP", "description": ""},
            "scaffolded_objects": [
                {
                    "type": "compliance_assessment",
                    "ref": "ca1",
                    "name": "WIP CA",
                    "framework": "",
                    "step_ref_id": "s1",
                }
            ],
            "steps": [
                {
                    "id": None,
                    "key": "s1",
                    "title": "",
                    "description": "",
                    "target_model": "",
                }
            ],
        }
        r = admin_client.patch(f"/api/presets/{pid}/save-draft/", draft, format="json")
        assert r.status_code == 200, r.data
        saved = r.data["editing_draft"]
        # Empty target_model preserved as the mode signal
        assert saved["steps"][0]["target_model"] == ""
        # Empty framework preserved on the scaffold
        assert saved["scaffolded_objects"][0]["framework"] == ""

    def test_publish_strict_rejects_empty_framework(self, admin_client):
        pid = _create_blank(admin_client)
        admin_client.post(f"/api/presets/{pid}/start-editing/")
        draft = {
            "journey_meta": {"name": "WIP", "description": ""},
            "scaffolded_objects": [
                {
                    "type": "compliance_assessment",
                    "ref": "ca1",
                    "name": "WIP CA",
                    "framework": "",
                }
            ],
            "steps": [],
        }
        admin_client.patch(f"/api/presets/{pid}/save-draft/", draft, format="json")
        r = admin_client.post(f"/api/presets/{pid}/publish-draft/")
        assert r.status_code == 400
        assert "framework" in str(r.data).lower()

    def test_publish_snapshots_history_and_clears_draft(
        self, admin_client, loaded_libs
    ):
        pid = _create_blank(admin_client)
        admin_client.post(f"/api/presets/{pid}/start-editing/")
        draft = {
            "journey_meta": {"name": "Final", "description": "Done"},
            "scaffolded_objects": [
                {
                    "type": "compliance_assessment",
                    "ref": "ca1",
                    "name": "Real CA",
                    "framework": loaded_libs["framework_urn"],
                    "step_ref_id": "compliance",
                }
            ],
            "steps": [
                {
                    "id": None,
                    "key": "compliance",
                    "title": "Run audit",
                    "description": "",
                    "target_model": "compliance-assessments",
                    "target_ref": "ca1",
                }
            ],
        }
        admin_client.patch(f"/api/presets/{pid}/save-draft/", draft, format="json")
        r = admin_client.post(f"/api/presets/{pid}/publish-draft/")
        assert r.status_code == 200, r.data
        p = Preset.objects.get(id=pid)
        assert p.editing_version == 2
        assert p.version == 2
        assert p.editing_draft is None
        assert len(p.editing_history) == 1
        # Live fields updated from the draft
        assert p.name == "Final"
        assert len(p.steps) == 1
        assert p.steps[0]["key"] == "compliance"
        assert len(p.scaffolded_objects) == 1

    def test_publish_preview_lists_step_deletions(self, admin_client, loaded_libs):
        pid = _create_blank(admin_client)
        admin_client.post(f"/api/presets/{pid}/start-editing/")
        # First publish: 2 steps
        full = {
            "journey_meta": {"name": "P", "description": ""},
            "scaffolded_objects": [],
            "steps": [
                {"id": None, "key": "a", "title": "A", "target_model": "assets"},
                {"id": None, "key": "b", "title": "B", "target_model": "assets"},
            ],
        }
        admin_client.patch(f"/api/presets/{pid}/save-draft/", full, format="json")
        admin_client.post(f"/api/presets/{pid}/publish-draft/")
        # Second draft: drop step "b"
        admin_client.post(f"/api/presets/{pid}/start-editing/")
        full["steps"] = [full["steps"][0]]
        admin_client.patch(f"/api/presets/{pid}/save-draft/", full, format="json")
        r = admin_client.post(f"/api/presets/{pid}/publish-draft-preview/")
        assert r.status_code == 200
        deleted = r.data["deleted_steps"]
        assert len(deleted) == 1
        assert deleted[0]["key"] == "b"

    def test_discard_draft_reverts_to_published(self, admin_client, loaded_libs):
        pid = _create_blank(admin_client)
        admin_client.post(f"/api/presets/{pid}/start-editing/")
        draft = {
            "journey_meta": {"name": "Edited", "description": ""},
            "scaffolded_objects": [],
            "steps": [],
        }
        admin_client.patch(f"/api/presets/{pid}/save-draft/", draft, format="json")
        p = Preset.objects.get(id=pid)
        assert p.editing_draft is not None
        r = admin_client.post(f"/api/presets/{pid}/discard-draft/")
        assert r.status_code == 200
        p.refresh_from_db()
        assert p.editing_draft is None
        # Live fields untouched
        assert p.name == "Test preset"

    def test_duplicate_clones_with_urn_null(self, admin_client):
        # Build a "library-backed" preset directly
        root = Folder.get_root_folder()
        source = Preset.objects.create(
            name="Source preset",
            description="Library source",
            folder=root,
            urn="urn:test:source",
            ref_id="source",
            version=3,
            provider="intuitem",
            scaffolded_objects=[{"type": "processing", "ref": "p1", "name": "P1"}],
            steps=[{"key": "s1", "title": "S1", "target_model": "processings"}],
            editing_history=[{"version": 1, "name": "old"}],
        )
        r = admin_client.post(f"/api/presets/{source.id}/duplicate/")
        assert r.status_code == 201, r.data
        new = Preset.objects.get(id=r.data["id"])
        assert new.urn is None
        assert new.ref_id is None
        assert new.version == 1
        assert new.provider is None
        assert new.editing_history == []
        assert new.editing_draft is None
        assert new.name == "Source preset (copy)"
        assert len(new.scaffolded_objects) == 1
        assert len(new.steps) == 1

    def test_library_preset_edit_blocked(self, admin_client):
        root = Folder.get_root_folder()
        lib = Preset.objects.create(
            name="Lib preset",
            folder=root,
            urn="urn:test:lib-edit",
            version=1,
        )
        r = admin_client.post(f"/api/presets/{lib.id}/start-editing/")
        assert r.status_code == 400
        assert "library" in str(r.data).lower()

    def test_apply_user_authored_creates_linked_journey(
        self, admin_client, loaded_libs
    ):
        pid = _create_blank(admin_client)
        admin_client.post(f"/api/presets/{pid}/start-editing/")
        draft = {
            "journey_meta": {"name": "Applyable", "description": ""},
            "scaffolded_objects": [
                {
                    "type": "compliance_assessment",
                    "ref": "ca1",
                    "name": "ISO audit",
                    "framework": loaded_libs["framework_urn"],
                }
            ],
            "steps": [
                {
                    "id": None,
                    "key": "compliance",
                    "title": "Audit",
                    "description": "",
                    "target_model": "compliance-assessments",
                    "target_ref": "ca1",
                }
            ],
        }
        admin_client.patch(f"/api/presets/{pid}/save-draft/", draft, format="json")
        admin_client.post(f"/api/presets/{pid}/publish-draft/")
        r = admin_client.post(
            f"/api/presets/{pid}/apply/",
            {"folder_name": "Applied folder", "apply_feature_flags": False},
            format="json",
        )
        assert r.status_code == 201, r.data
        journey = PresetJourney.objects.get(id=r.data["journey_id"])
        assert str(journey.preset_id) == pid
        assert journey.applied_version == 2
        # Step's target_ref should now point to the materialized CA UUID
        ca_step = PresetJourneyStep.objects.get(journey=journey, key="compliance")
        assert ca_step.target_ref and ca_step.target_ref != "ca1"

    def test_target_model_empty_round_trips_through_save(self, admin_client):
        """Mode signal ('user picked Model but hasn't filled it') survives save."""
        pid = _create_blank(admin_client)
        admin_client.post(f"/api/presets/{pid}/start-editing/")
        draft = {
            "journey_meta": {"name": "P", "description": ""},
            "scaffolded_objects": [],
            "steps": [
                {
                    "id": None,
                    "key": "s1",
                    "title": "S",
                    "target_model": "",  # Model mode, no model picked
                },
                {
                    "id": None,
                    "key": "s2",
                    "title": "S2",
                    "target_url": "",  # URL mode, no URL yet
                },
            ],
        }
        r = admin_client.patch(f"/api/presets/{pid}/save-draft/", draft, format="json")
        assert r.status_code == 200
        saved = r.data["editing_draft"]
        assert saved["steps"][0]["target_model"] == ""
        assert "target_url" not in saved["steps"][0]
        assert saved["steps"][1]["target_url"] == ""
        assert "target_model" not in saved["steps"][1]
