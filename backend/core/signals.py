from django.dispatch import receiver
from django.db.models.signals import pre_delete
from structlog import get_logger

from core.models import EvidenceRevision

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
                evidence_name=instance.evidence.name,
                error=str(e),
            )
