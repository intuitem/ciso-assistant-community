#!/usr/bin/env python3
"""Parallel functional test runner for CISO Assistant.

Runs Playwright functional tests in parallel, each in an isolated slot with its
own backend, frontend, MailHog, and SQLite database. Shared Keycloak instance.

Usage:
    python3 frontend/tests/run_functional_tests.py [OPTIONS] [TEST_FILES...] [PLAYWRIGHT_ARGS...]

Examples:
    python3 frontend/tests/run_functional_tests.py -j 4
    python3 frontend/tests/run_functional_tests.py -j 1 tests/functional/startup.test.ts
    python3 frontend/tests/run_functional_tests.py -e --headed --grep "login"
    python3 frontend/tests/run_functional_tests.py --timeout 30000 --retries 2
    python3 frontend/tests/run_functional_tests.py --report              # view latest report
    python3 frontend/tests/run_functional_tests.py --report 20260227-193500  # view specific run
"""

import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from threading import Lock
from typing import List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SlotConfig:
    """Port and path configuration for a given slot number (infrastructure only)."""
    slot_id: int
    backend_port: int
    frontend_port: int
    mailhog_smtp_port: int
    mailhog_web_port: int
    db_path: Path
    attachments_dir: Path

    @classmethod
    def for_slot(cls, slot_id: int, base_dir: Path) -> "SlotConfig":
        slot_dir = base_dir / f"slot-{slot_id}"
        return cls(
            slot_id=slot_id,
            backend_port=8200 + slot_id,
            frontend_port=4200 + slot_id,
            mailhog_smtp_port=1100 + slot_id,
            mailhog_web_port=8100 + slot_id,
            db_path=slot_dir / "test.sqlite3",
            attachments_dir=slot_dir / "attachments",
        )


@dataclass
class TestResult:
    """Result of running a single test file."""
    test_file: str
    exit_code: int
    duration: float
    slot_id: int
    output_dir: Path
    backend_log: Optional[Path] = None
    frontend_log: Optional[Path] = None


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def wait_for_port(port: int, host: str = "localhost", timeout: float = 30.0) -> bool:
    """Poll a TCP port until it accepts connections or timeout is reached."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def docker_cmd(no_sudo: bool = False) -> List[str]:
    """Return the docker command prefix, with or without sudo."""
    if no_sudo:
        return ["docker"]
    # Check if user can run docker without sudo
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return ["docker"]
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return ["sudo", "docker"]


def compute_hash(directory: Path, enterprise_dir: Optional[Path] = None) -> str:
    """Compute md5 hash of frontend source files for build caching."""
    h = hashlib.md5()
    if enterprise_dir:
        src_dirs = [enterprise_dir / "src", enterprise_dir / "messages"]
    else:
        src_dirs = [directory / "src", directory / "messages"]

    extensions = {".ts", ".svelte", ".json"}
    for src_dir in src_dirs:
        if not src_dir.exists():
            continue
        for fpath in sorted(src_dir.rglob("*")):
            if fpath.suffix in extensions and fpath.is_file():
                h.update(fpath.read_bytes())
    return h.hexdigest()


def find_test_files(frontend_dir: Path, enterprise: bool = False) -> List[str]:
    """Discover all functional test files."""
    if enterprise:
        test_dir = frontend_dir.parent / "enterprise" / "frontend" / ".build" / "frontend" / "tests" / "functional"
    else:
        test_dir = frontend_dir / "tests" / "functional"

    files = []
    for f in sorted(test_dir.rglob("*.test.ts")):
        # Store as relative path from frontend dir
        try:
            rel = f.relative_to(frontend_dir)
        except ValueError:
            rel = f
        files.append(str(rel))
    return files


def is_test_file_arg(arg: str) -> bool:
    """Check if an argument looks like a test file path."""
    return (
        arg.endswith(".test.ts")
        or arg.endswith(".test.js")
        or os.path.exists(arg)
        or ("tests/" in arg and not arg.startswith("-"))
    )


def port_is_free(port: int) -> bool:
    """Check if a TCP port is free."""
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return False
    except OSError:
        return True


# ---------------------------------------------------------------------------
# Color / formatting helpers
# ---------------------------------------------------------------------------

class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = ""
        cls.BOLD = cls.DIM = cls.RESET = ""


if not sys.stdout.isatty():
    Colors.disable()


def log(msg: str, slot: Optional[int] = None):
    prefix = f"{Colors.DIM}[slot {slot}]{Colors.RESET} " if slot is not None else ""
    print(f"{prefix}{msg}", flush=True)


def log_error(msg: str):
    print(f"{Colors.RED}{msg}{Colors.RESET}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# SlotManager
# ---------------------------------------------------------------------------

class SlotManager:
    """Manages per-slot services: backend, frontend, MailHog."""

    def __init__(
        self,
        app_dir: Path,
        frontend_dir: Path,
        backend_dir: Path,
        slots_base_dir: Path,
        run_dir: Path,
        db_snapshot_path: Path,
        docker: List[str],
        enterprise: bool,
        verbose: bool,
        playwright_args: List[str],
        no_report: bool = False,
        enterprise_settings: str = "enterprise_core.settings",
    ):
        self.app_dir = app_dir
        self.frontend_dir = frontend_dir
        self.backend_dir = backend_dir
        self.slots_base_dir = slots_base_dir
        self.run_dir = run_dir
        self.db_snapshot_path = db_snapshot_path
        self.docker = docker
        self.enterprise = enterprise
        self.verbose = verbose
        self.playwright_args = playwright_args
        self.no_report = no_report
        self.enterprise_settings = enterprise_settings
        self._lock = Lock()
        self._processes: List[subprocess.Popen] = []
        self._containers: List[str] = []

    def _track_process(self, proc: subprocess.Popen):
        with self._lock:
            self._processes.append(proc)

    def _untrack_process(self, proc: subprocess.Popen):
        with self._lock:
            if proc in self._processes:
                self._processes.remove(proc)

    def _track_container(self, cid: str):
        with self._lock:
            self._containers.append(cid)

    def _untrack_container(self, cid: str):
        with self._lock:
            if cid in self._containers:
                self._containers.remove(cid)

    def cleanup_all(self):
        """Kill all tracked processes and containers."""
        with self._lock:
            procs = list(self._processes)
            containers = list(self._containers)

        for proc in procs:
            self._kill_process(proc)

        for cid in containers:
            self._stop_container(cid)

    def _kill_process(self, proc: subprocess.Popen):
        try:
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except OSError:
                pass

    def _stop_container(self, container_id: str):
        try:
            subprocess.run(
                self.docker + ["stop", container_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        try:
            subprocess.run(
                self.docker + ["rm", "-f", container_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def run_test(self, test_file: str, slot_id: int) -> TestResult:
        """Run a single test file in an isolated slot."""
        config = SlotConfig.for_slot(slot_id, self.slots_base_dir)
        start_time = time.monotonic()
        backend_proc = None
        frontend_proc = None
        mailhog_cid = None
        backend_log_fh = None
        frontend_log_fh = None

        # Compute per-test output directory
        try:
            test_rel = Path(test_file).relative_to("tests/functional")
        except ValueError:
            test_rel = Path(Path(test_file).name)
        test_output_dir = self.run_dir / test_rel.parent / test_rel.name
        test_output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Prepare slot directory
            config.db_path.parent.mkdir(parents=True, exist_ok=True)
            config.attachments_dir.mkdir(parents=True, exist_ok=True)

            # Copy DB snapshot
            shutil.copy2(self.db_snapshot_path, config.db_path)

            # Start MailHog
            mailhog_name = f"ciso-test-mailhog-{slot_id}"
            # Remove stale container with same name
            subprocess.run(
                self.docker + ["rm", "-f", mailhog_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            result = subprocess.run(
                self.docker + [
                    "run", "-d",
                    "--name", mailhog_name,
                    "-p", f"{config.mailhog_smtp_port}:1025",
                    "-p", f"{config.mailhog_web_port}:8025",
                    "mailhog/mailhog",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                log_error(f"Failed to start MailHog for slot {slot_id}: {result.stderr}")
                return TestResult(
                    test_file=test_file, exit_code=1,
                    duration=time.monotonic() - start_time,
                    slot_id=slot_id, output_dir=test_output_dir,
                )
            mailhog_cid = result.stdout.strip()
            self._track_container(mailhog_cid)

            # Prepare backend environment
            git_version = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                capture_output=True, text=True, cwd=self.app_dir,
            ).stdout.strip()
            git_build = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, cwd=self.app_dir,
            ).stdout.strip()

            backend_env = {
                **os.environ,
                "SQLITE_FILE": str(config.db_path.relative_to(self.backend_dir)),
                "CISO_ASSISTANT_URL": f"http://localhost:{config.frontend_port}",
                "LOCAL_STORAGE_DIRECTORY": str(config.attachments_dir.relative_to(self.backend_dir)),
                "EMAIL_PORT": str(config.mailhog_smtp_port),
                "EMAIL_HOST": "localhost",
                "EMAIL_HOST_USER": "tests@tests.com",
                "DEFAULT_FROM_EMAIL": "ciso-assistant@tests.net",
                "EMAIL_HOST_PASSWORD": "pwd",
                "ALLOWED_HOSTS": "localhost,127.0.0.1",
                "DJANGO_DEBUG": "True",
                "DJANGO_SUPERUSER_EMAIL": "admin@tests.com",
                "DJANGO_SUPERUSER_PASSWORD": "1234",
                "CISO_ASSISTANT_VERSION": git_version,
                "CISO_ASSISTANT_BUILD": git_build,
                "LICENSE_SEATS": "999",
            }
            # Unset postgres vars to force SQLite
            for key in ["POSTGRES_NAME", "POSTGRES_USER", "POSTGRES_PASSWORD"]:
                backend_env.pop(key, None)

            django_args = []
            if self.enterprise:
                django_args = [f"--settings={self.enterprise_settings}"]

            # Start backend — logs go to per-test dir
            backend_log = test_output_dir / "backend.log"
            backend_log_fh = open(backend_log, "w")

            backend_cmd = [
                "poetry", "run", "python3", "manage.py",
                "runserver", str(config.backend_port), "--noreload",
            ] + django_args

            backend_proc = subprocess.Popen(
                backend_cmd,
                cwd=str(self.backend_dir),
                env=backend_env,
                stdout=backend_log_fh if not self.verbose else None,
                stderr=subprocess.STDOUT if not self.verbose else None,
                start_new_session=True,
            )
            self._track_process(backend_proc)

            if not wait_for_port(config.backend_port, timeout=60):
                log_error(f"Backend on port {config.backend_port} did not start (slot {slot_id})")
                return TestResult(
                    test_file=test_file, exit_code=1,
                    duration=time.monotonic() - start_time,
                    slot_id=slot_id, output_dir=test_output_dir,
                    backend_log=backend_log,
                )

            # Start frontend (node build/index.js) — logs go to per-test dir
            frontend_log = test_output_dir / "frontend.log"
            frontend_log_fh = open(frontend_log, "w")

            # Determine frontend working dir and build path
            if self.enterprise:
                fe_work_dir = self.app_dir / "enterprise" / "frontend" / ".build" / "frontend"
            else:
                fe_work_dir = self.frontend_dir

            frontend_env = {
                **os.environ,
                "PORT": str(config.frontend_port),
                "ORIGIN": f"http://localhost:{config.frontend_port}",
                "PUBLIC_BACKEND_API_URL": f"http://localhost:{config.backend_port}/api",
            }

            frontend_proc = subprocess.Popen(
                ["node", "build/index.js"],
                cwd=str(fe_work_dir),
                env=frontend_env,
                stdout=frontend_log_fh if not self.verbose else None,
                stderr=subprocess.STDOUT if not self.verbose else None,
                start_new_session=True,
            )
            self._track_process(frontend_proc)

            if not wait_for_port(config.frontend_port, timeout=30):
                log_error(f"Frontend on port {config.frontend_port} did not start (slot {slot_id})")
                return TestResult(
                    test_file=test_file, exit_code=1,
                    duration=time.monotonic() - start_time,
                    slot_id=slot_id, output_dir=test_output_dir,
                    backend_log=backend_log, frontend_log=frontend_log,
                )

            # Run Playwright test — blob reporter, per-test output isolation
            pw_env = {
                **os.environ,
                "FRONTEND_PORT": str(config.frontend_port),
                "MAILER_WEB_SERVER_PORT": str(config.mailhog_web_port),
                "PUBLIC_BACKEND_API_URL": f"http://localhost:{config.backend_port}/api",
                "ORIGIN": f"http://localhost:{config.frontend_port}",
                "PLAYWRIGHT_BLOB_OUTPUT_DIR": str(test_output_dir / "blob-report"),
            }
            if self.no_report:
                pw_env["PW_HTML_OPEN"] = "never"

            pw_cmd = [
                "pnpm", "exec", "playwright", "test",
                test_file,
                "--workers=1",
                f"--output={test_output_dir / 'pw-output'}",
                "--reporter=blob",
            ] + self.playwright_args

            log(f"Running {Colors.BOLD}{test_file}{Colors.RESET}", slot=slot_id)

            pw_result = subprocess.run(
                pw_cmd,
                cwd=str(fe_work_dir),
                env=pw_env,
                timeout=600,  # 10 min max per test file
            )

            duration = time.monotonic() - start_time

            # Rename directory to include pass/fail suffix
            suffix = ".PASSED" if pw_result.returncode == 0 else ".FAILED"
            final_dir = test_output_dir.parent / (test_output_dir.name + suffix)
            try:
                test_output_dir.rename(final_dir)
            except OSError:
                final_dir = test_output_dir  # fallback if rename fails

            return TestResult(
                test_file=test_file,
                exit_code=pw_result.returncode,
                duration=duration,
                slot_id=slot_id,
                output_dir=final_dir,
                backend_log=final_dir / "backend.log",
                frontend_log=final_dir / "frontend.log",
            )

        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start_time
            log_error(f"Test timed out: {test_file} (slot {slot_id})")
            return TestResult(
                test_file=test_file, exit_code=124,
                duration=duration, slot_id=slot_id, output_dir=test_output_dir,
            )
        except Exception as e:
            duration = time.monotonic() - start_time
            log_error(f"Error in slot {slot_id}: {e}")
            return TestResult(
                test_file=test_file, exit_code=1,
                duration=duration, slot_id=slot_id, output_dir=test_output_dir,
            )
        finally:
            # Cleanup slot
            if backend_proc:
                self._kill_process(backend_proc)
                self._untrack_process(backend_proc)
            if backend_log_fh:
                try:
                    backend_log_fh.close()
                except Exception:
                    pass

            if frontend_proc:
                self._kill_process(frontend_proc)
                self._untrack_process(frontend_proc)
            if frontend_log_fh:
                try:
                    frontend_log_fh.close()
                except Exception:
                    pass

            if mailhog_cid:
                self._stop_container(mailhog_cid)
                self._untrack_container(mailhog_cid)


# ---------------------------------------------------------------------------
# ParallelTestRunner
# ---------------------------------------------------------------------------

class ParallelTestRunner:
    """Orchestrates global setup, parallel execution, and reporting."""

    def __init__(self, args: argparse.Namespace, playwright_args: List[str], test_files: List[str]):
        self.args = args
        self.playwright_args = playwright_args
        self.requested_test_files = test_files
        self.enterprise = args.enterprise

        # Paths
        self.app_dir = Path(__file__).resolve().parent.parent.parent
        self.frontend_dir = self.app_dir / "frontend"
        self.backend_dir = self.app_dir / "backend"
        self.db_dir = self.backend_dir / "db"
        self.slots_base_dir = self.db_dir / "slots"
        self.results_dir = self.frontend_dir / "tests" / "results"
        # Separate snapshot from e2e-tests.sh (ours includes the superuser)
        self.db_snapshot_path = self.db_dir / "test-database-parallel.sqlite3"
        self.db_test_path = self.db_dir / "test-database.sqlite3"

        # Docker
        self.docker = docker_cmd(args.no_sudo)

        # State
        self.keycloak_cid: Optional[str] = None
        self.slot_manager: Optional[SlotManager] = None
        self._shutting_down = False

    def setup(self):
        """Global setup: check prerequisites, build frontend, prepare DB, start Keycloak."""
        self._check_prerequisites()
        self._clean_stale_containers()
        self._build_frontend()
        self._prepare_db_snapshot()
        self._start_keycloak()
        self._check_slot_ports()

    def _check_prerequisites(self):
        """Verify required tools are available."""
        required = ["docker", "poetry", "pnpm", "node"]
        missing = []
        for cmd in required:
            if shutil.which(cmd) is None:
                missing.append(cmd)
        if missing:
            log_error(f"Missing required tools: {', '.join(missing)}")
            sys.exit(1)

        # Check playwright is installed
        result = subprocess.run(
            ["pnpm", "exec", "playwright", "--version"],
            capture_output=True,
            cwd=str(self.frontend_dir),
        )
        if result.returncode != 0:
            log_error("Playwright is not installed. Run: pnpm exec playwright install")
            sys.exit(1)

        log(f"Prerequisites OK ({', '.join(required)}, playwright)")

    def _clean_stale_containers(self):
        """Remove containers from previous failed runs."""
        try:
            result = subprocess.run(
                self.docker + ["ps", "-aq", "--filter", "name=ciso-test-"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout.strip():
                container_ids = result.stdout.strip().split("\n")
                subprocess.run(
                    self.docker + ["rm", "-f"] + container_ids,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30,
                )
                log(f"Cleaned up {len(container_ids)} stale container(s)")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def _build_frontend(self):
        """Build frontend with hash-based caching."""
        if self.args.no_build:
            log("Skipping frontend build (--no-build)")
            return

        # Use a separate hash file from e2e-tests.sh (different hash algorithm)
        if self.enterprise:
            hash_file = self.frontend_dir / "tests" / ".frontend_hash_parallel.enterprise"
            enterprise_build_dir = self.app_dir / "enterprise" / "frontend" / ".build" / "frontend"
            current_hash = compute_hash(self.frontend_dir, enterprise_dir=enterprise_build_dir)
            build_marker = enterprise_build_dir / "build" / "index.js"
        else:
            hash_file = self.frontend_dir / "tests" / ".frontend_hash_parallel"
            current_hash = compute_hash(self.frontend_dir)
            build_marker = self.frontend_dir / "build" / "index.js"

        stored_hash = ""
        if hash_file.exists():
            stored_hash = hash_file.read_text().strip()

        if stored_hash == current_hash and build_marker.exists():
            log("Frontend build is up-to-date (hash match), skipping build")
            return

        # Build output exists but hash file is missing/stale (e.g. built by e2e-tests.sh)
        # Trust the existing build and record our hash for future runs
        if build_marker.exists() and not hash_file.exists():
            hash_file.write_text(current_hash)
            log("Frontend build exists (built externally), recorded hash for future runs")
            return

        log("Building frontend...")
        build_env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=8192"}
        if self.enterprise:
            result = subprocess.run(
                ["make", "clean"],
                cwd=str(self.app_dir / "enterprise" / "frontend"),
            )
            if result.returncode != 0:
                log_error("Enterprise frontend clean failed")
                sys.exit(1)
            result = subprocess.run(
                ["make"],
                cwd=str(self.app_dir / "enterprise" / "frontend"),
                env=build_env,
            )
        else:
            result = subprocess.run(
                ["pnpm", "run", "build"],
                cwd=str(self.frontend_dir),
                env=build_env,
            )

        if result.returncode != 0:
            log_error("Frontend build failed")
            sys.exit(1)

        hash_file.write_text(current_hash)
        log("Frontend build complete")

    def _prepare_db_snapshot(self):
        """Migrate DB and create snapshot for slot copying."""
        if self.args.keep_snapshot and self.db_snapshot_path.exists():
            log("Using existing DB snapshot")
            return

        log("Preparing database snapshot...")
        self.db_dir.mkdir(parents=True, exist_ok=True)

        # Remove existing snapshots and test DB
        for path in [self.db_snapshot_path, self.db_test_path]:
            if path.exists():
                path.unlink()

        env = {
            **os.environ,
            "SQLITE_FILE": f"db/{self.db_test_path.name}",
            "DJANGO_SUPERUSER_EMAIL": "admin@tests.com",
            "DJANGO_SUPERUSER_PASSWORD": "1234",
            "CISO_ASSISTANT_URL": "http://localhost:4200",
            "ALLOWED_HOSTS": "localhost,127.0.0.1",
            "DJANGO_DEBUG": "True",
            "LICENSE_SEATS": "999",
        }
        for key in ["POSTGRES_NAME", "POSTGRES_USER", "POSTGRES_PASSWORD"]:
            env.pop(key, None)

        django_args = ""
        if self.enterprise:
            django_args = " --settings=enterprise_core.settings"

        # makemigrations + migrate
        for cmd_name, cmd in [
            ("makemigrations", f"poetry run python3 manage.py makemigrations{django_args}"),
            ("migrate", f"poetry run python3 manage.py migrate{django_args}"),
        ]:
            log(f"  Running {cmd_name}...")
            result = subprocess.run(
                cmd, shell=True,
                cwd=str(self.backend_dir),
                env=env,
            )
            if result.returncode != 0:
                log_error(f"Django {cmd_name} failed")
                sys.exit(1)

        # Create superuser
        result = subprocess.run(
            f"poetry run python3 manage.py createsuperuser --noinput{django_args}",
            shell=True,
            cwd=str(self.backend_dir),
            env=env,
        )
        if result.returncode != 0:
            log_error("Failed to create superuser (may already exist)")

        # WAL checkpoint for clean snapshot
        try:
            import sqlite3
            conn = sqlite3.connect(str(self.db_test_path))
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
        except Exception:
            pass

        # Create snapshot
        shutil.copy2(self.db_test_path, self.db_snapshot_path)
        log("Database snapshot ready")

    def _start_keycloak(self):
        """Start shared Keycloak container."""
        keycloak_name = "ciso-test-keycloak"

        # Remove stale
        subprocess.run(
            self.docker + ["rm", "-f", keycloak_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        keycloak_import_dir = self.frontend_dir / "tests" / "keycloak"

        log("Starting Keycloak...")
        result = subprocess.run(
            self.docker + [
                "run", "-d",
                "--name", keycloak_name,
                "-p", "8080:8080",
                "-e", "KEYCLOAK_ADMIN=admin",
                "-e", "KEYCLOAK_ADMIN_PASSWORD=admin",
                "-v", f"{keycloak_import_dir}:/opt/keycloak/data/import",
                "quay.io/keycloak/keycloak:26.3.0",
                "start-dev", "--import-realm",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            log_error(f"Failed to start Keycloak: {result.stderr}")
            sys.exit(1)

        self.keycloak_cid = result.stdout.strip()
        log(f"Keycloak started (container: {self.keycloak_cid[:12]})")

    def _check_slot_ports(self):
        """Verify all slot ports are free before starting."""
        parallelism = self.args.parallel
        blocked = []
        for i in range(parallelism):
            config = SlotConfig.for_slot(i, self.slots_base_dir)
            for name, port in [
                ("backend", config.backend_port),
                ("frontend", config.frontend_port),
                ("mailhog-smtp", config.mailhog_smtp_port),
                ("mailhog-web", config.mailhog_web_port),
            ]:
                if not port_is_free(port):
                    blocked.append(f"  slot {i} {name}: port {port}")
        if blocked:
            log_error("The following ports are already in use:\n" + "\n".join(blocked))
            log_error("Stop the conflicting services or adjust parallelism with -j")
            sys.exit(1)

    def run(self) -> int:
        """Run all tests in parallel and return exit code."""
        # Discover test files
        if self.requested_test_files:
            test_files = self.requested_test_files
        else:
            test_files = find_test_files(self.frontend_dir, self.enterprise)

        if not test_files:
            log_error("No test files found")
            return 1

        # Filter enterprise-only tests when not in enterprise mode
        if not self.enterprise:
            test_files = [f for f in test_files if "/enterprise/" not in f]

        parallelism = min(self.args.parallel, len(test_files))
        log(f"\nRunning {len(test_files)} test file(s) with {parallelism} parallel slot(s)\n")

        # Prepare results directory with timestamped run dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir = self.results_dir / time.strftime("%Y%m%d-%H%M%S")
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Create/update 'latest' symlink
        latest_link = self.results_dir / "latest"
        if latest_link.is_symlink() or latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(self.run_dir.name)

        # Create slot manager
        self.slot_manager = SlotManager(
            app_dir=self.app_dir,
            frontend_dir=self.frontend_dir,
            backend_dir=self.backend_dir,
            slots_base_dir=self.slots_base_dir,
            run_dir=self.run_dir,
            db_snapshot_path=self.db_snapshot_path,
            docker=self.docker,
            enterprise=self.enterprise,
            verbose=self.args.verbose,
            playwright_args=self.playwright_args,
            no_report=self.args.no_report,
        )

        # Slot queue for reuse
        slot_queue: Queue = Queue()
        for i in range(parallelism):
            slot_queue.put(i)

        results: List[TestResult] = []
        results_lock = Lock()
        overall_start = time.monotonic()

        def run_with_slot(test_file: str) -> TestResult:
            slot = slot_queue.get()
            try:
                result = self.slot_manager.run_test(test_file, slot)
                with results_lock:
                    results.append(result)
                    self._print_result(result)
                return result
            finally:
                slot_queue.put(slot)

        try:
            with ThreadPoolExecutor(max_workers=parallelism) as pool:
                futures = {pool.submit(run_with_slot, f): f for f in test_files}
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        test_file = futures[future]
                        log_error(f"Unexpected error running {test_file}: {e}")
        except KeyboardInterrupt:
            log("\nInterrupted, cleaning up...")
            if self.slot_manager:
                self.slot_manager.cleanup_all()
            raise

        overall_duration = time.monotonic() - overall_start

        # Post-run: merge reports, write summary, prune old runs
        self._merge_reports()
        self._write_summary_json(results, overall_duration, parallelism)
        self._prune_old_runs()

        return self._print_summary(results, overall_duration)

    def _print_result(self, result: TestResult):
        """Print a single test result line."""
        if result.exit_code == 0:
            status = f"{Colors.GREEN}PASS{Colors.RESET}"
        else:
            status = f"{Colors.RED}FAIL{Colors.RESET}"
        duration = f"({result.duration:.0f}s)"
        log(f"{status} {result.test_file:<60} {Colors.DIM}{duration}{Colors.RESET}", slot=result.slot_id)

    def _print_summary(self, results: List[TestResult], total_duration: float) -> int:
        """Print final summary and return exit code."""
        passed = [r for r in results if r.exit_code == 0]
        failed = [r for r in results if r.exit_code != 0]
        total = len(results)

        minutes = int(total_duration) // 60
        seconds = int(total_duration) % 60
        time_str = f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"

        print()
        print("=" * 70)
        if failed:
            print(f"{Colors.RED}{Colors.BOLD}Results: {len(passed)} passed, {len(failed)} failed, {total} total ({time_str}){Colors.RESET}")
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}Results: {len(passed)} passed, {len(failed)} failed, {total} total ({time_str}){Colors.RESET}")
        print("-" * 70)

        if failed:
            print(f"\n{Colors.RED}FAILED:{Colors.RESET}")
            for r in failed:
                print(f"  {r.test_file}")
                print(f"    Logs: {r.output_dir}/")
            print()

        print(f"\nTo view the full report:")
        print(f"  python3 frontend/tests/run_functional_tests.py --report")
        print("=" * 70)
        return 1 if failed else 0

    def _write_summary_json(self, results: List[TestResult], total_duration: float, parallelism: int):
        """Write machine-readable summary to run directory."""
        passed = [r for r in results if r.exit_code == 0]
        failed = [r for r in results if r.exit_code != 0]
        summary = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration": round(total_duration, 1),
            "parallelism": parallelism,
            "passed": len(passed),
            "failed": len(failed),
            "total": len(results),
            "results": [
                {
                    "file": r.test_file,
                    "status": "passed" if r.exit_code == 0 else "failed",
                    "exit_code": r.exit_code,
                    "duration": round(r.duration, 1),
                    "slot": r.slot_id,
                    "output_dir": str(r.output_dir),
                }
                for r in results
            ],
        }
        (self.run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    def _merge_reports(self):
        """Merge per-test blob reports into a single HTML report."""
        blob_dirs = list(self.run_dir.rglob("blob-report"))
        if not blob_dirs:
            return
        # Collect all blob zip files
        blob_files = []
        for d in blob_dirs:
            blob_files.extend(d.glob("*.zip"))
        if not blob_files:
            return
        # Create a temporary directory with all blobs for merge
        merged_input = self.run_dir / "blob-reports-merged"
        merged_input.mkdir(exist_ok=True)
        for bf in blob_files:
            shutil.copy2(bf, merged_input / bf.name)
        report_dir = self.run_dir / "report"
        env = {**os.environ, "PLAYWRIGHT_HTML_REPORT": str(report_dir)}
        subprocess.run(
            ["pnpm", "exec", "playwright", "merge-reports",
             str(merged_input), "--reporter", "html"],
            cwd=str(self.frontend_dir),
            env=env,
        )
        # Clean up merged input dir
        shutil.rmtree(merged_input, ignore_errors=True)

    def _prune_old_runs(self):
        """Remove old run directories, keeping only the most recent N."""
        run_pattern = re.compile(r"^\d{8}-\d{6}$")
        run_dirs = sorted(
            [d for d in self.results_dir.iterdir()
             if d.is_dir() and not d.is_symlink() and run_pattern.match(d.name)],
            key=lambda d: d.name,
        )
        keep = self.args.keep_runs
        for old_dir in run_dirs[:-keep]:
            shutil.rmtree(old_dir, ignore_errors=True)

    def cleanup(self):
        """Clean up all resources."""
        if self._shutting_down:
            return
        self._shutting_down = True

        log("\nCleaning up...")

        # Clean up slot manager processes
        if self.slot_manager:
            self.slot_manager.cleanup_all()

        # Stop Keycloak
        if self.keycloak_cid:
            log("Stopping Keycloak...")
            self._stop_container(self.keycloak_cid)

        # Remove slot directories
        if self.slots_base_dir.exists():
            shutil.rmtree(self.slots_base_dir, ignore_errors=True)

        # Clean up test history
        test_history = self.frontend_dir / "tests" / "utils" / ".testhistory"
        if test_history.exists():
            shutil.rmtree(test_history, ignore_errors=True)

        log("Cleanup done")

    def _stop_container(self, container_id: str):
        try:
            subprocess.run(
                self.docker + ["stop", container_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        try:
            subprocess.run(
                self.docker + ["rm", "-f", container_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def cleanup_and_exit(self):
        """Signal handler: cleanup and exit."""
        self.cleanup()
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def default_parallelism() -> int:
    """Compute default parallelism: nproc/2, capped at 8."""
    try:
        cpus = os.cpu_count() or 2
    except Exception:
        cpus = 2
    return min(max(cpus // 2, 1), 8)


def main():
    parser = argparse.ArgumentParser(
        description="Parallel functional test runner for CISO Assistant",
        epilog=textwrap.dedent("""\
            All unrecognized arguments are forwarded to Playwright.
            Examples:
              %(prog)s -j 4 --ui
              %(prog)s -e --headed --grep "login"
              %(prog)s --timeout 30000 --retries 2
              %(prog)s tests/functional/startup.test.ts --headed
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-j", "--parallel",
        type=int,
        default=default_parallelism(),
        help=f"Number of parallel slots (default: {default_parallelism()})",
    )
    parser.add_argument(
        "-e", "--enterprise",
        action="store_true",
        help="Run in enterprise mode",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip frontend build",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show backend/frontend logs in real-time",
    )
    parser.add_argument(
        "-k", "--keep-snapshot",
        action="store_true",
        default=True,
        help="Keep DB snapshot across runs (default: true)",
    )
    parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Fresh DB every run (don't keep snapshot for reuse)",
    )
    parser.add_argument(
        "--fresh-db",
        action="store_true",
        help="Delete existing DB snapshot and regenerate from scratch",
    )
    parser.add_argument(
        "--no-sudo",
        action="store_true",
        help="Run docker without sudo",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Don't open HTML report after tests finish",
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const="",
        default=None,
        help="Open HTML report for latest or specified run (no tests executed)",
    )
    parser.add_argument(
        "--keep-runs",
        type=int,
        default=5,
        help="Number of past test runs to keep (default: 5)",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List available test runs (one per line, newest last)",
    )
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List discovered test files (one per line)",
    )

    known_args, unknown_args = parser.parse_known_args()

    frontend_dir = Path(__file__).resolve().parent.parent
    results_dir = frontend_dir / "tests" / "results"

    # Handle --list-runs: print available runs and exit
    if known_args.list_runs:
        run_pattern = re.compile(r"^\d{8}-\d{6}$")
        if results_dir.exists():
            run_dirs = sorted(
                d.name for d in results_dir.iterdir()
                if d.is_dir() and not d.is_symlink() and run_pattern.match(d.name)
            )
            for name in run_dirs:
                print(name)
        sys.exit(0)

    # Handle --list-tests: print discovered test files and exit
    if known_args.list_tests:
        files = find_test_files(frontend_dir, known_args.enterprise)
        if not known_args.enterprise:
            files = [f for f in files if "/enterprise/" not in f]
        for f in files:
            print(f)
        sys.exit(0)

    # Handle --no-snapshot and --fresh-db overriding --keep-snapshot
    if known_args.no_snapshot:
        known_args.keep_snapshot = False
    if known_args.fresh_db:
        known_args.keep_snapshot = False

    # Handle --report: open report and exit without running tests
    if known_args.report is not None:
        run_name = known_args.report if known_args.report else "latest"
        report_dir = results_dir / run_name / "report"
        if not report_dir.exists():
            log_error(f"No report found at {report_dir}")
            sys.exit(1)
        subprocess.run(
            ["pnpm", "exec", "playwright", "show-report", str(report_dir)],
            cwd=str(frontend_dir),
        )
        sys.exit(0)

    # Separate test files from Playwright args
    test_files = []
    playwright_args = []
    for arg in unknown_args:
        if is_test_file_arg(arg):
            test_files.append(arg)
        else:
            playwright_args.append(arg)

    # Create runner
    runner = ParallelTestRunner(known_args, playwright_args, test_files)

    # Signal handling
    def signal_handler(signum, frame):
        runner.cleanup_and_exit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(runner.cleanup)

    try:
        runner.setup()
        exit_code = runner.run()
    except KeyboardInterrupt:
        exit_code = 130
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 1
    finally:
        runner.cleanup()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
