import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pandas as pd
from click.testing import CliRunner
import sys


# Add the parent directory to sys.path to import clica
sys.path.insert(0, str(Path(__file__).parent.parent))
from clica import (
    TOKEN,
    API_URL,
    VERIFY_CERTIFICATE,
    cli,
    get_folders,
    get_perimeters,
    get_matrices,
    import_risk_assessment,
    import_assets,
    import_controls,
    import_evidences,
    upload_attachment,
    ids_map,
    batch_create,
    get_unique_parsed_values,
    _get_folders
)


class TestAuthentication:
    """Test suite for authentication-related functionality"""
    
    def test_token_validation_success(self, mock_requests_success, mock_token, auth_headers):
        """
        Purpose: Verifies that authentication works with a valid token.
        Input: TOKEN in .env
        Output: API call succeeds
        Assertions: status_code == 200
        """
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"folders": {"test": 1}}
                mock_get.return_value = mock_response
                
                result = ids_map("folders")
                
                # Check that the API call was made with the correct headers
                mock_get.assert_called_once_with(
                    f"{API_URL}/folders/ids/",
                    headers={"Authorization": f"Token {mock_token}"},
                    verify=VERIFY_CERTIFICATE
                )
                assert result == {"folders": {"test": 1}}
    
    def test_token_none_failure(self, capsys):
        """
        Objective: Check the management of the None token 
        Input: TOKEN = None 
        Output: Error message + sys.exit(1) 
        Assertions: "No authentication token" in captured_output
        """
        with patch('clica.TOKEN', None):
            with pytest.raises(SystemExit) as exc_info:
                ids_map("folders")
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No authentication token available" in captured.err
    
    def test_api_url_configuration(self, mock_token):
        """
        Purpose: Verifies that the API URL is correctly configured
        Input: Various API_URL values
        Output: Correctly formatted URLs in requests
        Assertions: Constructed URL == expected
        """
        test_cases = [
            ("http://localhost:8000/api", "folders", "http://localhost:8000/api/folders/ids/"),
            ("https://ciso.example.com/api", "perimeters", "https://ciso.example.com/api/perimeters/ids/"),
            ("http://192.168.1.100:8080/api", "risk-matrices", "http://192.168.1.100:8080/api/risk-matrices/ids/"),
        ]
        
        for api_url, model, expected_url in test_cases:
            with patch('clica.API_URL', api_url):
                with patch('clica.TOKEN', mock_token):
                    with patch('requests.get') as mock_get:
                        mock_response = MagicMock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = {"test": "data"}
                        mock_get.return_value = mock_response
                        
                        ids_map(model)
                        
                        # Check that the constructed URL is correct
                        mock_get.assert_called_once_with(
                            expected_url,
                            headers={"Authorization": f"Token {mock_token}"},
                            verify=VERIFY_CERTIFICATE
                        )
    
    def test_authentication_failure_401(self, mock_token, capsys):
        """
        Objective: Test management of auth 401 error 
        Input: Mock API response 401 
        Output: Error message + exit 
        Assertions: "check authentication" in output
        """
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_get.return_value = mock_response
                
                with pytest.raises(SystemExit) as exc_info:
                    ids_map("folders")
                
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "check authentication" in captured.out
    
    def test_authentication_failure_403(self, mock_token, capsys):
        """
        Objective: Test management of auth 403 error 
        Input: Mock API response 403 
        Output: Error message + exit 
        Assertions: "check authentication" in output
        """
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 403
                mock_get.return_value = mock_response
                
                with pytest.raises(SystemExit) as exc_info:
                    ids_map("folders")
                
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "check authentication" in captured.out
    
    def test_verify_certificate_configuration(self, mock_token):
        """
        Purpose: Verifies that the VERIFY_CERTIFICATE configuration is met.
        Input: Various VERIFY_CERTIFICATE values.
        Output: Verify parameter correctly passed to requests.
        Assertions: verify parameter == expected.
        """
        test_cases = [
            (True, True),
            (False, False),
        ]
        
        for verify_value, expected in test_cases:
            with patch('clica.VERIFY_CERTIFICATE', verify_value):
                with patch('clica.TOKEN', mock_token):
                    with patch('requests.get') as mock_get:
                        mock_response = MagicMock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = {}
                        mock_get.return_value = mock_response
                        
                        ids_map("folders")
                        
                        call_args = mock_get.call_args
                        assert call_args[1]['verify'] == expected
    
    def test_get_folders_authentication_success(self, mock_token):
        """
        Purpose: Verifies that the VERIFY_CERTIFICATE configuration is met.
        Input: Various VERIFY_CERTIFICATE values.
        Output: Verify parameter correctly passed to requests.
        Assertions: verify parameter == expected.
        """
        mock_folders_response = {
            "results": [
                {"id": 1, "name": "Global", "content_type": "GLOBAL"},
                {"id": 2, "name": "Project1", "content_type": "DOMAIN"}
            ]
        }
        
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_folders_response
                mock_get.return_value = mock_response
                
                global_id, folders = _get_folders()
                
                assert global_id == 1
                assert len(folders) == 2
                assert folders[0]["name"] == "Global"
                assert folders[0]["content_type"] == "GLOBAL"
    
    def test_get_folders_authentication_failure(self, capsys):
        """
        Purpose: Verifies that the VERIFY_CERTIFICATE configuration is met.
        Input: Various VERIFY_CERTIFICATE values.
        Output: Verify parameter correctly passed to requests.
        Assertions: verify parameter == expected.
        """
        with patch('clica.TOKEN', ''):
            with pytest.raises(SystemExit) as exc_info:
                _get_folders()
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No authentication token available" in captured.err


class TestQueryCommands:
    """Test suite for query commands (get_folders, get_perimeters, get_matrices)"""
    
    def test_get_folders_success(self, mock_token):
        """
        Test successful retrieval of folders
        Input: Mock API response with valid folders
        Output: JSON of folders
        Assertions: JSON contains mocked folders, correct format
        """
        mock_folders_response = {
            "results": [
                {"id": 1, "name": "Global", "content_type": "GLOBAL"},
                {"id": 2, "name": "Project1", "content_type": "DOMAIN"},
                {"id": 3, "name": "BU 1", "content_type": "DOMAIN"}
            ]
        }
        
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"folders": {"Global": 1, "Project1": 2, "BU 1": 3}}
                mock_get.return_value = mock_response
                
                runner = CliRunner()
                result = runner.invoke(get_folders)
                
                assert result.exit_code == 0
                output_data = json.loads(result.output)
                assert "folders" in output_data
                assert output_data["folders"]["Global"] == 1
                assert output_data["folders"]["Project1"] == 2
                mock_get.assert_called_once_with(
                    f"{API_URL}/folders/ids/",
                    headers={"Authorization": f"Token {mock_token}"},
                    verify=VERIFY_CERTIFICATE
                )
    
    def test_get_perimeters_success(self, mock_token):
        """
        Test successful retrieval of perimeters
        Input: Mock API response with perimeters
        Output: JSON of perimeters
        Assertions: JSON contains mocked perimeters
        """
        mock_perimeters_data = {
            "Global": {"Orion": 1, "Alpha": 2},
            "Project1": {"Beta": 3}
        }
        
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_perimeters_data
                mock_get.return_value = mock_response
                
                runner = CliRunner()
                result = runner.invoke(get_perimeters)
                
                assert result.exit_code == 0
                output_data = json.loads(result.output)
                assert "Global" in output_data
                assert output_data["Global"]["Orion"] == 1
                assert output_data["Project1"]["Beta"] == 3
                mock_get.assert_called_once_with(
                    f"{API_URL}/perimeters/ids/",
                    headers={"Authorization": f"Token {mock_token}"},
                    verify=VERIFY_CERTIFICATE
                )
    
    def test_get_matrices_success(self, mock_token):
        """
        Test successful retrieval of matrices from Global folder
        Input: Mock API response with matrices
        Output: JSON of matrices
        Assertions: Only Global matrices are returned
        """
        mock_matrices_data = {
            "4x4 risk matrix": 1,
            "EBIOS-RM matrix": 2,
            "Custom matrix": 3
        }
        
        with patch('clica.TOKEN', mock_token):
            with patch('clica.ids_map', return_value=mock_matrices_data):
                runner = CliRunner()
                result = runner.invoke(get_matrices)

                assert result.exit_code == 0
                output_data = json.loads(result.output)
                assert "4x4 risk matrix" in output_data
    
    def test_get_folders_empty_response(self, mock_token):
        """
        Test get_folders with empty API response
        Input: Mock API response with empty results
        Output: Empty JSON object
        Assertions: Command succeeds but returns empty data
        """
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {}
                mock_get.return_value = mock_response
                
                runner = CliRunner()
                result = runner.invoke(get_folders)
                
                assert result.exit_code == 0
                output_data = json.loads(result.output)
                assert output_data == {}
    
    def test_get_perimeters_empty_response(self, mock_token):
        """
        Test get_perimeters with empty API response
        Input: Mock API response with empty results
        Output: Empty JSON object
        Assertions: Command succeeds but returns empty data
        """
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {}
                mock_get.return_value = mock_response
                
                runner = CliRunner()
                result = runner.invoke(get_perimeters)
                
                assert result.exit_code == 0
                output_data = json.loads(result.output)
                assert output_data == {}
    
    def test_get_matrices_empty_response(self, mock_token):
        """
        Test get_matrices with empty Global folder
        Input: Mock API response with empty Global folder
        Output: None (empty response)
        Assertions: Command succeeds but returns empty data
        """
        with patch('clica.TOKEN', mock_token):
            with patch('clica.ids_map', return_value={}):
                runner = CliRunner()
                result = runner.invoke(get_matrices)

                assert result.exit_code == 0
                output_data = json.loads(result.output)
                assert output_data == {}
    
    def test_query_commands_auth_failure_401(self, mock_token, capsys):
        """
        Test auth failure (401) for all query commands
        Input: Mock API response 401
        Output: Error message + exit
        Assertions: "check authentication" in output
        """
        commands_to_test = [get_folders, get_perimeters, get_matrices]
        
        for command in commands_to_test:
            with patch('clica.TOKEN', mock_token):
                with patch('requests.get') as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = 401
                    mock_get.return_value = mock_response
                    
                    runner = CliRunner()
                    result = runner.invoke(command)
                    
                    assert result.exit_code == 1
                    # Check if error message is in stdout or stderr
                    assert "check authentication" in result.output
    
    def test_query_commands_auth_failure_403(self, mock_token, capsys):
        """
        Test auth failure (403) for all query commands
        Input: Mock API response 403
        Output: Error message + exit
        Assertions: "check authentication" in output
        """
        commands_to_test = [get_folders, get_perimeters, get_matrices]
        
        for command in commands_to_test:
            with patch('clica.TOKEN', mock_token):
                with patch('requests.get') as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = 403
                    mock_get.return_value = mock_response
                    
                    runner = CliRunner()
                    result = runner.invoke(command)
                    
                    assert result.exit_code == 1
                    assert "check authentication" in result.output
    
    def test_query_commands_server_error_500(self, mock_token):
        """
        Test server error (500) handling for query commands
        Input: Mock API response 500
        Output: Error message + exit
        Assertions: Commands handle server errors gracefully
        """
        commands_to_test = [get_folders, get_perimeters, get_matrices]
        
        for command in commands_to_test:
            with patch('clica.TOKEN', mock_token):
                with patch('requests.get') as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = 500
                    mock_get.return_value = mock_response
                    
                    runner = CliRunner()
                    result = runner.invoke(command)
                    
                    assert result.exit_code == 1
                    assert "check authentication" in result.output
    
    def test_query_commands_no_token(self):
        """
        Test query commands without authentication token
        Input: Empty TOKEN
        Output: Error message about missing token
        Assertions: All commands fail with appropriate error message
        """
        commands_to_test = [get_folders, get_perimeters, get_matrices]
        
        for command in commands_to_test:
            with patch('clica.TOKEN', ''):
                runner = CliRunner()
                result = runner.invoke(command)
                
                assert result.exit_code == 1
                assert "No authentication token available" in result.output
    
    def test_get_folders_json_output_format(self, mock_token):
        """
        Test that get_folders outputs valid JSON
        Input: Mock API response with folders
        Output: Valid JSON format
        Assertions: Output is valid JSON and can be parsed
        """
        mock_data = {"folders": {"Global": 1, "Test": 2}}
        
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_data
                mock_get.return_value = mock_response
                
                runner = CliRunner()
                result = runner.invoke(get_folders)
                
                assert result.exit_code == 0
                # Test that output is valid JSON
                try:
                    parsed_json = json.loads(result.output)
                    assert isinstance(parsed_json, dict)
                    assert parsed_json == mock_data
                except json.JSONDecodeError:
                    pytest.fail("Output is not valid JSON")
    
    def test_get_perimeters_json_output_format(self, mock_token):
        """
        Test that get_perimeters outputs valid JSON
        Input: Mock API response with perimeters
        Output: Valid JSON format
        Assertions: Output is valid JSON and can be parsed
        """
        mock_data = {"Global": {"Orion": 1}, "Project1": {"Alpha": 2}}
        
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_data
                mock_get.return_value = mock_response
                
                runner = CliRunner()
                result = runner.invoke(get_perimeters)
                
                assert result.exit_code == 0
                # Test that output is valid JSON
                try:
                    parsed_json = json.loads(result.output)
                    assert isinstance(parsed_json, dict)
                    assert parsed_json == mock_data
                except json.JSONDecodeError:
                    pytest.fail("Output is not valid JSON")
    
    def test_get_matrices_json_output_format(self, mock_token):
        """
        Test that get_matrices outputs valid JSON
        Input: Mock API response with matrices
        Output: Valid JSON format
        Assertions: Output is valid JSON and can be parsed
        """
        mock_data = {"4x4 matrix": 1, "EBIOS matrix": 2}
        
        with patch('clica.TOKEN', mock_token):
            with patch('clica.ids_map', return_value=mock_data):
                runner = CliRunner()
                result = runner.invoke(get_matrices)
                
                assert result.exit_code == 0
                # Test that output is valid JSON
                try:
                    parsed_json = json.loads(result.output)
                    assert isinstance(parsed_json, dict)
                    assert parsed_json == mock_data
                except json.JSONDecodeError:
                    pytest.fail("Output is not valid JSON")

                   

class TestUtilityFunctions:
    """Test utility functions used across the CLI"""
    
    @patch('clica.requests.get')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_ids_map_success(self, mock_get):
        """Test ids_map with successful API response"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Folder1": {"item1": 1, "item2": 2},
            "Folder2": {"item3": 3, "item4": 4}
        }
        mock_get.return_value = mock_response
        
        # Test without folder filter
        result = ids_map("folders")
        
        expected_result = {
            "Folder1": {"item1": 1, "item2": 2},
            "Folder2": {"item3": 3, "item4": 4}
        }
        assert result == expected_result
        mock_get.assert_called_once_with(
            f"{API_URL}/folders/ids/",
            headers={"Authorization": "Token test-token-12345"},
            verify=VERIFY_CERTIFICATE
        )

    @patch('clica.requests.get')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_ids_map_with_folder_filter(self, mock_get):
        """Test ids_map with folder filter"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "TestFolder": {"perimeter1": 1, "perimeter2": 2},
            "OtherFolder": {"perimeter3": 3}
        }
        mock_get.return_value = mock_response
        
        # Test with folder filter
        result = ids_map("perimeters", folder="TestFolder")
        
        expected_result = {"perimeter1": 1, "perimeter2": 2}
        assert result == expected_result
        mock_get.assert_called_once_with(
            f"{API_URL}/perimeters/ids/",
            headers={"Authorization": "Token test-token-12345"},
            verify=VERIFY_CERTIFICATE
        )

    @patch('clica.requests.get')
    @patch('clica.TOKEN', 'invalid-token')
    def test_ids_map_auth_failure(self, mock_get):
        """Test ids_map handles authentication failure"""
        # Mock API response with auth error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        with pytest.raises(SystemExit) as exc_info:
            with patch('sys.stderr'):
                ids_map("folders")
        assert exc_info.value.code == 1

    def test_get_unique_parsed_values(self):
        """Test parsing unique values from DataFrame column"""
        # Create test DataFrame
        df = pd.DataFrame({
            'test_column': [
                'value1,value2,value3',
                'value2,value4',
                'value1,value5',
                None,  # Test NaN handling
                'value6'
            ]
        })
        
        result = get_unique_parsed_values(df, 'test_column')
        
        expected_result = {'value1', 'value2', 'value3', 'value4', 'value5', 'value6'}
        assert result == expected_result

    def test_get_unique_parsed_values_empty_column(self):
        """Test get_unique_parsed_values with empty or non-existent column"""
        df = pd.DataFrame({'other_column': ['value1', 'value2']})
        
        # Test with non-existent column
        with pytest.raises(KeyError):
            get_unique_parsed_values(df, 'non_existent_column')
        
        # Test with empty DataFrame
        empty_df = pd.DataFrame({'test_column': []})
        result = get_unique_parsed_values(empty_df, 'test_column')
        assert result == set()

    def test_get_unique_parsed_values_whitespace_handling(self):
        """Test that whitespace is properly handled in parsed values"""
        df = pd.DataFrame({
            'test_column': [
                'value1, value2 , value3',
                ' value4,value5 ',
            ]
        })
        
        result = get_unique_parsed_values(df, 'test_column')
        
        # All values should be stripped of whitespace
        expected_result = {'value1', 'value2', 'value3', 'value4', 'value5'}
        assert result == expected_result

    @patch('clica.requests.post')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_batch_create_success(self, mock_post):
        """Test successful batch creation of objects"""
        # Mock successful API responses
        mock_responses = [
            MagicMock(status_code=201, json=lambda: {"id": 1}),
            MagicMock(status_code=201, json=lambda: {"id": 2}),
            MagicMock(status_code=201, json=lambda: {"id": 3})
        ]
        mock_post.side_effect = mock_responses
        
        items = ["asset1", "asset2", "asset3"]
        folder_id = 10
        
        result = batch_create("assets", items, folder_id)
        
        expected_result = {"asset1": 1, "asset2": 2, "asset3": 3}
        assert result == expected_result
        
        # Verify all API calls were made correctly
        assert mock_post.call_count == 3
        for i, item in enumerate(items):
            call_args = mock_post.call_args_list[i]
            assert call_args[1]['json'] == {
                "folder": folder_id,
                "name": item
            }
            assert call_args[1]['headers'] == {"Authorization": "Token test-token-12345"}

    @patch('clica.requests.post')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_batch_create_partial_failure(self, mock_post):
        """Test batch_create when some creations fail"""
        # Mock mixed success/failure responses
        mock_responses = [
            MagicMock(status_code=201, json=lambda: {"id": 1}),
            MagicMock(status_code=400, json=lambda: {"error": "Bad request"}),
            MagicMock(status_code=201, json=lambda: {"id": 3})
        ]
        mock_post.side_effect = mock_responses
        
        items = ["asset1", "asset2", "asset3"]
        folder_id = 10
        
        with patch('sys.stdout'):  # Suppress print output
            result = batch_create("assets", items, folder_id)
        
        # Only successful creations should be in result
        expected_result = {"asset1": 1, "asset3": 3}
        assert result == expected_result

    @patch('clica.requests.post')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_batch_create_empty_items(self, mock_post):
        """Test batch_create with empty items list"""
        result = batch_create("assets", [], 1)
        
        assert result == {}
        mock_post.assert_not_called()



class TestImportRiskAssessment:
    
    @pytest.fixture
    def sample_csv_content(self):
        """Sample CSV content for risk assessment tests"""
        return """ref_id;assets;threats;name;description;existing_controls;current_impact;current_proba;current_risk;additional_controls;residual_impact;residual_proba;residual_risk;treatment
                R.1;asset1,asset2;threat1,threat2;Test Risk 1;Test description;control1,control2;Significant;Likely;Low;control3;Critical;Very likely;High;open
                R.2;asset3;threat3;Test Risk 2;Another description;control4;Important;Unlikely;Medium;control5;Significant;Likely;High;mitigate"""
    
    @pytest.fixture
    def sample_matrix_definition(self):
        """Sample matrix definition for risk assessment tests"""
        return {
            "impact": [
                {"id": 1, "name": "Important"},
                {"id": 2, "name": "Significant"}, 
                {"id": 3, "name": "Critical"}
            ],
            "probability": [
                {"id": 1, "name": "Unlikely"},
                {"id": 2, "name": "Likely"},
                {"id": 3, "name": "Very likely"}
            ]
        }
    
    @pytest.fixture
    def mock_ids_responses(self):
        """Mock responses for IDs mapping"""
        return {
            "folders": {"Test Folder": 1},
            "perimeters": {"Test Perimeter": 2},
            "risk-matrices": {"Test Matrix": 3},
            "threats": {"threat1": 10, "threat2": 11, "threat3": 12},
            "assets": {"asset1": 20, "asset2": 21, "asset3": 22},
            "applied-controls": {
                "control1": 30, "control2": 31, "control3": 32,
                "control4": 33, "control5": 34
            }
        }

    def test_import_risk_assessment_complete_workflow(self, sample_csv_content, sample_matrix_definition, mock_ids_responses):
        """
        Test complete risk assessment import workflow with create_all=True
        """
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_content)
            csv_file = f.name
        
        try:
            with patch('clica.TOKEN', 'test-token'), \
                 patch('clica.requests.get') as mock_get, \
                 patch('clica.requests.post') as mock_post, \
                 patch('clica.ids_map') as mock_ids_map, \
                 patch('clica.batch_create') as mock_batch_create:
                
                # Setup mock responses for ids_map calls
                def ids_map_side_effect(model, folder=None):
                    if folder == "Global":
                        return mock_ids_responses.get("risk-matrices", {})
                    elif folder == "Test Folder":
                        return mock_ids_responses.get(model, {})
                    return mock_ids_responses.get(model, {})
                
                mock_ids_map.side_effect = ids_map_side_effect
                
                # Mock matrix definition response
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "json_definition": json.dumps(sample_matrix_definition)
                }
                
                # Mock risk assessment creation
                mock_post.return_value.status_code = 201
                mock_post.return_value.json.return_value = {"id": 100}
                
                # Mock batch_create responses
                mock_batch_create.return_value = {"item1": 1, "item2": 2}
                
                result = runner.invoke(import_risk_assessment, [
                    '--file', csv_file,
                    '--folder', 'Test Folder',
                    '--perimeter', 'Test Perimeter', 
                    '--matrix', 'Test Matrix',
                    '--name', 'Test RA',
                    '--create_all'
                ])
                
                # Verify risk assessment was created
                assert result.exit_code == 0
                assert mock_post.call_count >= 1  # At least one POST for RA creation
                
                # Verify matrix definition was fetched
                mock_get.assert_called_with(
                    f"{API_URL}/risk-matrices/3",
                    headers={"Authorization": "Token test-token"}
                )
                
        finally:
            os.unlink(csv_file)



    def test_import_risk_assessment_invalid_csv(self):
        """
        Test with malformed CSV file
        """
        runner = CliRunner()
        
        # Create invalid CSV (missing required columns)
        invalid_csv = """ref_id;name
R.1;Test Risk"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(invalid_csv)
            csv_file = f.name
        
        try:
            with patch('clica.TOKEN', 'test-token'):
                result = runner.invoke(import_risk_assessment, [
                    '--file', csv_file,
                    '--folder', 'Test Folder',
                    '--perimeter', 'Test Perimeter',
                    '--matrix', 'Test Matrix',
                    '--name', 'Test RA'
                ])
                
                # Should handle pandas errors gracefully
                assert result.exit_code != 0 or "error" in result.output.lower()
                
        finally:
            os.unlink(csv_file)

    def test_import_risk_assessment_matrix_mismatch(self, sample_csv_content, mock_ids_responses):
        """
        Test with matrix labels that don't match CSV values
        """
        runner = CliRunner()
        
        # Matrix with different labels than CSV
        mismatched_matrix = {
            "impact": [
                {"id": 1, "name": "Low"},
                {"id": 2, "name": "Medium"},
                {"id": 3, "name": "High"}
            ],
            "probability": [
                {"id": 1, "name": "Rare"},
                {"id": 2, "name": "Possible"},
                {"id": 3, "name": "Certain"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_content)
            csv_file = f.name
        
        try:
            with patch('clica.TOKEN', 'test-token'), \
                 patch('clica.requests.get') as mock_get, \
                 patch('clica.requests.post') as mock_post, \
                 patch('clica.ids_map') as mock_ids_map, \
                 patch('builtins.print') as mock_print:
                
                # Setup mock responses
                def ids_map_side_effect(model, folder=None):
                    if folder == "Global":
                        return mock_ids_responses.get("risk-matrices", {})
                    elif folder == "Test Folder":
                        return mock_ids_responses.get(model, {})
                    return mock_ids_responses.get(model, {})
                
                mock_ids_map.side_effect = ids_map_side_effect
                
                # Mock matrix definition response with mismatched labels
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "json_definition": json.dumps(mismatched_matrix)
                }
                
                # Mock risk assessment creation
                mock_post.return_value.status_code = 201
                mock_post.return_value.json.return_value = {"id": 100}
                
                result = runner.invoke(import_risk_assessment, [
                    '--file', csv_file,
                    '--folder', 'Test Folder',
                    '--perimeter', 'Test Perimeter',
                    '--matrix', 'Test Matrix',
                    '--name', 'Test RA'
                ])
                
                # Verify matrix mismatch error was printed
                mock_print.assert_any_call("Matrix doesn't match the labels used on your input file")
                
        finally:
            os.unlink(csv_file)

    def test_import_risk_assessment_auth_failure(self, sample_csv_content):
        """
        Test authentication failure during risk assessment import
        """
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_content)
            csv_file = f.name
        
        try:
            with patch('clica.TOKEN', ''), \
                 patch('builtins.print') as mock_print:
                
                result = runner.invoke(import_risk_assessment, [
                    '--file', csv_file,
                    '--folder', 'Test Folder',
                    '--perimeter', 'Test Perimeter',
                    '--matrix', 'Test Matrix',
                    '--name', 'Test RA'
                ])
                
                # Should exit with authentication error
                assert result.exit_code == 1
                mock_print.assert_any_call(
                    "No authentication token available. Please set PAT token in .clica.env.",
                    file=mock_print.call_args.kwargs.get('file')
                )
                
        finally:
            os.unlink(csv_file)

    def test_import_risk_assessment_missing_file(self):
        """
        Test with non-existent CSV file
        """
        runner = CliRunner()
        
        with patch('clica.TOKEN', 'test-token'):
            result = runner.invoke(import_risk_assessment, [
                '--file', 'non_existent_file.csv',
                '--folder', 'Test Folder',
                '--perimeter', 'Test Perimeter',
                '--matrix', 'Test Matrix',
                '--name', 'Test RA'
            ])
            
            # Should handle file not found error
            assert result.exit_code != 0
            assert isinstance(result.exception, FileNotFoundError)

    def test_import_risk_assessment_api_error(self, sample_csv_content, mock_ids_responses):
        """
        Test API error during risk assessment creation
        """
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_content)
            csv_file = f.name
        
        try:
            with patch('clica.TOKEN', 'test-token'), \
                 patch('clica.requests.post') as mock_post, \
                 patch('clica.ids_map') as mock_ids_map, \
                 patch('builtins.print') as mock_print:
                
                # Setup mock responses
                mock_ids_map.return_value = mock_ids_responses.get("folders", {})
                
                # Mock API error response
                mock_post.return_value.status_code = 400
                mock_post.return_value.json.return_value = {"error": "Bad request"}
                
                result = runner.invoke(import_risk_assessment, [
                    '--file', csv_file,
                    '--folder', 'Test Folder',
                    '--perimeter', 'Test Perimeter',
                    '--matrix', 'Test Matrix',
                    '--name', 'Test RA'
                ])
                
                # Should handle API error gracefully
                mock_print.assert_any_call("something went wrong.")
                
        finally:
            os.unlink(csv_file)


class TestImportAssets:
    """Tests for import_assets command"""
    
    @patch('clica.requests.post')
    @patch('clica._get_folders')
    @patch('pandas.read_csv')
    @patch('click.confirm')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_import_assets_success(self, mock_confirm, mock_read_csv, mock_get_folders, mock_post):
        print("Starting test_import_assets_success...")
        """Test successful asset import with user confirmation"""
        # Setup
        runner = CliRunner()
        mock_confirm.return_value = True
        mock_get_folders.return_value = (1, [{"id": 1, "name": "Global"}])
        
        # Mock CSV data
        mock_df = pd.DataFrame({
            'name': ['Server-01', 'Database-01'],
            'type': ['Primary', 'Support']
        })
        mock_read_csv.return_value = mock_df
        
        # Mock successful API responses
        mock_post.side_effect = [
            MagicMock(status_code=201, json=lambda: {"id": 1}),
            MagicMock(status_code=201, json=lambda: {"id": 2})
        ]
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,type\nServer-01,Primary\nDatabase-01,Support")
            temp_file = f.name
        
        try:
            # Execute
            result = runner.invoke(import_assets, ['--file', temp_file])
            
            # Assertions
            assert result.exit_code == 0
            mock_confirm.assert_called_once_with("I'm about to create 2 assets. Are you sure?")
            assert mock_post.call_count == 2
            
            # Check first API call
            first_call = mock_post.call_args_list[0]
            expected_data_1 = {
                "name": "Server-01",
                "folder": 1,
                "type": "PR"  # Primary -> PR
            }
            assert first_call[1]['json'] == expected_data_1
            
            # Check second API call
            second_call = mock_post.call_args_list[1]
            expected_data_2 = {
                "name": "Database-01", 
                "folder": 1,
                "type": "SP"  # Support -> SP
            }
            assert second_call[1]['json'] == expected_data_2
            
        finally:
            os.unlink(temp_file)
    
    @patch('clica._get_folders')
    @patch('pandas.read_csv')
    @patch('click.confirm')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_import_assets_user_cancellation(self, mock_confirm, mock_read_csv, mock_get_folders):
        """Test user cancellation during asset import"""
        # Setup
        runner = CliRunner()
        mock_confirm.return_value = False
        mock_get_folders.return_value = (1, [{"id": 1, "name": "Global"}])
        
        # Mock CSV data
        mock_df = pd.DataFrame({
            'name': ['Server-01'],
            'type': ['Primary']
        })
        mock_read_csv.return_value = mock_df
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,type\nServer-01,Primary")
            temp_file = f.name
        
        try:
            # Execute
            with patch('clica.requests.post') as mock_post:
                result = runner.invoke(import_assets, ['--file', temp_file])
                
                # Assertions
                assert result.exit_code == 0
                mock_confirm.assert_called_once_with("I'm about to create 1 assets. Are you sure?")
                mock_post.assert_not_called()  # No API calls should be made
                
        finally:
            os.unlink(temp_file)

    @patch('clica._get_folders')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_import_assets_missing_file(self, mock_get_folders):
        """Test import with non-existent CSV file"""
        # Setup
        runner = CliRunner()
        non_existent_file = "non_existent_file.csv"
        mock_get_folders.return_value = (1, [{"id": 1, "name": "Global"}])
        
        # Execute
        result = runner.invoke(import_assets, ['--file', non_existent_file])
        
        # Assertions
        assert result.exit_code != 0
        assert isinstance(result.exception, FileNotFoundError)
    
    @patch('clica.requests.post')
    @patch('clica._get_folders')
    @patch('pandas.read_csv')
    @patch('click.confirm')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_import_assets_api_error(self, mock_confirm, mock_read_csv, mock_get_folders, mock_post):
        """Test handling of API errors during asset creation"""
        # Setup
        runner = CliRunner()
        mock_confirm.return_value = True
        mock_get_folders.return_value = (1, [{"id": 1, "name": "Global"}])
        
        # Mock CSV data
        mock_df = pd.DataFrame({
            'name': ['Server-01'],
            'type': ['Primary']
        })
        mock_read_csv.return_value = mock_df
        
        # Mock API error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_post.return_value = mock_response
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,type\nServer-01,Primary")
            temp_file = f.name
        
        try:
            # Execute
            result = runner.invoke(import_assets, ['--file', temp_file])
            
            # Assertions
            assert result.exit_code == 0  # Command completes but with errors
            mock_post.assert_called_once()
            # Error message should be printed to stderr
            assert "something went wrong" in result.output or len(result.output) > 0
            
        finally:
            os.unlink(temp_file)
    
    @patch('clica.requests.post')
    @patch('clica._get_folders')
    @patch('pandas.read_csv')
    @patch('click.confirm')
    @patch('clica.TOKEN', 'test-token-12345')
    def test_import_assets_type_mapping(self, mock_confirm, mock_read_csv, mock_get_folders, mock_post):
        """Test correct mapping of asset types (Primary->PR, Support->SP)"""
        # Setup
        runner = CliRunner()
        mock_confirm.return_value = True
        mock_get_folders.return_value = (1, [{"id": 1, "name": "Global"}])
        
        # Mock CSV data with different type cases
        mock_df = pd.DataFrame({
            'name': ['Asset1', 'Asset2', 'Asset3'],
            'type': ['primary', 'SUPPORT', 'Primary']  # Test case insensitivity
        })
        mock_read_csv.return_value = mock_df
        
        # Mock successful API responses
        mock_post.side_effect = [
            MagicMock(status_code=201, json=lambda: {"id": i}) for i in range(1, 4)
        ]
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,type\nAsset1,primary\nAsset2,SUPPORT\nAsset3,Primary")
            temp_file = f.name
        
        try:
            # Execute
            result = runner.invoke(import_assets, ['--file', temp_file])
            
            # Assertions
            assert result.exit_code == 0
            assert mock_post.call_count == 3
            
            # Check type mappings
            calls = mock_post.call_args_list
            assert calls[0][1]['json']['type'] == 'PR'  # primary -> PR
            assert calls[1][1]['json']['type'] == 'SP'  # SUPPORT -> SP
            assert calls[2][1]['json']['type'] == 'PR'  # Primary -> PR
            
        finally:
            os.unlink(temp_file)
    
    @patch.dict(os.environ, {'TOKEN': ''})
    def test_import_assets_no_token(self):
        """Test import assets without authentication token"""
        # Setup
        runner = CliRunner()
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,type\nServer-01,Primary")
            temp_file = f.name
        
        try:
            # Execute
            result = runner.invoke(import_assets, ['--file', temp_file])
            
            # Assertions
            assert result.exit_code == 1
            assert "No authentication token available" in result.output
            
        finally:
            os.unlink(temp_file)

class TestImportEvidences:
    """Test suite for evidence import functionality"""

    def test_import_evidences_success(self, mock_token, sample_evidences_csv):
        """
        Test successful import of evidences
        Input: Valid CSV file with evidences, user confirmation=True
        Output: Evidences created in CISO Assistant
        Assertions: All evidences created, success messages displayed
        """
        with patch('clica.TOKEN', mock_token):
            with patch('clica._get_folders', return_value=(1, [])):
                with patch('pandas.read_csv', return_value=sample_evidences_csv):
                    with patch('click.confirm', return_value=True):
                        with patch('requests.post') as mock_post:
                            # Mock successful creation responses
                            mock_response = MagicMock()
                            mock_response.status_code = 201
                            mock_post.return_value = mock_response

                            runner = CliRunner()
                            result = runner.invoke(import_evidences, ['--file', 'test.csv'])

                            # Verify CSV was processed
                            assert result.exit_code == 0
                            
                            # Verify correct number of POST calls made
                            assert mock_post.call_count == len(sample_evidences_csv)
                            
                            # Verify request structure for each evidence
                            for call in mock_post.call_args_list:
                                args, kwargs = call
                                assert kwargs['json']['folder'] == 1
                                assert 'name' in kwargs['json']
                                assert 'description' in kwargs['json']
                                assert kwargs['json']['applied_controls'] == []
                                assert kwargs['json']['requirement_assessments'] == []
                                assert kwargs['headers']['Authorization'] == f"Token {mock_token}"
                                assert kwargs['verify'] == VERIFY_CERTIFICATE

    def test_import_evidences_user_cancellation(self, mock_token, sample_evidences_csv):
        """
        Test cancellation of evidence import by user
        Input: Valid CSV file, user confirmation=False
        Output: No evidences created
        Assertions: No API calls made for creation
        """
        with patch('clica.TOKEN', mock_token):
            with patch('clica._get_folders', return_value=(1, [])):
                with patch('pandas.read_csv', return_value=sample_evidences_csv):
                    with patch('click.confirm', return_value=False):
                        with patch('requests.post') as mock_post:
                            runner = CliRunner()
                            result = runner.invoke(import_evidences, ['--file', 'test.csv'])

                            # Verify no POST calls were made
                            mock_post.assert_not_called()
                            assert result.exit_code == 0

    def test_import_evidences_api_error(self, mock_token, sample_evidences_csv, capsys):
        """
        Test handling of API errors during evidence creation
        Input: Valid CSV, but API returns error status
        Output: Error messages displayed for failed creations
        Assertions: Error messages shown, continues processing remaining evidences
        """
        with patch('clica.TOKEN', mock_token):
            with patch('clica._get_folders', return_value=(1, [])):
                with patch('pandas.read_csv', return_value=sample_evidences_csv):
                    with patch('click.confirm', return_value=True):
                        with patch('requests.post') as mock_post:
                            # Mock API error response
                            mock_response = MagicMock()
                            mock_response.status_code = 400
                            mock_response.json.return_value = {"error": "Validation failed"}
                            mock_post.return_value = mock_response

                            runner = CliRunner()
                            result = runner.invoke(import_evidences, ['--file', 'test.csv'])

                            # Verify error handling
                            captured = capsys.readouterr()
                            assert "❌ something went wrong" in result.output
                            
                            # All evidences should have been attempted
                            assert mock_post.call_count == len(sample_evidences_csv)

    def test_import_evidences_csv_file_not_found(self, mock_token):
        """
        Test handling of missing CSV file
        Input: Non-existent file path
        Output: FileNotFoundError or appropriate error handling
        Assertions: Error properly handled when file doesn't exist
        """
        with patch('clica.TOKEN', mock_token):
            with patch('pandas.read_csv', side_effect=FileNotFoundError("File not found")):
                runner = CliRunner()
                result = runner.invoke(import_evidences, ['--file', 'nonexistent.csv'])

                # Verify command fails gracefully
                assert result.exit_code != 0

        def test_import_evidences_folders_unavailable(self, mock_token, sample_evidences_csv, capsys):
            """Test behavior when folders cannot be retrieved
            Input: Valid CSV but _get_folders fails
            Output: Error from _get_folders function
            Assertions: Proper error handling when folder retrieval fails
            """
            with patch('clica.TOKEN', mock_token):
                with patch('clica._get_folders', side_effect=SystemExit(1)):
                    with patch('pandas.read_csv', return_value=sample_evidences_csv):
                        runner = CliRunner()
                        result = runner.invoke(import_evidences, ['--file', 'test.csv'])
                        assert result.exit_code == 1

    def test_import_evidences_partial_success(self, mock_token, sample_evidences_csv, capsys):
        """
        Test mixed success/failure scenario
        Input: Valid CSV, some evidences succeed, others fail
        Output: Mix of success and error messages
        Assertions: Successful creations logged, errors handled gracefully
        """
        with patch('clica.TOKEN', mock_token):
            with patch('clica._get_folders', return_value=(1, [])):
                with patch('pandas.read_csv', return_value=sample_evidences_csv):
                    with patch('click.confirm', return_value=True):
                        with patch('requests.post') as mock_post:
                            # Alternate between success and failure responses
                            responses = []
                            for i in range(len(sample_evidences_csv)):
                                mock_response = MagicMock()
                                if i % 2 == 0:  # Even indices succeed
                                    mock_response.status_code = 201
                                else:  # Odd indices fail
                                    mock_response.status_code = 400
                                    mock_response.json.return_value = {"error": "Failed"}
                                responses.append(mock_response)
                            
                            mock_post.side_effect = responses

                            runner = CliRunner()
                            result = runner.invoke(import_evidences, ['--file', 'test.csv'])

                            captured = capsys.readouterr()
                            # Should have both success and error messages
                            assert "✅" in result.output  # Success messages
                            assert "❌" in result.output  # Error messages


class TestUploadAttachment:
    """Test suite for upload_attachment functionality"""

    def test_upload_attachment_success(self, mock_token, tmp_path):
        """
        Objectif: Test upload fichier vers évidence existante
        Input: Fichier existant, nom évidence valide
        Output: Fichier uploadé avec succès
        Assertions: 
        - Évidence trouvée par nom
        - Upload réussi avec bon Content-Disposition header
        """
        # Create a temporary test file
        test_file = tmp_path / "test_document.pdf"
        test_file.write_text("Test file content")
        
        evidence_name = "Test Evidence"
        
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                with patch('requests.post') as mock_post:
                    # Mock evidence search response
                    mock_get_response = MagicMock()
                    mock_get_response.status_code = 200
                    mock_get_response.json.return_value = {
                        "results": [
                            {"id": 123, "name": evidence_name}
                        ]
                    }
                    mock_get.return_value = mock_get_response
                    
                    # Mock upload response
                    mock_post_response = MagicMock()
                    mock_post_response.status_code = 200
                    mock_post_response.text = "Upload successful"
                    mock_post.return_value = mock_post_response
                    
                    runner = CliRunner()
                    result = runner.invoke(upload_attachment, [
                        '--file', str(test_file),
                        '--name', evidence_name
                    ])
                    
                    # Verify evidence search was called correctly
                    mock_get.assert_called_once_with(
                        f"{API_URL}/evidences/",
                        headers={"Authorization": f"Token {mock_token}"},
                        params={"name": evidence_name},
                        verify=VERIFY_CERTIFICATE
                    )
                    
                    # Verify upload was called with correct parameters
                    mock_post.assert_called_once()
                    upload_call = mock_post.call_args
                    
                    # Check URL
                    assert upload_call[0][0] == f"{API_URL}/evidences/123/upload/"
                    
                    # Check headers
                    expected_headers = {
                        "Authorization": f"Token {mock_token}",
                        "Content-Disposition": 'attachment;filename="test_document.pdf"'
                    }
                    assert upload_call[1]['headers'] == expected_headers
                    
                    # Check verify parameter
                    assert upload_call[1]['verify'] == VERIFY_CERTIFICATE
                    
                    assert result.exit_code == 0

    def test_upload_attachment_multiple_evidences(self, mock_token, tmp_path):
        """
        Objectif: Test quand plusieurs évidences ont le même nom
        Input: Nom évidence avec multiples résultats
        Output: Utilise la première évidence trouvée
        Assertions: Upload vers data["results"][0]["id"]
        """
        # Create a temporary test file
        test_file = tmp_path / "test_document.pdf"
        test_file.write_text("Test file content")
        
        evidence_name = "Duplicate Evidence"
        
        with patch('clica.TOKEN', mock_token):
            with patch('requests.get') as mock_get:
                with patch('requests.post') as mock_post:
                    # Mock evidence search response - multiple results
                    mock_get_response = MagicMock()
                    mock_get_response.status_code = 200
                    mock_get_response.json.return_value = {
                        "results": [
                            {"id": 456, "name": evidence_name},  # First one should be used
                            {"id": 789, "name": evidence_name}
                        ]
                    }
                    mock_get.return_value = mock_get_response
                    
                    # Mock upload response
                    mock_post_response = MagicMock()
                    mock_post_response.status_code = 200
                    mock_post_response.text = "Upload successful"
                    mock_post.return_value = mock_post_response
                    
                    runner = CliRunner()
                    result = runner.invoke(upload_attachment, [
                        '--file', str(test_file),
                        '--name', evidence_name
                    ])
                    
                    # Verify upload was called with first evidence ID (456)
                    mock_post.assert_called_once()
                    upload_call = mock_post.call_args
                    assert upload_call[0][0] == f"{API_URL}/evidences/456/upload/"
                    
                    assert result.exit_code == 0

 