from auditlog import middleware
from django.utils.functional import SimpleLazyObject


# Fix the actor resolution with the custom middleware
# Based on https://stackoverflow.com/questions/40740061/auditlog-with-django-and-drf
#
# Folder/actor enrichment of LogEntry is no longer done here via a post_save
# signal: folder is captured inline at log creation through
# AbstractBaseModel.get_additional_data(), and actor/actor_email are native
# LogEntry columns. This fixes delete events (instance still in memory) and
# covers m2m changes.
class AuditlogMiddleware(middleware.AuditlogMiddleware):
    @staticmethod
    def _get_actor(request):
        return SimpleLazyObject(
            lambda: middleware.AuditlogMiddleware._get_actor(request)
        )
