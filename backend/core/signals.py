from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_delete
from structlog import get_logger

from core.models import EvidenceAttachment, EvidenceRevision

logger = get_logger(__name__)


@receiver(pre_delete, sender=EvidenceRevision)
def _delete_evidence_revision_attachment(sender, instance: EvidenceRevision, **kwargs):
    if instance.attachment and instance.attachment.name:
        try:
            instance.attachment.delete(save=False)
        except Exception as e:
            logger.warning(
                "Failed to delete evidence revision attachment",
                revision_id=instance.pk,
                evidence_id=instance.evidence_id,
                error=str(e),
            )


@receiver(post_delete, sender=EvidenceAttachment)
def delete_additional_evidence_attachment(sender, instance, **kwargs):
    from django.db import transaction

    if instance.attachment:
        storage, name = instance.attachment.storage, instance.attachment.name
        transaction.on_commit(lambda: storage.delete(name))
