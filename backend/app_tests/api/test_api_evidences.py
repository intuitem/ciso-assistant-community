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


@pytest.mark.django_db
class TestEvidenceCreationAuthorization:
    """Naming an evidence on a task writes through the ORM, ahead of the task's own
    permission check, so it has to authorize add_evidence itself."""

    def _viewset(self, user, folder, names):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from core.views import TaskTemplateViewSet

        request = APIRequestFactory().post(
            "/api/task-templates/",
            {"name": "Guarded task", "folder": str(folder.id), "evidences": names},
            format="json",
        )
        force_authenticate(request, user=user)
        response = TaskTemplateViewSet.as_view({"post": "create"})(request)
        response.render()
        return response

    def test_typed_name_is_refused_without_add_evidence(self, authenticated_client):
        """The reason this test exists: add_tasktemplate alone used to be enough."""
        from unittest.mock import patch
        from iam.models import RoleAssignment, User
        from core.models import Evidence

        user = User.objects.filter(is_superuser=True).first()
        folder = Folder.get_root_folder()
        real = RoleAssignment.is_access_allowed

        def deny_add_evidence(user, perm, folder=None):
            if perm.codename == "add_evidence":
                return False
            return real(user=user, perm=perm, folder=folder)

        before = Evidence.objects.count()
        with patch.object(
            RoleAssignment, "is_access_allowed", side_effect=deny_add_evidence
        ):
            response = self._viewset(user, folder, ["Brand new evidence"])
        assert response.status_code == 403, response.data
        assert Evidence.objects.count() == before, "evidence created despite refusal"

    def test_existing_evidence_is_linked_without_add_evidence(
        self, authenticated_client
    ):
        """Reuse needs no add permission — only creation does."""
        from unittest.mock import patch
        from iam.models import RoleAssignment, User
        from core.models import Evidence, TaskTemplate

        user = User.objects.filter(is_superuser=True).first()
        folder = Folder.get_root_folder()
        existing = Evidence.objects.create(name="Already there", folder=folder)
        real = RoleAssignment.is_access_allowed

        def deny_add_evidence(user, perm, folder=None):
            if perm.codename == "add_evidence":
                return False
            return real(user=user, perm=perm, folder=folder)

        with patch.object(
            RoleAssignment, "is_access_allowed", side_effect=deny_add_evidence
        ):
            response = self._viewset(user, folder, ["Already there"])
        assert response.status_code == 201, response.data
        template = TaskTemplate.objects.get(id=response.data["id"])
        assert list(template.evidences.all()) == [existing]


@pytest.mark.django_db
class TestEvidenceRevisionFolderAuthorization:
    """EvidenceRevision.save() replaces the submitted folder with the evidence's,
    so the submitted one must not be what gets authorized."""

    def _post_revision(self, user, evidence, claimed_folder):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from core.views import EvidenceRevisionViewSet

        request = APIRequestFactory().post(
            "/api/evidence-revisions/",
            {
                "evidence": str(evidence.id),
                "folder": str(claimed_folder.id),
                "observation": "cross-folder attempt",
            },
            format="json",
        )
        force_authenticate(request, user=user)
        response = EvidenceRevisionViewSet.as_view({"post": "create"})(request)
        response.render()
        return response

    def test_claimed_folder_does_not_authorize_the_write(self, authenticated_client):
        from unittest.mock import patch
        from core.models import Evidence, EvidenceRevision
        from iam.models import Folder, RoleAssignment, User

        user = User.objects.filter(is_superuser=True).first()
        root = Folder.get_root_folder()
        allowed = Folder.objects.create(name="revision-allowed", parent_folder=root)
        forbidden = Folder.objects.create(name="revision-forbidden", parent_folder=root)
        evidence = Evidence.objects.create(name="Elsewhere", folder=forbidden)

        real = RoleAssignment.is_access_allowed

        def only_in_allowed(user, perm, folder=None):
            if perm.codename == "add_evidencerevision":
                return folder == allowed
            return real(user=user, perm=perm, folder=folder)

        before = EvidenceRevision.objects.count()
        with patch.object(
            RoleAssignment, "is_access_allowed", side_effect=only_in_allowed
        ):
            response = self._post_revision(user, evidence, claimed_folder=allowed)

        assert response.status_code == 403, response.data
        assert EvidenceRevision.objects.count() == before
        evidence.refresh_from_db()
        assert evidence.status != Evidence.Status.IN_REVIEW, (
            "evidence was moved to in_review by a refused revision"
        )

    def test_revision_requires_change_permission_on_the_evidence(
        self, authenticated_client
    ):
        """create() flips the evidence to in_review, so filing a revision is also a
        write to the parent row."""
        from unittest.mock import patch
        from core.models import Evidence, EvidenceRevision
        from iam.models import Folder, RoleAssignment, User

        user = User.objects.filter(is_superuser=True).first()
        root = Folder.get_root_folder()
        folder = Folder.objects.create(name="revision-add-only", parent_folder=root)
        evidence = Evidence.objects.create(name="Add only", folder=folder)

        real = RoleAssignment.is_access_allowed

        def no_change_evidence(user, perm, folder=None):
            if perm.codename == "change_evidence":
                return False
            return real(user=user, perm=perm, folder=folder)

        before = EvidenceRevision.objects.count()
        with patch.object(
            RoleAssignment, "is_access_allowed", side_effect=no_change_evidence
        ):
            response = self._post_revision(user, evidence, claimed_folder=folder)

        assert response.status_code == 403, response.data
        assert EvidenceRevision.objects.count() == before
        evidence.refresh_from_db()
        assert evidence.status != Evidence.Status.IN_REVIEW
