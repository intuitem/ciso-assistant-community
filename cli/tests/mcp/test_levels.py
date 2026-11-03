"""Connection levels: every tool has one, the guard refuses tools above it, and
the tool list hides them."""

import asyncio
import sys
from pathlib import Path

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import levels, server  # noqa: E402


def _access(level=None, profile=None, scopes=("mcp:read",)):
    claims = {k: v for k, v in {"level": level, "profile": profile}.items() if v}
    return AccessToken(
        token="t", client_id="c", scopes=list(scopes), claims=claims or None
    )


@pytest.fixture
def connected():
    tokens = []

    def connect(access):
        tokens.append(auth_context_var.set(AuthenticatedUser(access)))

    yield connect
    for token in reversed(tokens):
        auth_context_var.reset(token)


def test_every_tool_has_exactly_one_level():
    tools = server.READ_TOOLS + server.WRITE_TOOLS
    names = [tool.__name__ for tool in tools]
    assert len(names) == len(set(names))
    assert set(names) == set(server.TOOL_LEVELS)


def test_writes_are_never_read_level():
    for tool in server.WRITE_TOOLS:
        assert server.TOOL_LEVELS[tool.__name__] != levels.READ, tool.__name__


def test_a_token_without_level_falls_back_to_its_scopes():
    assert levels.granted_level(_access()) == levels.READ
    assert (
        levels.granted_level(_access(scopes=("mcp:read", "mcp:write"))) == levels.UPDATE
    )
    assert levels.granted_level(None) == levels.READ


def test_the_guard_refuses_above_the_level(connected):
    async def tool():
        return "ran"

    guarded = server._require_level(tool, levels.UPDATE)

    connected(_access(level=levels.CREATE, profile="Vendor helper"))
    refused = asyncio.run(guarded())
    assert 'uses the "Vendor helper" profile' in refused
    assert "changing or deleting data" in refused

    connected(_access(level=levels.UPDATE))
    assert asyncio.run(guarded()) == "ran"


def test_the_tool_list_hides_tools_above_the_level(connected):
    app = server.LevelFilteredServer("test")
    app.tool()(server.get_my_access)
    for tool in (server.CREATE_TOOLS[0], server.UPDATE_TOOLS[0]):
        app.tool()(tool)

    connected(_access(level=levels.CREATE))
    names = {tool.name for tool in asyncio.run(app.list_tools())}

    assert names == {"get_my_access", server.CREATE_TOOLS[0].__name__}


def test_get_my_access_says_what_is_missing(connected):
    connected(_access(level=levels.READ, profile="Read only"))
    text = asyncio.run(server.get_my_access())
    assert text.startswith('Profile "Read only" (read).')
    assert "does not allow creating data" in text
