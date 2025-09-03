import pytest
import os
import tempfile
import pandas as pd
from unittest.mock import MagicMock, patch
from pathlib import Path


@pytest.fixture
def mock_token():
    """FProvides a valid test tokene"""
    return "test-token-12345-abcdef"


@pytest.fixture
def auth_headers(mock_token):
    """Headers d'authentification pour les tests"""
    return {"Authorization": f"Token {mock_token}"}


@pytest.fixture
def mock_requests_success():
    """Authentication headers for testing"""
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        # Mock successful GET response
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"results": []}
        mock_get.return_value = mock_get_response
        
        # Mock successful POST response
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"id": 1, "name": "test"}
        mock_post.return_value = mock_post_response
        
        yield {"get": mock_get, "post": mock_post}


@pytest.fixture
def mock_requests_auth_failure():
    """Mock requests with authentication failure"""
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        # Mock authentication failure
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid token"}
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        yield {"get": mock_get, "post": mock_post}


@pytest.fixture
def sample_folders_response():
    """API response folders with Global folder"""
    return {
        "results": [
            {"id": 1, "name": "Global", "content_type": "GLOBAL"},
            {"id": 2, "name": "Project1", "content_type": "DOMAIN"},
            {"id": 3, "name": "BU 1", "content_type": "DOMAIN"}
        ]
    }


@pytest.fixture
def sample_perimeters_response():
    """API Perimeters Response"""
    return {
        "Project1": {"Orion": 1, "Cassiopeia": 2, "Beta": 3, "Gamma": 4},
        "BU 1": {"Orion": 3, "Vega": 4, "Alpha": 2}
    }


@pytest.fixture
def sample_matrices_response():
    """Sample API response for risk matrices"""
    return {
        "Global": {
            "4x4 risk matrix from EBIOS-RM": 1,
            "5x5 standard matrix": 2
        },
        "EBIOS-RM matrix": 2,
        "Custom matrix": 3
    }


@pytest.fixture
def sample_risk_assessment_csv():
    """Test DataFrame for Risk Assessment"""
    data = {
        'ref_id': ['R.1', 'R.2', 'R.3'],
        'name': ['Test Risk 1', 'Test Risk 2', 'Test Risk 3'],
        'assets': ['asset1', 'asset2', 'asset1,asset2'],
        'threats': ['threat1', 'threat2', 'threat1,threat3'],
        'description': ['Description 1', 'Description 2', 'Description 3'],
        'existing_controls': ['control1', 'control2', 'control1,control2'],
        'current_impact': ['Low', 'High', 'Medium'],
        'current_proba': ['Unlikely', 'Likely', 'Possible'],
        'current_risk': ['Low', 'High', 'Medium'],
        'additional_controls': ['new_control1', 'new_control2', '--'],
        'residual_impact': ['Low', 'Medium', 'Low'],
        'residual_proba': ['Unlikely', 'Possible', 'Unlikely'],
        'residual_risk': ['Low', 'Medium', 'Low'],
        'treatment': ['mitigate', 'accept', 'open']
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_matrix_definition():
    """Definition of test risk matrix"""
    return {
        "impact": [
            {"id": 1, "name": "Low"},
            {"id": 2, "name": "Medium"},
            {"id": 3, "name": "High"},
            {"id": 4, "name": "Critical"}
        ],
        "probability": [
            {"id": 1, "name": "Unlikely"},
            {"id": 2, "name": "Possible"},
            {"id": 3, "name": "Likely"},
            {"id": 4, "name": "Very likely"}
        ]
    }


@pytest.fixture
def sample_assets_csv():
    """Test DataFrame for Assets"""
    data = {
        'name': ['Server-01', 'Database-01', 'Workstation-01'],
        'description': ['Main server', 'Primary database', 'User workstation'],
        'domain': ['Global', 'Global', 'Global'],
        'type': ['Primary', 'Support', 'Primary']
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_controls_csv():
    """Test dataFrame for controls"""
    data = {
        'name': ['Firewall', 'Access Policy', 'Encryption'],
        'description': ['Network traffic control', 'Define user privileges', 'Data encryption'],
        'category': ['Technical', 'Policy', 'Technical'],
        'csf_function': ['Protect', 'Protect', 'Protect']
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_evidences_csv():
    """Test DataFrame for Evidence"""
    data = {
        'name': ['Evidence 1', 'Evidence 2', 'Evidence 3'],
        'description': ['Security policy document', 'Audit report', 'Training records']
    }
    return pd.DataFrame(data)


@pytest.fixture
def temp_env_file():
    """Creates a temporary .env file for testing"""
    def _create_env_file(content="TOKEN=test-token-12345\nAPI_URL=http://localhost:8000/api\nVERIFY_CERTIFICATE=false\n"):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(content)
            temp_file = f.name
        return temp_file
    
    created_files = []
    
    def create_file(content=None):
        if content is None:
            content = "TOKEN=test-token-12345\nAPI_URL=http://localhost:8000/api\nVERIFY_CERTIFICATE=false\n"
        file_path = _create_env_file(content)
        created_files.append(file_path)
        return file_path
    
    yield create_file
    
    # Cleanup
    for filepath in created_files:
        if os.path.exists(filepath):
            os.unlink(filepath)


@pytest.fixture
def temp_csv_file():
    """Creates a temporary CSV file for testing"""
    def _create_csv(data, filename_suffix="test"):
        if isinstance(data, pd.DataFrame):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{filename_suffix}.csv', delete=False) as f:
                data.to_csv(f.name, index=False)
                return f.name
        elif isinstance(data, dict):
            # Convert dict to CSV format
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{filename_suffix}.csv', delete=False) as f:
                header = ','.join(data.keys())
                rows = []
                for i in range(len(list(data.values())[0])):
                    row = ','.join(str(data[key][i]) for key in data.keys())
                    rows.append(row)
                content = header + '\n' + '\n'.join(rows)
                f.write(content)
                return f.name
        else:
            # String content
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{filename_suffix}.csv', delete=False) as f:
                f.write(data)
                return f.name
    
    created_files = []
    
    def csv_creator(data=None, filename_suffix="test"):
        if data is None:
            # Create empty file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                filepath = f.name
        else:
            filepath = _create_csv(data, filename_suffix)
        created_files.append(filepath)
        return filepath
    
    yield csv_creator
    
    # Cleanup
    for filepath in created_files:
        if os.path.exists(filepath):
            os.unlink(filepath)


@pytest.fixture
def clean_environment():
    """Clear environment variables before testing"""
    original_env = {}
    env_vars = ['TOKEN', 'API_URL', 'VERIFY_CERTIFICATE']
    
    # Sauvegarder les valeurs originales
    for var in env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restaurer les valeurs originales
    for var, value in original_env.items():
        os.environ[var] = value


@pytest.fixture
def mock_file_system():
    """Mock file system for upload testing"""
    def _mock_file(filename="test.txt", content="test content"):
        mock_file = MagicMock()
        mock_file.name = filename
        mock_file.read.return_value = content.encode()
        return mock_file
    
    return _mock_file


@pytest.fixture
def sample_ids_map_response():
    """Typical response for ids_map"""
    return {
        "Global": {
            "folder1": 1,
            "folder2": 2
        },
        "Project1": {
            "item1": 10,
            "item2": 20
        }
    }


@pytest.fixture
def mock_successful_response():
    """Mock a successful HTTP response"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    return mock_response


@pytest.fixture
def mock_auth_failure_response():
    """Mock an authentication failure HTTP response"""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"detail": "Invalid token"}
    return mock_response


@pytest.fixture
def mock_successful_api_response():
    """Mock successful API response"""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": 1}
    return mock_response


@pytest.fixture
def mock_failed_api_response():
    """Mock failed API response"""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"error": "Bad request"}
    return mock_response


@pytest.fixture
def sample_evidence_response():
    """API response for evidence search"""
    return {
        "results": [
            {
                "id": 123,
                "name": "Test Evidence",
                "description": "Test evidence description",
                "folder": {"id": 1, "name": "Global"}
            }
        ]
    }


@pytest.fixture  
def empty_evidence_response():
    """Empty API response for evidence not found"""
    return {"results": []}


@pytest.fixture
def multiple_evidence_response():
    """API response with multiple evidences of the same name"""
    return {
        "results": [
            {"id": 456, "name": "Duplicate Evidence"},
            {"id": 789, "name": "Duplicate Evidence"}
        ]
    }


@pytest.fixture
def temp_test_file(tmp_path):
    """Creates a temporary file for upload tests"""
    test_file = tmp_path / "test_attachment.pdf"
    test_file.write_text("This is a test file content for upload testing")
    return test_file


@pytest.fixture(autouse=True)
def reset_global_variables():
    """Reset les variables globales avant chaque test"""
    # Import ici pour éviter les problèmes de circular import
    import clica
    
    # Sauvegarder les valeurs originales
    original_global_folder_id = getattr(clica, 'GLOBAL_FOLDER_ID', None)
    
    yield
    
    # Restaurer les valeurs
    clica.GLOBAL_FOLDER_ID = original_global_folder_id