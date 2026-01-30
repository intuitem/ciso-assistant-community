from pathlib import Path
from typing import Any, Optional

import openpyxl
import structlog
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from core.sandbox import SandboxFactory, SandboxTimeoutError, SandboxViolationError

logger = structlog.get_logger(__name__)


class ExcelUploadHandler:
    """
    Django-specific handler for secure Excel processing using external conversion script.
    """

    DEFAULT_SCRIPT_PATH = (
        "scripts/convert_library_v2.py"  # Relative to backend directory
    )

    # TODO: if imported excel (or ) lacks the 'library_meta' sheet,
    V1_TO_V2_SCRIPT_PATH = "scripts/convert_v1_to_v2.py"

    CIS_V8_PREP_SCRIPT_PATH = "scripts/prep_cis.py"
    CSA_CCM_PREP_SCRIPT_PATH = "scripts/convert_ccm.py"

    # Default packager name to use when running prep scripts
    DEFAULT_PACKAGER = "intuitem"

    def __init__(
        self,
        max_file_size: int = 10 * 1024 * 1024,
        script_path: Optional[str] = None,
        compat_mode: int = 0,
        **sandbox_options,
    ):
        self.max_file_size = max_file_size
        self.compat_mode = compat_mode
        self.sandbox = SandboxFactory.create(**sandbox_options)

        # Resolve script path relative to Django settings or repo root
        if script_path is None:
            self.script_path = self._resolve_script_path()
        else:
            self.script_path = Path(script_path).resolve()

        if not self.script_path.exists():
            raise FileNotFoundError(
                f"Conversion script not found: {self.script_path}. "
                f"Ensure scripts/convert_library_v2.py exists in backend directory."
            )

    def _resolve_script_path(self) -> Path:
        """
        Resolve default script path relative to Django project structure.
        """
        return settings.BASE_DIR / "scripts" / "convert_library_v2.py"

    def _get_sheet_names(self, content: bytes) -> list[str]:
        """
        Extract sheet names from the Excel file content without full parsing.
        """
        import io

        try:
            # read_only=True and data_only=True for performance and safety
            wb = openpyxl.load_workbook(
                io.BytesIO(content), read_only=True, data_only=True
            )
            return wb.sheetnames
        except Exception:
            logger.warning("Failed to parse sheet names from Excel file", exc_info=True)
            return []

    def process_upload(
        self, uploaded_file: UploadedFile, compat_mode: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Process Django UploadedFile using external conversion script.
        """
        if not uploaded_file.size:
            logger.error("No file uploaded or file is empty")
            return {"error": "No file uploaded", "status": 400}
        if uploaded_file.size > self.max_file_size:
            logger.error(
                "Uploaded file exceeds maximum size",
                uploaded_file_size=uploaded_file.size,
                max_size=self.max_file_size,
            )
            return {
                "error": f"File too large (max {self.max_file_size} bytes)",
                "status": 413,
            }

        mode = compat_mode if compat_mode is not None else self.compat_mode

        try:
            content = uploaded_file.read()

            # Validate it's actually an Excel file (zip bomb check)
            self._validate_excel(content)

            # Framework Pre-processing

            sheet_names = self._get_sheet_names(content)
            prep_script = ""
            prep_output_filename = ""

            # Check for CIS V8
            if any(s.strip().lower().startswith("controls v8") for s in sheet_names):
                prep_script = self.CIS_V8_PREP_SCRIPT_PATH
                prep_output_filename = "cis-controls-v8.xlsx"

            # Check for CSA CCM
            elif "CCM" in sheet_names:
                prep_script = self.CSA_CCM_PREP_SCRIPT_PATH
                prep_output_filename = "ccm-controls-v4.xlsx"

            # If a prep script is identified, run it first
            if prep_script:
                logger.info(f"Detected framework requiring prep script: {prep_script}")
                content = self.sandbox.run_python(
                    script_path=prep_script,
                    input_data=content,
                    input_filename="input.xlsx",
                    output_filename=prep_output_filename,
                    args=["--packager", self.DEFAULT_PACKAGER],
                    binary_output=True,
                )

            # V1 compatibility

            sheet_names = self._get_sheet_names(content)
            if "library_meta" not in sheet_names:
                logger.info(
                    "Detected V1 library format; running V1 to V2 conversion",
                    sheet_names=sheet_names,
                )
                content = self.sandbox.run_python(
                    script_path=self.V1_TO_V2_SCRIPT_PATH,
                    input_data=content,
                    input_filename=prep_output_filename or "input.xlsx",
                    output_filename="library.xlsx",
                    args=[],
                    binary_output=True,  # This outputs bytes for next step
                )

            # Main Conversion

            # Run the external script in sandbox
            yaml_output = self.sandbox.run_python(
                script_path=str(self.script_path),
                input_data=content,
                input_filename="library.xlsx",
                output_filename="library.yaml",
                args=[
                    "--compat",
                    str(mode),
                    "--verbose",
                ],
                binary_output=False,
            )

            return {"yaml": yaml_output, "status": 200}

        except SandboxViolationError as e:
            logger.warning(f"Security violation in Excel upload: {e}", exc_info=True)
            return {"error": "File failed security validation", "status": 400}
        except SandboxTimeoutError:
            logger.warning("Excel conversion timed out", exc_info=True)
            return {
                "error": "Processing timeout - file may be too complex",
                "status": 504,
            }
        except FileNotFoundError as e:
            logger.error(f"Configuration error: {e}")
            return {"error": "Server configuration error", "status": 500}
        except Exception:
            logger.exception("Conversion failed")
            return {"error": "Processing failed", "status": 500}

    def _validate_excel(self, data: bytes):
        """Basic validation to prevent zip bombs"""
        import io
        import zipfile

        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                total_uncompressed = sum(info.file_size for info in zf.infolist())
                total_compressed = sum(info.compress_size for info in zf.infolist())

                if total_compressed == 0:
                    raise SandboxViolationError("Invalid zip file")

                ratio = total_uncompressed / total_compressed
                if ratio > 50:  # 50:1 compression ratio
                    raise SandboxViolationError("Suspicious compression ratio")

                if total_uncompressed > 100 * 1024 * 1024:  # 100MB
                    raise SandboxViolationError("File too large uncompressed")

        except zipfile.BadZipFile:
            raise SandboxViolationError("Invalid Excel file format")
