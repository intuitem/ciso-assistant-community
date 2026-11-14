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
            if ff_is_enabled("chat_mode"):
                index(instance)

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
    folder_id = str(parent.folder_id)
    transaction.on_commit(lambda: move_document_chunks(doc_ids, folder_id))


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

    doc = IndexedDocument.objects.create(
        folder=source.folder,
        file=file,
        filename=filename,
        content_type=content_type,
        source_type=source_type,
        source_content_type=ContentType.objects.get_for_model(source),
        source_object_id=source.id,
    )
    transaction.on_commit(lambda: ingest_document(str(doc.id)))
    logger.info("Queued document for indexing", filename=filename)


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
    current = previous.filter(file=revision.attachment.name)
    if current.exclude(status=IndexedDocument.Status.FAILED).exists():
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
    own = _indexed_for(revision)
    if own.exclude(status=IndexedDocument.Status.FAILED).exists():
        return
    _drop_indexed(own)

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
    from django.contrib.contenttypes.models import ContentType
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
    for revisions, index in (
        (evidence, index_evidence_revision),
        (documents, index_document_revision),
    ):
        for revision in revisions.iterator():
            try:
                index(revision)
            except Exception as e:
                logger.warning(
                    "Failed to index revision", revision_id=revision.id, error=e
                )
    return evidence.count(), documents.count()


# Do NOT call connect_signals() at module level.
# It is called from ChatConfig.ready() in apps.py, which ensures
# all models are fully loaded before we try to resolve them.
