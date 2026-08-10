"""Per-request credential resolution.

Under HTTP transport each request carries its own PAT, so the credential cannot
live in a module-level singleton the way it does for stdio. The MCP SDK exposes
the originating Starlette request through its own context var, which is set in
the same task that dispatches the tool call -- reading it here avoids threading
a Context parameter through every tool.
"""

import logging

from mcp.server.lowlevel.server import request_ctx

from . import config

logger = logging.getLogger(__name__)

CUSTOM_HEADER = "x-ciso-token"
_SCHEMES = ("token", "bearer")


def _strip_scheme(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    parts = value.split(None, 1)
    if len(parts) == 2 and parts[0].lower() in _SCHEMES:
        return parts[1].strip() or None
    return value


def _request_headers():
    try:
        request = request_ctx.get().request
    except LookupError:
        return None
    return getattr(request, "headers", None)


def _describe(source: str, token: str) -> None:
    """Log where the credential came from, never its value."""
    logger.info(
        "credential source=%s length=%d",
        source,
        len(token),
    )


class MissingCredentialError(RuntimeError):
    """Raised when an HTTP request carries no usable credential."""


def get_request_token() -> str:
    """PAT for the current request.

    Under HTTP each caller must present its own credential; falling back to the
    env token there would serve every caller as one identity and defeat the
    per-user scoping the transport exists to provide.
    """
    headers = _request_headers()
    if headers is None:
        return config.TOKEN

    for name in ("authorization", CUSTOM_HEADER):
        token = _strip_scheme(headers.get(name) or "")
        if token:
            _describe(name, token)
            return token

    if config.ALLOW_ENV_TOKEN:
        _describe("env fallback (CA_MCP_ALLOW_ENV_TOKEN)", config.TOKEN)
        return config.TOKEN

    _describe("none (no credential header)", "")
    raise MissingCredentialError(
        "No credential supplied. Send your CISO Assistant personal access token as "
        "'Authorization: Token <PAT>' (Bearer also accepted) or 'X-CISO-Token: <PAT>'. "
        "Set CA_MCP_ALLOW_ENV_TOKEN=true to use the server's own token instead."
    )
