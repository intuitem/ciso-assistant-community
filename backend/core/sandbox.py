import io
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

import structlog

logger = structlog.get_logger(__name__)


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
        binary_output: bool = False,
    ) -> str | bytes:
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
    but without bubblewrap restrictions.
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

                return result.stdout + result.stderr

            except subprocess.TimeoutExpired:
                raise SandboxTimeoutError("Execution exceeded time limit")

    def run_python(
        self,
        script_path: str,
        input_data: Optional[bytes] = None,
        input_filename: str = "input.xlsx",
        output_filename: str = "output.yaml",
        args: Optional[List[str]] = None,
        binary_output: bool = False,
    ) -> str | bytes:
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

                mode = "rb" if binary_output else "r"
                encoding = None if binary_output else "utf-8"

                with open(output_path, mode, encoding=encoding) as f:
                    return f.read()

            except subprocess.TimeoutExpired:
                raise SandboxTimeoutError("Script execution exceeded time limit")

    def _get_python(self) -> str:
        """Return path to Python interpreter"""
        return sys.executable or "/usr/bin/python3"


class LinuxSandbox(Sandbox):
    """Production sandbox using bubblewrap (bwrap)"""

    BWRAP_PATH = shutil.which("bwrap") or "/usr/bin/bwrap"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._check_bwrap()

    def _check_bwrap(self):
        if not os.path.exists(self.BWRAP_PATH):
            raise RuntimeError(
                f"bubblewrap not found at {self.BWRAP_PATH}. "
                "Install with 'apt-get install bubblewrap' or set ENABLE_SANDBOX=False."
            )

    def _get_base_bwrap_cmd(self, tmpdir: str) -> List[str]:
        uid = os.getuid()
        gid = os.getgid()

        cmd = [
            self.BWRAP_PATH,
            "--unshare-all",
            "--die-with-parent",
            "--uid",
            str(uid),
            "--gid",
            str(gid),
            "--tmpfs",
            "/tmp",
            # Standard system paths
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/bin",
            "/bin",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/etc/alternatives",
            "/etc/alternatives",
        ]

        # 1. Mount /usr/local (Crucial for Docker/Pip packages)
        if os.path.exists("/usr/local"):
            cmd.extend(["--ro-bind", "/usr/local", "/usr/local"])

        # 2. Handle 64-bit libraries if they exist
        if os.path.exists("/lib64"):
            cmd.extend(["--ro-bind", "/lib64", "/lib64"])

        # 3. Explicitly find and bind site-packages (Replicates your nsjail logic)
        # This ensures 'openpyxl' and other dependencies are visible to the sandbox python
        site_packages = None
        for path in sys.path:
            if "site-packages" in path and os.path.exists(path):
                site_packages = path
                break

        if site_packages:
            # We bind the host's site-packages to the sandbox's dist-packages
            # This forces the sandbox Python to see these libraries.
            cmd.extend(["--ro-bind", site_packages, "/usr/lib/python3/dist-packages"])

        # Bind the working directory
        cmd.extend(["--bind", tmpdir, "/sandbox"])

        if self.enable_network:
            cmd.remove("--unshare-all")
            cmd.extend(["--unshare-ipc", "--unshare-uts"])

        return cmd

    def run(self, code, input_data=None, input_filename="input.bin", extra_args=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, input_filename)
            if input_data:
                with open(input_path, "wb") as f:
                    f.write(input_data)

            # 1024*1024 multiplier for MB to Bytes
            mem_bytes = self.memory_limit * 1024 * 1024
            # fsize limit in blocks (approx) or bytes depending on system,
            # usually bytes for prlimit. Setting strict limit.
            prlimit_cmd = ["prlimit", f"--as={mem_bytes}"]

            cmd = prlimit_cmd + self._get_base_bwrap_cmd(tmpdir)
            cmd.extend(["--chdir", "/sandbox", "--", "/usr/bin/python3", "-c", code])

            if input_data:
                cmd.append(f"/sandbox/{input_filename}")
            if extra_args:
                cmd.extend(extra_args)

            return self._execute(cmd, tmpdir)

    def run_python(
        self,
        script_path,
        input_data=None,
        input_filename="input.xlsx",
        output_filename="output.yaml",
        args=None,
        binary_output=False,
    ) -> str | bytes:
        script_path = Path(script_path).resolve()
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        script_dir = str(script_path.parent)
        script_name = script_path.name

        with tempfile.TemporaryDirectory() as tmpdir:
            if input_data:
                with open(os.path.join(tmpdir, input_filename), "wb") as f:
                    f.write(input_data)

            output_path = os.path.join(tmpdir, output_filename)
            mem_bytes = self.memory_limit * 1024 * 1024
            prlimit_cmd = ["prlimit", f"--as={mem_bytes}"]

            cmd = prlimit_cmd + self._get_base_bwrap_cmd(tmpdir)

            # Add script directory bind
            cmd.extend(["--ro-bind", script_dir, "/scripts"])

            cmd.extend(
                [
                    "--chdir",
                    "/sandbox",
                    "--",
                    "/usr/bin/python3",
                    f"/scripts/{script_name}",
                    f"/sandbox/{input_filename}",
                    "--output",
                    f"/sandbox/{output_filename}",
                ]
            )

            if args:
                cmd.extend(args)

            self._execute(cmd, tmpdir)

            mode = "rb" if binary_output else "r"
            encoding = None if binary_output else "utf-8"

            if not os.path.exists(output_path):
                raise RuntimeError(
                    "Sandbox script finished but did not produce output file"
                )

            with open(output_path, mode, encoding=encoding) as f:
                return f.read()

    def _execute(self, cmd: List[str], cwd: str) -> str:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.time_limit,
                cwd=cwd,
            )

            if result.returncode != 0:
                stderr = result.stderr.lower()
                if result.returncode == 137 or "memory" in stderr:
                    raise SandboxViolationError("Memory limit exceeded")

                # Check for other common bwrap failures
                if "bind" in stderr or "permissions" in stderr:
                    raise SandboxViolationError(
                        f"Security/Mount error: {result.stderr}"
                    )

                raise RuntimeError(f"Sandbox error: {result.stderr}")

            return result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            raise SandboxTimeoutError("Execution exceeded time limit")


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
                                   bubblewrap in development.
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
