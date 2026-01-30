import pytest
import io
import zipfile
from unittest.mock import MagicMock, patch, ANY
from django.core.files.uploadedfile import SimpleUploadedFile
from core.excel import ExcelUploadHandler
from core.sandbox import SandboxViolationError, SandboxTimeoutError


@pytest.fixture
def mock_settings(monkeypatch):
    from pathlib import Path

    mock_base_dir = MagicMock(spec=Path)

    # Mock path division / operator
    def mock_div(other):
        m = MagicMock(spec=Path)
        m.__truediv__.side_effect = mock_div
        m.exists.return_value = True
        m.resolve.return_value = m
        m.__str__.return_value = f"/mock/path/{other}"
        return m

    mock_base_dir.__truediv__.side_effect = mock_div

    monkeypatch.setattr("django.conf.settings.BASE_DIR", mock_base_dir)
    return mock_base_dir


@pytest.fixture
def mock_sandbox():
    sandbox = MagicMock()
    return sandbox


@pytest.fixture
def mock_sandbox_factory(mock_sandbox):
    with patch("core.excel.SandboxFactory") as mock:
        mock.create.return_value = mock_sandbox
        yield mock


@pytest.fixture
def valid_excel_content():
    # Create a minimal valid zip file (Excel files are zips)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.txt", "data")
    return buffer.getvalue()


@pytest.fixture
def excel_handler(mock_settings, mock_sandbox_factory):
    # Ensure script path check passes
    # If script_path resolves to a Mock, exists() returns a Mock (truthy)
    # We just need to make sure we can instantiate it
    handler = ExcelUploadHandler()
    return handler


class TestExcelUploadHandler:
    def test_init_script_not_found(self, mock_settings, mock_sandbox_factory):
        # We need to simulate script path NOT existing.
        # BASE_DIR / "scripts" / "convert_library_v2.py"
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            with pytest.raises(FileNotFoundError):
                ExcelUploadHandler()

    def test_process_upload_empty_file(self, excel_handler):
        uploaded_file = SimpleUploadedFile("test.xlsx", b"")
        result = excel_handler.process_upload(uploaded_file)
        assert result["status"] == 400
        assert result["error"] == "No file uploaded"

    def test_process_upload_too_large(self, excel_handler):
        uploaded_file = SimpleUploadedFile("test.xlsx", b"data")
        # Mock size attribute
        uploaded_file.size = excel_handler.max_file_size + 1

        result = excel_handler.process_upload(uploaded_file)
        assert result["status"] == 413
        assert "File too large" in result["error"]

    def test_validate_excel_invalid_zip(self, excel_handler):
        with pytest.raises(SandboxViolationError, match="Invalid Excel file format"):
            excel_handler._validate_excel(b"not a zip file")

    def test_validate_excel_zip_bomb(self, excel_handler):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # High compression: 100KB of '0's
            zf.writestr("bomb.xml", b"0" * 100 * 1024)

        with pytest.raises(SandboxViolationError, match="Suspicious compression ratio"):
            excel_handler._validate_excel(buffer.getvalue())

    @patch("core.excel.openpyxl.load_workbook")
    def test_process_upload_success_basic(
        self, mock_load_workbook, excel_handler, valid_excel_content, mock_sandbox
    ):
        # Mock sheet names to return standard v2 sheets
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["library_meta", "controls"]
        mock_load_workbook.return_value = mock_wb

        # Mock sandbox output
        mock_sandbox.run_python.return_value = "yaml_content"

        uploaded_file = SimpleUploadedFile("test.xlsx", valid_excel_content)
        result = excel_handler.process_upload(uploaded_file)

        assert result["status"] == 200
        assert result["yaml"] == "yaml_content"

        # Verify correct script was called
        # Only main conversion script should be called
        assert mock_sandbox.run_python.call_count == 1
        call_args = mock_sandbox.run_python.call_args[1]
        # Since script_path is a Mock, check if it was cast to str
        assert call_args["script_path"]
        assert call_args["input_filename"] == "library.xlsx"



    @patch("core.excel.openpyxl.load_workbook")
    def test_process_upload_cis_prep(
        self, mock_load_workbook, excel_handler, valid_excel_content, mock_sandbox
    ):
        # We need to handle multiple calls to load_workbook
        mock_wb_cis = MagicMock()
        mock_wb_cis.sheetnames = ["Controls V8"]

        mock_wb_v2 = MagicMock()
        mock_wb_v2.sheetnames = ["library_meta", "controls"]

        mock_load_workbook.side_effect = [mock_wb_cis, mock_wb_v2]

        mock_sandbox.run_python.side_effect = [
            b"prep_output",  # Prep result
            "yaml_content",  # Main result (skipped v1 conversion because v2 detected)
        ]

        uploaded_file = SimpleUploadedFile("test.xlsx", valid_excel_content)
        result = excel_handler.process_upload(uploaded_file)

        assert result["status"] == 200
        assert mock_sandbox.run_python.call_count == 2

        # Check prep call
        args1 = mock_sandbox.run_python.call_args_list[0][1]
        assert "prep_cis_v2.py" in str(args1["script_path"])

        # Check main call uses prep output
        args2 = mock_sandbox.run_python.call_args_list[1][1]
        assert args2["input_data"] == b"prep_output"

    @patch("core.excel.openpyxl.load_workbook")
    def test_process_upload_sandbox_violation(
        self, mock_load_workbook, excel_handler, valid_excel_content, mock_sandbox
    ):
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["library_meta"]
        mock_load_workbook.return_value = mock_wb

        mock_sandbox.run_python.side_effect = SandboxViolationError("Violation")

        uploaded_file = SimpleUploadedFile("test.xlsx", valid_excel_content)
        result = excel_handler.process_upload(uploaded_file)

        assert result["status"] == 400
        assert "File failed security validation" in result["error"]

    @patch("core.excel.openpyxl.load_workbook")
    def test_process_upload_timeout(
        self, mock_load_workbook, excel_handler, valid_excel_content, mock_sandbox
    ):
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["library_meta"]
        mock_load_workbook.return_value = mock_wb

        mock_sandbox.run_python.side_effect = SandboxTimeoutError("Timeout")

        uploaded_file = SimpleUploadedFile("test.xlsx", valid_excel_content)
        result = excel_handler.process_upload(uploaded_file)

        assert result["status"] == 504
        assert "Processing timeout" in result["error"]

    def test_process_upload_invalid_zip_content(self, excel_handler):
        # Passing invalid zip content to trigger _validate_excel failure
        uploaded_file = SimpleUploadedFile("test.xlsx", b"invalid data")
        result = excel_handler.process_upload(uploaded_file)

        assert result["status"] == 400
        assert "failed security validation" in result["error"]
