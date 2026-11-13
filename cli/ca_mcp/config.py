"""Configuration module for CISO Assistant MCP server"""

import os
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

# Load environment variables from .mcp.env file
load_dotenv(".mcp.env")

# Configuration dictionary (for backward compatibility)
cli_cfg = dict()
auth_data = dict()
GLOBAL_FOLDER_ID = None

_TRUTHY = ("true", "1", "yes", "on")


def canonical_url(url: str) -> str:
    """The URL as clients write it: lowercase host, no default port. Clients
    send https://host/mcp even when the instance is set to https://host:443,
    and the backend compares against this same form."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = parts.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    port = parts.port
    default = {"http": 80, "https": 443}.get(scheme)
    netloc = host if port in (None, default) else f"{host}:{port}"
    return urlunsplit((scheme, netloc, parts.path.rstrip("/"), parts.query, ""))


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() in _TRUTHY


def _csv(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


# Read TOKEN and VERIFY_CERTIFICATE from environment variables
API_URL = os.getenv("API_URL", "")
TOKEN = os.getenv("TOKEN", "")
VERIFY_CERTIFICATE = _flag("VERIFY_CERTIFICATE", "true")
HTTP_TIMEOUT = 30  # seconds

# Response bounding. A single unbounded list call can cost more context than the
# entire tool surface, and unlike the tool list it recurs on every call.
#
# MAX_RESPONSE_CHARS is the real protection; the row limits exist so the common
# case never reaches it. Keep the page limit generous enough that ordinary
# registers come back whole -- truncating an 82-row list at 50 costs
# completeness for no context benefit, since 100 rows still fits the cap.
# Bounding applies to DISPLAY only: callers computing aggregates or driving
# bulk writes pass max_items=None (see fetch_all_results).
DEFAULT_PAGE_LIMIT = int(os.getenv("CA_MCP_PAGE_LIMIT", "100"))
MAX_TOTAL_ITEMS = int(os.getenv("CA_MCP_MAX_ITEMS", "200"))
MAX_RESPONSE_CHARS = int(os.getenv("CA_MCP_MAX_RESPONSE_CHARS", "20000"))

# Remote MCP server of an instance (the `mcp` service): "oauth" takes the
# OAuth tokens of AI apps only, "pat" (default) takes a PAT.
AUTH_MODE = os.getenv("CA_MCP_AUTH", "pat").lower()
# OAuth sign-in only exists over HTTP
TRANSPORT = os.getenv(
    "CA_MCP_TRANSPORT", "streamable-http" if AUTH_MODE == "oauth" else "stdio"
).lower()
IS_HTTP = TRANSPORT in ("http", "streamable-http")
# honoured in every mode; only the default differs: stdio is one local user, and
# in OAuth mode each connection's profile decides, in the backend too
READ_ONLY = _flag(
    "CA_MCP_READ_ONLY", "true" if IS_HTTP and AUTH_MODE != "oauth" else "false"
)
HTTP_HOST = os.getenv("CA_MCP_HOST", "127.0.0.1")
HTTP_PORT = int(os.getenv("CA_MCP_PORT", "8001"))
HTTP_PATH = os.getenv("CA_MCP_PATH", "/mcp")
ALLOWED_HOSTS = _csv("CA_MCP_ALLOWED_HOSTS")
ALLOWED_ORIGINS = _csv("CA_MCP_ALLOWED_ORIGINS")
# Stateless avoids Mcp-Session-Id expiry (Copilot Studio), but some clients
# expect a session. JSON responses instead of SSE framing suit non-streaming clients.
STATELESS = _flag("CA_MCP_STATELESS", "true")
JSON_RESPONSE = _flag("CA_MCP_JSON_RESPONSE", "false")
# Serving every HTTP caller with the server's own TOKEN collapses all users into
# one identity; opt-in only.
ALLOW_ENV_TOKEN = _flag("CA_MCP_ALLOW_ENV_TOKEN", "false")

# The instance's public URL: the token issuer is <url>/api, this server <url>/mcp.
PUBLIC_URL = canonical_url(os.getenv("CISO_ASSISTANT_URL", ""))
# How long the backend's answer about a token is reused. Revoking a connection
# still takes effect at once: the backend checks the token on every call.
TOKEN_CACHE_SECONDS = int(os.getenv("CA_MCP_TOKEN_CACHE_SECONDS", "60"))
# Backend calls run at once: they share the backend's workers with the UI.
MAX_CONCURRENT_CALLS = int(os.getenv("CA_MCP_MAX_CONCURRENT_CALLS", "2"))
# Budget per connection (one user with one app), counted by this process.
# 0 = no limit.
MAX_CALLS_PER_MINUTE = int(os.getenv("MCP_MAX_CALLS_PER_MINUTE", "60"))
MAX_RESPONSE_CHARS_PER_HOUR = int(
    os.getenv("MCP_MAX_RESPONSE_CHARS_PER_HOUR", "2000000")
)
