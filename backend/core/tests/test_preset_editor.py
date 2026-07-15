"""Preset apply (journey creation).

The standalone preset-editor endpoints (create-blank/start-editing/
save-draft/publish-draft/discard/duplicate) were retired with the other
per-object editors: presets are authored in the library builder and
materialize through the loader. What remains user-facing on PresetViewSet
is `apply`, covered here against an ORM-authored preset.
"""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import (
    Framework,
    LoadedLibrary,
    Preset,
    PresetJourney,
    PresetJourneyStep,
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
def loaded_framework(app_config):
    """A loaded framework so compliance-assessment scaffolds can resolve."""
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
    return fw_lib.urn


@pytest.mark.django_db
def test_apply_preset_creates_linked_journey(admin_client, loaded_framework):
    preset = Preset.objects.create(
        name="Applyable",
        folder=Folder.get_root_folder(),
        scaffolded_objects=[
            {
                "type": "compliance_assessment",
                "ref": "ca1",
                "name": "ISO audit",
                "framework": loaded_framework,
            }
        ],
        steps=[
            {
                "id": "step-1",
                "key": "compliance",
                "title": "Audit",
                "description": "",
                "target_model": "compliance-assessments",
                "target_ref": "ca1",
            }
        ],
    )
    response = admin_client.post(
        f"/api/presets/{preset.id}/apply/",
        {"folder_name": "Applied folder", "apply_feature_flags": False},
        format="json",
    )
    assert response.status_code == 201, response.data
    journey = PresetJourney.objects.get(id=response.data["journey_id"])
    assert journey.preset_id == preset.id
    # The step's target_ref now points at the materialized CA, not the seed.
    ca_step = PresetJourneyStep.objects.get(journey=journey, key="compliance")
    assert ca_step.target_ref and ca_step.target_ref != "ca1"
