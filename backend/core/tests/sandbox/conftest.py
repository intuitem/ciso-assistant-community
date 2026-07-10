import pytest
import os
import sys
import shutil
from core.sandbox import LinuxSandbox, PassthroughSandbox

BWRAP_PATH = shutil.which("bwrap") or "/usr/bin/bwrap"


@pytest.fixture(scope="session")
def is_secure_env():
    """Returns True if bubblewrap is present, indicating a secure environment."""
    return os.path.exists(BWRAP_PATH)


@pytest.fixture
def sandbox(is_secure_env):
    """
    Returns a Sandbox instance appropriate for the current environment.
    If bubblewrap is present, returns LinuxSandbox.
    Otherwise, returns PassthroughSandbox with a warning.
    """
    if is_secure_env:
        return LinuxSandbox()
    else:
        print(
            "\nWARNING: bubblewrap not found. Using PassthroughSandbox for tests. Isolation tests may be skipped or modified."
        )
        return PassthroughSandbox()
