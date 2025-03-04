from .signals import _thread_locals


class ThreadLocalUserMiddleware:
    """
    Middleware that puts the user object in the thread local storage.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store the current user in thread local storage
        if hasattr(request, "user"):
            _thread_locals.user = request.user
        else:
            _thread_locals.user = None

        response = self.get_response(request)

        # Clean up after request is complete
        if hasattr(_thread_locals, "user"):
            delattr(_thread_locals, "user")

        return response
