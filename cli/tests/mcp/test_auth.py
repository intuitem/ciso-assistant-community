"""Per-request credentials: middleware -> worker thread -> get_request_token."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import auth, server  # noqa: E402


async def _whoami():
    return auth.get_request_token()


def _dispatch(headers):
    """Run a tool the way the server does: inside the middleware, offloaded."""
    ctx = SimpleNamespace(request=SimpleNamespace(headers=headers))

    async def call_next(_ctx):
        return await server._offload(_whoami)()

    return asyncio.run(auth.capture_headers(ctx, call_next))


@pytest.fixture
def http():
    with (
        patch.object(auth.config, "IS_HTTP", True),
        patch.object(auth.config, "ALLOW_ENV_TOKEN", False),
        patch.object(auth.config, "TOKEN", "server-env-token"),
    ):
        yield


def test_middleware_is_registered():
    assert auth.capture_headers in server.mcp.middleware


@pytest.mark.parametrize(
    "headers",
    [
        {"authorization": "Token caller-pat"},
        {"authorization": "Bearer caller-pat"},
        {"x-ciso-token": "caller-pat"},
    ],
)
def test_caller_token_reaches_worker_thread(http, headers):
    assert _dispatch(headers) == "caller-pat"


def test_http_without_credential_fails_closed(http):
    with pytest.raises(auth.MissingCredentialError):
        _dispatch({})


def test_stdio_uses_env_token():
    ctx = SimpleNamespace(request=None)

    async def call_next(_ctx):
        return await server._offload(_whoami)()

    with (
        patch.object(auth.config, "IS_HTTP", False),
        patch.object(auth.config, "TOKEN", "server-env-token"),
    ):
        assert asyncio.run(auth.capture_headers(ctx, call_next)) == "server-env-token"
