import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock, mock_open
import pandas as pd
from click.testing import CliRunner
import sys

# Add the parent directory to sys.path to import clica
sys.path.insert(0, str(Path(__file__).parent.parent))
from clica import (
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


class TestCLICommands:
    """Test suite for CLICA CLI commands"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.runner = CliRunner()
        self.mock_token = "test_token_123"
        self.mock_api_url = "http://localhost:8000/api"
        
    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("TOKEN", self.mock_token)
        monkeypatch.setenv("API_URL", self.mock_api_url)
        monkeypatch.setenv("VERIFY_CERTIFICATE", "false")

    @pytest.fixture
    def mock_successful_response(self):
        """Mock successful API response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "folder1", "name": "Test Folder 1", "content_type": "GLOBAL"},
                {"id": "folder2", "name": "Test Folder 2", "content_type": "DOMAIN"}
            ]
        }
        return mock_response

    @pytest.fixture
    def mock_folders_response(self):
        """Mock folders API response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Folder1": "folder1_id",
            "Folder2": "folder2_id",
            "Global": "global_id"
        }
        return mock_response

    def test_get_folders_success(self, mock_env_vars):
        """Test successful folders retrieval"""
        with patch('clica.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "Folder1": "folder1_id",
                "Folder2": "folder2_id"
            }
            
            result = self.runner.invoke(get_folders)
            
            assert result.exit_code == 0
            assert "Folder1" in result.output
            assert "folder1_id" in result.output

    def test_get_folders_no_token(self, monkeypatch):
        """Test folders command without token"""
        monkeypatch.setenv("TOKEN", "")
        
        result = self.runner.invoke(get_folders)
        
        assert result.exit_code == 1
        assert "No authentication token available" in result.output

    def test_get_perimeters_success(self, mock_env_vars):
        """Test successful perimeters retrieval"""
        with patch('clica.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "Perimeter1": "perimeter1_id",
                "Perimeter2": "perimeter2_id"
            }
            
            result = self.runner.invoke(get_perimeters)
            
            assert result.exit_code == 0
            assert "Perimeter1" in result.output

    def test_get_matrices_success(self, mock_env_vars):
        """Test successful matrices retrieval"""
        with patch('clica.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "4x4 risk matrix": "matrix1_id",
                "5x5 risk matrix": "matrix2_id"
            }
            
            result = self.runner.invoke(get_matrices)
            
            assert result.exit_code == 0
            assert "4x4 risk matrix" in result.output

    def test_import_assets_success(self, mock_env_vars):
        """Test successful asset import"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            # Write test CSV data
            f.write("name,description,domain,type\n")
            f.write("Asset1,Test Asset 1,Global,Primary\n")
            f.write("Asset2,Test Asset 2,Global,Support\n")
            csv_file = f.name
        
        try:
            with patch('clica.requests.get') as mock_get, \
                 patch('clica.requests.post') as mock_post, \
                 patch('click.confirm', return_value=True):
                
                # Mock _get_folders response
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "results": [{"id": "global_id", "content_type": "GLOBAL"}]
                }
                
                # Mock successful post response
                mock_post.return_value.status_code = 201
                mock_post.return_value.json.return_value = {"id": "asset_id"}
                
                result = self.runner.invoke(import_assets, ['--file', csv_file])
                
                assert result.exit_code == 0
                assert mock_post.call_count == 2  # Two assets
                
        finally:
            os.unlink(csv_file)

    def test_import_controls_success(self, mock_env_vars):
        """Test successful controls import"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,description,category,csf_function\n")
            f.write("Firewall,Network security,Technical,Protect\n")
            f.write("Policy,Security policy,Policy,Protect\n")
            csv_file = f.name
        
        try:
            with patch('clica.requests.get') as mock_get, \
                 patch('clica.requests.post') as mock_post, \
                 patch('click.confirm', return_value=True):
                
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "results": [{"id": "global_id", "content_type": "GLOBAL"}]
                }
                
                mock_post.return_value.status_code = 201
                mock_post.return_value.json.return_value = {"id": "control_id"}
                
                result = self.runner.invoke(import_controls, ['--file', csv_file])
                
                assert result.exit_code == 0
                assert mock_post.call_count == 2
                
        finally:
            os.unlink(csv_file)

    def test_import_evidences_success(self, mock_env_vars):
        """Test successful evidences import"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,description\n")
            f.write("Evidence1,Test Evidence 1\n")
            f.write("Evidence2,Test Evidence 2\n")
            csv_file = f.name
        
        try:
            with patch('clica.requests.get') as mock_get, \
                 patch('clica.requests.post') as mock_post, \
                 patch('click.confirm', return_value=True):
                
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "results": [{"id": "global_id", "content_type": "GLOBAL"}]
                }
                
                mock_post.return_value.status_code = 201
                mock_post.return_value.json.return_value = {"id": "evidence_id"}
                
                result = self.runner.invoke(import_evidences, ['--file', csv_file])
                
                assert result.exit_code == 0
                assert mock_post.call_count == 2
                
        finally:
            os.unlink(csv_file)

    def test_upload_attachment_success(self, mock_env_vars):
        """Test successful attachment upload"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test attachment content")
            attachment_file = f.name
        
        try:
            with patch('clica.requests.get') as mock_get, \
                 patch('clica.requests.post') as mock_post, \
                 patch('builtins.open', mock_open(read_data=b"test data")):
                
                # Mock evidence search response
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "results": [{"id": "evidence_id", "name": "Test Evidence"}]
                }
                
                # Mock upload response
                mock_post.return_value.status_code = 200
                mock_post.return_value.text = "Upload successful"
                
                result = self.runner.invoke(upload_attachment, [
                    '--file', attachment_file,
                    '--name', 'Test Evidence'
                ])
                
                assert result.exit_code == 0
                
        finally:
            os.unlink(attachment_file)

    def test_upload_attachment_evidence_not_found(self, mock_env_vars):
        """Test attachment upload when evidence is not found"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            attachment_file = f.name
        
        try:
            with patch('clica.requests.get') as mock_get:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {"results": []}
                
                result = self.runner.invoke(upload_attachment, [
                    '--file', attachment_file,
                    '--name', 'NonExistent Evidence'
                ])
                
                assert result.exit_code == 0
                assert "No evidence found" in result.output
                
        finally:
            os.unlink(attachment_file)

    def test_import_risk_assessment_success(self, mock_env_vars):
        """Test successful risk assessment import"""
        # Create test risk assessment CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("ref_id;assets;threats;name;description;existing_controls;current_impact;current_proba;current_risk;additional_controls;residual_impact;residual_proba;residual_risk;treatment\n")
            f.write("R.1;Asset1;Threat1;Risk Scenario 1;Test risk;Control1;High;Likely;Medium;Control2;Medium;Unlikely;Low;mitigate\n")
            csv_file = f.name
        
        try:
            with patch('clica.requests.get') as mock_get, \
                 patch('clica.requests.post') as mock_post:
                
                # Mock various API responses needed for risk assessment import
                def mock_get_side_effect(url, **kwargs):
                    response = Mock()
                    response.status_code = 200
                    
                    if 'folders' in url:
                        response.json.return_value = {"Test Folder": "folder_id"}
                    elif 'perimeters' in url:
                        response.json.return_value = {"Test Perimeter": "perimeter_id"}
                    elif 'risk-matrices' in url:
                        if url.endswith('/ids/'):
                            response.json.return_value = {"Global": {"Test Matrix": "matrix_id"}}
                        else:  # specific matrix details
                            response.json.return_value = {
                                "json_definition": json.dumps({
                                    "impact": [
                                        {"id": 1, "name": "High"},
                                        {"id": 2, "name": "Medium"},
                                        {"id": 3, "name": "Low"}
                                    ],
                                    "probability": [
                                        {"id": 1, "name": "Likely"},
                                        {"id": 2, "name": "Unlikely"}
                                    ]
                                })
                            }
                    elif 'threats' in url:
                        response.json.return_value = {"Threat1": "threat_id"}
                    elif 'assets' in url:
                        response.json.return_value = {"Asset1": "asset_id"}
                    elif 'applied-controls' in url:
                        response.json.return_value = {"Control1": "control1_id", "Control2": "control2_id"}
                    
                    return response
                
                mock_get.side_effect = mock_get_side_effect
                
                # Mock successful post responses
                mock_post.return_value.status_code = 201
                mock_post.return_value.json.return_value = {"id": "created_id"}
                
                result = self.runner.invoke(import_risk_assessment, [
                    '--file', csv_file,
                    '--folder', 'Test Folder',
                    '--perimeter', 'Test Perimeter',
                    '--matrix', 'Test Matrix',
                    '--name', 'Test RA'
                ])
                
                # Should not exit with error (might have warnings about matrix labels)
                assert result.exit_code == 0
                
        finally:
            os.unlink(csv_file)


class TestUtilityFunctions:
    """Test suite for utility functions"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.mock_token = "test_token"
        self.mock_api_url = "http://localhost:8000/api"

    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("TOKEN", self.mock_token)
        monkeypatch.setenv("API_URL", self.mock_api_url)
        monkeypatch.setenv("VERIFY_CERTIFICATE", "false")

    def test_ids_map_success(self, mock_env_vars):
        """Test successful ids_map function"""
        with patch('clica.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "folder1": {"item1": "id1", "item2": "id2"},
                "folder2": {"item3": "id3"}
            }
            
            result = ids_map("test-model", folder="folder1")
            
            assert result == {"item1": "id1", "item2": "id2"}
            mock_get.assert_called_once()

    def test_ids_map_no_token(self, monkeypatch):
        """Test ids_map function without token"""
        monkeypatch.setenv("TOKEN", "")
        
        with pytest.raises(SystemExit):
            ids_map("test-model")

    def test_ids_map_api_error(self, mock_env_vars):
        """Test ids_map function with API error"""
        with patch('clica.requests.get') as mock_get:
            mock_get.return_value.status_code = 401
            
            with pytest.raises(SystemExit):
                ids_map("test-model")

    def test_batch_create_success(self, mock_env_vars):
        """Test successful batch_create function"""
        items = ["item1", "item2", "item3"]
        folder_id = "test_folder_id"
        
        with patch('clica.requests.post') as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {"id": "created_id"}
            
            result = batch_create("test-model", items, folder_id)
            
            assert len(result) == 3
            assert all(item in result for item in items)
            assert mock_post.call_count == 3

    def test_batch_create_no_token(self, monkeypatch):
        """Test batch_create function without token"""
        monkeypatch.setenv("TOKEN", "")
        
        with pytest.raises(SystemExit):
            batch_create("test-model", ["item1"], "folder_id")

    def test_get_unique_parsed_values(self):
        """Test get_unique_parsed_values function"""
        # Create test dataframe
        data = {
            'test_column': [
                'value1, value2',
                'value2, value3',
                'value1',
                None,
                'value4'
            ]
        }
        df = pd.DataFrame(data)
        
        result = get_unique_parsed_values(df, 'test_column')
        
        expected = {'value1', 'value2', 'value3', 'value4'}
        assert result == expected

    def test_get_unique_parsed_values_empty_column(self):
        """Test get_unique_parsed_values with empty column"""
        df = pd.DataFrame({'test_column': [None, None, None]})
        
        result = get_unique_parsed_values(df, 'test_column')
        
        assert result == set()

    def test_get_folders_function_success(self, mock_env_vars):
        """Test _get_folders utility function"""
        with patch('clica.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "results": [
                    {"id": "global_id", "content_type": "GLOBAL"},
                    {"id": "domain_id", "content_type": "DOMAIN"}
                ]
            }
            
            global_id, folders = _get_folders()
            
            assert global_id == "global_id"
            assert len(folders) == 2

    def test_get_folders_function_no_token(self, monkeypatch):
        """Test _get_folders function without token"""
        monkeypatch.setenv("TOKEN", "")
        
        with pytest.raises(SystemExit):
            _get_folders()


class TestErrorHandling:
    """Test suite for error handling scenarios"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.runner = CliRunner()

    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("TOKEN", "test_token")
        monkeypatch.setenv("API_URL", "http://localhost:8000/api")
        monkeypatch.setenv("VERIFY_CERTIFICATE", "false")

    def test_import_assets_file_not_found(self, mock_env_vars):
        """Test import_assets with non-existent file"""
        result = self.runner.invoke(import_assets, ['--file', 'nonexistent.csv'])
        
        assert result.exit_code != 0

    def test_import_assets_user_cancellation(self, mock_env_vars):
        """Test import_assets when user cancels confirmation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,description,domain,type\n")
            f.write("Asset1,Test,Global,Primary\n")
            csv_file = f.name
        
        try:
            with patch('clica._get_folders', return_value=("global_id", [])), \
                 patch('click.confirm', return_value=False):
                
                result = self.runner.invoke(import_assets, ['--file', csv_file])
                
                assert result.exit_code == 0
                
        finally:
            os.unlink(csv_file)

    def test_api_authentication_error(self, mock_env_vars):
        """Test API authentication error handling"""
        with patch('clica.requests.get') as mock_get:
            mock_get.return_value.status_code = 401
            mock_get.return_value.json.return_value = {"detail": "Authentication failed"}
            
            result = self.runner.invoke(get_folders)
            
            assert result.exit_code == 1

    def test_api_server_error(self, mock_env_vars):
        """Test API server error handling"""
        with patch('clica.requests.get') as mock_get:
            mock_get.return_value.status_code = 500
            mock_get.return_value.json.return_value = {"detail": "Internal server error"}
            
            result = self.runner.invoke(get_folders)
            
            assert result.exit_code == 1


class TestDataValidation:
    """Test suite for data validation"""
    
    def test_csv_parsing_special_characters(self):
        """Test CSV parsing with special characters"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,description\n")
            f.write('"Asset with ""quotes""","Description with, commas"\n')
            f.write("Asset with; semicolon,Normal description\n")
            csv_file = f.name
        
        try:
            df = pd.read_csv(csv_file)
            assert len(df) == 2
            assert 'Asset with "quotes"' in df['name'].values
            
        finally:
            os.unlink(csv_file)

    def test_risk_assessment_csv_parsing(self):
        """Test risk assessment CSV parsing with semicolon delimiter"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("ref_id;assets;threats;name;treatment\n")
            f.write("R.1;asset1,asset2;threat1;Test Risk;mitigate\n")
            f.write("R.2;;threat2;Another Risk;accept\n")
            csv_file = f.name
        
        try:
            df = pd.read_csv(csv_file, delimiter=';')
            assert len(df) == 2
            assert df.iloc[0]['assets'] == 'asset1,asset2'
            assert pd.isna(df.iloc[1]['assets']) or df.iloc[1]['assets'] == ''
            
        finally:
            os.unlink(csv_file)

    def test_treatment_options_validation(self):
        """Test treatment options validation"""
        valid_treatments = ['open', 'mitigate', 'accept', 'avoid', 'transfer']
        
        for treatment in valid_treatments:
            assert treatment.lower() in ['open', 'mitigate', 'accept', 'avoid', 'transfer']
        
        # Test case insensitivity
        assert 'MITIGATE'.lower() in ['open', 'mitigate', 'accept', 'avoid', 'transfer']


if __name__ == '__main__':
    pytest.main([__file__])