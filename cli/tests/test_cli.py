"""
Tests unitaires pour CLICA - CLI tool pour CISO Assistant REST API

Ce module contient tous les tests pour les commandes CLI:
- get_folders
- get_perimeters  
- get_matrices
- import_risk_assessment
- import_assets
- import_controls
- import_evidences
- upload_attachment
- Fonctions utilitaires (ids_map, batch_create, etc.)
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pandas as pd
from click.testing import CliRunner
import requests_mock

# Import du module à tester
import clica


class TestCLIConfiguration:
    """Tests pour la configuration de base du CLI"""
    
    def test_environment_variables_loading(self):
        """Test du chargement des variables d'environnement"""
        with patch.dict(os.environ, {
            'API_URL': 'http://test.local:8000/api',
            'TOKEN': 'test-token-123',
            'VERIFY_CERTIFICATE': 'false'
        }):
            # Recharger le module pour prendre en compte les nouvelles variables
            import importlib
            importlib.reload(clica)
            
            assert clica.API_URL == 'http://test.local:8000/api'
            assert clica.TOKEN == 'test-token-123'
            assert clica.VERIFY_CERTIFICATE is False

    def test_cli_group_exists(self):
        """Test que le groupe CLI principal existe"""
        runner = CliRunner()
        result = runner.invoke(clica.cli, ['--help'])
        assert result.exit_code == 0
        assert "CLICA is the CLI tool to interact with CISO Assistant REST API" in result.output


class TestUtilityFunctions:
    """Tests pour les fonctions utilitaires"""
    
    @pytest.fixture
    def mock_requests(self):
        """Fixture pour mocker les requêtes HTTP"""
        with requests_mock.Mocker() as m:
            yield m
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica.API_URL', 'http://test.local:8000/api')
    def test_ids_map_success(self, mock_requests):
        """Test de la fonction ids_map avec succès"""
        mock_data = {
            "folder1": {"id": 1, "name": "Folder 1"},
            "folder2": {"id": 2, "name": "Folder 2"}
        }
        
        mock_requests.get(
            'http://test.local:8000/api/folders/ids/',
            json=mock_data,
            status_code=200
        )
        
        result = clica.ids_map("folders")
        assert result == mock_data
    
    @patch('clica.TOKEN', '')
    def test_ids_map_no_token(self):
        """Test de ids_map sans token"""
        with pytest.raises(SystemExit):
            clica.ids_map("folders")
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica.API_URL', 'http://test.local:8000/api')
    def test_ids_map_with_folder_filter(self, mock_requests):
        """Test de ids_map avec filtre par dossier"""
        mock_data = {
            "Global": {
                "matrix1": {"id": 1, "name": "Matrix 1"},
                "matrix2": {"id": 2, "name": "Matrix 2"}
            }
        }
        
        mock_requests.get(
            'http://test.local:8000/api/risk-matrices/ids/',
            json=mock_data,
            status_code=200
        )
        
        result = clica.ids_map("risk-matrices", folder="Global")
        assert result == mock_data["Global"]
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica.API_URL', 'http://test.local:8000/api')
    def test_get_folders_function(self, mock_requests):
        """Test de la fonction _get_folders"""
        mock_data = {
            "results": [
                {"id": 1, "name": "Global", "content_type": "GLOBAL"},
                {"id": 2, "name": "BU 1", "content_type": "DOMAIN"}
            ]
        }
        
        mock_requests.get(
            'http://test.local:8000/api/folders/',
            json=mock_data,
            status_code=200
        )
        
        global_id, folders = clica._get_folders()
        assert global_id == 1
        assert len(folders) == 2
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica.API_URL', 'http://test.local:8000/api')
    def test_batch_create_success(self, mock_requests):
        """Test de la fonction batch_create"""
        items = ["Asset 1", "Asset 2", "Asset 3"]
        folder_id = 1
        
        # Mock des réponses pour chaque création
        for i, item in enumerate(items, 1):
            mock_requests.post(
                'http://test.local:8000/api/assets/',
                json={"id": i, "name": item},
                status_code=201
            )
        
        result = clica.batch_create("assets", items, folder_id)
        
        expected = {
            "Asset 1": 1,
            "Asset 2": 2,
            "Asset 3": 3
        }
        assert result == expected
    
    def test_get_unique_parsed_values(self):
        """Test de la fonction get_unique_parsed_values"""
        # Création d'un DataFrame de test
        data = {
            'assets': ['asset1,asset2', 'asset2,asset3', 'asset1', None],
            'threats': ['threat1', 'threat2,threat3', None, 'threat1']
        }
        df = pd.DataFrame(data)
        
        # Test pour la colonne assets
        result_assets = clica.get_unique_parsed_values(df, 'assets')
        expected_assets = {'asset1', 'asset2', 'asset3'}
        assert result_assets == expected_assets
        
        # Test pour la colonne threats
        result_threats = clica.get_unique_parsed_values(df, 'threats')
        expected_threats = {'threat1', 'threat2', 'threat3'}
        assert result_threats == expected_threats


class TestGetCommands:
    """Tests pour les commandes de récupération (get_*)"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @patch('clica.ids_map')
    def test_get_folders_command(self, mock_ids_map, runner):
        """Test de la commande get-folders"""
        mock_data = {
            "folder1": {"id": 1, "name": "Global"},
            "folder2": {"id": 2, "name": "BU 1"}
        }
        mock_ids_map.return_value = mock_data
        
        result = runner.invoke(clica.get_folders)
        
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data == mock_data
        mock_ids_map.assert_called_once_with("folders")
    
    @patch('clica.ids_map')
    def test_get_perimeters_command(self, mock_ids_map, runner):
        """Test de la commande get-perimeters"""
        mock_data = {
            "perimeter1": {"id": 1, "name": "Orion"},
            "perimeter2": {"id": 2, "name": "Cassiopée"}
        }
        mock_ids_map.return_value = mock_data
        
        result = runner.invoke(clica.get_perimeters)
        
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data == mock_data
        mock_ids_map.assert_called_once_with("perimeters")
    
    @patch('clica.ids_map')
    def test_get_matrices_command(self, mock_ids_map, runner):
        """Test de la commande get-matrices"""
        mock_data = {
            "matrix1": {"id": 1, "name": "4x4 risk matrix from EBIOS-RM"},
            "matrix2": {"id": 2, "name": "5x5 risk matrix"}
        }
        mock_ids_map.return_value = mock_data
        
        result = runner.invoke(clica.get_matrices)
        
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data == mock_data
        mock_ids_map.assert_called_once_with("risk-matrices", folder="Global")


class TestImportAssets:
    """Tests pour la commande import-assets"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def sample_assets_csv(self):
        """Créer un fichier CSV de test pour les assets"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,type,description\n")
            f.write("Server-Web-01,Primary,Main web server\n")
            f.write("Database-01,Primary,Main database\n")
            f.write("Backup-System,Support,Backup infrastructure\n")
            return f.name
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica._get_folders')
    @patch('requests.post')
    def test_import_assets_success(self, mock_post, mock_get_folders, runner, sample_assets_csv):
        """Test d'import d'assets avec succès"""
        # Configuration des mocks
        mock_get_folders.return_value = (1, [])
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": 1, "name": "test"}
        
        # Exécution de la commande avec confirmation automatique
        result = runner.invoke(clica.import_assets, [
            '--file', sample_assets_csv
        ], input='y\n')
        
        assert result.exit_code == 0
        # Vérifier que 3 requêtes POST ont été faites (3 assets)
        assert mock_post.call_count == 3
        
        # Nettoyer le fichier temporaire
        os.unlink(sample_assets_csv)
    
    @patch('clica.TOKEN', '')
    def test_import_assets_no_token(self, runner, sample_assets_csv):
        """Test d'import d'assets sans token"""
        result = runner.invoke(clica.import_assets, [
            '--file', sample_assets_csv
        ])
        
        assert result.exit_code == 1
        assert "No authentication token available" in result.output
        
        os.unlink(sample_assets_csv)
    
    def test_import_assets_file_not_found(self, runner):
        """Test d'import d'assets avec fichier inexistant"""
        result = runner.invoke(clica.import_assets, [
            '--file', 'nonexistent.csv'
        ])
        
        assert result.exit_code != 0


class TestImportControls:
    """Tests pour la commande import-controls"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def sample_controls_csv(self):
        """Créer un fichier CSV de test pour les contrôles"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,description,csf_function,category\n")
            f.write("Firewall,Network security control,Protect,Technical\n")
            f.write("Access Control Policy,User access management,Protect,Policy\n")
            f.write("Backup Procedure,Data backup process,Recover,Process\n")
            return f.name
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica._get_folders')
    @patch('requests.post')
    def test_import_controls_success(self, mock_post, mock_get_folders, runner, sample_controls_csv):
        """Test d'import de contrôles avec succès"""
        mock_get_folders.return_value = (1, [])
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": 1, "name": "test"}
        
        result = runner.invoke(clica.import_controls, [
            '--file', sample_controls_csv
        ], input='y\n')
        
        assert result.exit_code == 0
        assert mock_post.call_count == 3
        
        os.unlink(sample_controls_csv)


class TestImportEvidences:
    """Tests pour la commande import-evidences"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def sample_evidences_csv(self):
        """Créer un fichier CSV de test pour les évidences"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,description\n")
            f.write("Security Policy,Main security policy document\n")
            f.write("Audit Report,Annual security audit report\n")
            f.write("Training Records,Security awareness training records\n")
            return f.name
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica._get_folders')
    @patch('requests.post')
    def test_import_evidences_success(self, mock_post, mock_get_folders, runner, sample_evidences_csv):
        """Test d'import d'évidences avec succès"""
        mock_get_folders.return_value = (1, [])
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": 1, "name": "test"}
        
        result = runner.invoke(clica.import_evidences, [
            '--file', sample_evidences_csv
        ], input='y\n')
        
        assert result.exit_code == 0
        assert mock_post.call_count == 3
        
        os.unlink(sample_evidences_csv)


class TestUploadAttachment:
    """Tests pour la commande upload-attachment"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def sample_file(self):
        """Créer un fichier de test pour l'upload"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document for evidence upload.")
            return f.name
    
    @patch('clica.TOKEN', 'test-token')
    @patch('requests.get')
    @patch('requests.post')
    def test_upload_attachment_success(self, mock_post, mock_get, runner, sample_file):
        """Test d'upload d'attachment avec succès"""
        # Mock de la recherche d'évidence
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "results": [{"id": 1, "name": "Test Evidence"}]
        }
        
        # Mock de l'upload
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "Upload successful"
        
        result = runner.invoke(clica.upload_attachment, [
            '--file', sample_file,
            '--name', 'Test Evidence'
        ])
        
        assert result.exit_code == 0
        mock_get.assert_called_once()
        mock_post.assert_called_once()
        
        os.unlink(sample_file)
    
    @patch('clica.TOKEN', 'test-token')
    @patch('requests.get')
    def test_upload_attachment_evidence_not_found(self, mock_get, runner, sample_file):
        """Test d'upload avec évidence introuvable"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"results": []}
        
        result = runner.invoke(clica.upload_attachment, [
            '--file', sample_file,
            '--name', 'Nonexistent Evidence'
        ])
        
        assert result.exit_code == 0
        assert "No evidence found" in result.output
        
        os.unlink(sample_file)


class TestImportRiskAssessment:
    """Tests pour la commande import-risk-assessment"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def sample_risk_assessment_csv(self):
        """Créer un fichier CSV de test pour l'évaluation de risques"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("ref_id;assets;threats;name;description;existing_controls;current_impact;current_proba;current_risk;additional_controls;residual_impact;residual_proba;residual_risk;treatment\n")
            f.write("R.1;Server-01;Malware;Malware infection;Risk of malware infection;Antivirus;Significant;Likely;Medium;EDR;Minor;Unlikely;Low;mitigate\n")
            f.write("R.2;Database-01;Data breach;Unauthorized access;Risk of data breach;Access controls;Critical;Possible;High;Encryption;Important;Rare;Low;mitigate\n")
            return f.name
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica.ids_map')
    @patch('requests.post')
    @patch('requests.get')
    def test_import_risk_assessment_success(self, mock_get, mock_post, mock_ids_map, runner, sample_risk_assessment_csv):
        """Test d'import d'évaluation de risques avec succès"""
        # Configuration des mocks
        mock_ids_map.side_effect = [
            {"BU 1": 1},  # folders
            {"Orion": 2},  # perimeters  
            {"4x4 risk matrix": 3},  # matrices
            {"Server-01": 1, "Database-01": 2},  # assets
            {"Malware": 1, "Data breach": 2},  # threats
            {"Antivirus": 1, "Access controls": 2, "EDR": 3, "Encryption": 4}  # controls
        ]
        
        # Mock de la création de l'évaluation de risques
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": 1}
        
        # Mock de la récupération de la matrice de risques
        matrix_definition = {
            "impact": [
                {"id": 1, "name": "Minor"},
                {"id": 2, "name": "Significant"},
                {"id": 3, "name": "Important"},
                {"id": 4, "name": "Critical"}
            ],
            "probability": [
                {"id": 1, "name": "Rare"},
                {"id": 2, "name": "Unlikely"},
                {"id": 3, "name": "Possible"},
                {"id": 4, "name": "Likely"}
            ]
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "json_definition": json.dumps(matrix_definition)
        }
        
        result = runner.invoke(clica.import_risk_assessment, [
            '--file', sample_risk_assessment_csv,
            '--folder', 'BU 1',
            '--perimeter', 'Orion',
            '--matrix', '4x4 risk matrix',
            '--name', 'Test Risk Assessment'
        ])
        
        assert result.exit_code == 0
        
        os.unlink(sample_risk_assessment_csv)
    
    @patch('clica.TOKEN', '')
    def test_import_risk_assessment_no_token(self, runner, sample_risk_assessment_csv):
        """Test d'import d'évaluation de risques sans token"""
        result = runner.invoke(clica.import_risk_assessment, [
            '--file', sample_risk_assessment_csv,
            '--folder', 'BU 1',
            '--perimeter', 'Orion',
            '--matrix', '4x4 risk matrix',
            '--name', 'Test Risk Assessment'
        ])
        
        assert result.exit_code == 1
        assert "No authentication token available" in result.output
        
        os.unlink(sample_risk_assessment_csv)


class TestErrorHandling:
    """Tests pour la gestion d'erreurs"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica.API_URL', 'http://test.local:8000/api')
    def test_ids_map_api_error(self):
        """Test de ids_map avec erreur API"""
        with requests_mock.Mocker() as m:
            m.get(
                'http://test.local:8000/api/folders/ids/',
                status_code=401,
                json={"error": "Unauthorized"}
            )
            
            with pytest.raises(SystemExit):
                clica.ids_map("folders")
    
    @patch('clica.TOKEN', 'test-token')
    @patch('clica._get_folders')
    @patch('requests.post')
    def test_batch_create_api_error(self, mock_post, mock_get_folders):
        """Test de batch_create avec erreur API"""
        mock_get_folders.return_value = (1, [])
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"error": "Bad request"}
        
        items = ["Asset 1"]
        result = clica.batch_create("assets", items, 1)
        
        # Devrait retourner un dictionnaire vide en cas d'erreur
        assert result == {}


class TestDataValidation:
    """Tests pour la validation des données"""
    
    def test_get_unique_parsed_values_empty_dataframe(self):
        """Test avec un DataFrame vide"""
        df = pd.DataFrame()
        result = clica.get_unique_parsed_values(df, 'nonexistent_column')
        assert result == set()
    
    def test_get_unique_parsed_values_with_whitespace(self):
        """Test avec des espaces dans les valeurs"""
        data = {
            'test_column': [' value1 , value2 ', 'value3, value1 ']
        }
        df = pd.DataFrame(data)
        
        result = clica.get_unique_parsed_values(df, 'test_column')
        expected = {'value1', 'value2', 'value3'}
        assert result == expected
    
    def test_get_unique_parsed_values_with_nan(self):
        """Test avec des valeurs NaN"""
        data = {
            'test_column': ['value1', None, 'value2', pd.NA]
        }
        df = pd.DataFrame(data)
        
        result = clica.get_unique_parsed_values(df, 'test_column')
        expected = {'value1', 'value2'}
        assert result == expected


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configuration globale pour tous les tests"""
    # S'assurer que les variables d'environnement de test sont définies
    os.environ.setdefault('API_URL', 'http://test.local:8000/api')
    os.environ.setdefault('TOKEN', 'test-token')
    os.environ.setdefault('VERIFY_CERTIFICATE', 'false')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])