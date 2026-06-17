import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

# Add the parent directory to the path to import ca_mcp
sys.path.insert(0, str(Path(__file__).parent.parent))
import ca_mcp


class TestMCPSetup:
    """Test MCP server initialization and configuration"""

    def test_mcp_server_initialization(self):
        """
        Test that MCP server initializes correctly with proper name
        """
        # The mcp server should be initialized with "ciso-assistant" name
        assert ca_mcp.mcp.name == "ciso-assistant"

    @patch.dict(
        os.environ,
        {
            "TOKEN": "test-token-123",
            "API_URL": "https://api.test.com",
            "VERIFY_CERTIFICATE": "false",
        },
    )
    def test_mcp_environment_loading(self):
        """
        Test that environment variables are loaded correctly from .mcp.env
        """
        # Reload the module to pick up new environment variables
        import importlib

        importlib.reload(ca_mcp)

        assert ca_mcp.TOKEN == "test-token-123"
        assert ca_mcp.API_URL == "https://api.test.com"
        assert ca_mcp.VERIFY_CERTIFICATE == False


class TestMCPTools:
    """Test MCP tool functions"""

    @pytest.fixture
    def mock_requests_success(self):
        """Mock successful API responses"""
        with patch("ca_mcp.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "name": "Test Risk 1",
                        "description": "Test description",
                        "current_level": "High",
                        "residual_level": "Medium",
                        "folder": "TestFolder",
                    }
                ]
            }
            mock_get.return_value = mock_response
            yield mock_get

    @pytest.fixture
    def mock_requests_empty(self):
        """Mock API responses with empty results"""
        with patch("ca_mcp.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": []}
            mock_get.return_value = mock_response
            yield mock_get

    @pytest.mark.asyncio
    async def test_get_risk_scenarios_success(self, mock_requests_success):
        """
        Test successful retrieval of risk scenarios via MCP
        """
        result = await ca_mcp.get_risk_scenarios()

        # Check that result contains markdown table format
        assert "|name|description|current_level|residual_level|domain|" in result
        assert "|---|---|---|---|---|" in result
        assert "Test Risk 1" in result
        assert "Test description" in result
        assert "High" in result
        assert "Medium" in result

    @pytest.mark.asyncio
    async def test_get_risk_scenarios_empty_results(self, mock_requests_empty):
        """
        Test handling of empty risk scenarios results
        """
        with patch("ca_mcp.rprint") as mock_rprint:
            result = await ca_mcp.get_risk_scenarios()

            # Should return None and print error message
            assert result is None
            mock_rprint.assert_called_once()
            args, kwargs = mock_rprint.call_args
            assert "No risk scenarios found" in str(args[0])

    @pytest.mark.asyncio
    async def test_get_applied_controls_success(self):
        """
        Test successful retrieval of applied controls via MCP
        """
        with patch("ca_mcp.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "name": "Test Control",
                        "description": "Control description",
                        "status": "active",
                        "eta": "2024-12-31",
                        "folder": {"str": "TestDomain"},
                    }
                ]
            }
            mock_get.return_value = mock_response

            result = await ca_mcp.get_applied_controls()

            # Check markdown table format
            assert "|name|description|status|eta|domain|" in result
            assert "|---|---|---|---|---|" in result
            assert "Test Control" in result
            assert "Control description" in result
            assert "active" in result
            assert "2024-12-31" in result
            assert "TestDomain" in result

    @pytest.mark.asyncio
    async def test_get_applied_controls_empty_results(self, mock_requests_empty):
        """
        Test handling of empty applied controls results
        """
        with patch("ca_mcp.rprint") as mock_rprint:
            result = await ca_mcp.get_applied_controls()

            assert result is None
            mock_rprint.assert_called_once()
            args, kwargs = mock_rprint.call_args
            assert "No applied controls found" in str(args[0])

    @pytest.mark.asyncio
    async def test_get_audits_progress_success(self):
        """
        Test successful retrieval of audit progress via MCP
        """
        with patch("ca_mcp.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "name": "ISO 27001 Audit",
                        "framework": {"str": "ISO 27001"},
                        "status": "in_progress",
                        "progress": "75%",
                        "folder": {"str": "TestDomain"},
                    }
                ]
            }
            mock_get.return_value = mock_response

            result = await ca_mcp.get_audits_progress()

            # Check markdown table format
            assert "|name|framework|status|progress|domain|" in result
            assert "|---|---|---|---|---|" in result
            assert "ISO 27001 Audit" in result
            assert "ISO 27001" in result
            assert "in_progress" in result
            assert "75%" in result
            assert "TestDomain" in result

    @pytest.mark.asyncio
    async def test_get_audits_progress_empty_results(self, mock_requests_empty):
        """
        Test handling of empty audits results
        """
        with patch("ca_mcp.rprint") as mock_rprint:
            result = await ca_mcp.get_audits_progress()

            assert result is None
            mock_rprint.assert_called_once()
            args, kwargs = mock_rprint.call_args
            assert "No audits found" in str(args[0])


class TestMCPErrorHandling:
    """Test error handling in MCP tools"""

    @pytest.fixture
    def mock_requests_auth_failure(self):
        """Mock API responses with authentication failure"""
        with patch("ca_mcp.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Authentication failed"}
            mock_get.return_value = mock_response
            yield mock_get

    @pytest.fixture
    def mock_requests_forbidden(self):
        """Mock API responses with forbidden access"""
        with patch("ca_mcp.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.json.return_value = {"detail": "Forbidden"}
            mock_get.return_value = mock_response
            yield mock_get

    @pytest.fixture
    def mock_requests_server_error(self):
        """Mock API responses with server error"""
        with patch("ca_mcp.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"detail": "Internal server error"}
            mock_get.return_value = mock_response
            yield mock_get

    @pytest.mark.asyncio
    async def test_mcp_tools_auth_failure(self, mock_requests_auth_failure):
        """
        Test that all MCP tools handle authentication failures uniformly
        """
        with patch("ca_mcp.rprint") as mock_rprint:
            # Test get_risk_scenarios
            result1 = await ca_mcp.get_risk_scenarios()
            assert result1 is None

            # Test get_applied_controls
            result2 = await ca_mcp.get_applied_controls()
            assert result2 is None

            # Test get_audits_progress
            result3 = await ca_mcp.get_audits_progress()
            assert result3 is None

            # All should have printed error messages about credentials
            assert mock_rprint.call_count == 3
            for call in mock_rprint.call_args_list:
                args, kwargs = call
                assert "check credentials" in str(args[0])

    @pytest.mark.asyncio
    async def test_mcp_tools_forbidden_access(self, mock_requests_forbidden):
        """
        Test handling of forbidden access errors
        """
        with patch("ca_mcp.rprint") as mock_rprint:
            result = await ca_mcp.get_risk_scenarios()
            assert result is None

            mock_rprint.assert_called_once()
            args, kwargs = mock_rprint.call_args
            assert "check credentials" in str(args[0])

    @pytest.mark.asyncio
    async def test_mcp_tools_api_error(self, mock_requests_server_error):
        """
        Test handling of API server errors
        """
        with patch("ca_mcp.rprint") as mock_rprint:
            result = await ca_mcp.get_risk_scenarios()
            assert result is None

            mock_rprint.assert_called_once()
            args, kwargs = mock_rprint.call_args
            assert "check credentials" in str(args[0])


class _MockResponse:
    def __init__(self, payload, status_code=200, text="OK"):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


class TestPolicyControlCatalogueMCP:
    def test_resolve_policy_id_returns_uuid_without_api_lookup(self):
        from ca_mcp.resolvers import resolve_policy_id

        policy_id = "11111111-1111-1111-1111-111111111111"

        assert resolve_policy_id(policy_id) == policy_id

    def test_resolve_policy_id_exact_ref_id_and_name(self, monkeypatch):
        from ca_mcp import resolvers

        policies = [
            {"id": "policy-a", "name": "Policy A", "ref_id": "POL-A"},
            {"id": "policy-b", "name": "Policy B", "ref_id": "POL-B"},
        ]

        def fake_fetch_all_results(endpoint, params=None):
            assert endpoint == "/policies/"
            assert params == {"search": "POL-A"}
            return policies, None

        monkeypatch.setattr(resolvers, "fetch_all_results", fake_fetch_all_results)

        assert resolvers.resolve_policy_id("POL-A") == "policy-a"

        def fake_fetch_all_results_by_name(endpoint, params=None):
            assert endpoint == "/policies/"
            assert params == {"search": "Policy B"}
            return policies, None

        monkeypatch.setattr(
            resolvers, "fetch_all_results", fake_fetch_all_results_by_name
        )

        assert resolvers.resolve_policy_id("Policy B") == "policy-b"

    def test_resolve_policy_id_rejects_ambiguity(self, monkeypatch):
        from ca_mcp import resolvers

        def fake_fetch_all_results(endpoint, params=None):
            return [
                {"id": "policy-a", "name": "Policy", "ref_id": "POL"},
                {"id": "policy-b", "name": "Policy", "ref_id": "POL"},
            ], None

        monkeypatch.setattr(resolvers, "fetch_all_results", fake_fetch_all_results)

        with pytest.raises(ValueError, match="Ambiguous policy"):
            resolvers.resolve_policy_id("POL")

    @pytest.mark.asyncio
    async def test_get_policy_control_catalogue_passes_bounded_request_params(
        self, monkeypatch
    ):
        from ca_mcp import resolvers
        from ca_mcp.tools import read_tools

        calls = []

        monkeypatch.setattr(resolvers, "resolve_policy_id", lambda policy: "policy-id")
        monkeypatch.setattr(
            read_tools,
            "fetch_all_results",
            lambda *args, **kwargs: pytest.fail("should not fetch all pages"),
        )

        def fake_make_get_request(endpoint, params=None):
            calls.append((endpoint, params))
            return _MockResponse(
                {
                    "count": 10,
                    "next": (
                        "https://example.test/api/policies/policy-id/"
                        "control-catalogue/?offset=2"
                    ),
                    "results": [
                        {
                            "id": "ctrl-a",
                            "ref_id": "CTRL-A",
                            "name": "Alpha Control",
                            "status": "active",
                            "category": "Technical",
                            "csf_function": "Identify",
                            "owner": [{"str": "Owner A"}],
                            "folder": {"str": "Domain A"},
                            "eta": "2026-01-01",
                        },
                        {
                            "id": "ctrl-b",
                            "ref_id": "CTRL-B",
                            "name": "Beta Control",
                            "status": "to_do",
                            "category": "Process",
                            "csf_function": "Protect",
                            "owner": [],
                            "folder": {"str": "Domain A"},
                            "eta": None,
                        },
                    ],
                }
            )

        monkeypatch.setattr(read_tools, "make_get_request", fake_make_get_request)

        result = await read_tools.get_policy_control_catalogue(
            "POL-A", search="control", ordering="-ref_id", limit=2
        )

        assert calls == [
            (
                "/policies/policy-id/control-catalogue/",
                {"limit": 2, "search": "control", "ordering": "-ref_id"},
            )
        ]
        assert (
            "|UUID|Ref|Name|Status|Category|CSF Function|Owner|Domain|ETA|"
            in result
        )
        assert "CTRL-A" in result
        assert "CTRL-B" in result
        assert "Found 10 policy control catalogue rows" in result
        assert "showing first 2" in result

    @pytest.mark.asyncio
    async def test_get_policy_control_catalogue_caps_limit(self, monkeypatch):
        from ca_mcp import resolvers
        from ca_mcp.tools import read_tools

        calls = []

        monkeypatch.setattr(resolvers, "resolve_policy_id", lambda policy: "policy-id")

        def fake_make_get_request(endpoint, params=None):
            calls.append((endpoint, params))
            return _MockResponse(
                {
                    "count": 1,
                    "results": [
                        {
                            "id": "ctrl-a",
                            "ref_id": "CTRL-A",
                            "name": "Alpha Control",
                            "folder": {"str": "Domain A"},
                        }
                    ],
                }
            )

        monkeypatch.setattr(read_tools, "make_get_request", fake_make_get_request)

        await read_tools.get_policy_control_catalogue("POL-A", limit=999)

        assert calls == [("/policies/policy-id/control-catalogue/", {"limit": 500})]
