from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
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


def _scope_with(role, folder):
    from chat.scoping import ReadScope
    from iam.models import RoleAssignment, User, UserGroup

    user = User.objects.create(email=f"{role.name}@test.local")
    group = UserGroup.objects.create(folder=folder, name=f"{role.name}-group")
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=role,
        folder=Folder.get_root_folder(),
        is_recursive=True,
    )
    assignment.perimeter_folders.add(folder)
    group.user_set.add(user)
    return ReadScope(user)


def _other_domain():
    return Folder.objects.create(
        name="Other",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


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


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.catch_up_indexing")
def test_turning_chat_mode_on_triggers_catch_up(catch_up, evidence):
    from django.db.models.signals import post_save, pre_save

    from chat.signals import _catch_up_when_chat_turned_on, _remember_chat_mode
    from global_settings.models import GlobalSettings

    receivers = [
        (pre_save, _remember_chat_mode),
        (post_save, _catch_up_when_chat_turned_on),
    ]
    already = [sig.disconnect(fn, sender=GlobalSettings) for sig, fn in receivers]
    for sig, fn in receivers:
        sig.connect(fn, sender=GlobalSettings, weak=False)
    try:
        flags = GlobalSettings.objects.get(name=GlobalSettings.Names.FEATURE_FLAGS)
        for chat_mode in (False, True, True):
            flags.value = {**flags.value, "chat_mode": chat_mode}
            flags.save()
        assert catch_up.call_count == 1
    finally:
        for (sig, fn), was in zip(receivers, already):
            if not was:
                sig.disconnect(fn, sender=GlobalSettings)


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.remove_document_chunks")
@patch("chat.tasks.ingest_document")
def test_cleared_or_failed_attachments_are_reconciled(ingest, remove, evidence):
    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "policy.txt")
    index_evidence_revision(revision)
    failed = IndexedDocument.objects.get()
    failed.status = IndexedDocument.Status.FAILED
    failed.save()

    index_evidence_revision(revision)
    retried = IndexedDocument.objects.get()
    assert retried.id == failed.id and ingest.call_count == 2
    assert retried.status == IndexedDocument.Status.PENDING
    remove.assert_not_called()

    revision.attachment = None
    revision.save()
    index_evidence_revision(revision)
    assert not IndexedDocument.objects.exists()
    assert remove.call_count == 1


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.move_document_chunks")
@patch("chat.tasks.ingest_document")
def test_moved_evidence_moves_its_chunks(ingest, move, evidence):
    from chat.signals import _follow_folder

    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "policy.txt")
    index_evidence_revision(revision)
    doc = IndexedDocument.objects.get()

    other = Folder.objects.create(
        name="Other",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    evidence.folder = other
    evidence.save()
    _follow_folder(evidence, EvidenceRevision.objects.filter(evidence=evidence))

    doc.refresh_from_db()
    assert doc.folder_id == other.id
    move.assert_called_once_with([str(doc.id)], str(other.id))


@pytest.mark.django_db
def test_chunks_need_read_access_to_their_source(evidence):
    from django.contrib.auth.models import Permission

    from chat.rag import _readable_document_ids
    from iam.models import Role

    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "policy.pdf")
    doc = IndexedDocument.objects.create(
        folder=evidence.folder,
        file=revision.attachment.name,
        filename="policy.pdf",
        content_type="application/pdf",
        source_type=IndexedDocument.SourceType.EVIDENCE,
        source_content_type=ContentType.objects.get_for_model(EvidenceRevision),
        source_object_id=revision.id,
    )

    def user_with(role):
        return _scope_with(role, evidence.folder)

    chunks_only = Role.objects.create(
        name="chunks-only", folder=Folder.get_root_folder()
    )
    chunks_only.permissions.set(
        Permission.objects.filter(codename__in=["view_folder", "view_indexeddocument"])
    )
    orphan = IndexedDocument.objects.create(
        folder=evidence.folder,
        file="orphan.pdf",
        filename="orphan.pdf",
        content_type="application/pdf",
        source_type=IndexedDocument.SourceType.EVIDENCE,
    )
    folders = [str(evidence.folder_id)]
    assert _readable_document_ids(user_with(chunks_only), folders) == []
    auditor = user_with(Role.objects.get(name="BI-RL-AUD"))
    assert _readable_document_ids(auditor, folders) == [str(doc.id)]
    assert str(orphan.id) not in _readable_document_ids(auditor, folders)


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.ingest_document")
def test_catch_up_resubmits_stuck_pending_documents(ingest, evidence):
    from datetime import timedelta

    from django.utils import timezone

    from chat.signals import index_missing_documents

    stuck = IndexedDocument.objects.create(
        folder=evidence.folder,
        file="chat.txt",
        filename="chat.txt",
        content_type="text/plain",
        source_type=IndexedDocument.SourceType.CHAT,
    )
    fresh = IndexedDocument.objects.create(
        folder=evidence.folder,
        file="fresh.txt",
        filename="fresh.txt",
        content_type="text/plain",
        source_type=IndexedDocument.SourceType.CHAT,
    )
    IndexedDocument.objects.filter(id=stuck.id).update(
        updated_at=timezone.now() - timedelta(hours=2)
    )
    index_missing_documents()
    ingest.assert_called_once_with(str(stuck.id))
    assert fresh.status == IndexedDocument.Status.PENDING


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.ingest_document")
def test_long_attachment_names_are_indexed(ingest, evidence):
    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "a" * 150 + ".txt")
    index_evidence_revision(revision)

    doc = IndexedDocument.objects.get()
    assert doc.file.name == revision.attachment.name
    assert len(doc.file.name) > 100


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.ingest_document")
def test_indexing_failure_does_not_fail_the_save(ingest, evidence):
    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "policy.txt")
    with patch.object(IndexedDocument, "save", side_effect=RuntimeError("down")):
        index_evidence_revision(revision)

    assert not IndexedDocument.objects.exists()
    ingest.assert_not_called()


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.remove_document_chunks")
@patch("chat.tasks.ingest_document")
def test_chunks_are_checked_against_the_live_source(ingest, remove, evidence, document):
    """What the index copied may have gone stale: the source decides, as it is now."""
    import uuid

    from chat.rag import _readable_document_ids
    from chat.scoping import ReadScope
    from doc_management.models import DocumentRevision
    from iam.models import Role

    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "policy.txt")
    index_evidence_revision(revision)
    published = document.revisions.first()
    published.publish()
    index_document_revision(published)
    from_evidence = IndexedDocument.objects.get(
        source_type=IndexedDocument.SourceType.EVIDENCE
    )
    from_document = IndexedDocument.objects.get(
        source_type=IndexedDocument.SourceType.DOCUMENT
    )

    user = _scope_with(Role.objects.get(name="BI-RL-AUD"), evidence.folder).user
    folders = [str(evidence.folder_id)]

    def readable():
        return set(_readable_document_ids(ReadScope(user), folders))

    both = {str(from_evidence.id), str(from_document.id)}
    assert readable() == both

    # None of these writes fires a signal, so the index does not follow.
    this_revision = EvidenceRevision.objects.filter(pk=revision.pk)
    this_revision.update(attachment="replaced.txt")
    assert readable() == {str(from_document.id)}
    this_revision.update(attachment=from_evidence.file.name)

    this_revision.update(folder=_other_domain())
    assert readable() == {str(from_document.id)}
    this_revision.update(folder=evidence.folder)
    assert readable() == both

    DocumentRevision.objects.filter(pk=published.pk).update(
        status=DocumentRevision.Status.DEPRECATED
    )
    assert readable() == {str(from_evidence.id)}

    IndexedDocument.objects.filter(pk=from_evidence.pk).update(
        source_object_id=uuid.uuid4()
    )
    assert readable() == set()


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.move_document_chunks")
@patch("chat.tasks.remove_document_chunks")
@patch("chat.tasks.ingest_document")
def test_catch_up_realigns_folders_and_drops_orphans(ingest, remove, move, evidence):
    import uuid

    from chat.signals import index_missing_documents

    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "policy.txt")
    index_evidence_revision(revision)
    doc = IndexedDocument.objects.get()

    IndexedDocument.objects.filter(pk=doc.pk).update(folder=_other_domain())
    index_missing_documents()
    doc.refresh_from_db()
    assert doc.folder_id == evidence.folder_id
    move.assert_called_once_with([str(doc.id)], str(evidence.folder_id))

    # Their evidence is gone, and no signal said so.
    IndexedDocument.objects.filter(pk=doc.pk).update(source_object_id=uuid.uuid4())
    unsourced = IndexedDocument.objects.create(
        folder=evidence.folder,
        file="orphan.txt",
        filename="orphan.txt",
        content_type="text/plain",
        source_type=IndexedDocument.SourceType.EVIDENCE,
    )
    chat_upload = IndexedDocument.objects.create(
        folder=evidence.folder,
        file="chat.txt",
        filename="chat.txt",
        content_type="text/plain",
        source_type=IndexedDocument.SourceType.CHAT,
    )
    index_missing_documents()

    left = set(IndexedDocument.objects.values_list("id", flat=True))
    assert chat_upload.id in left and not {doc.id, unsourced.id} & left
    assert {call.args[0] for call in remove.call_args_list} == {
        str(doc.id),
        str(unsourced.id),
    }
    # The attachment itself is still there, so it is indexed afresh.
    assert IndexedDocument.objects.get(source_object_id=revision.id).id != doc.id


@pytest.mark.django_db(transaction=True)
@patch("chat.tasks.remove_document_chunks")
@patch("chat.tasks.ingest_document")
def test_saves_while_chat_is_off_drop_the_indexed_copy(ingest, remove, evidence):
    from chat.signals import _sync_source

    revision = EvidenceRevision.objects.create(evidence=evidence)
    _attach(revision, "policy.txt")
    _sync_source(revision, index_evidence_revision, True)
    doc = IndexedDocument.objects.get()

    _sync_source(revision, index_evidence_revision, False)
    assert not IndexedDocument.objects.exists()
    remove.assert_called_once_with(str(doc.id))
    assert revision.attachment.storage.exists(revision.attachment.name)


@pytest.mark.django_db
def test_api_clients_cannot_claim_a_source(evidence, document):
    """A forged link to a published revision would pass its content off as the document."""
    from chat.serializers import IndexedDocumentWriteSerializer
    from doc_management.models import DocumentRevision

    serializer = IndexedDocumentWriteSerializer(
        data={
            "folder": str(evidence.folder_id),
            "file": SimpleUploadedFile("forged.txt", b"not the policy"),
            "filename": "AI policy v1",
            "content_type": "text/plain",
            "source_type": IndexedDocument.SourceType.DOCUMENT,
            "source_content_type": ContentType.objects.get_for_model(
                DocumentRevision
            ).id,
            "source_object_id": str(document.revisions.first().id),
        },
        context={},
    )
    serializer.is_valid(raise_exception=True)
    doc = serializer.save()

    assert doc.source_type == IndexedDocument.SourceType.CUSTOM
    assert doc.source_content_type is None and doc.source_object_id is None
