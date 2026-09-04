from os import path
import pytest
from rest_framework.test import APIClient
from core.models import AppliedControl
from core.models import Evidence
from iam.models import Folder

from test_utils import EndpointTestsQueries

# Generic evidence data for tests
EVIDENCE_NAME = "Test Evidence"
EVIDENCE_DESCRIPTION = "Test Description"
EVIDENCE_LINK = "https://example.com"
EVIDENCE_ATTACHMENT = "test_image.jpg"


@pytest.mark.django_db
class TestEvidencesUnauthenticated:
    """Perform tests on Evidences API endpoint without authentication"""

    client = APIClient()

    def test_get_evidences(self):
        """test to get evidences from the API without authentication"""

        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.get_object(
            self.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "folder": folder,
                "applied_controls": [
                    AppliedControl.objects.create(name="test", folder=folder)
                ],
            },
        )

    def test_create_evidences(self):
        """test to create evidences with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Evidences",
            Evidence,
            {"name": EVIDENCE_NAME, "folder": Folder.objects.create(name="test").id},
        )

    def test_update_evidences(self):
        """test to update evidences with the API without authentication"""

        folder = Folder.objects.create(name="test")
        folder2 = Folder.objects.create(name="test2")

        EndpointTestsQueries.update_object(
            self.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "folder": folder,
                "applied_controls": [
                    AppliedControl.objects.create(name="test", folder=folder)
                ],
            },
            {
                "name": "new " + EVIDENCE_NAME,
                "folder": str(folder2.id),
            },
        )

    def test_delete_evidences(self):
        """test to delete evidences with the API without authentication"""

        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.delete_object(
            self.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "folder": folder,
                "applied_controls": [
                    AppliedControl.objects.create(name="test", folder=folder)
                ],
            },
        )


@pytest.mark.django_db
class TestEvidencesAuthenticated:
    """Perform tests on Evidences API endpoint with authentication"""

    def test_get_evidences(self, test):
        """test to get evidences from the API with authentication"""

        applied_control = AppliedControl.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "description": EVIDENCE_DESCRIPTION,
                "folder": test.folder,
                "applied_controls": [applied_control],
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "applied_controls": [
                    {
                        "id": str(applied_control.id),
                        "str": applied_control.name,
                    }
                ],
            },
            user_group=test.user_group,
        )

    def test_create_evidences(self, test):
        """test to create evidences with the API with authentication"""

        applied_control = AppliedControl.objects.create(name="test", folder=test.folder)

        with open(
            path.join(path.dirname(path.dirname(__file__)), EVIDENCE_ATTACHMENT), "rb"
        ) as file:
            EndpointTestsQueries.Auth.create_object(
                test.client,
                "Evidences",
                Evidence,
                {
                    "name": EVIDENCE_NAME,
                    "description": EVIDENCE_DESCRIPTION,
                    "link": EVIDENCE_LINK,
                    "folder": str(test.folder.id),
                    "applied_controls": [str(applied_control.id)],
                    "attachment": file,
                },
                {
                    "folder": {"id": str(test.folder.id), "str": test.folder.name},
                    "applied_controls": [
                        {
                            "id": str(applied_control.id),
                            "str": applied_control.name,
                        }
                    ],
                    "attachment": "/" + EVIDENCE_ATTACHMENT,
                },
                query_format="multipart",
                user_group=test.user_group,
                scope=str(test.folder),
            )

    def test_update_evidences(self, test):
        """test to update evidences with the API with authentication"""

        folder = Folder.objects.create(name="test2")
        applied_control = AppliedControl.objects.create(name="test", folder=test.folder)
        applied_control2 = AppliedControl.objects.create(name="test2", folder=folder)

        with open(
            path.join(path.dirname(path.dirname(__file__)), EVIDENCE_ATTACHMENT), "rb"
        ) as file:
            EndpointTestsQueries.Auth.update_object(
                test.client,
                "Evidences",
                Evidence,
                {
                    "name": EVIDENCE_NAME,
                    "description": EVIDENCE_DESCRIPTION,
                    "folder": test.folder,
                    "applied_controls": [applied_control],
                },
                {
                    "name": "new " + EVIDENCE_NAME,
                    "description": "new " + EVIDENCE_DESCRIPTION,
                    "folder": str(folder.id),
                    "applied_controls": [str(applied_control2.id)],
                },
                {
                    "folder": {"id": str(test.folder.id), "str": test.folder.name},
                    "applied_controls": [
                        {
                            "id": str(applied_control.id),
                            "str": applied_control.name,
                        }
                    ],
                },
                {
                    "applied_controls": [str(applied_control2.id)],
                },
                query_format="multipart",
                user_group=test.user_group,
            )

    def test_delete_evidences(self, test):
        """test to delete evidences with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "folder": test.folder,
                "applied_controls": [
                    AppliedControl.objects.create(name="test", folder=test.folder)
                ],
            },
            user_group=test.user_group,
        )


@pytest.mark.django_db
class TestEvidenceRevisionCreation:
    """A revision stands for a deposited artifact, so an empty one is not opened."""

    def _create(self, authenticated_client, name, **extra):
        response = authenticated_client.post(
            "/api/evidences/",
            {
                "name": name,
                "folder": str(Folder.get_root_folder().id),
                **extra,
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        return Evidence.objects.get(id=response.json()["id"])

    def test_no_revision_when_nothing_is_deposited(self, authenticated_client):
        evidence = self._create(authenticated_client, "Definition only")
        assert evidence.revisions.count() == 0
        assert evidence.last_revision is None

    def test_blank_values_do_not_count_as_content(self, authenticated_client):
        evidence = self._create(authenticated_client, "Blank fields", observation="")
        assert evidence.revisions.count() == 0

    def test_link_opens_a_revision(self, authenticated_client):
        evidence = self._create(
            authenticated_client, "With link", link="https://example.com/proof"
        )
        assert evidence.revisions.count() == 1
        assert evidence.last_revision.link == "https://example.com/proof"

    def test_observation_opens_a_revision(self, authenticated_client):
        evidence = self._create(
            authenticated_client, "With observation", observation="collected by hand"
        )
        assert evidence.revisions.count() == 1
        assert evidence.last_revision.observation == "collected by hand"

    def test_attachment_endpoint_404s_without_a_revision(self, authenticated_client):
        evidence = self._create(authenticated_client, "No attachment")
        response = authenticated_client.get(f"/api/evidences/{evidence.id}/attachment/")
        assert response.status_code == 404

    def test_observation_is_not_echoed_back(self, authenticated_client):
        """It belongs to the revision, not to the evidence representation."""
        response = authenticated_client.post(
            "/api/evidences/",
            {
                "name": "Write only",
                "folder": str(Folder.get_root_folder().id),
                "observation": "internal note",
            },
            format="json",
        )
        assert response.status_code == 201
        assert "observation" not in response.json()
