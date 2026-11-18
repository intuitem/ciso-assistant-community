from .events import hold_inline_runs


class InlineWorkflowRunsMiddleware:
    """Starts a request's inline workflow runs once its view has returned.

    Listed before AuditlogMiddleware, so it wraps it: by the time the runs
    start, audit entries are no longer stamped with the request's user, and a
    run's changes are logged like a queued run's rather than as the user's own.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with hold_inline_runs():
            return self.get_response(request)
