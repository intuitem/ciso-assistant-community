"""Configuration module for CISO Assistant MCP server"""

import os
from dotenv import load_dotenv

# Load environment variables from .mcp.env file
load_dotenv(".mcp.env")

# Configuration dictionary (for backward compatibility)
cli_cfg = dict()
auth_data = dict()
GLOBAL_FOLDER_ID = None

_TRUTHY = ("true", "1", "yes", "on")


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

# HTTP transport (spike). Read-only by default: the HTTP endpoint is the one
# surface that can be reached by a third-party orchestrator.
TRANSPORT = os.getenv("CA_MCP_TRANSPORT", "stdio").lower()
READ_ONLY = _flag("CA_MCP_READ_ONLY", "true")
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
