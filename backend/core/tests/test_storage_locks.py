import pytest
from django.core.files.base import ContentFile

from core.storage_locks import _lock_key, lock_stored_name


class _Cursor:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.sink.append((sql, params))

    def fetchone(self):
        return (None,)


class _Connection:
    def __init__(self, vendor, sink):
        self.vendor = vendor
        self.in_atomic_block = True
        self.sink = sink

    def cursor(self):
        return _Cursor(self.sink)


def test_postgres_lock_uses_a_stable_advisory_key(monkeypatch):
    sink = []
    monkeypatch.setattr(
        "core.storage_locks.connection", _Connection("postgresql", sink)
    )
    lock_stored_name("answer_attachments/note.txt")
    sql, params = sink[0]
    assert "pg_advisory_xact_lock" in sql
    assert params == [_lock_key("answer_attachments/note.txt")]
    assert params[0] == _lock_key("answer_attachments/note.txt")
    assert params[0] != _lock_key("answer_attachments/other.txt")
    assert -(2**63) <= params[0] < 2**63


def test_sqlite_lock_does_not_touch_the_database(monkeypatch):
    sink = []
    monkeypatch.setattr("core.storage_locks.connection", _Connection("sqlite", sink))
    lock_stored_name("answer_attachments/note.txt")
    assert sink == []


@pytest.mark.django_db
def test_name_reusers_take_the_stored_name_lock(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    seen = []
    monkeypatch.setattr(
        "core.storage_locks.lock_stored_name", lambda name: seen.append(name)
    )

    from core.answer_attachments import promote_to_evidence
    from core.tests.test_stored_file_cleanup import _answer_attachment
    from iam.models import User

    attachment, _answer, stored = _answer_attachment()
    promote_to_evidence(attachment, User.objects.create_user(email="lock@example.com"))
    assert stored[0][1] in seen

    from doc_management.demo_builders import ATTACHMENT_NAME, DocumentsBuilder
    from doc_management.models import DocumentContainer, ManagedDocument
    from iam.models import Folder

    if Folder.get_root_folder() is None:
        Folder._init_root_folder()
    folder = Folder.objects.create(
        name="Locks",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    container = DocumentContainer.objects.create(name="Policy", folder=folder)
    document = ManagedDocument.objects.create(
        name="Policy", container=container, folder=folder
    )
    seen.clear()
    DocumentsBuilder().attach(document)
    assert seen == [ATTACHMENT_NAME]

    from chat.signals import _queue
    from core.models import Evidence

    evidence = Evidence.objects.create(name="Policy", folder=folder)
    seen.clear()
    _queue(
        evidence,
        "evidence",
        "answer_attachments/note.txt",
        "note.txt",
        "text/plain",
    )
    assert seen == ["answer_attachments/note.txt"]

    seen.clear()
    _queue(
        evidence,
        "document",
        ContentFile(b"authored", name="copy.txt"),
        "copy.txt",
        "text/plain",
    )
    assert seen == []


@pytest.mark.django_db
def test_queue_skips_a_name_cleanup_already_removed(
    settings, tmp_path, django_capture_on_commit_callbacks
):
    settings.MEDIA_ROOT = str(tmp_path)
    from chat.models import IndexedDocument
    from chat.signals import _queue

    from core.tests.test_stored_file_cleanup import _evidence_revision

    revision, _evidence, stored = _evidence_revision()
    storage, name = stored[0]
    stale = type(revision)._base_manager.get(pk=revision.pk)
    with django_capture_on_commit_callbacks(execute=True):
        revision.delete()
    assert not storage.exists(name)

    _queue(stale, "evidence", name, "policy.pdf", "application/pdf")
    assert not IndexedDocument.objects.filter(file=name).exists()
