"""Published-only read access through the baseline reader role: anyone with a
role somewhere reads the revision in force of Global documents, never drafts;
domain documents stay behind the domain's own roles."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.startup import startup
from doc_management.models import DocumentAttachment, DocumentRevision, ManagedDocument
from doc_management.serializers import ManagedDocumentWriteSerializer
from iam.models import Folder, User, UserGroup, UserGroupCodename


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _domain(name):
    folder = Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(folder)
    return folder


def _member(email, folder, codename):
    user = User.objects.create_user(email)
    UserGroup.objects.get(name=str(codename), folder=folder).user_set.add(user)
    return _client(user)


def _document(folder, name, *, published=True, draft=False):
    s = ManagedDocumentWriteSerializer(
        data={"folder": str(folder.id), "locale": "en", "name": name}, context={}
    )
    s.is_valid(raise_exception=True)
    doc = s.save()
    first = doc.revisions.first()
    first.content = f"{name} in force"
    first.save()
    if published:
        first.publish()
    if draft:
        DocumentRevision.objects.create(
            document=doc, version_number=2, content=f"{name} secret draft"
        )
    doc.refresh_from_db()
    return doc


@pytest.fixture
def setup(db):
    startup(sender=None)
    root = Folder.get_root_folder()
    hr, sales = _domain("HR"), _domain("Sales")
    return {
        "root": root,
        "hr": hr,
        # An auditee somewhere: no document permission of their own, so
        # Global documents reach them only through the baseline reader role.
        "employee": _member("employee@docs.test", sales, UserGroupCodename.AUDITEE),
        "hr_reader": _member("reader@docs.test", hr, UserGroupCodename.READER),
        "charter": _document(root, "Charter", draft=True),
        "unpublished": _document(root, "Unpublished", published=False),
        "hr_policy": _document(hr, "HR policy"),
    }


def _ids(resp):
    assert resp.status_code == 200, resp.content
    body = resp.json()
    rows = body["results"] if isinstance(body, dict) else body
    return {row["id"] for row in rows}


@pytest.mark.django_db
class TestPublishedOnlyReader:
    def test_catalog_lists_published_global_documents_only(self, setup):
        ids = _ids(setup["employee"].get("/api/document-containers/catalog/"))
        assert ids == {str(setup["charter"].container_id)}

    def test_container_list_and_detail_hide_work_in_progress(self, setup):
        client, container_id = setup["employee"], setup["charter"].container_id
        assert _ids(client.get("/api/document-containers/")) == {str(container_id)}
        resp = client.get(f"/api/document-containers/{container_id}/")
        assert resp.status_code == 200
        assert resp.json()["pending_revision"] is None

    def test_reads_the_revision_in_force(self, setup):
        client, doc = setup["employee"], setup["charter"]
        docs = client.get(f"/api/managed-documents/?container={doc.container_id}")
        assert _ids(docs) == {str(doc.id)}
        row = docs.json()["results"][0]
        assert row["latest_draft"] is None
        # The read page follows this link; a masked relation reads as "no published version".
        assert row["current_revision"]["id"] == str(doc.current_revision_id)
        rev = client.get(f"/api/document-revisions/{doc.current_revision_id}/")
        assert rev.status_code == 200
        assert rev.json()["content"] == "Charter in force"

    def test_drafts_history_and_diffs_are_out_of_reach(self, setup):
        client, doc = setup["employee"], setup["charter"]
        draft = doc.revisions.get(status=DocumentRevision.Status.DRAFT)
        published = doc.current_revision_id
        revisions = client.get(f"/api/document-revisions/?document={doc.id}")
        assert _ids(revisions) == {str(published)}
        base = "/api/document-revisions"
        assert client.get(f"{base}/{draft.id}/").status_code == 404
        assert client.get(f"{base}/{draft.id}/file/").status_code == 403
        assert client.get(f"{base}/{draft.id}/export-pdf/").status_code == 404
        assert client.get(f"{base}/{published}/diff/{draft.id}/").status_code == 403
        assert client.get(f"{base}/{published}/edit-history/").status_code == 403

    def test_counts_do_not_reveal_drafts(self, setup):
        client, doc = setup["employee"], setup["charter"]
        container = client.get(f"/api/document-containers/{doc.container_id}/").json()
        assert container["document_count"] is None
        docs = client.get(f"/api/managed-documents/?container={doc.container_id}")
        assert docs.json()["results"][0]["revision_count"] is None

    def test_images_uploaded_for_a_later_draft_stay_hidden(self, setup):
        client, doc = setup["employee"], setup["charter"]
        img = DocumentAttachment.objects.create(
            document=doc, file=SimpleUploadedFile("draft.png", b"\x89PNG\r\n")
        )
        resp = client.get(f"/api/document-attachments/{img.id}/file/")
        assert resp.status_code == 403

    def test_draft_default_locale_reports_no_status(self, setup):
        # Readable through its published FR locale while the EN default is a draft.
        en = _document(setup["root"], "Bilingual", published=False)
        fr = ManagedDocument.objects.create(
            container=en.container, locale="fr", default_locale=False, name="Bilingue"
        )
        DocumentRevision.objects.create(document=fr, content="fr").publish()
        resp = setup["employee"].get(f"/api/document-containers/{en.container_id}/")
        assert resp.status_code == 200
        assert (resp.json()["status"], resp.json()["progress"]) == (None, None)

    def test_cannot_change_a_published_document(self, setup):
        client, container_id = setup["employee"], setup["charter"].container_id
        resp = client.patch(
            f"/api/document-containers/{container_id}/", {"name": "x"}, format="json"
        )
        assert resp.status_code in (403, 404)

    def test_domain_documents_stay_behind_domain_roles(self, setup):
        container_id = setup["hr_policy"].container_id
        resp = setup["employee"].get(f"/api/document-containers/{container_id}/")
        assert resp.status_code == 404
        ids = _ids(setup["hr_reader"].get("/api/document-containers/catalog/"))
        assert str(container_id) in ids


@pytest.mark.django_db
class TestFullViewUnchanged:
    def test_domain_reader_still_sees_drafts(self, setup):
        doc = _document(setup["hr"], "HR draft", draft=True)
        client = setup["hr_reader"]
        assert _ids(client.get(f"/api/document-revisions/?document={doc.id}")) == {
            str(r.id) for r in doc.revisions.all()
        }
        resp = client.get(f"/api/document-containers/{doc.container_id}/")
        assert resp.json()["pending_revision"]["status"] == "draft"
