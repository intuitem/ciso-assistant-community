"""
Django signals to trigger incremental re-indexing of model objects
when they are created, updated, or deleted.
"""

import structlog

from django.db.models.signals import post_save, post_delete
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

    from global_settings.utils import ff_is_enabled

    for model_class in _get_model_classes():

        @receiver(post_save, sender=model_class, weak=False)
        def on_save(sender, instance, **kwargs):
            if not ff_is_enabled("chat_mode"):
                return
            from .tasks import index_model_object

            index_model_object(
                sender._meta.app_label,
                sender.__name__,
                str(instance.id),
            )

        @receiver(post_delete, sender=model_class, weak=False)
        def on_delete(sender, instance, **kwargs):
            if not ff_is_enabled("chat_mode"):
                return
            from .tasks import remove_model_object

            remove_model_object(
                sender._meta.app_label,
                sender.__name__,
                str(instance.id),
            )

    # Auto-ingest evidence attachments when a new revision is uploaded
    _connect_evidence_signal(ff_is_enabled)


def _connect_evidence_signal(ff_is_enabled):
    """Connect signal to auto-ingest evidence file attachments."""
    from django.apps import apps

    try:
        EvidenceRevision = apps.get_model("core", "EvidenceRevision")
    except LookupError:
        logger.warning(
            "EvidenceRevision model not found, skipping evidence auto-ingest signal"
        )
        return

    @receiver(post_save, sender=EvidenceRevision, weak=False)
    def on_evidence_revision_save(sender, instance, created, **kwargs):
        if not created or not ff_is_enabled("chat_mode"):
            return
        if not instance.attachment:
            return

        from django.contrib.contenttypes.models import ContentType

        from .models import IndexedDocument
        from .tasks import ingest_document

        # Determine content type from file name
        import mimetypes

        mime_type, _ = mimetypes.guess_type(instance.attachment.name)
        if not mime_type:
            return

        # Only ingest supported file types
        from .extractors import get_extractor

        if not get_extractor(mime_type):
            return

        # Avoid duplicate indexing for same attachment
        ct = ContentType.objects.get_for_model(EvidenceRevision)
        if IndexedDocument.objects.filter(
            source_content_type=ct,
            source_object_id=instance.id,
        ).exists():
            return

        doc = IndexedDocument.objects.create(
            folder=instance.folder,
            file=instance.attachment,
            filename=instance.attachment.name.split("/")[-1],
            content_type=mime_type,
            source_type=IndexedDocument.SourceType.EVIDENCE,
            source_content_type=ct,
            source_object_id=instance.id,
        )
        ingest_document(str(doc.id))
        logger.info("Auto-queued evidence attachment for indexing: %s", doc.filename)


# Do NOT call connect_signals() at module level.
# It is called from ChatConfig.ready() in apps.py, which ensures
# all models are fully loaded before we try to resolve them.
