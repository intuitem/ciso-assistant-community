import os
import sys
import tempfile
from click.testing import CliRunner
from unittest.mock import patch

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
from clica import import_risk_assessment  # noqa: E402


class TestImportRiskAssessmentCommand:
    def test_import_risk_assessment_calls_backend(self):
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            file_path = tmp.name

        try:
            with patch("clica.upload_data_wizard_file") as mock_upload:
                result = runner.invoke(
                    import_risk_assessment,
                    [
                        "--file",
                        file_path,
                        "--perimeter",
                        "Test Perimeter",
                        "--matrix",
                        "Test Matrix",
                        "--folder",
                        "Global",
                    ],
                )

                assert result.exit_code == 0
                mock_upload.assert_called_once_with(
                    model_type="RiskAssessment",
                    file_path=file_path,
                    folder="Global",
                    perimeter="Test Perimeter",
                    framework=None,
                    matrix="Test Matrix",
                    requires_folder=False,
                    requires_perimeter=True,
                    requires_framework=False,
                    requires_matrix=True,
                )
        finally:
            os.unlink(file_path)

    def test_import_risk_assessment_requires_matrix(self):
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            file_path = tmp.name

        try:
            result = runner.invoke(
                import_risk_assessment,
                [
                    "--file",
                    file_path,
                    "--perimeter",
                    "Test Perimeter",
                ],
            )
            assert result.exit_code != 0
            assert "Missing option '--matrix'" in result.output
        finally:
            os.unlink(file_path)
