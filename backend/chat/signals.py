"""
Django signals to trigger incremental re-indexing of model objects
when they are created, updated, or deleted.
"""

import structlog

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

logger = structlog.get_logger(__name__)

# Models to index for RAG
INDEXED_MODELS = [
    "core.AppliedControl",
    "core.RiskScenario",
    "core.Asset",
    "core.Threat",
    "core.ComplianceAssessment",
    "core.RiskAssessment",
    "core.RequirementAssessment",
]


def _get_model_classes():
    """Lazily resolve model classes from strings."""
    from django.apps import apps

    classes = []
    for model_path in INDEXED_MODELS:
        app_label, model_name = model_path.split(".")
        try:
            classes.append(apps.get_model(app_label, model_name))
        except LookupError:
            logger.warning("Model %s not found, skipping RAG indexing", model_path)
    return classes


_connected = False


def connect_signals():
    """Connect post_save and post_delete signals for indexed models."""
    global _connected
    if _connected:
        return
    _connected = True

    from django.conf import settings as django_settings

    if not getattr(django_settings, "ENABLE_CHAT", False):
        return

    from global_settings.utils import ff_is_enabled

    for model_class in _get_model_classes():

        @receiver(post_save, sender=model_class, weak=False)
        def on_save(sender, instance, **kwargs):
            if not ff_is_enabled("chat_mode"):
                return
            from django.db import transaction
            from .tasks import index_model_object

            app = sender._meta.app_label
            name = sender.__name__
            obj_id = str(instance.id)
            transaction.on_commit(lambda: index_model_object(app, name, obj_id))

        @receiver(post_delete, sender=model_class, weak=False)
        def on_delete(sender, instance, **kwargs):
            if not ff_is_enabled("chat_mode"):
                return
            from django.db import transaction
            from .tasks import remove_model_object

            app = sender._meta.app_label
            name = sender.__name__
            obj_id = str(instance.id)
            transaction.on_commit(lambda: remove_model_object(app, name, obj_id))

    _connect_source_signals(ff_is_enabled)

    from global_settings.models import GlobalSettings

    pre_save.connect(_remember_chat_mode, sender=GlobalSettings, weak=False)
    post_save.connect(_catch_up_when_chat_turned_on, sender=GlobalSettings, weak=False)


def _chat_mode(value):
    return isinstance(value, dict) and bool(value.get("chat_mode"))


def _remember_chat_mode(sender, instance, **kwargs):
    if instance.name != sender.Names.FEATURE_FLAGS:
        return
    previous = sender.objects.filter(pk=instance.pk).values_list("value", flat=True)
    instance._chat_mode_was_on = _chat_mode(previous.first())


def _catch_up_when_chat_turned_on(sender, instance, **kwargs):
    if instance.name != sender.Names.FEATURE_FLAGS or not _chat_mode(instance.value):
        return
    if getattr(instance, "_chat_mode_was_on", False):
        return
    from django.db import transaction

    from .tasks import catch_up_indexing

    transaction.on_commit(catch_up_indexing, robust=True)


def _connect_source_signals(ff_is_enabled):
    """Keep the index in step with evidence attachments and published documents."""
    from django.apps import apps

    for model_path, index in (
        ("core.EvidenceRevision", index_evidence_revision),
        ("doc_management.DocumentRevision", index_document_revision),
    ):
        try:
            model_class = apps.get_model(model_path)
        except LookupError:
            logger.warning("%s not found, skipping document indexing", model_path)
            continue

        @receiver(post_save, sender=model_class, weak=False)
        def on_source_save(sender, instance, index=index, **kwargs):
            _sync_source(instance, index, ff_is_enabled("chat_mode"))

        @receiver(post_delete, sender=model_class, weak=False)
        def on_source_delete(sender, instance, **kwargs):
            _drop_indexed(_indexed_for(instance))

    for parent_path, source_path, lookup in (
        ("core.Evidence", "core.EvidenceRevision", "evidence"),
        (
            "doc_management.DocumentContainer",
            "doc_management.DocumentRevision",
            "document__container",
        ),
    ):
        try:
            parent, source = apps.get_model(parent_path), apps.get_model(source_path)
        except LookupError:
            continue

        @receiver(post_save, sender=parent, weak=False)
        def on_parent_save(sender, instance, source=source, lookup=lookup, **kwargs):
            _follow_folder(instance, source.objects.filter(**{lookup: instance}))


def _sync_source(source, index, chat_enabled):
    if chat_enabled:
        index(source)
    else:
        # Nothing is indexed while chat is off, but a copy this save may have
        # made stale must not outlive it; the catch-up re-indexes.
        _drop_indexed(_indexed_for(source))


def _follow_folder(parent, revisions):
    from django.contrib.contenttypes.models import ContentType
    from django.db import transaction

    from .models import IndexedDocument
    from .tasks import move_document_chunks

    stale = IndexedDocument.objects.filter(
        source_content_type=ContentType.objects.get_for_model(revisions.model),
        source_object_id__in=revisions.values("id"),
    ).exclude(folder_id=parent.folder_id)
    doc_ids = [str(i) for i in stale.values_list("id", flat=True)]
    if not doc_ids:
        return
    stale.update(folder_id=parent.folder_id)
    transaction.on_commit(lambda: move_document_chunks(doc_ids))


def _indexed_for(source):
    from django.contrib.contenttypes.models import ContentType

    from .models import IndexedDocument

    return IndexedDocument.objects.filter(
        source_content_type=ContentType.objects.get_for_model(source),
        source_object_id=source.id,
    )


def _drop_indexed(docs):
    from django.db import transaction

    from .models import IndexedDocument
    from .tasks import remove_document_chunks

    owned_prefix = IndexedDocument.file.field.upload_to
    for doc in docs:
        transaction.on_commit(lambda d=str(doc.id): remove_document_chunks(d))
        if doc.file.name.startswith(owned_prefix):
            storage, name = doc.file.storage, doc.file.name
            transaction.on_commit(lambda s=storage, n=name: s.delete(n))
        doc.delete()


def _queue(source, source_type, file, filename, content_type):
    from django.contrib.contenttypes.models import ContentType
    from django.db import transaction

    from .models import IndexedDocument
    from .tasks import ingest_document

    doc = IndexedDocument(
        folder=source.folder,
        file=file,
        filename=filename,
        content_type=content_type,
        source_type=source_type,
        source_content_type=ContentType.objects.get_for_model(source),
        source_object_id=source.id,
    )
    # Indexing must not fail the upload or publication that triggered it: the
    # nightly catch-up queues whatever is missing.
    try:
        with transaction.atomic():
            # A string is an existing stored name (evidence or uploaded revision),
            # not a new copy. Hold it until this index row commits.
            if isinstance(file, str) and file:
                from core.storage_locks import lock_stored_name

                lock_stored_name(file)
            doc.save()
    except Exception:
        logger.exception(
            "Failed to queue document for indexing",
            source_object_id=str(source.id),
        )
        # A copy written before the row failed is ours to remove; the source's
        # own file (evidence attachment, uploaded revision) never is.
        if doc.file.name and doc.file.name.startswith(
            IndexedDocument.file.field.upload_to
        ):
            try:
                doc.file.storage.delete(doc.file.name)
            except Exception:
                logger.exception("Failed to remove unindexed copy", file=doc.file.name)
        return
    transaction.on_commit(lambda: ingest_document(str(doc.id)))
    logger.info("Queued document for indexing", filename=filename)


def _refresh(doc, source):
    """Keep an indexed document that still matches its source: follow the source's
    folder, and resubmit a failed one in place rather than re-creating its row and file."""
    from django.db import transaction
    from django.utils import timezone

    from .models import IndexedDocument
    from .tasks import ingest_document, move_document_chunks

    if doc.folder_id != source.folder_id:
        IndexedDocument.objects.filter(pk=doc.pk).update(folder_id=source.folder_id)
        transaction.on_commit(lambda: move_document_chunks([str(doc.id)]))
    if doc.status != IndexedDocument.Status.FAILED:
        return
    IndexedDocument.objects.filter(pk=doc.pk).update(
        status=IndexedDocument.Status.PENDING,
        error_message="",
        updated_at=timezone.now(),
    )
    transaction.on_commit(lambda: ingest_document(str(doc.id)))


def _supported_type(name):
    import mimetypes

    from .extractors import get_extractor

    mime_type, _ = mimetypes.guess_type(name)
    return mime_type if mime_type and get_extractor(mime_type) else None


def index_evidence_revision(revision):
    """Queue a revision's attachment for indexing unless that file is already indexed."""
    from .models import IndexedDocument

    previous = _indexed_for(revision)
    mime_type = revision.attachment and _supported_type(revision.attachment.name)
    if not mime_type:
        _drop_indexed(previous)
        return
    current = previous.filter(file=revision.attachment.name).first()
    if current:
        _drop_indexed(previous.exclude(pk=current.pk))
        _refresh(current, revision)
        return
    _drop_indexed(previous)
    _queue(
        revision,
        IndexedDocument.SourceType.EVIDENCE,
        revision.attachment.name,
        revision.filename(),
        mime_type,
    )


def index_document_revision(revision):
    """Index only the published revision of a managed document, dropping the others."""
    from django.contrib.contenttypes.models import ContentType
    from django.core.files.base import ContentFile

    from .models import IndexedDocument

    siblings = revision.document.revisions.exclude(pk=revision.pk)
    if revision.status != revision.Status.PUBLISHED:
        _drop_indexed(_indexed_for(revision))
        return
    _drop_indexed(
        IndexedDocument.objects.filter(
            source_content_type=ContentType.objects.get_for_model(revision),
            source_object_id__in=siblings.values("id"),
        )
    )
    own = _indexed_for(revision).first()
    if own:
        _refresh(own, revision)
        return

    filename = f"{revision.document.display_name} v{revision.version_number}"
    if revision.source == revision.Source.AUTHORED and revision.content.strip():
        file = ContentFile(
            f"# {filename}\n\n{revision.content}".encode(), name=f"{revision.id}.txt"
        )
        mime_type = "text/plain"
    elif revision.source == revision.Source.UPLOADED and revision.file:
        mime_type = _supported_type(revision.file.name)
        file = revision.file.name
    else:
        mime_type = None
    if not mime_type:
        return
    _queue(revision, IndexedDocument.SourceType.DOCUMENT, file, filename, mime_type)


def index_missing_documents(folder_id=None):
    """Reconcile the index with evidence attachments and published documents."""
    from datetime import timedelta

    from django.contrib.contenttypes.models import ContentType
    from django.utils import timezone
    from django.db.models import Q

    from core.models import EvidenceRevision
    from doc_management.models import DocumentRevision

    from .models import IndexedDocument

    def indexed(model):
        return IndexedDocument.objects.filter(
            source_content_type=ContentType.objects.get_for_model(model)
        ).values("source_object_id")

    evidence = EvidenceRevision.objects.filter(
        ~Q(attachment="") & Q(attachment__isnull=False)
        | Q(id__in=indexed(EvidenceRevision))
    )
    documents = DocumentRevision.objects.filter(
        Q(status=DocumentRevision.Status.PUBLISHED)
        | Q(id__in=indexed(DocumentRevision))
    )
    if folder_id:
        evidence = evidence.filter(folder_id=folder_id)
        documents = documents.filter(folder_id=folder_id)
    # Sources deleted while nothing was listening (chat disabled, older versions)
    # are in neither queryset: their indexed copies would otherwise stay forever.
    for model, source_type in (
        (EvidenceRevision, IndexedDocument.SourceType.EVIDENCE),
        (DocumentRevision, IndexedDocument.SourceType.DOCUMENT),
    ):
        orphans = IndexedDocument.objects.filter(source_type=source_type).exclude(
            source_content_type=ContentType.objects.get_for_model(model),
            source_object_id__in=model.objects.values("id"),
        )
        if folder_id:
            orphans = orphans.filter(folder_id=folder_id)
        _drop_indexed(orphans)
    for revisions, index in (
        (evidence, index_evidence_revision),
        (documents, index_document_revision),
    ):
        # Ids only, each revision read when its turn comes: one loaded ahead may
        # be published, replaced or deleted before it is reached, and reconciling
        # from that copy would index the old state over the new one.
        for pk in revisions.values_list("pk", flat=True).iterator():
            try:
                revision = revisions.model.objects.filter(pk=pk).first()
                if revision is not None:
                    index(revision)
            except Exception as e:
                logger.warning("Failed to index revision", revision_id=pk, error=e)
    from .tasks import INGESTION_LEASE, ingest_document

    now = timezone.now()
    waiting = IndexedDocument.objects.all()
    if folder_id:
        waiting = waiting.filter(folder_id=folder_id)
    # A worker stopped mid-ingestion never releases its claim: once the lease has
    # passed, hand the document back. It is then old enough to be resubmitted below.
    waiting.filter(
        status=IndexedDocument.Status.PROCESSING,
        updated_at__lt=now - INGESTION_LEASE,
    ).update(status=IndexedDocument.Status.PENDING)
    stuck = waiting.filter(
        status=IndexedDocument.Status.PENDING,
        updated_at__lt=now - timedelta(hours=1),
    )
    for doc_id in stuck.values_list("id", flat=True):
        ingest_document(str(doc_id))
    return evidence.count(), documents.count()


# Do NOT call connect_signals() at module level.
# It is called from ChatConfig.ready() in apps.py, which ensures
# all models are fully loaded before we try to resolve them.
