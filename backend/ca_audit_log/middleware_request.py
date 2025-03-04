# middleware_request.py
import logging
from threading import local
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# Thread local storage
_thread_locals = local()


class UserMiddleware(MiddlewareMixin):
    """Middleware to store the current user in thread local storage."""

    def process_request(self, request):
        user = getattr(request, "user", None)
        _thread_locals.user = user
        logger.debug(f"UserMiddleware: Set thread local user to {user}")

    def process_response(self, request, response):
        if hasattr(_thread_locals, "user"):
            logger.debug(
                f"UserMiddleware: Cleaning up thread local user {_thread_locals.user}"
            )
            del _thread_locals.user
        return response
