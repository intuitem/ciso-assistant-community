"""MCP server setup and the request/response contract of the core read tools.

HTTP is mocked at `ca_mcp.client.requests.get`, so the real request building
(auth header, limit clamping) and status handling run.
"""

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import config, server  # noqa: E402
from ca_mcp.tools import read_tools  # noqa: E402
from tests.mcp.helpers import _response, run  # noqa: E402

TOOLS = [
    read_tools.get_risk_scenarios,
    read_tools.get_applied_controls,
    read_tools.get_audits_progress,
]


@pytest.fixture
def stdio_token():
    with (
        patch.object(config, "IS_HTTP", False),
        patch.object(config, "TOKEN", "test-token-123"),
    ):
        yield


@pytest.fixture
def api(stdio_token):
    with patch("ca_mcp.client.requests.get") as get:
        yield get


class TestMCPSetup:
    def test_mcp_server_initialization(self):
        assert server.mcp.name == "ciso-assistant"

    def test_mcp_environment_loading(self):
        env = {
            "TOKEN": "test-token-123",
            "API_URL": "https://api.test.com/api",
            "VERIFY_CERTIFICATE": "false",
        }
        try:
            with patch.dict(os.environ, env):
                importlib.reload(config)
                assert config.TOKEN == "test-token-123"
                assert config.API_URL == "https://api.test.com/api"
                assert config.VERIFY_CERTIFICATE is False
        finally:
            importlib.reload(config)

    def test_tool_lists_are_disjoint(self):
        assert not set(server.READ_TOOLS) & set(server.WRITE_TOOLS)


class TestMCPTools:
    def test_get_risk_scenarios_success(self, api):
        api.return_value = _response(
            json_data={
                "count": 1,
                "results": [
                    {
                        "id": "rs-1",
                        "ref_id": "R.1",
                        "name": "Test Risk 1",
                        "inherent_level": {"name": "Critical"},
                        "current_level": {"name": "High"},
                        "residual_level": {"name": "Medium"},
                        "treatment": "mitigate",
                    }
                ],
            }
        )

        result = run(read_tools.get_risk_scenarios())

        assert (
            "|UUID|Ref|Name|Inherent Level|Current Level|Residual Level|Treatment|"
            in result
        )
        assert "|rs-1|R.1|Test Risk 1|Critical|High|Medium|mitigate|" in result
        assert "[SUCCESS] get_risk_scenarios" in result

    def test_get_applied_controls_success(self, api):
        api.return_value = _response(
            json_data={
                "results": [
                    {
                        "id": "ac-1",
                        "name": "Test Control",
                        "status": "active",
                        "eta": "2024-12-31",
                        "owner": [{"id": "u-1", "str": "Alice"}],
                        "folder": {"str": "TestDomain"},
                    }
                ]
            }
        )

        result = run(read_tools.get_applied_controls())

        assert (
            "|ac-1|N/A|Test Control|active|2024-12-31|Alice|u-1|TestDomain|" in result
        )
        assert "[SUCCESS] get_applied_controls" in result

    def test_get_audits_progress_success(self, api):
        api.return_value = _response(
            json_data={
                "count": 1,
                "results": [
                    {
                        "name": "ISO 27001 Audit",
                        "framework": {"str": "ISO 27001"},
                        "status": "in_progress",
                        "progress": 75,
                        "folder": {"str": "TestDomain"},
                    }
                ],
            }
        )

        result = run(read_tools.get_audits_progress())

        assert "|Name|Framework|Status|Progress|Domain|" in result
        assert "|ISO 27001 Audit|ISO 27001|in_progress|75|TestDomain|" in result

    @pytest.mark.parametrize(
        "tool,noun",
        [
            (read_tools.get_risk_scenarios, "risk scenarios"),
            (read_tools.get_applied_controls, "applied controls"),
            (read_tools.get_audits_progress, "audits"),
        ],
    )
    def test_empty_results(self, api, tool, noun):
        api.return_value = _response(json_data={"count": 0, "results": []})

        assert run(tool()).startswith(f"[RESULT] No {noun} found.")

    def test_request_carries_token_and_clamps_limit(self, api):
        api.return_value = _response(json_data={"results": []})

        run(read_tools.get_risk_scenarios(limit=10_000))

        kwargs = api.call_args.kwargs
        assert kwargs["headers"]["Authorization"] == "Token test-token-123"
        assert kwargs["params"]["limit"] == config.MAX_TOTAL_ITEMS


class TestMCPErrorHandling:
    @pytest.mark.parametrize("tool", TOOLS)
    @pytest.mark.parametrize(
        "status,label",
        [
            (401, "[ERROR] Authentication Failed"),
            (403, "[ERROR] Permission Denied"),
            (500, "[ERROR] Server Error"),
        ],
    )
    def test_http_errors(self, api, tool, status, label):
        api.return_value = _response(status_code=status, text="boom")

        result = run(tool())

        assert result.startswith(label)
        assert "Do NOT retry" in result

    def test_transport_failure_is_reported_not_raised(self, api):
        api.side_effect = ConnectionError("connection refused")

        result = run(read_tools.get_risk_scenarios())

        assert result.startswith("[ERROR] Internal Error")
        assert "connection refused" in result
