from auditlog import middleware
from django.utils.functional import SimpleLazyObject
from auditlog.models import LogEntry
from django.db.models.signals import post_save
from django.dispatch import receiver

import structlog

logger = structlog.getLogger(__name__)


# Fix the actor resolution with the custom middleware
# Based on https://stackoverflow.com/questions/40740061/auditlog-with-django-and-drf
class AuditlogMiddleware(middleware.AuditlogMiddleware):
    @staticmethod
    def _get_actor(request):
        return SimpleLazyObject(
            lambda: middleware.AuditlogMiddleware._get_actor(request)
        )


# Add a post-save signal to add the additional info after the log entry is saved
# Think about the potential perf overhead of this
@receiver(post_save, sender=LogEntry)
def add_user_info_to_log_entry(sender, instance, created, **kwargs):
    if created and instance.actor:
        # Only update if this is a new log entry and it has an actor
        try:
            user_uuid = str(instance.actor.id)
            user_email = instance.actor.email

            LogEntry.objects.filter(pk=instance.pk).update(
                additional_data={"user_uuid": user_uuid, "user_email": user_email}
            )
        except Exception:
            # Fail silently if there's any issue
            logger.debug("audit log enrichment with actor failed.")
            pass
