import pytest
import os
import sys
from core.sandbox import LinuxSandbox, PassthroughSandbox

NSJAIL_PATH = "/usr/local/bin/nsjail"

@pytest.fixture(scope="session")
def is_secure_env():
    """Returns True if nsjail is present, indicating a secure environment."""
    return os.path.exists(NSJAIL_PATH)

@pytest.fixture
def sandbox(is_secure_env):
    """
    Returns a Sandbox instance appropriate for the current environment.
    If nsjail is present, returns LinuxSandbox.
    Otherwise, returns PassthroughSandbox with a warning.
    """
    if is_secure_env:
        return LinuxSandbox()
    else:
        print("\nWARNING: nsjail not found. Using PassthroughSandbox for tests. Isolation tests may be skipped or modified.")
        return PassthroughSandbox()
