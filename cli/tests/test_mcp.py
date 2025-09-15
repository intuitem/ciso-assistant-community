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
    
    @patch.dict(os.environ, {
        'TOKEN': 'test-token-123',
        'API_URL': 'https://api.test.com',
        'VERIFY_CERTIFICATE': 'false'
    })
    def test_mcp_environment_loading(self):
        """
        Test that environment variables are loaded correctly from .mcp.env
        """
        # Reload the module to pick up new environment variables
        import importlib
        importlib.reload(ca_mcp)
        
        assert ca_mcp.TOKEN == 'test-token-123'
        assert ca_mcp.API_URL == 'https://api.test.com'
        assert ca_mcp.VERIFY_CERTIFICATE == False


class TestMCPTools:
    """Test MCP tool functions"""
    
    @pytest.fixture
    def mock_requests_success(self):
        """Mock successful API responses"""
        with patch('ca_mcp.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "name": "Test Risk 1",
                        "description": "Test description",
                        "current_level": "High",
                        "residual_level": "Medium",
                        "folder": "TestFolder"
                    }
                ]
            }
            mock_get.return_value = mock_response
            yield mock_get
    
    @pytest.fixture
    def mock_requests_empty(self):
        """Mock API responses with empty results"""
        with patch('ca_mcp.requests.get') as mock_get:
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
        with patch('ca_mcp.rprint') as mock_rprint:
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
        with patch('ca_mcp.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "name": "Test Control",
                        "description": "Control description",
                        "status": "active",
                        "eta": "2024-12-31",
                        "folder": {"str": "TestDomain"}
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
        with patch('ca_mcp.rprint') as mock_rprint:
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
        with patch('ca_mcp.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "name": "ISO 27001 Audit",
                        "framework": {"str": "ISO 27001"},
                        "status": "in_progress",
                        "progress": "75%",
                        "folder": {"str": "TestDomain"}
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
        with patch('ca_mcp.rprint') as mock_rprint:
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
        with patch('ca_mcp.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Authentication failed"}
            mock_get.return_value = mock_response
            yield mock_get
    
    @pytest.fixture
    def mock_requests_forbidden(self):
        """Mock API responses with forbidden access"""
        with patch('ca_mcp.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.json.return_value = {"detail": "Forbidden"}
            mock_get.return_value = mock_response
            yield mock_get
    
    @pytest.fixture
    def mock_requests_server_error(self):
        """Mock API responses with server error"""
        with patch('ca_mcp.requests.get') as mock_get:
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
        with patch('ca_mcp.rprint') as mock_rprint:
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
        with patch('ca_mcp.rprint') as mock_rprint:
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
        with patch('ca_mcp.rprint') as mock_rprint:
            result = await ca_mcp.get_risk_scenarios()
            assert result is None
            
            mock_rprint.assert_called_once()
            args, kwargs = mock_rprint.call_args
            assert "check credentials" in str(args[0])