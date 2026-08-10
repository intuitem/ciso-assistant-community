from uuid import uuid4

from auditlog import middleware
from auditlog.cid import correlation_id, set_cid
from auditlog.context import set_extra_data
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

    def __call__(self, request):
        # Reimplements the parent __call__ (cannot super(): it calls set_cid then
        # get_response in one go, leaving no seam to mint a cid between them).
        # set_cid honors an x-correlation-id header and resets the ContextVar per
        # request; mint one when absent so all audit entries in a request share a cid.
        set_cid(request)
        if correlation_id.get() is None:
            correlation_id.set(str(uuid4()))

        with set_extra_data(context_data=self.get_extra_data(request)):
            return self.get_response(request)
