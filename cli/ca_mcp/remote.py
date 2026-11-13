"""The MCP server of an instance, run as its own service, with no database
access and no secret.

It asks the backend what each caller's token may do, with the token itself,
then makes the tools' API calls with that same token. It accepts MCP tokens
only. The backend checks every call again, the connection's profile included."""

import hashlib
import json
import logging
import threading
import time
from contextvars import ContextVar
from urllib.parse import parse_qsl, urlencode, urlsplit

import anyio
import requests
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken

from . import actions, client, config

logger = logging.getLogger(__name__)

MCP_SCOPE = "mcp"


def issuer_url() -> str:
    return config.PUBLIC_URL + "/api"


def resource_url() -> str:
    return config.PUBLIC_URL + "/mcp"


# every backend call, token checks included: any request with a made-up token
# triggers one, and they share the backend's workers with the UI
_backend_calls = threading.BoundedSemaphore(max(1, config.MAX_CONCURRENT_CALLS))


class TokenVerifier:
    """Asks the backend what the token may do. Only an MCP token gets an
    answer: a PAT or any other token is refused. Each answer is reused for a
    short while, a refusal too."""

    MAX_ENTRIES = 10_000

    def __init__(self, session=None, cache_seconds=None, clock=time.monotonic):
        self._http = session or requests.Session()
        self._ttl = (
            config.TOKEN_CACHE_SECONDS if cache_seconds is None else cache_seconds
        )
        self._clock = clock
        self._cache: dict[str, tuple[float, AccessToken | None]] = {}
        self._lock = threading.Lock()

    async def verify_token(self, token: str) -> AccessToken | None:
        access, final = await anyio.to_thread.run_sync(self.check, token)
        if not final:
            _note_outage()
        return access

    def verify(self, token: str) -> AccessToken | None:
        return self.check(token)[0]

    def check(self, token: str) -> tuple[AccessToken | None, bool]:
        """The answer about the token, and whether it is one (see _ask)."""
        key = hashlib.sha256(token.encode()).hexdigest()
        now = self._clock()
        with self._lock:
            hit = self._cache.get(key)
            if hit and hit[0] > now:
                return hit[1], True
            # forget the expired answers now and then; a flood of made-up
            # tokens that are all still fresh empties it, rather than make every
            # call copy it again
            if len(self._cache) > self.MAX_ENTRIES:
                self._cache = {k: v for k, v in self._cache.items() if v[0] > now}
                if len(self._cache) > self.MAX_ENTRIES:
                    self._cache = {}
        access, final = self._ask(token)
        # a backend outage is not an answer: ask again on the next call
        if final:
            with self._lock:
                self._cache[key] = (now + self._ttl, access)
        return access, final

    def _ask(self, token: str) -> tuple[AccessToken | None, bool]:
        """The backend's answer, and whether it is one: a refusal is, an error
        or a timeout is not."""
        try:
            with _backend_calls:
                res = self._http.get(
                    f"{config.API_URL.rstrip('/')}/iam/mcp/access/",
                    headers={"Authorization": f"Bearer {token}"},
                    verify=config.VERIFY_CERTIFICATE,
                    timeout=config.HTTP_TIMEOUT,
                )
        except requests.RequestException as e:
            logger.warning("token check failed: %s", type(e).__name__)
            return None, False
        if res.status_code in (401, 403):
            return None, True
        if res.status_code != 200:
            logger.warning("token check failed: HTTP %s", res.status_code)
            return None, False
        data = res.json()
        return AccessToken(
            token=token,
            client_id=data.get("client_id") or "",
            scopes=[MCP_SCOPE],
            resource=resource_url(),
            subject=data.get("user"),
            claims={
                "actions": data.get("actions") or [actions.READ],
                "profile": data.get("profile"),
                "app": data.get("app"),
            },
        ), True


# Set per request by outage_as_503: the token check marks it when the backend
# gave no answer, so the 401 the SDK then sends becomes a 503.
_outage: ContextVar[list | None] = ContextVar("mcp_backend_outage", default=None)


def _note_outage() -> None:
    marks = _outage.get()
    if marks is not None:
        marks.append(True)


def outage_as_503(app):
    """A 401 tells the app its token is dead, and it signs the user in again.
    When the backend could not check the token, answer 503 instead: the app
    retries later with the same token."""

    async def wrapped(scope, receive, send):
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        marks: list = []
        reset = _outage.set(marks)
        replaced = []

        async def send_checked(message):
            if (
                message["type"] == "http.response.start"
                and message["status"] == 401
                and marks
            ):
                replaced.append(True)
                return
            if replaced:
                # drop the 401's body, then send ours once it is complete
                if not message.get("more_body"):
                    await _send_unavailable(send)
                return
            await send(message)

        try:
            await app(scope, receive, send_checked)
        finally:
            _outage.reset(reset)

    return wrapped


async def _send_unavailable(send) -> None:
    body = json.dumps(
        {
            "error": "temporarily_unavailable",
            "error_description": "CISO Assistant cannot check the token right now. Try again shortly.",
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 503,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"retry-after", b"5"),
                (b"content-security-policy", b"sandbox"),
                (b"x-content-type-options", b"nosniff"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class _Refused:
    """The slice of requests.Response the tools read."""

    status_code = 401
    text = '{"detail": "Not authenticated."}'

    def json(self):
        return json.loads(self.text)


def _with_params(endpoint, params) -> str:
    # pagination links already carry a query string: merge, params winning
    parts = urlsplit(endpoint)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in (params or {})
    ]
    for key, value in (params or {}).items():
        values = value if isinstance(value, (list, tuple)) else [value]
        query += [(key, v) for v in values]
    return parts.path + ("?" + urlencode(query) if query else "")


def forward(method, endpoint, *, params=None, json=None, data=None, headers=None):
    """ca_mcp transport: the call goes out with the caller's own token."""
    access = get_access_token()
    if access is None:
        return _Refused()
    with _backend_calls:
        return requests.request(
            method,
            config.API_URL.rstrip("/") + _with_params(endpoint, params),
            json=json,
            data=data,
            headers={**(headers or {}), "Authorization": f"Bearer {access.token}"},
            verify=config.VERIFY_CERTIFICATE,
            timeout=config.HTTP_TIMEOUT,
        )


MINUTE = 60
HOUR = 3600


class ToolCallHooks:
    """Every tool call is logged, and each connection has a budget: calls per
    minute and characters returned per hour. The counters live in this process:
    with several processes, each one counts on its own."""

    def __init__(self, clock=time.time):
        self._clock = clock
        self._counts: dict[tuple, int] = {}
        self._lock = threading.Lock()

    def _bucket(self, kind, access, period) -> tuple:
        return (kind, access.subject, access.client_id, int(self._clock() // period))

    def _add(self, key, amount) -> int:
        with self._lock:
            # keep the current buckets only
            if len(self._counts) > 10_000:
                now = self._clock()
                self._counts = {
                    k: v
                    for k, v in self._counts.items()
                    if k[3] >= int(now // (MINUTE if k[0] == "calls" else HOUR))
                }
            self._counts[key] = self._counts.get(key, 0) + amount
            return self._counts[key]

    def before(self, tool, access):
        if access is None:
            return None
        max_calls = config.MAX_CALLS_PER_MINUTE
        if (
            max_calls
            and self._add(self._bucket("calls", access, MINUTE), 1) > max_calls
        ):
            return (
                f"Error: this connection made more than {max_calls} calls in a "
                "minute. Wait a minute, then continue with fewer calls."
            )
        max_chars = config.MAX_RESPONSE_CHARS_PER_HOUR
        if max_chars and self._add(self._bucket("chars", access, HOUR), 0) >= max_chars:
            return (
                "Error: this connection has read its data budget for this hour. "
                "Wait for the next hour, or narrow the request with filters."
            )
        return None

    def after(self, tool, access, result, seconds, error):
        size = len(result) if isinstance(result, str) else 0
        if error == "limited":
            outcome = "limited"
        elif error:
            outcome = "error"
        elif isinstance(result, str) and result.startswith("Error"):
            outcome = "refused"
        else:
            outcome = "ok"
        # a refused or failed call returned no data
        if outcome == "ok" and access is not None:
            self._add(self._bucket("chars", access, HOUR), size)
        claims = (access.claims or {}) if access else {}
        record = {
            "tool": tool,
            "outcome": outcome,
            "error": error if error != "limited" else None,
            "user": access.subject if access else None,
            "client_id": access.client_id if access else None,
            "app": claims.get("app"),
            "profile": claims.get("profile"),
            "actions": claims.get("actions"),
            "duration_ms": round(seconds * 1000),
            "result_chars": size,
        }
        log = logger.warning if outcome in ("limited", "error") else logger.info
        log("mcp tool call %s", json.dumps(record))


def build_app():
    missing = [
        name
        for name, value in (
            ("CISO_ASSISTANT_URL", config.PUBLIC_URL),
            ("API_URL", config.API_URL),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"CA_MCP_AUTH=oauth needs: {', '.join(missing)}")
    from .server import build_oauth_http_app

    if not config.ALLOWED_HOSTS:
        # with or without a port: some proxies change it in Host
        public = urlsplit(config.PUBLIC_URL)
        config.ALLOWED_HOSTS = [public.netloc, f"{public.hostname}:*"]
    client.set_transport(forward)
    return outage_as_503(
        build_oauth_http_app(
            token_verifier=TokenVerifier(),
            issuer_url=issuer_url(),
            resource_url=resource_url(),
            hooks=ToolCallHooks(),
        )
    )
