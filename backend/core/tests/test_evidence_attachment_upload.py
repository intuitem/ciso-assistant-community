"""Re-uploading onto an evidence that already carries a file must replace it, not empty it (#4873)."""

import hashlib

import pytest
from iam.models import Folder, User, UserGroup
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.apps import startup
from core.models import Evidence


@pytest.fixture
def app_config():
    startup(sender=None)


@pytest.fixture
def admin_client(app_config):
    admin = User.objects.create_superuser("admin@evidence-upload-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def evidence(app_config, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    folder = Folder.objects.create(name="folder-evidence-upload", parent_folder=root)
    return Evidence.objects.create(name="Evidence under test", folder=folder)


def _upload(client, evidence, filename, content):
    """The frontend's call: raw body + Content-Disposition (see actions.ts)."""
    response = client.post(
        f"/api/evidences/{evidence.id}/upload/",
        data=content,
        content_type="application/pdf",
        HTTP_CONTENT_DISPOSITION=f'attachment; filename="{filename}"',
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    return response


def _stored(evidence):
    revision = evidence.revisions.order_by("-version").first()
    revision.refresh_from_db()
    return revision


@pytest.mark.django_db
class TestEvidenceAttachmentUpload:
    def test_first_upload_is_stored(self, admin_client, evidence):
        _upload(admin_client, evidence, "first.pdf", b"%PDF-1.4 first")

        revision = _stored(evidence)
        assert revision.attachment
        assert revision.attachment.read() == b"%PDF-1.4 first"
        assert revision.original_filename == "first.pdf"

    def test_second_upload_replaces_instead_of_clearing(self, admin_client, evidence):
        _upload(admin_client, evidence, "first.pdf", b"%PDF-1.4 first")
        first_name = _stored(evidence).attachment.name

        _upload(admin_client, evidence, "second.pdf", b"%PDF-1.4 second")

        revision = _stored(evidence)
        assert revision.attachment, "the evidence was emptied by the second upload"
        assert revision.attachment.read() == b"%PDF-1.4 second"
        assert revision.original_filename == "second.pdf"
        assert not revision.attachment.storage.exists(first_name)

    def test_reupload_under_the_same_name_updates_the_content(
        self, admin_client, evidence
    ):
        _upload(admin_client, evidence, "report.pdf", b"%PDF-1.4 v1")
        _upload(admin_client, evidence, "report.pdf", b"%PDF-1.4 v2")

        revision = _stored(evidence)
        assert revision.attachment
        assert revision.attachment.read() == b"%PDF-1.4 v2"

    @pytest.mark.parametrize("second_name", ["second.pdf", "first.pdf"])
    def test_the_hash_follows_the_new_file(self, admin_client, evidence, second_name):
        _upload(admin_client, evidence, "first.pdf", b"%PDF-1.4 first")
        _upload(admin_client, evidence, second_name, b"%PDF-1.4 second")

        revision = _stored(evidence)
        assert (
            revision.attachment_hash == hashlib.sha256(b"%PDF-1.4 second").hexdigest()
        )

    def test_a_rejected_upload_leaves_the_existing_file_untouched(
        self, admin_client, evidence
    ):
        _upload(admin_client, evidence, "first.pdf", b"%PDF-1.4 first")
        kept_name = _stored(evidence).attachment.name

        response = admin_client.post(
            f"/api/evidences/{evidence.id}/upload/",
            data=b"MZ payload",
            content_type="application/octet-stream",
            HTTP_CONTENT_DISPOSITION='attachment; filename="payload.exe"',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        revision = _stored(evidence)
        assert revision.attachment.name == kept_name
        assert revision.attachment.read() == b"%PDF-1.4 first"
