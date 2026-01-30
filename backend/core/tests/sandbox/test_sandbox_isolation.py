import pytest
import os
import shutil
from core.sandbox import SandboxViolationError, SandboxTimeoutError


def test_filesystem_access(sandbox, is_secure_env):
    """Test accessing sensitive files."""
    code = """
try:
    with open('/etc/passwd', 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Error: {e}")
"""
    if is_secure_env:
        # In secure mode, this should fail either by being blocked or file not found
        # LinuxSandbox parses stderr for "permission denied" -> SandboxViolationError
        # OR it might just print "Error: [Errno 2] No such file or directory" if /etc is not mounted

        try:
            output = sandbox.run(code)
            # If it didn't raise, check output.
            # If /etc is not mounted, it prints "Error: ... No such file..." which is good (isolation working)
            # If it actually printed content of /etc/passwd, that's a fail.
            assert "root:" not in output
        except SandboxViolationError:
            # This is also an acceptable outcome
            pass
    else:
        # In passthrough mode, we expect it to succeed (read the file)
        # assuming the user running tests has read access to /etc/passwd (standard on unix)
        output = sandbox.run(code)
        if "No such file" not in output:
            assert (
                "root:" in output or "Error:" in output
            )  # "Error" if permissions denied by OS
        else:
            pytest.skip("/etc/passwd not found")


def test_network_access(sandbox, is_secure_env):
    """Test network connectivity."""
    code = """
import socket
try:
    socket.create_connection(("8.8.8.8", 53), timeout=2)
    print("connected")
except Exception as e:
    print(f"failed: {e}")
"""
    if is_secure_env:
        # Should fail
        try:
            output = sandbox.run(code)
            # nsjail with --disable_clone_newnet might make socket creation fail or connect fail
            assert "failed" in output.lower() or "connected" not in output
        except SandboxViolationError:
            pass
    else:
        # Passthrough
        output = sandbox.run(code)
        if "failed" in output:
            pytest.skip(f"Network check failed in passthrough (no internet?): {output}")
        assert "connected" in output


@pytest.mark.skipif(
    condition=lambda: not os.path.exists("/usr/bin/bwrap")
    and not shutil.which("bwrap"),
    reason="Memory limit test requires bubblewrap",
)
# Using the fixture value in 'if' is better, but skipif runs at collection time.
# We can check the fixture inside the test and skip.
def test_memory_limit(sandbox, is_secure_env):
    """Test memory limits."""
    if not is_secure_env:
        pytest.skip("Memory limits only enforced in secure environment (bubblewrap)")

    code = """
l = []
while True:
    l.append(b"0" * 1024 * 1024) # 1MB chunks
"""
    # default limit is 512MB

    with pytest.raises((SandboxTimeoutError, RuntimeError, SandboxViolationError)):
        # It might be killed by OOM (RuntimeError or specific SandboxTimeoutError logic in wrapper)
        sandbox.run(code)
