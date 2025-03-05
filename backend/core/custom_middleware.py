from auditlog import middleware
from django.utils.functional import SimpleLazyObject

# based on the trick here: https://stackoverflow.com/questions/40740061/auditlog-with-django-and-drf


class AuditlogMiddleware(middleware.AuditlogMiddleware):
    @staticmethod
    def _get_actor(request):
        return SimpleLazyObject(
            lambda: middleware.AuditlogMiddleware._get_actor(request)
        )
