import os
import sys
import tempfile
from click.testing import CliRunner
from unittest.mock import MagicMock, call, patch

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
from clica import ensure_identifier, import_risk_assessment  # noqa: E402


def response(payload):
    mocked_response = MagicMock()
    mocked_response.status_code = 200
    mocked_response.json.return_value = payload
    return mocked_response


def test_ensure_identifier_resolves_framework_from_later_page():
    first_page = {
        "count": 3,
        "next": "/api/frameworks/?page=2",
        "results": [{"id": "first-id", "name": "First framework"}],
    }
    second_page = {
        "count": 3,
        "next": "https://example.test/api/frameworks/?page=3",
        "results": [{"id": "second-id", "name": "Second framework"}],
    }
    third_page = {
        "count": 3,
        "next": None,
        "results": [{"id": "third-id", "name": "Third framework"}],
    }

    with (
        patch("clica.API_URL", "https://example.test/api"),
        patch("clica.TOKEN", "test-token"),
        patch("clica.VERIFY_CERTIFICATE", True),
        patch(
            "clica.requests.get",
            side_effect=[
                response(first_page),
                response(second_page),
                response(third_page),
            ],
        ) as mock_get,
    ):
        assert (
            ensure_identifier("Third framework", "frameworks", "framework")
            == "third-id"
        )

    assert mock_get.call_args_list == [
        call(
            "https://example.test/api/frameworks",
            headers={"Authorization": "Token test-token"},
            verify=True,
        ),
        call(
            "https://example.test/api/frameworks/?page=2",
            headers={"Authorization": "Token test-token"},
            verify=True,
        ),
        call(
            "https://example.test/api/frameworks/?page=3",
            headers={"Authorization": "Token test-token"},
            verify=True,
        ),
    ]


def test_ensure_identifier_rejects_ambiguous_framework_name():
    frameworks = {
        "results": [
            {"id": "first-id", "name": "Duplicate framework"},
            {"id": "second-id", "name": "Duplicate framework"},
        ]
    }

    with (
        patch("clica.ids_map", return_value=frameworks),
        patch("clica.click.echo") as mock_echo,
    ):
        try:
            ensure_identifier("Duplicate framework", "frameworks", "framework")
        except SystemExit as exc:
            assert exc.code == 1
        else:
            raise AssertionError("Ambiguous framework name was not rejected")

    mock_echo.assert_called_once_with(
        "❌ Ambiguous framework name 'Duplicate framework', found 2", err=True
    )


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
