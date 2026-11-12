"""Connection actions: every tool has one, the guard refuses tools whose action
is not granted, and the tool list hides them."""

import asyncio
import sys
from pathlib import Path

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import actions, server  # noqa: E402


def _access(granted=None, profile=None, scopes=("mcp",)):
    claims = {k: v for k, v in {"actions": granted, "profile": profile}.items() if v}
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


def test_every_tool_has_exactly_one_action():
    tools = server.READ_TOOLS + server.WRITE_TOOLS
    names = [tool.__name__ for tool in tools]
    assert len(names) == len(set(names))
    assert set(names) == set(server.TOOL_ACTIONS)


def test_writes_are_never_read():
    for tool in server.WRITE_TOOLS:
        assert server.TOOL_ACTIONS[tool.__name__] != actions.READ, tool.__name__


def test_read_is_always_granted():
    assert actions.granted_actions(_access(granted=["update"])) == {"read", "update"}
    assert actions.granted_actions(_access(granted=["approve"])) == {"read"}


def test_a_token_without_actions_may_only_read():
    assert actions.granted_actions(_access()) == {"read"}
    assert actions.granted_actions(None) == {"read"}


def test_the_guard_refuses_an_action_not_granted(connected):
    async def tool():
        return "ran"

    guarded = server._require_action(tool, {actions.CREATE})

    connected(_access(granted=["read"], profile="Read"))
    refused = asyncio.run(guarded())
    assert 'uses the "Read" profile' in refused
    assert "creating data" in refused

    connected(_access(granted=["read", "create"]))
    assert asyncio.run(guarded()) == "ran"


def test_delete_is_its_own_action(connected):
    async def tool():
        return "ran"

    name = server.delete_vulnerability.__name__
    assert server.needed_actions(name) == {actions.DELETE}
    guarded = server._require_action(tool, server.needed_actions(name))

    connected(_access(granted=["read", "create", "update"]))
    assert "deleting data" in asyncio.run(guarded())

    connected(_access(granted=["read", "delete"]))
    assert asyncio.run(guarded()) == "ran"


def test_the_ebios_sync_needs_create_and_update(connected):
    async def tool():
        return "ran"

    name = server.sync_risk_assessment_from_ebios_rm.__name__
    guarded = server._require_action(tool, server.needed_actions(name))

    connected(_access(granted=["read", "update"]))
    assert "creating data" in asyncio.run(guarded())

    connected(_access(granted=["read", "create", "update"]))
    assert asyncio.run(guarded()) == "ran"


def _tool_names(remote):
    app = server.ActionFilteredServer("test")
    server._register_on(app, read_only=False, remote=remote)
    return {tool.name for tool in app._tool_manager.list_tools()}


def test_the_oauth_server_never_offers_create_evidence(monkeypatch):
    monkeypatch.setattr(server.config, "IS_HTTP", False)
    names = _tool_names(remote=True)
    assert "create_evidence" not in names
    assert "create_applied_control" in names


def test_admin_tools_are_only_offered_locally(monkeypatch):
    monkeypatch.setattr(server.config, "IS_HTTP", False)
    admin = {"create_folder", "update_folder", "update_user"}
    assert not admin & _tool_names(remote=True)
    assert admin <= _tool_names(remote=False)


def test_the_tool_list_hides_tools_not_granted(connected):
    app = server.ActionFilteredServer("test")
    app.tool()(server.get_my_access)
    for tool in (server.CREATE_TOOLS[0], server.UPDATE_TOOLS[0]):
        app.tool()(tool)

    connected(_access(granted=["read", "update"]))
    names = {tool.name for tool in asyncio.run(app.list_tools())}

    assert names == {"get_my_access", server.UPDATE_TOOLS[0].__name__}


def test_get_my_access_says_what_is_missing(connected):
    connected(_access(granted=["read"], profile="Read"))
    text = asyncio.run(server.get_my_access())
    assert text == (
        'Profile "Read". This connection can read data in CISO Assistant. '
        "It does not allow creating, changing or deleting data."
    )

    connected(_access(granted=["read", "create", "update"]))
    text = asyncio.run(server.get_my_access())
    assert text == (
        "This connection can read, create and change data in CISO Assistant. "
        "It does not allow deleting data."
    )

    connected(_access(granted=["read", "create", "update", "delete"]))
    text = asyncio.run(server.get_my_access())
    assert text == (
        "This connection can read, create, change and delete data in CISO Assistant."
    )


def test_a_cancelled_call_is_recorded(connected):
    async def tool():
        raise asyncio.CancelledError

    hooks = _Hooks()
    connected(_access())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(server._with_hooks(tool, "get_folders", hooks)())
    assert hooks.calls == [("get_folders", None, "cancelled")]


class _Hooks:
    def __init__(self, refusal=None):
        self.refusal = refusal
        self.calls = []

    def before(self, tool, access):
        return self.refusal

    def after(self, tool, access, result, seconds, error):
        self.calls.append((tool, result, error))


def test_hooks_record_every_call(connected):
    async def tool():
        return "rows"

    hooks = _Hooks()
    connected(_access())
    assert asyncio.run(server._with_hooks(tool, "get_folders", hooks)()) == "rows"
    assert hooks.calls == [("get_folders", "rows", None)]


def test_a_hook_refusal_stops_the_call(connected):
    ran = []

    async def tool():
        ran.append(True)

    hooks = _Hooks(refusal="Error: too many calls")
    connected(_access())
    result = asyncio.run(server._with_hooks(tool, "get_folders", hooks)())
    assert result == "Error: too many calls"
    assert not ran
    assert hooks.calls == [("get_folders", "Error: too many calls", "limited")]


def test_a_failing_tool_is_recorded_then_raises(connected):
    async def tool():
        raise RuntimeError("boom")

    hooks = _Hooks()
    connected(_access())
    with pytest.raises(RuntimeError):
        asyncio.run(server._with_hooks(tool, "get_folders", hooks)())
    assert hooks.calls == [("get_folders", None, "RuntimeError")]
