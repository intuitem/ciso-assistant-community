"""
Focus Mode Middleware

Allows scoping the entire application to a single domain/folder
Frontend sends X-Focus-Folder-Id header, middleware validates
and attaches it to the request for use in BaseModelViewSet.get_queryset().
"""

import re
import structlog
from uuid import UUID

from core.context import focus_folder_id_var
from global_settings.utils import ff_is_enabled

logger = structlog.getLogger(__name__)

# Allowlist of endpoints exempt from focus mode
FOCUS_MODE_EXEMPT_PATHS = [
    "/api/iam/current-user/",
    "/api/csrf/",
    "/api/_allauth/",
    "/api/build/",
    "/api/settings/",
    "/api/get-waiting-risk-acceptances/",
    "/api/license/",
    "/api/iam/sso-settings/",
]


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() == "true"


def _is_path_exempt(request) -> bool:
    """
    Check if the request path should be exempt from focus mode filtering.
    """
    if request.path == "/api/folders/":
        # Only exempt if no_focus is set
        return _is_truthy(request.GET.get("no_focus"))
    for exempt_path in FOCUS_MODE_EXEMPT_PATHS:
        if request.path.startswith(exempt_path):
            return True
    return False


def _validate_uuid(value: str) -> UUID | None:
    """Validate and return UUID from string, or None if invalid."""
    if not value:
        return None
    try:
        return UUID(value.strip())
    except (ValueError, AttributeError):
        return None


class FocusModeMiddleware:
    """
    Middleware that reads the X-Focus-Folder-Id header and attaches
    the focus folder ID to the request object for downstream use.

    The focus_folder_id is then used by BaseModelViewSet.get_queryset()
    to scope all queries to a specific folder.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if _is_path_exempt(request):
            focus_folder_id_var.set(None)
            return self.get_response(request)

        focus_header = request.headers.get("X-Focus-Folder-Id")
        if focus_header:
            if not ff_is_enabled("focus_mode"):
                focus_folder_id_var.set(None)
                return self.get_response(request)
            folder_id = _validate_uuid(focus_header)
            if folder_id:
                focus_folder_id_var.set(folder_id)
            else:
                logger.warning(
                    "Invalid X-Focus-Folder-Id header value",
                    value=focus_header,
                    path=request.path,
                )
        else:
            focus_folder_id_var.set(None)

        return self.get_response(request)
