from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from chat.models import IndexedDocument
from chat.signals import index_document_revision, index_evidence_revision
from core.apps import startup
from core.models import Evidence, EvidenceRevision
from iam.models import Folder


@pytest.fixture
def evidence(db):
    startup(sender=None)
    domain = Folder.objects.create(
        name="Dom",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    return Evidence.objects.create(name="AI policy", folder=domain)


def _attach(revision, name):
    revision.set_new_attachment(
        SimpleUploadedFile(name, b"policy text", content_type="text/plain")
    )
    revision.save()


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.remove_document_chunks")
@patch("chat.tasks.ingest_document")
def test_attachment_added_after_creation_is_indexed_once(ingest, remove, evidence):
    revision = EvidenceRevision.objects.create(evidence=evidence)
    index_evidence_revision(revision)
    assert not IndexedDocument.objects.exists()

    _attach(revision, "policy.txt")
    index_evidence_revision(revision)
    index_evidence_revision(revision)

    doc = IndexedDocument.objects.get()
    assert doc.source_type == IndexedDocument.SourceType.EVIDENCE
    assert doc.source_object_id == revision.id
    assert doc.filename == "policy.txt"
    ingest.assert_called_once_with(str(doc.id))
    remove.assert_not_called()


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.remove_document_chunks")
@patch("chat.tasks.ingest_document")
def test_replaced_attachment_is_reindexed(ingest, remove, evidence):
    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "v1.txt")
    index_evidence_revision(revision)
    old = IndexedDocument.objects.get()

    _attach(revision, "v2.txt")
    index_evidence_revision(revision)

    new = IndexedDocument.objects.get()
    assert new.id != old.id and new.filename == "v2.txt"
    remove.assert_called_once_with(str(old.id))
    assert ingest.call_count == 2


@pytest.fixture
def document(evidence):
    from doc_management.serializers import ManagedDocumentWriteSerializer

    s = ManagedDocumentWriteSerializer(
        data={"folder": str(evidence.folder_id), "locale": "en", "name": "AI policy"},
        context={},
    )
    s.is_valid(raise_exception=True)
    doc = s.save()
    revision = doc.revisions.first()
    revision.content = "## Responsibilities\n\nThe CISO owns AI risk."
    revision.save()
    return doc


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.remove_document_chunks")
@patch("chat.tasks.ingest_document")
def test_only_the_published_document_revision_is_indexed(ingest, remove, document):
    from doc_management.models import DocumentRevision

    v1 = document.revisions.first()
    index_document_revision(v1)
    assert not IndexedDocument.objects.exists()

    v1.publish()
    index_document_revision(v1)
    index_document_revision(v1)
    doc_v1 = IndexedDocument.objects.get()
    assert doc_v1.source_type == IndexedDocument.SourceType.DOCUMENT
    assert doc_v1.filename == "AI policy v1"
    doc_v1.file.open()
    assert b"The CISO owns AI risk." in doc_v1.file.read()
    doc_v1.file.close()
    ingest.assert_called_once_with(str(doc_v1.id))

    v2 = DocumentRevision.objects.create(
        document=document, version_number=2, content="The DPO owns AI risk."
    )
    index_document_revision(v2)
    assert IndexedDocument.objects.get().id == doc_v1.id

    v2.publish()
    index_document_revision(v2)
    doc_v2 = IndexedDocument.objects.get()
    assert doc_v2.filename == "AI policy v2"
    remove.assert_called_once_with(str(doc_v1.id))
    assert not doc_v1.file.storage.exists(doc_v1.file.name)

    v2.status = DocumentRevision.Status.DEPRECATED
    v2.save()
    index_document_revision(v2)
    assert not IndexedDocument.objects.exists()


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.remove_document_chunks")
@patch("chat.tasks.ingest_document")
def test_nightly_catch_up_indexes_what_signals_missed(
    ingest, remove, evidence, document
):
    from chat.signals import index_missing_documents

    document.revisions.first().publish()
    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "policy.txt")

    assert index_missing_documents() == (1, 1)
    assert set(IndexedDocument.objects.values_list("source_type", flat=True)) == {
        IndexedDocument.SourceType.EVIDENCE,
        IndexedDocument.SourceType.DOCUMENT,
    }
    index_missing_documents()
    assert IndexedDocument.objects.count() == 2 and ingest.call_count == 2
