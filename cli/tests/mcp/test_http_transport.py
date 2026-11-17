"""Streamable HTTP as a remote connector (ChatGPT, Copilot Studio) drives it.

Requests go through the real ASGI app from `build_http_app`: stateless, SSE-framed
responses, the PAT in a custom header with no scheme. Only the backend is mocked.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from mcp.server.mcpserver import MCPServer
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import config, server  # noqa: E402
from ca_mcp.auth import capture_headers  # noqa: E402
from tests.mcp.helpers import _response  # noqa: E402

ACCEPT = "application/json, text/event-stream"
FOLDERS = {"count": 1, "results": [{"id": "f1", "name": "Global"}]}


@pytest.fixture
def backend():
    with patch("ca_mcp.client.requests.get") as get:
        get.return_value = _response(json_data=FOLDERS)
        yield get


def _app(allowed_hosts=()):
    with (
        patch.multiple(
            config,
            IS_HTTP=True,
            READ_ONLY=True,
            HTTP_HOST="0.0.0.0",  # nosec B104 - nothing binds; asserts the host guard
            HTTP_PATH="/mcp",
            STATELESS=True,
            JSON_RESPONSE=False,
            ALLOWED_HOSTS=list(allowed_hosts),
            ALLOWED_ORIGINS=[],
        ),
        patch.object(
            server, "mcp", MCPServer("ciso-assistant", middleware=[capture_headers])
        ),
        patch.object(server, "_registered", False),
    ):
        return server.build_http_app()


@pytest.fixture
def client():
    with (
        patch.multiple(
            config, IS_HTTP=True, ALLOW_ENV_TOKEN=False, TOKEN="server-env-token"
        ),
        TestClient(_app(), base_url="http://127.0.0.1:8001") as c,
    ):
        yield c


def rpc(client, method, params=None, headers=None, rpc_id=1):
    res = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params or {}},
        headers={"Accept": ACCEPT, "Authorization": "caller-pat", **(headers or {})},
    )
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("text/event-stream")
    events = [line[5:] for line in res.text.splitlines() if line.startswith("data:")]
    return json.loads(events[-1])


def _initialize(client, version="2025-06-18", **kw):
    params = {
        "protocolVersion": version,
        "capabilities": {},
        "clientInfo": {"name": "openai-mcp", "version": "1"},
    }
    return rpc(client, "initialize", params, **kw)


@pytest.mark.parametrize("version", HANDSHAKE_PROTOCOL_VERSIONS)
def test_handshake_negotiates_every_version(client, version):
    result = _initialize(client, version)["result"]

    assert result["protocolVersion"] == version
    assert result["serverInfo"]["name"] == "ciso-assistant"


def test_read_only_tool_surface(client):
    tools = rpc(client, "tools/list")["result"]["tools"]

    assert {t["name"] for t in tools} == {fn.__name__ for fn in server.READ_TOOLS}
    assert all(t["annotations"]["readOnlyHint"] for t in tools)


@pytest.mark.parametrize(
    "header", ["caller-pat", "Token caller-pat", "Bearer caller-pat"]
)
def test_caller_token_reaches_backend(client, backend, header):
    reply = rpc(
        client,
        "tools/call",
        {"name": "get_folders", "arguments": {}},
        headers={"Authorization": header},
    )

    assert reply["result"].get("isError") is not True
    assert "Global" in reply["result"]["content"][0]["text"]
    assert backend.call_args.kwargs["headers"]["Authorization"] == "Token caller-pat"


def test_call_without_token_never_reaches_backend(client, backend):
    reply = rpc(
        client,
        "tools/call",
        {"name": "get_folders", "arguments": {}},
        headers={"Authorization": ""},
    )

    assert "No credential supplied" in reply["result"]["content"][0]["text"]
    backend.assert_not_called()


def _post_ping(client, host):
    return client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Accept": ACCEPT, "Host": host},
    )


def test_foreign_host_rejected_when_bound_to_all_interfaces(client):
    assert _post_ping(client, "evil.example").status_code == 421


def test_configured_public_host_is_accepted():
    with TestClient(_app(allowed_hosts=["grc.example.com"])) as c:
        assert _post_ping(c, "grc.example.com").status_code == 200
        assert _post_ping(c, "127.0.0.1:8001").status_code == 200
        assert _post_ping(c, "evil.example").status_code == 421
