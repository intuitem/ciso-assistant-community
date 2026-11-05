import pytest
from auditlog.models import LogEntry
from django.core.cache import cache
from django.test import override_settings
from mcp.server.auth.provider import AccessToken
from structlog.testing import capture_logs

from iam.models import Folder, User
from mcp_server import transport
from mcp_server.tool_calls import ToolCallHooks
from webhooks.ocsf import log_entry_to_ocsf, log_entry_to_raw

VIA = {"client_id": "abc", "name": "Claude Code", "profile": "Read only"}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


def _access(subject="u1", client_id="abc"):
    return AccessToken(
        token="t",
        client_id=client_id,
        scopes=["mcp:read"],
        subject=subject,
        claims={"actions": ["read"], "profile": "Read only", "app": "Claude Code"},
    )


class TestBudget:
    @override_settings(MCP_MAX_CALLS_PER_MINUTE=2)
    def test_calls_above_the_minute_limit_are_refused(self):
        hooks, access = ToolCallHooks(), _access()
        assert hooks.before("get_folders", access) is None
        assert hooks.before("get_folders", access) is None
        refused = hooks.before("get_folders", access)
        assert "more than 2 calls in a minute" in refused

    @override_settings(MCP_MAX_CALLS_PER_MINUTE=1)
    def test_each_connection_has_its_own_budget(self):
        hooks = ToolCallHooks()
        assert hooks.before("get_folders", _access(subject="u1")) is None
        assert hooks.before("get_folders", _access(subject="u2")) is None
        assert hooks.before("get_folders", _access(client_id="other")) is None

    @override_settings(MCP_MAX_RESPONSE_CHARS_PER_HOUR=100)
    def test_data_above_the_hourly_budget_is_refused(self):
        hooks, access = ToolCallHooks(), _access()
        hooks.after("get_folders", access, "x" * 60, 0.1, None)
        assert hooks.before("get_folders", access) is None
        hooks.after("get_folders", access, "x" * 60, 0.1, None)
        assert "data budget for this hour" in hooks.before("get_folders", access)

    @override_settings(MCP_MAX_RESPONSE_CHARS_PER_HOUR=100)
    def test_refusals_do_not_use_the_budget(self):
        hooks, access = ToolCallHooks(), _access()
        hooks.after("get_folders", access, "Error: " + "x" * 200, 0.0, "limited")
        assert hooks.before("get_folders", access) is None

    @override_settings(MCP_MAX_RESPONSE_CHARS_PER_HOUR=100)
    def test_tool_refusals_do_not_use_the_budget(self):
        hooks, access = ToolCallHooks(), _access()
        hooks.after("update_folder", access, "Error: " + "x" * 200, 0.0, None)
        assert hooks.before("get_folders", access) is None

    @override_settings(MCP_MAX_CALLS_PER_MINUTE=0, MCP_MAX_RESPONSE_CHARS_PER_HOUR=0)
    def test_zero_turns_the_limits_off(self):
        hooks, access = ToolCallHooks(), _access()
        for _ in range(5):
            hooks.after("get_folders", access, "x" * 1000, 0.1, None)
            assert hooks.before("get_folders", access) is None


class TestLog:
    def test_each_call_is_logged_with_user_app_and_profile(self):
        with capture_logs() as logs:
            ToolCallHooks().after("get_folders", _access(), "rows", 0.25, None)
        (entry,) = [log for log in logs if log["event"] == "mcp tool call"]
        assert entry["tool"] == "get_folders"
        assert entry["outcome"] == "ok"
        assert entry["user"] == "u1"
        assert entry["app"] == "Claude Code"
        assert entry["profile"] == "Read only"
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
    def test_outcomes(self, result, error, outcome):
        with capture_logs() as logs:
            ToolCallHooks().after("update_folder", _access(), result, 0.0, error)
        assert logs[-1]["outcome"] == outcome


@pytest.mark.django_db
class TestAudit:
    def _change_a_folder(self):
        folder = Folder.objects.create(name="Acme")
        return LogEntry.objects.get_for_object(folder).latest("timestamp")

    def test_changes_made_through_an_app_name_it(self):
        token = transport._via_app.set(VIA)
        try:
            entry = self._change_a_folder()
        finally:
            transport._via_app.reset(token)
        assert entry.additional_data["via_app"] == VIA

    def test_other_changes_are_not_tagged(self):
        entry = self._change_a_folder()
        assert "via_app" not in (entry.additional_data or {})

    def test_the_dispatch_thread_does_not_keep_the_app(self, monkeypatch):
        seen = []
        user = User.objects._create_user(
            email="u@example.com", password=None, mailing=False, initial_group=None
        )
        # _run recycles connections, which would close the test database
        monkeypatch.setattr(transport, "close_old_connections", lambda: None)
        monkeypatch.setattr(
            transport,
            "request_as",
            lambda *a, **kw: seen.append(transport._via_app.get()),
        )

        transport._run(user.pk, VIA, "GET", "/folders/", {})

        assert seen == [VIA]
        assert transport._via_app.get() is None

    def test_siem_events_carry_the_app(self):
        token = transport._via_app.set(VIA)
        try:
            entry = self._change_a_folder()
        finally:
            transport._via_app.reset(token)
        entry.actor_email = "u@example.com"
        actor = log_entry_to_ocsf(entry)["actor"]
        assert actor["app_name"] == "Claude Code"
        assert actor["app_uid"] == "abc"
        assert log_entry_to_raw(entry)["via_app"] == VIA
