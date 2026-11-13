"""The MCP server of an instance: tokens checked with the backend, calls made
with the caller's own token, a budget per connection, and every call logged."""

import json
import logging
import sys
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import client, config, remote  # noqa: E402
from tests.mcp.helpers import _response  # noqa: E402

PUBLIC = "https://ca.example.com"
API = "http://backend:8000/api"
METADATA_PATH = "/.well-known/oauth-protected-resource/mcp"
MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}
ACCESS = {
    "user": "u1",
    "client_id": "abc",
    "actions": ["read", "create"],
    "profile": "Read and create",
    "app": "Claude Code",
}


@pytest.fixture(autouse=True)
def _config():
    with patch.multiple(
        config,
        PUBLIC_URL=PUBLIC,
        API_URL=API,
        MAX_CALLS_PER_MINUTE=60,
        MAX_RESPONSE_CHARS_PER_HOUR=2_000_000,
    ):
        yield


def _session(answer=None, status=200):
    session = Mock()
    session.get.return_value = (
        _response(json_data=answer) if answer else _response(status_code=403)
    )
    if answer is None and status != 200:
        session.get.return_value = _response(status_code=status)
    return session


def _access(subject="u1", client_id="abc", token="t"):
    return AccessToken(
        token=token,
        client_id=client_id,
        scopes=["mcp"],
        subject=subject,
        claims={"actions": ["read"], "profile": "Read", "app": "Claude Code"},
    )


@pytest.fixture
def connected():
    tokens = []

    def connect(access):
        tokens.append(auth_context_var.set(AuthenticatedUser(access)))

    yield connect
    for token in reversed(tokens):
        auth_context_var.reset(token)


class TestTokenVerifier:
    def test_an_mcp_token_carries_its_connection(self):
        session = _session(ACCESS)
        access = remote.TokenVerifier(session).verify("raw")

        assert access.subject == "u1"
        assert access.resource == PUBLIC + "/mcp"
        assert access.claims == {
            "actions": ["read", "create"],
            "profile": "Read and create",
            "app": "Claude Code",
        }
        call = session.get.call_args
        assert call.args[0] == API + "/iam/mcp/access/"
        assert call.kwargs["headers"] == {"Authorization": "Bearer raw"}

    def test_any_other_credential_is_refused(self):
        # the backend answers only for MCP tokens: a PAT gets nothing here
        assert remote.TokenVerifier(_session()).verify("pat") is None

    def test_answers_are_reused_for_a_while(self):
        now = [0.0]
        session = _session(ACCESS)
        verifier = remote.TokenVerifier(session, cache_seconds=60, clock=lambda: now[0])

        verifier.verify("raw")
        verifier.verify("raw")
        assert session.get.call_count == 1

        now[0] = 61
        verifier.verify("raw")
        assert session.get.call_count == 2

    def test_a_failing_instance_refuses(self):
        assert remote.TokenVerifier(_session(status=503)).verify("raw") is None

    def test_an_outage_is_not_remembered(self):
        # refused while the backend is down, accepted as soon as it is back
        session = _session(status=503)
        verifier = remote.TokenVerifier(session, cache_seconds=60)
        assert verifier.verify("raw") is None

        session.get.return_value = _response(json_data=ACCESS)
        assert verifier.verify("raw").subject == "u1"

    def test_an_unreachable_backend_is_not_remembered(self):
        session = _session(ACCESS)
        session.get.side_effect = [remote.requests.ConnectionError(), None]
        verifier = remote.TokenVerifier(session, cache_seconds=60)
        assert verifier.verify("raw") is None

        session.get.side_effect = None
        assert verifier.verify("raw").subject == "u1"

    def test_a_refusal_is_remembered(self):
        session = _session()
        verifier = remote.TokenVerifier(session, cache_seconds=60)
        verifier.verify("pat")
        verifier.verify("pat")
        assert session.get.call_count == 1

    def test_a_flood_of_fresh_refusals_does_not_grow_the_cache(self, monkeypatch):
        monkeypatch.setattr(remote.TokenVerifier, "MAX_ENTRIES", 3)
        verifier = remote.TokenVerifier(_session(), cache_seconds=60)
        for i in range(10):
            verifier.verify(f"made-up-{i}")
        assert len(verifier._cache) <= 4


def test_oauth_mode_serves_http_by_default(monkeypatch):
    import importlib

    monkeypatch.setenv("CA_MCP_AUTH", "oauth")
    monkeypatch.delenv("CA_MCP_TRANSPORT", raising=False)
    try:
        assert importlib.reload(config).IS_HTTP
    finally:
        monkeypatch.delenv("CA_MCP_AUTH")
        importlib.reload(config)


def test_oauth_mode_refuses_stdio():
    from ca_mcp import server

    with patch.multiple(config, AUTH_MODE="oauth", IS_HTTP=False):
        with pytest.raises(SystemExit, match="streamable-http"):
            server.main()


class TestForward:
    def test_the_call_carries_the_callers_token(self, connected):
        connected(_access(token="oauth"))
        with patch("ca_mcp.remote.requests.request") as request:
            remote.forward("GET", "/folders/", params={"limit": 5})

        method, url = request.call_args.args
        assert (method, url) == ("GET", API + "/folders/?limit=5")
        assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer oauth"

    def test_no_caller_no_call(self):
        with patch("ca_mcp.remote.requests.request") as request:
            assert remote.forward("GET", "/folders/").status_code == 401
        request.assert_not_called()

    def test_params_merge_into_a_pagination_link(self):
        path = remote._with_params("/folders/?limit=100&offset=100", {"limit": 100})
        assert path == "/folders/?offset=100&limit=100"
        assert remote._with_params("/folders/", {"id": ["a", "b"]}) == (
            "/folders/?id=a&id=b"
        )
        assert remote._with_params("/folders/", None) == "/folders/"

    def test_a_tool_follows_pagination_links(self, connected):
        connected(_access())
        pages = {
            API + "/folders/?limit=2": {
                "count": 3,
                "results": [{"name": "a"}, {"name": "b"}],
                "next": "/api/folders/?limit=2&offset=2",
            },
            API + "/folders/?offset=2&limit=2": {
                "count": 3,
                "results": [{"name": "c"}],
                "next": None,
            },
        }

        def request(method, url, **kwargs):
            return _response(json_data=pages[url])

        with (
            patch("ca_mcp.remote.requests.request", side_effect=request),
            patch.object(client, "_transport", remote.forward),
            patch.object(client, "API_PATH", "/api"),
            patch.object(client, "DEFAULT_PAGE_LIMIT", 2),
        ):
            results, error = client.fetch_all_results("/folders/")

        assert error is None
        assert [row["name"] for row in results] == ["a", "b", "c"]


class TestBudget:
    def test_calls_above_the_minute_limit_are_refused(self):
        hooks, access = remote.ToolCallHooks(), _access()
        with patch.object(config, "MAX_CALLS_PER_MINUTE", 2):
            assert hooks.before("get_folders", access) is None
            assert hooks.before("get_folders", access) is None
            assert "more than 2 calls in a minute" in hooks.before(
                "get_folders", access
            )

    def test_each_connection_has_its_own_budget(self):
        hooks = remote.ToolCallHooks()
        with patch.object(config, "MAX_CALLS_PER_MINUTE", 1):
            assert hooks.before("get_folders", _access(subject="u1")) is None
            assert hooks.before("get_folders", _access(subject="u2")) is None
            assert hooks.before("get_folders", _access(client_id="other")) is None

    def test_the_count_starts_again_each_minute(self):
        now = [0.0]
        hooks, access = remote.ToolCallHooks(clock=lambda: now[0]), _access()
        with patch.object(config, "MAX_CALLS_PER_MINUTE", 1):
            assert hooks.before("get_folders", access) is None
            assert hooks.before("get_folders", access) is not None
            now[0] = 60
            assert hooks.before("get_folders", access) is None

    def test_data_above_the_hourly_budget_is_refused(self):
        hooks, access = remote.ToolCallHooks(), _access()
        with patch.object(config, "MAX_RESPONSE_CHARS_PER_HOUR", 100):
            hooks.after("get_folders", access, "x" * 60, 0.1, None)
            assert hooks.before("get_folders", access) is None
            hooks.after("get_folders", access, "x" * 60, 0.1, None)
            assert "data budget for this hour" in hooks.before("get_folders", access)

    def test_refusals_do_not_use_the_budget(self):
        hooks, access = remote.ToolCallHooks(), _access()
        with patch.object(config, "MAX_RESPONSE_CHARS_PER_HOUR", 100):
            hooks.after("get_folders", access, "Error: " + "x" * 200, 0.0, "limited")
            hooks.after("get_folders", access, "Error: " + "x" * 200, 0.0, None)
            assert hooks.before("get_folders", access) is None

    def test_zero_turns_the_limits_off(self):
        hooks, access = remote.ToolCallHooks(), _access()
        with patch.multiple(
            config, MAX_CALLS_PER_MINUTE=0, MAX_RESPONSE_CHARS_PER_HOUR=0
        ):
            for _ in range(5):
                hooks.after("get_folders", access, "x" * 1000, 0.1, None)
                assert hooks.before("get_folders", access) is None


class TestLog:
    def _logged(self, caplog, *args):
        with caplog.at_level(logging.INFO, logger="ca_mcp.remote"):
            remote.ToolCallHooks().after(*args)
        message = caplog.records[-1].getMessage()
        assert message.startswith("mcp tool call ")
        return json.loads(message[len("mcp tool call ") :])

    def test_each_call_is_logged_with_user_app_and_profile(self, caplog):
        entry = self._logged(caplog, "get_folders", _access(), "rows", 0.25, None)
        assert entry["tool"] == "get_folders"
        assert entry["outcome"] == "ok"
        assert entry["user"] == "u1"
        assert entry["app"] == "Claude Code"
        assert entry["profile"] == "Read"
        assert entry["duration_ms"] == 250
        assert entry["result_chars"] == 4

    @pytest.mark.parametrize(
        "result, error, outcome",
        [
            ("Error: this connection uses ...", None, "refused"),
            ("Error: too many calls", "limited", "limited"),
            (None, "HTTPError", "error"),
        ],
    )
    def test_outcomes(self, caplog, result, error, outcome):
        entry = self._logged(caplog, "update_asset", _access(), result, 0.0, error)
        assert entry["outcome"] == outcome


@pytest.fixture
def app():
    with patch.object(config, "ALLOWED_HOSTS", ["localhost:8001"]):
        yield remote.build_app()
    client.set_transport(None)


def test_an_unconfigured_server_does_not_start():
    with patch.object(config, "API_URL", ""):
        with pytest.raises(SystemExit, match="API_URL"):
            remote.build_app()


def test_an_unauthenticated_call_points_to_the_metadata(app):
    with TestClient(app, base_url="http://localhost:8001") as http:
        response = http.post("/mcp", headers=MCP_HEADERS, json={})
    assert response.status_code == 401
    assert METADATA_PATH in response.headers["www-authenticate"]


def test_protected_resource_metadata(app):
    with TestClient(app, base_url="http://localhost:8001") as http:
        metadata = http.get(METADATA_PATH).json()
    assert metadata["resource"] == PUBLIC + "/mcp"
    assert metadata["authorization_servers"] == [PUBLIC + "/api"]
    assert metadata["scopes_supported"] == ["mcp"]


def test_a_tool_call_runs_with_the_callers_token(app):
    call = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "get_folders", "arguments": {}},
    }
    folders = _response(json_data={"count": 1, "results": [{"name": "Global"}]})
    with (
        patch("ca_mcp.remote.requests.Session.get") as lookup,
        patch("ca_mcp.remote.requests.request", return_value=folders) as request,
        TestClient(app, base_url="http://localhost:8001") as http,
    ):
        lookup.return_value = _response(json_data=ACCESS)
        response = http.post(
            "/mcp", headers={**MCP_HEADERS, "Authorization": "Bearer raw"}, json=call
        )

    assert response.status_code == 200
    payload = json.loads(
        next(
            line[len("data:") :]
            for line in response.text.splitlines()
            if line.startswith("data:")
        )
    )
    assert payload["result"].get("isError") is not True
    assert request.call_args.args[1].startswith(API + "/folders/")
    assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer raw"


def test_backend_calls_are_limited(connected):
    connected(_access())
    running, peak = [0], [0]

    def request(*args, **kwargs):
        running[0] += 1
        peak[0] = max(peak[0], running[0])
        time.sleep(0.05)
        running[0] -= 1
        return _response(json_data={})

    with patch("ca_mcp.remote.requests.request", side_effect=request):
        token = auth_context_var.get()
        threads = [
            threading.Thread(
                target=lambda: (
                    auth_context_var.set(token),
                    remote.forward("GET", "/folders/"),
                )
            )
            for _ in range(6)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert peak[0] <= config.MAX_CONCURRENT_CALLS


def test_an_unknown_auth_mode_refuses_to_start():
    from ca_mcp import server

    with patch.multiple(config, AUTH_MODE="oauht"):
        with pytest.raises(SystemExit, match="pat or oauth"):
            server.main()


def test_token_checks_share_the_backend_call_limit():
    inflight, peak, lock = [0], [0], threading.Lock()

    def slow_get(*args, **kwargs):
        with lock:
            inflight[0] += 1
            peak[0] = max(peak[0], inflight[0])
        time.sleep(0.05)
        with lock:
            inflight[0] -= 1
        return _response(status_code=401)

    session = Mock()
    session.get.side_effect = slow_get
    verifier = remote.TokenVerifier(session, cache_seconds=60)
    threads = [
        threading.Thread(target=verifier.verify, args=(f"made-up-{i}",))
        for i in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert peak[0] <= config.MAX_CONCURRENT_CALLS


@pytest.mark.parametrize(
    "configured, expected",
    [
        ("https://ca.example.com:443", "https://ca.example.com"),
        ("https://CA.example.com/", "https://ca.example.com"),
        ("http://ca.example.com:80", "http://ca.example.com"),
        ("https://ca.example.com:8443", "https://ca.example.com:8443"),
        ("", ""),
    ],
)
def test_the_public_url_drops_the_default_port(configured, expected):
    # the backend expects the resource as clients send it, without :443
    assert config.canonical_url(configured) == expected


def test_the_server_applies_the_proxy_rules_itself():
    # behind an ingress that applies none of them (one Ingress for the whole app)
    from starlette.responses import PlainTextResponse

    from ca_mcp.server import isolated

    async def upstream(scope, receive, send):
        cookie = dict(scope["headers"]).get(b"cookie", b"none").decode()
        response = PlainTextResponse(cookie)
        response.set_cookie("session", "x")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Content-Security-Policy"] = "default-src *"
        await response(scope, receive, send)

    # no lifespan: the fake upstream only speaks http
    http = TestClient(isolated(upstream))
    response = http.get("/mcp", headers={"Cookie": "token=secret"})
    assert response.text == "none"
    assert "set-cookie" not in response.headers
    assert "service-worker-allowed" not in response.headers
    assert response.headers["content-security-policy"] == "sandbox"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_the_metadata_is_served_isolated(app):
    with TestClient(app, base_url="http://localhost:8001") as http:
        response = http.get(METADATA_PATH)
    assert response.status_code == 200
    assert response.headers["content-security-policy"] == "sandbox"


@pytest.mark.parametrize(
    "backend",
    [
        _response(status_code=503),
        remote.requests.ConnectionError(),
    ],
    ids=["backend-503", "backend-unreachable"],
)
def test_a_backend_outage_is_not_a_dead_token(backend):
    # a 401 would make the app sign its user in again; a 503 makes it retry
    session = Mock()
    if isinstance(backend, Exception):
        session.get.side_effect = backend
    else:
        session.get.return_value = backend
    with (
        patch("ca_mcp.remote.requests.Session", return_value=session),
        patch.object(config, "ALLOWED_HOSTS", ["localhost:8001"]),
    ):
        app = remote.build_app()
    with TestClient(app, base_url="http://localhost:8001") as http:
        response = http.post(
            "/mcp", headers={**MCP_HEADERS, "Authorization": "Bearer t"}, json={}
        )
    client.set_transport(None)
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert response.headers["content-security-policy"] == "sandbox"
    assert response.json()["error"] == "temporarily_unavailable"


def test_a_refused_token_is_still_a_401():
    session = _session(status=401)
    with (
        patch("ca_mcp.remote.requests.Session", return_value=session),
        patch.object(config, "ALLOWED_HOSTS", ["localhost:8001"]),
    ):
        app = remote.build_app()
    with TestClient(app, base_url="http://localhost:8001") as http:
        response = http.post(
            "/mcp", headers={**MCP_HEADERS, "Authorization": "Bearer t"}, json={}
        )
    client.set_transport(None)
    assert response.status_code == 401
    assert "invalid_token" in response.headers["www-authenticate"]


@pytest.mark.parametrize("read_only", [True, False])
def test_read_only_holds_in_oauth_mode(read_only):
    from ca_mcp import server

    with (
        patch.object(config, "READ_ONLY", read_only),
        patch.object(config, "ALLOWED_HOSTS", ["localhost:8001"]),
        patch.object(server, "_register_on") as register,
    ):
        remote.build_app()
    client.set_transport(None)
    assert register.call_args.args[1] is read_only


def test_oauth_mode_is_not_read_only_by_default(monkeypatch):
    import importlib

    monkeypatch.setenv("CA_MCP_AUTH", "oauth")
    monkeypatch.delenv("CA_MCP_READ_ONLY", raising=False)
    try:
        assert importlib.reload(config).READ_ONLY is False
        monkeypatch.setenv("CA_MCP_READ_ONLY", "true")
        assert importlib.reload(config).READ_ONLY is True
    finally:
        monkeypatch.undo()
        importlib.reload(config)


@pytest.mark.parametrize(
    "public, host",
    [
        ("https://ca.example.com", "ca.example.com"),
        # a proxy that drops the public port (nginx's $host) must still pass
        ("https://ca.example.com:8443", "ca.example.com"),
        ("https://[::1]:8443", "[::1]"),
    ],
)
def test_the_default_hosts_take_the_host_with_or_without_a_port(public, host):
    from mcp.server.transport_security import (
        TransportSecurityMiddleware,
        TransportSecuritySettings,
    )

    allowed = remote.default_allowed_hosts(public)
    check = TransportSecurityMiddleware(
        TransportSecuritySettings(allowed_hosts=allowed)
    )
    for sent in (host, f"{host}:8443", f"{host}:443"):
        assert check._validate_host(sent), sent
    assert not check._validate_host("other.example.com")
    assert not check._validate_host("other.example.com:8443")
