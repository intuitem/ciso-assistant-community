"""Every MCP tool call is logged, and each connection has a budget: calls per
minute and characters returned per hour."""

import time

import structlog
from django.conf import settings
from django.core.cache import cache

logger = structlog.get_logger(__name__)

MINUTE = 60
HOUR = 3600


def _connection(access) -> str:
    return f"{access.subject}:{access.client_id}"


def _bucket(kind, access, period) -> str:
    return f"mcp:{kind}:{_connection(access)}:{int(time.time() // period)}"


def _count(key, amount, period) -> int:
    # add() is a no-op when the key exists; the expiry outlives the bucket
    cache.add(key, 0, timeout=period * 2)
    try:
        return cache.incr(key, amount)
    except ValueError:
        # expired between add() and incr()
        cache.set(key, amount, timeout=period * 2)
        return amount


def _claims(access) -> dict:
    return access.claims or {}


class ToolCallHooks:
    def before(self, tool, access):
        if access is None:
            return None
        max_calls = settings.MCP_MAX_CALLS_PER_MINUTE
        if (
            max_calls
            and _count(_bucket("calls", access, MINUTE), 1, MINUTE) > max_calls
        ):
            return (
                f"Error: this connection made more than {max_calls} calls in a "
                "minute. Wait a minute, then continue with fewer calls."
            )
        max_chars = settings.MCP_MAX_RESPONSE_CHARS_PER_HOUR
        if max_chars and (cache.get(_bucket("chars", access, HOUR)) or 0) >= max_chars:
            return (
                "Error: this connection has read its data budget for this hour. "
                "Wait for the next hour, or narrow the request with filters."
            )
        return None

    def after(self, tool, access, result, seconds, error):
        size = len(result) if isinstance(result, str) else 0
        # a refused or failed call returned no data
        if (
            access is not None
            and size
            and not error
            and settings.MCP_MAX_RESPONSE_CHARS_PER_HOUR
        ):
            _count(_bucket("chars", access, HOUR), size, HOUR)
        if error == "limited":
            outcome = "limited"
        elif error:
            outcome = "error"
        elif isinstance(result, str) and result.startswith("Error"):
            outcome = "refused"
        else:
            outcome = "ok"
        claims = _claims(access) if access else {}
        log = logger.warning if outcome in ("limited", "error") else logger.info
        log(
            "mcp tool call",
            tool=tool,
            outcome=outcome,
            error=error if error != "limited" else None,
            user=access.subject if access else None,
            client_id=access.client_id if access else None,
            app=claims.get("app"),
            profile=claims.get("profile"),
            level=claims.get("level"),
            duration_ms=round(seconds * 1000),
            result_chars=size,
        )
