from os import path
import pytest
from rest_framework.test import APIClient
from core.models import AppliedControl
from core.models import Evidence
from core.models import TaskTemplate
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


@pytest.mark.django_db
class TestEvidenceTaskTemplateLink:
    """Creating an evidence from a task's evidence table has to link it back:
    task_templates is a reverse M2M, so it only travels if declared."""

    def _task(self, name="Recurring task"):
        return TaskTemplate.objects.create(name=name, folder=Folder.get_root_folder())

    def test_create_links_the_task(self, authenticated_client):
        task = self._task()
        response = authenticated_client.post(
            "/api/evidences/",
            {
                "name": "Quarterly report",
                "folder": str(Folder.get_root_folder().id),
                "task_templates": [str(task.id)],
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        evidence = Evidence.objects.get(id=response.json()["id"])
        assert list(evidence.task_templates.all()) == [task]

    def test_a_task_accepts_several_evidences(self, authenticated_client):
        task = self._task()
        for name in ("First deposit", "Second deposit"):
            response = authenticated_client.post(
                "/api/evidences/",
                {
                    "name": name,
                    "folder": str(Folder.get_root_folder().id),
                    "task_templates": [str(task.id)],
                },
                format="json",
            )
            assert response.status_code == 201, response.json()
        assert task.evidences.count() == 2

    def test_update_links_the_task(self, authenticated_client):
        task = self._task()
        evidence = Evidence.objects.create(
            name="Existing", folder=Folder.get_root_folder()
        )
        response = authenticated_client.patch(
            f"/api/evidences/{evidence.id}/",
            {"task_templates": [str(task.id)]},
            format="json",
        )
        assert response.status_code == 200, response.json()
        assert list(evidence.task_templates.all()) == [task]

    def test_retrieve_exposes_the_linked_tasks(self, authenticated_client):
        task = self._task()
        evidence = Evidence.objects.create(
            name="Linked", folder=Folder.get_root_folder()
        )
        evidence.task_templates.set([task])
        response = authenticated_client.get(f"/api/evidences/{evidence.id}/")
        assert response.status_code == 200, response.json()
        assert [t["id"] for t in response.json()["task_templates"]] == [str(task.id)]

    def test_omitting_the_field_keeps_existing_links(self, authenticated_client):
        task = self._task()
        evidence = Evidence.objects.create(
            name="Existing", folder=Folder.get_root_folder()
        )
        evidence.task_templates.set([task])
        response = authenticated_client.patch(
            f"/api/evidences/{evidence.id}/",
            {"name": "Renamed"},
            format="json",
        )
        assert response.status_code == 200, response.json()
        assert list(evidence.task_templates.all()) == [task]


@pytest.mark.django_db
class TestEvidenceUploadUrl:
    """Single-use upload URL: what the remote MCP tool hands to the claude.ai
    sandbox curl. The token in the URL is the only credential."""

    @pytest.fixture(autouse=True)
    def _media(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        settings.CISO_ASSISTANT_URL = "https://ca.example.com"

    def _evidence(self, name="Token evidence"):
        return Evidence.objects.create(name=name, folder=Folder.get_root_folder())

    def _issue(self, authenticated_client, evidence, filename="proof.pdf"):
        response = authenticated_client.post(
            f"/api/evidences/{evidence.id}/upload-url/",
            {"filename": filename},
            format="json",
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["expires_at"]
        prefix = "https://ca.example.com/api/evidences/upload/"
        assert body["url"].startswith(prefix)
        return body["url"][len("https://ca.example.com") :]

    def _put(self, path, content=b"%PDF-1.4 token upload", **extra):
        # Unauthenticated, like the sandbox curl
        return APIClient().generic(
            "POST", path, content, content_type="application/octet-stream", **extra
        )

    def _latest(self, evidence):
        return evidence.revisions.order_by("-version").first()

    def _has_file(self, evidence):
        revision = self._latest(evidence)
        return bool(revision and revision.attachment)

    def test_upload_stores_the_file_as_the_token_user(self, authenticated_client):
        from iam.models import User

        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        response = self._put(path)
        assert response.status_code == 200, response.content
        assert response.json() == {
            "evidence": str(evidence.id),
            "filename": "proof.pdf",
            "size": len(b"%PDF-1.4 token upload"),
        }
        revision = self._latest(evidence)
        assert revision.attachment.read() == b"%PDF-1.4 token upload"
        assert revision.original_filename == "proof.pdf"
        assert revision.uploaded_by == User.objects.get(email="admin@tests.com")

    def test_token_is_single_use(self, authenticated_client):
        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        assert self._put(path).status_code == 200
        replay = self._put(path, b"%PDF-1.4 other bytes")
        assert replay.status_code == 410
        assert self._latest(evidence).attachment.read() == b"%PDF-1.4 token upload"

    def test_replay_with_identical_bytes_is_refused(self, authenticated_client):
        """Same content, same hash: the stored name still changes the state."""
        evidence = self._evidence()
        assert self._put(self._issue(authenticated_client, evidence)).status_code == 200
        second = self._issue(authenticated_client, evidence)
        assert self._put(second).status_code == 200
        assert self._put(second).status_code == 410

    def test_existing_file_is_replaced(self, authenticated_client):
        evidence = self._evidence()
        assert self._put(self._issue(authenticated_client, evidence)).status_code == 200
        path = self._issue(authenticated_client, evidence, "second.pdf")
        assert self._put(path, b"%PDF-1.4 second").status_code == 200
        revision = self._latest(evidence)
        assert revision.attachment.read() == b"%PDF-1.4 second"
        assert revision.original_filename == "second.pdf"

    def test_expired_token_is_gone(self, authenticated_client):
        import time
        from unittest.mock import patch

        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        later = time.time() + 15 * 60 + 5
        with patch("django.core.signing.time.time", return_value=later):
            assert self._put(path).status_code == 410
        assert not self._has_file(evidence)

    def test_tampered_token_is_not_found(self, authenticated_client):
        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        token = path.rstrip("/").rsplit("/", 1)[1]
        tampered = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
        assert self._put(f"/api/evidences/upload/{tampered}/").status_code == 404
        assert self._put("/api/evidences/upload/garbage/").status_code == 404
        assert not self._has_file(evidence)

    def test_revoked_permission_is_refused(self, authenticated_client):
        from unittest.mock import patch
        from iam.models import RoleAssignment

        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        with patch.object(RoleAssignment, "is_object_accessible", return_value=False):
            assert self._put(path).status_code == 403
        assert not self._has_file(evidence)

    def test_inactive_user_is_refused(self, authenticated_client):
        from iam.models import User

        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        User.objects.filter(email="admin@tests.com").update(is_active=False)
        assert self._put(path).status_code == 404

    def test_declared_too_large_is_refused(self, authenticated_client, settings):
        settings.ATTACHMENT_MAX_SIZE_MB = 1
        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        response = self._put(path, b"x", CONTENT_LENGTH="2000001")
        assert response.status_code == 413
        assert not self._has_file(evidence)

    def test_missing_content_length_is_a_411(self, authenticated_client):
        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        response = self._put(path, CONTENT_LENGTH="")
        assert response.status_code == 411
        assert not self._has_file(evidence)

    def test_refused_file_type_is_refused_at_issue(self, authenticated_client):
        evidence = self._evidence()
        response = authenticated_client.post(
            f"/api/evidences/{evidence.id}/upload-url/",
            {"filename": "tool.exe"},
            format="json",
        )
        assert response.status_code == 400
        assert "extension" in response.json()["filename"]

    def test_control_characters_in_the_name_are_refused(self, authenticated_client):
        evidence = self._evidence()
        response = authenticated_client.post(
            f"/api/evidences/{evidence.id}/upload-url/",
            {"filename": "proof\r\n.pdf"},
            format="json",
        )
        assert response.status_code == 400

    def test_non_object_body_is_a_400(self, authenticated_client):
        evidence = self._evidence()
        response = authenticated_client.post(
            f"/api/evidences/{evidence.id}/upload-url/", ["proof.pdf"], format="json"
        )
        assert response.status_code == 400

    def test_replay_after_a_new_empty_revision_is_refused(self, authenticated_client):
        """The fingerprint only moves forward: an empty revision added after the
        upload does not bring back the state the token was issued for."""
        from core.models import EvidenceRevision

        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        assert self._put(path).status_code == 200
        EvidenceRevision.objects.create(evidence=evidence, version=99)
        assert self._put(path, b"%PDF-1.4 replay").status_code == 410

    def test_replay_after_deleting_the_uploaded_revision_is_refused(
        self, authenticated_client
    ):
        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        assert self._put(path).status_code == 200
        evidence.revisions.all().delete()
        assert self._put(path, b"%PDF-1.4 replay").status_code == 410

    def test_audit_log_credits_the_token_user(self, authenticated_client):
        from auditlog.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        from core.models import EvidenceRevision
        from iam.models import User

        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        assert self._put(path).status_code == 200
        entry = (
            LogEntry.objects.filter(
                content_type=ContentType.objects.get_for_model(EvidenceRevision),
                object_pk=str(self._latest(evidence).id),
            )
            .order_by("-timestamp")
            .first()
        )
        assert entry is not None
        assert entry.actor == User.objects.get(email="admin@tests.com")

    def test_empty_body_is_a_400(self, authenticated_client):
        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence)
        assert self._put(path, b"").status_code == 400

    def test_upload_reopens_a_decided_review(self, authenticated_client):
        evidence = self._evidence()
        assert self._put(self._issue(authenticated_client, evidence)).status_code == 200
        Evidence.objects.filter(id=evidence.id).update(status=Evidence.Status.APPROVED)
        path = self._issue(authenticated_client, evidence, "new.pdf")
        assert self._put(path, b"%PDF-1.4 new").status_code == 200
        evidence.refresh_from_db()
        assert evidence.status == Evidence.Status.IN_REVIEW

    def test_regular_upload_still_works(self, authenticated_client):
        from iam.models import User

        evidence = self._evidence()
        response = authenticated_client.post(
            f"/api/evidences/{evidence.id}/upload/",
            data=b"%PDF-1.4 classic",
            content_type="application/pdf",
            HTTP_CONTENT_DISPOSITION='attachment; filename="classic.pdf"',
        )
        assert response.status_code == 200, response.content
        revision = self._latest(evidence)
        assert revision.attachment.read() == b"%PDF-1.4 classic"
        assert revision.uploaded_by == User.objects.get(email="admin@tests.com")

    def test_issuing_needs_change_permission(self, authenticated_client):
        from unittest.mock import patch
        from iam.models import RoleAssignment

        evidence = self._evidence()
        real = RoleAssignment.is_object_accessible

        def no_change(user, perm_prefix, model, id):
            if perm_prefix == "change":
                return False
            return real(user, perm_prefix, model, id)

        with patch.object(
            RoleAssignment, "is_object_accessible", side_effect=no_change
        ):
            response = authenticated_client.post(
                f"/api/evidences/{evidence.id}/upload-url/",
                {"filename": "proof.pdf"},
                format="json",
            )
        assert response.status_code == 403

    def test_issuing_needs_a_filename(self, authenticated_client):
        evidence = self._evidence()
        response = authenticated_client.post(
            f"/api/evidences/{evidence.id}/upload-url/", {}, format="json"
        )
        assert response.status_code == 400

    def test_issuing_keeps_only_the_base_name(self, authenticated_client):
        evidence = self._evidence()
        path = self._issue(authenticated_client, evidence, "../../etc/proof.pdf")
        assert self._put(path).json()["filename"] == "proof.pdf"

    def test_issuing_requires_authentication(self):
        evidence = self._evidence()
        response = APIClient().post(
            f"/api/evidences/{evidence.id}/upload-url/",
            {"filename": "proof.pdf"},
            format="json",
        )
        assert response.status_code in (401, 403)

    def test_token_is_redacted_from_logs(self):
        import logging
        from ciso_assistant.settings import (
            RedactUploadTokenFilter,
            redact_upload_tokens,
        )

        event = redact_upload_tokens(
            None, None, {"request": "POST /api/evidences/upload/abc.def:ghi/"}
        )
        assert event["request"] == "POST /api/evidences/upload/REDACTED/"

        record = logging.LogRecord(
            "django.request",
            logging.WARNING,
            "",
            0,
            "%s: %s",
            ("Gone", "/api/evidences/upload/abc.def:ghi/"),
            None,
        )
        RedactUploadTokenFilter().filter(record)
        assert record.getMessage() == "Gone: /api/evidences/upload/REDACTED/"

    def test_token_redaction_is_wired_into_logging(self):
        import structlog
        from django.conf import settings as django_settings
        from ciso_assistant.settings import redact_upload_tokens

        handlers = django_settings.LOGGING["handlers"]
        for name in ("stdout", "stderr", "file"):
            if name in handlers:
                assert "redact_upload_token" in handlers[name]["filters"], name
        processors = structlog.get_config()["processors"]
        assert redact_upload_tokens in processors
