import json
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.core.handlers.base import BaseHandler
from django.db import close_old_connections
from django.test import RequestFactory
from mcp.server.auth.middleware.auth_context import get_access_token

from iam.models import User

API_PREFIX = "/api"

# Tools run inside asyncio.run() in a worker thread, where Django refuses ORM
# calls; dispatch from plain threads instead.
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="mcp-dispatch")
_handler = None


class Response:
    """The slice of requests.Response the ca_mcp tools read."""

    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content
        self.text = content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.content)


def _get_handler() -> BaseHandler:
    global _handler
    if _handler is None:
        handler = BaseHandler()
        handler.load_middleware()
        _handler = handler
    return _handler


def request_as(
    user, method, endpoint, *, params=None, json=None, data=None, headers=None
) -> Response:
    """Run one API call through the full middleware stack as `user`, so RBAC,
    audit logging and every other request hook behave as for a REST call."""
    public = urlsplit(settings.CISO_ASSISTANT_URL)
    path = API_PREFIX + endpoint
    if params:
        path += "?" + urlencode(params, doseq=True)
    extra = {
        "HTTP_" + name.upper().replace("-", "_"): value
        for name, value in (headers or {}).items()
    }
    if json is not None:
        body, content_type = _json_dumps(json), "application/json"
    elif data is not None:
        body = data.read() if hasattr(data, "read") else data
        content_type = "application/octet-stream"
    else:
        body, content_type = "", "application/octet-stream"
    request = RequestFactory().generic(
        method,
        path,
        data=body,
        content_type=content_type,
        secure=public.scheme == "https",
        HTTP_HOST=public.netloc,
        **extra,
    )
    if user is not None:
        # DRF's Request honours this in place of its authenticators.
        request._force_auth_user = user
    response = _get_handler().get_response(request)
    if response.streaming:
        content = b"".join(response.streaming_content)
    else:
        content = response.content
    return Response(response.status_code, content)


def _json_dumps(payload) -> str:
    return json.dumps(payload, default=str)


def _run(user_id, method, endpoint, kwargs) -> Response:
    close_old_connections()
    try:
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return Response(401, b'{"detail": "User is inactive or unknown."}')
        return request_as(user, method, endpoint, **kwargs)
    finally:
        close_old_connections()


def anonymous_get(endpoint) -> Response:
    close_old_connections()
    try:
        return request_as(None, "GET", endpoint)
    finally:
        close_old_connections()


def dispatch(method, endpoint, **kwargs) -> Response:
    """ca_mcp transport: the caller is whoever the verified access token says."""
    access = get_access_token()
    if access is None or access.subject is None:
        return Response(401, b'{"detail": "Not authenticated."}')
    return _executor.submit(_run, access.subject, method, endpoint, kwargs).result()
