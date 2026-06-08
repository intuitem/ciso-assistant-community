from uuid import uuid4

from auditlog import middleware
from auditlog.cid import correlation_id, set_cid
from auditlog.context import set_extra_data
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

    def __call__(self, request):
        # set_cid honors an x-correlation-id header and resets the ContextVar per
        # request; mint one when absent so all audit entries in a request share a cid.
        set_cid(request)
        if correlation_id.get() is None:
            correlation_id.set(str(uuid4()))

        with set_extra_data(context_data=self.get_extra_data(request)):
            return self.get_response(request)


# Add a post-save signal to add the additional info after the log entry is saved
# Think about the potential perf overhead of this
@receiver(post_save, sender=LogEntry)
def add_user_info_to_log_entry(sender, instance, created, **kwargs):
    if not created or not instance.actor_id:
        return

    obj = None
    model_class = instance.content_type.model_class()
    if model_class is not None:
        try:
            obj = model_class.objects.get(pk=instance.object_pk)
        except model_class.DoesNotExist:
            logger.debug("audit log enrichment failed: no model_class.")
            pass

    # Only update if this is a new log entry and it has an actor
    try:
        user_uuid = str(instance.actor_id)
        user_email = instance.actor.email
        folder = (
            "/".join([f.name for f in obj.get_folder_full_path()])
            if obj and hasattr(obj, "get_folder_full_path")
            else None
        )

        LogEntry.objects.filter(pk=instance.pk).update(
            additional_data={
                "user_uuid": user_uuid,
                "user_email": user_email,
                "folder": folder,
            }
        )
    except Exception:
        # Fail silently if there's any issue
        logger.debug("audit log enrichment with actor failed.")
        pass
