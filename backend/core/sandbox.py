import io
import logging
import os
import platform
import subprocess
import sys
import tempfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class SandboxViolationError(Exception):
    """Raised when sandbox restrictions prevent execution"""

    pass


class SandboxTimeoutError(Exception):
    """Raised when execution exceeds time limits"""

    pass


class Sandbox(ABC):
    """Abstract base for sandbox implementations"""

    def __init__(
        self,
        memory_limit_mb: int = 512,
        time_limit_sec: int = 30,
        enable_network: bool = False,
        allowed_paths: Optional[list] = None,
    ):
        self.memory_limit = memory_limit_mb
        self.time_limit = time_limit_sec
        self.enable_network = enable_network
        self.allowed_paths = allowed_paths or []

    @abstractmethod
    def run(
        self,
        code: str,
        input_data: Optional[bytes] = None,
        input_filename: str = "input.bin",
        extra_args: Optional[list] = None,
    ) -> str:
        pass

    @abstractmethod
    def run_python(
        self,
        script_path: str,
        input_data: Optional[bytes] = None,
        input_filename: str = "input.xlsx",
        output_filename: str = "output.yaml",
        args: Optional[List[str]] = None,
    ) -> str:
        pass

    def _validate_excel_size(self, data: bytes, max_ratio: int = 50):
        """Check compression ratio to detect zip bombs"""
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                total_uncompressed = sum(info.file_size for info in zf.infolist())
                total_compressed = sum(info.compress_size for info in zf.infolist())

                if total_compressed == 0:
                    total_compressed = 1

                ratio = total_uncompressed / total_compressed

                if ratio > max_ratio:
                    raise SandboxViolationError(
                        f"Zip bomb detected: compression ratio {ratio:.1f}x exceeds limit"
                    )

                if total_uncompressed > 100 * 1024 * 1024:
                    raise SandboxViolationError(
                        f"Excel too large: {total_uncompressed} bytes uncompressed"
                    )

        except zipfile.BadZipFile:
            raise SandboxViolationError("Invalid Excel file format (not a zip)")


class PassthroughSandbox(Sandbox):
    """
    Development sandbox without OS-level isolation.
    Still uses subprocess for crash protection and timeout enforcement,
    but without nsjail/sandbox-exec restrictions.
    """

    def run(
        self,
        code: str,
        input_data: Optional[bytes] = None,
        input_filename: str = "input.bin",
        extra_args: Optional[list] = None,
    ) -> str:
        """Execute Python code directly (no sandbox)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = None
            if input_data:
                input_path = os.path.join(tmpdir, input_filename)
                with open(input_path, "wb") as f:
                    f.write(input_data)

            cmd = [self._get_python(), "-c", code]
            if input_path:
                cmd.append(input_path)
            if extra_args:
                cmd.extend(extra_args)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.time_limit,
                    cwd=tmpdir,
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Execution failed: {result.stderr}")

                return result.stdout

            except subprocess.TimeoutExpired:
                raise SandboxTimeoutError("Execution exceeded time limit")

    def run_python(
        self,
        script_path: str,
        input_data: Optional[bytes] = None,
        input_filename: str = "input.xlsx",
        output_filename: str = "output.yaml",
        args: Optional[List[str]] = None,
    ) -> str:
        """Execute script directly (no sandbox)"""
        script_path = Path(script_path).resolve()
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, input_filename)
            output_path = os.path.join(tmpdir, output_filename)

            if input_data:
                with open(input_path, "wb") as f:
                    f.write(input_data)

            cmd = [
                self._get_python(),
                str(script_path),
                input_path,
                "--output",
                output_path,
            ]

            if args:
                cmd.extend(args)

            # Set environment variables for resource limits (soft protection)
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.time_limit,
                    cwd=tmpdir,
                    env=env,
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Script failed: {result.stderr}")

                if not os.path.exists(output_path):
                    raise RuntimeError("Script did not produce output file")

                with open(output_path, "r", encoding="utf-8") as f:
                    return f.read()

            except subprocess.TimeoutExpired:
                raise SandboxTimeoutError("Script execution exceeded time limit")

    def _get_python(self) -> str:
        """Return path to Python interpreter"""
        return sys.executable or "/usr/bin/python3"


class LinuxSandbox(Sandbox):
    """Production sandbox using nsjail"""

    NSJAIL_PATH = "/usr/local/bin/nsjail"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._check_nsjail()

    def _check_nsjail(self):
        if not os.path.exists(self.NSJAIL_PATH):
            raise RuntimeError(
                f"nsjail not found at {self.NSJAIL_PATH}. "
                "Install or set ENABLE_SANDBOX=False for development."
            )

    def run(self, code, input_data=None, input_filename="input.bin", extra_args=None):
        # ... (previous implementation) ...
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = None
            if input_data:
                input_path = os.path.join(tmpdir, input_filename)
                with open(input_path, "wb") as f:
                    f.write(input_data)
                os.chmod(input_path, 0o444)

            cmd = [
                self.NSJAIL_PATH,
                "--mode",
                "once",
                "--user",
                "65534",
                "--group",
                "65534",
                "--time_limit",
                str(self.time_limit),
                "--rlimit_as",
                str(self.memory_limit),
                "--rlimit_cpu",
                str(self.time_limit),
                "--rlimit_fsize",
                "10",
                "--disable_proc",
                "--quiet",
            ]

            if not self.enable_network:
                cmd.append("--disable_clone_newnet")

            cmd.extend(["--bindmount", f"{tmpdir}:/sandbox:rw"])

            # Add site-packages for imports
            import sys

            site_packages = None
            for path in sys.path:
                if "site-packages" in path and os.path.exists(path):
                    site_packages = path
                    break

            if site_packages:
                cmd.extend(
                    [
                        "--bindmount",
                        f"{site_packages}:/usr/lib/python3/dist-packages:ro",
                    ]
                )

            cmd.extend(["--", "/usr/bin/python3", "-c", code])
            if input_path:
                cmd.append(f"/sandbox/{input_filename}")
            if extra_args:
                cmd.extend(extra_args)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.time_limit + 5,
                    cwd=tmpdir,
                )

                if result.returncode != 0:
                    stderr = result.stderr.lower()
                    if "time limit" in stderr or "killed" in stderr:
                        raise SandboxTimeoutError("Execution timed out")
                    if any(x in stderr for x in ["permission denied", "seccomp"]):
                        raise SandboxViolationError(
                            f"Security violation: {result.stderr}"
                        )
                    raise RuntimeError(f"Sandbox error: {result.stderr}")

                return result.stdout

            except subprocess.TimeoutExpired:
                raise SandboxTimeoutError("Execution exceeded time limit")

    def run_python(
        self,
        script_path,
        input_data=None,
        input_filename="input.xlsx",
        output_filename="output.yaml",
        args=None,
    ):
        # ... (previous implementation) ...
        script_path = Path(script_path).resolve()
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        script_dir = str(script_path.parent)
        script_name = script_path.name

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, input_filename)
            if input_data:
                with open(input_path, "wb") as f:
                    f.write(input_data)
                os.chmod(input_path, 0o444)

            output_path = os.path.join(tmpdir, output_filename)

            cmd = [
                self.NSJAIL_PATH,
                "--mode",
                "once",
                "--user",
                "65534",
                "--group",
                "65534",
                "--time_limit",
                str(self.time_limit),
                "--rlimit_as",
                str(self.memory_limit),
                "--rlimit_cpu",
                str(self.time_limit),
                "--rlimit_fsize",
                "50",
                "--disable_proc",
                "--quiet",
                "--bindmount",
                f"{tmpdir}:/sandbox:rw",
                "--bindmount",
                f"{script_dir}:/scripts:ro",
            ]

            if not self.enable_network:
                cmd.append("--disable_clone_newnet")

            import sys

            site_packages = None
            for path in sys.path:
                if "site-packages" in path and os.path.exists(path):
                    site_packages = path
                    break

            if site_packages:
                cmd.extend(
                    [
                        "--bindmount",
                        f"{site_packages}:/usr/lib/python3/dist-packages:ro",
                    ]
                )

            cmd.extend(["--", "/usr/bin/python3", f"/scripts/{script_name}"])
            cmd.append(f"/sandbox/{input_filename}")
            cmd.extend(["--output", f"/sandbox/{output_filename}"])

            if args:
                cmd.extend(args)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.time_limit + 5,
                    cwd=tmpdir,
                )

                if result.returncode != 0:
                    stderr = result.stderr.lower()
                    if "time limit" in stderr or "killed" in stderr:
                        raise SandboxTimeoutError("Script execution timed out")
                    if any(
                        x in stderr
                        for x in [
                            "permission denied",
                            "seccomp",
                            "operation not permitted",
                        ]
                    ):
                        raise SandboxViolationError(
                            f"Security violation: {result.stderr}"
                        )
                    raise RuntimeError(f"Script failed: {result.stderr}")

                if not os.path.exists(output_path):
                    raise RuntimeError("Script did not produce output file")

                with open(output_path, "r", encoding="utf-8") as f:
                    return f.read()

            except subprocess.TimeoutExpired:
                raise SandboxTimeoutError("Script execution exceeded time limit")


class SandboxFactory:
    """Factory to create appropriate sandbox for current platform and settings"""

    @staticmethod
    def create(**kwargs) -> Sandbox:
        """
        Create sandbox instance based on Django settings.

        If ENABLE_SANDBOX is False (development), returns PassthroughSandbox
        without OS-level isolation but with subprocess crash protection.

        Settings:
            ENABLE_SANDBOX (bool): Default True. Set to False to disable
                                   nsjail/sandbox-exec in development.
        """
        # Lazy import to avoid AppRegistryNotReady during module import
        try:
            from django.conf import settings

            # Default to True (secure by default)
            enable_sandbox = getattr(settings, "ENABLE_SANDBOX", True)
        except ImportError:
            # Django not available, default to safe sandbox
            enable_sandbox = True

        if not enable_sandbox:
            logger.warning(
                "SECURITY WARNING: Running in DEVELOPMENT MODE without sandbox isolation. "
                "ENABLE_SANDBOX is set to False. Malicious files could harm the system."
            )
            return PassthroughSandbox(**kwargs)

        # Production: Use proper sandbox
        system = platform.system()

        if system == "Linux":
            return LinuxSandbox(**kwargs)
        else:
            raise RuntimeError(
                f"Unsupported platform: {system}. "
                f"Set ENABLE_SANDBOX=False to use passthrough mode, "
                f"or use Docker for consistent Linux behavior."
            )
