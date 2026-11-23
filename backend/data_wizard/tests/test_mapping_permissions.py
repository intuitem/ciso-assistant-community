"""Real role checks (no RBAC patching) for the mapped import and saved mappings:
an admin, an analyst of one domain, and a user without any role."""

import json
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import AppliedControl
from data_wizard.models import ImportMapping
from iam.models import Folder, User, UserGroup

SAMPLES = Path(__file__).parent / "samples"
TRACKER = "02_isms_controls_tracker_EN.xlsx"
IMPORT_URL = "/api/data-wizard/mapping/import/"
MAPPINGS_URL = "/api/data-wizard/mappings/"
STEP = {
    "model_type": "AppliedControl",
    "sheets": [
        {
            "source": "Controls",
            "target": "Sheet1",
            "header_row": 2,
            "columns": {"Control ID": "ref_id", "Control": "name"},
        }
    ],
}


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def domains(app_ready):
    mine = Folder.objects.create(
        name="Analyst domain",
        parent_folder=app_ready,
        content_type=Folder.ContentType.DOMAIN,
        create_iam_groups=True,
    )
    other = Folder.objects.create(
        name="Someone else's domain",
        parent_folder=app_ready,
        content_type=Folder.ContentType.DOMAIN,
    )
    Folder.create_default_ug_and_ra(mine)
    return mine, other


@pytest.fixture
def analyst_client(domains):
    user = User.objects.create_user("analyst@datawizard.test")
    UserGroup.objects.get(name="BI-UG-ANA", folder=domains[0]).user_set.add(user)
    return _client(user)


def _import(client, folder, dry_run=False):
    return client.post(
        IMPORT_URL,
        {
            "file": SimpleUploadedFile(TRACKER, (SAMPLES / TRACKER).read_bytes()),
            "mapping": json.dumps({"steps": [STEP]}),
            "options": json.dumps({"folder_id": str(folder.id), "on_conflict": "skip"}),
            "dry_run": str(dry_run).lower(),
        },
        format="multipart",
    )


@pytest.mark.django_db
class TestImport:
    def test_analyst_imports_into_their_domain(self, analyst_client, domains):
        resp = _import(analyst_client, domains[0])
        assert resp.status_code == 200
        assert resp.json()["steps"][0]["status"] == 200
        assert AppliedControl.objects.filter(folder=domains[0]).count() == 10

    def test_analyst_cannot_import_elsewhere_even_in_a_dry_run(
        self, analyst_client, domains
    ):
        for dry_run in (True, False):
            resp = _import(analyst_client, domains[1], dry_run)
            step = resp.json()["steps"][0]
            assert (step["status"], step["error"]) == (403, "notAllowed")
        assert not AppliedControl.objects.exists()

    def test_user_without_role_cannot_import(self, knox_restricted_client, domains):
        resp = _import(knox_restricted_client, domains[0], dry_run=True)
        assert resp.json()["steps"][0]["status"] == 403


@pytest.mark.django_db
class TestSavedMappings:
    @pytest.fixture
    def saved(self, app_ready):
        return ImportMapping.objects.create(
            name="Shared tracker",
            folder=app_ready,
            sheets=[
                {**STEP["sheets"][0], "model_type": "AppliedControl", "headers": []}
            ],
        )

    def test_domain_users_see_instance_mappings(
        self, analyst_client, knox_restricted_client, saved
    ):
        # Through the baseline reader role the Global domain grants to anyone
        # with a role somewhere; a user with no role at all sees nothing.
        names = [m["name"] for m in analyst_client.get(MAPPINGS_URL).json()["results"]]
        assert names == ["Shared tracker"]
        assert knox_restricted_client.get(MAPPINGS_URL).json()["results"] == []

    def test_domain_analyst_cannot_save_or_delete_in_global(
        self, analyst_client, app_ready, saved
    ):
        body = {
            "name": "Mine",
            "folder": str(app_ready.id),
            "sheets": [
                {
                    **STEP["sheets"][0],
                    "model_type": "AppliedControl",
                    "headers": ["Control ID", "Control"],
                }
            ],
        }
        assert analyst_client.post(MAPPINGS_URL, body, format="json").status_code == 403
        assert analyst_client.delete(f"{MAPPINGS_URL}{saved.id}/").status_code in (
            403,
            404,
        )
        assert ImportMapping.objects.filter(id=saved.id).exists()

    def test_admin_can_delete(self, knox_admin_client, saved):
        assert knox_admin_client.delete(f"{MAPPINGS_URL}{saved.id}/").status_code == 204
        assert not ImportMapping.objects.exists()
