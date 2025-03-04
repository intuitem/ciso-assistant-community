from threading import local
from django.utils.deprecation import MiddlewareMixin

# Thread local storage
_thread_locals = local()


class UserMiddleware(MiddlewareMixin):
    """Middleware to store the current user in thread local storage."""

    def process_request(self, request):
        _thread_locals.user = getattr(request, "user", None)

    def process_response(self, request, response):
        if hasattr(_thread_locals, "user"):
            del _thread_locals.user
        return response
