"""
tests/test_only_harness.py

Test-Only Monkey-Patch Execution Harness (HARD-01).
IMPORTANT: This harness is strictly for offline unit testing of isolation primitives.
It MUST NEVER be used in production runtime to execute untrusted user code.
Production code strictly requires ephemeral containers (Docker/Podman); if unavailable,
execution is refused and static analysis is used instead.
"""

from __future__ import annotations

import builtins
import os
import subprocess
import sys
import tempfile
import time
from typing import Optional

from rl.sandbox.container import PatchResult


class MockRestrictedSubprocessHarness:
    """
    Test-only execution harness simulating memory, network, and filesystem restrictions
    via monkey-patching for environments without container engines.
    """

    def __init__(
        self,
        timeout: float = 5.0,
        memory_limit_mb: int = 512,
    ) -> None:
        self.timeout = max(0.5, float(timeout))
        self.memory_limit_mb = max(16, int(memory_limit_mb))

    def _generate_restricted_harness_code(self, user_code: str, sandbox_dir: str) -> str:
        escaped_sandbox_dir = os.path.normcase(os.path.realpath(sandbox_dir)).replace("\\", "\\\\")
        memory_bytes = self.memory_limit_mb * 1024 * 1024

        return f'''# Test-Only In-Process Restricted Harness
import os
import sys
import builtins
import tracemalloc

# 1. Memory Ceiling
MEMORY_LIMIT_BYTES = {memory_bytes}
tracemalloc.start()

def _check_memory_usage():
    current, peak = tracemalloc.get_traced_memory()
    if peak > MEMORY_LIMIT_BYTES or current > MEMORY_LIMIT_BYTES:
        raise MemoryError(f"Security violation: Memory limit exceeded (peak={{peak}} bytes > {{MEMORY_LIMIT_BYTES}} bytes)")

_orig_bytearray = builtins.bytearray
class _sandboxed_bytearray(_orig_bytearray):
    def __new__(cls, *args, **kwargs):
        if args and isinstance(args[0], int) and args[0] > MEMORY_LIMIT_BYTES:
            raise MemoryError(f"Security violation: Allocation of {{args[0]}} bytes exceeds limit {{MEMORY_LIMIT_BYTES}} bytes")
        res = super().__new__(cls, *args, **kwargs)
        _check_memory_usage()
        return res
builtins.bytearray = _sandboxed_bytearray

_orig_bytes = builtins.bytes
class _sandboxed_bytes(_orig_bytes):
    def __new__(cls, *args, **kwargs):
        if args and isinstance(args[0], int) and args[0] > MEMORY_LIMIT_BYTES:
            raise MemoryError(f"Security violation: Allocation of {{args[0]}} bytes exceeds limit {{MEMORY_LIMIT_BYTES}} bytes")
        res = super().__new__(cls, *args, **kwargs)
        _check_memory_usage()
        return res
builtins.bytes = _sandboxed_bytes

# 2. Network Isolation
import socket
def _blocked_socket(*args, **kwargs):
    raise PermissionError("Security violation: Outbound network access is strictly prohibited in sandbox")

socket.socket = _blocked_socket
socket.create_connection = _blocked_socket

# 3. Filesystem Confinement
SANDBOX_DIR = "{escaped_sandbox_dir}"
_orig_open = builtins.open

def _sandboxed_open(file, *args, **kwargs):
    mode = args[0] if args else kwargs.get("mode", "r")
    if any(m in str(mode) for m in ("w", "a", "+", "x")):
        abs_target = os.path.normcase(os.path.realpath(os.path.abspath(str(file))))
        allowed_dirs = [d for d in [SANDBOX_DIR, "/sandbox"] if d]
        cwd = os.path.normcase(os.path.realpath(os.getcwd()))
        if cwd == "/sandbox" or cwd.startswith(SANDBOX_DIR):
            allowed_dirs.append(cwd)
        is_allowed = any(
            abs_target == d
            or abs_target.startswith(d.rstrip("/\\\\") + "/")
            or abs_target.startswith(d.rstrip("/\\\\") + "\\\\")
            for d in allowed_dirs
        )
        if not is_allowed:
            raise PermissionError(f"Security violation: Write outside ephemeral sandbox is forbidden: {{file}}")
    return _orig_open(file, *args, **kwargs)

builtins.open = _sandboxed_open

# 4. User Code Execution
{user_code}
'''

    def run_test_code(self, code: str) -> PatchResult:
        """Run code inside the test-only monkey-patched subprocess."""
        start_time = time.time()
        with tempfile.TemporaryDirectory(prefix="aion_test_harness_") as tmpdir:
            harness_code = self._generate_restricted_harness_code(code, tmpdir)
            script_path = os.path.join(tmpdir, "entrypoint.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(harness_code)

            clean_env = {
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "TMP": tmpdir,
                "TEMP": tmpdir,
                "PYTHONUNBUFFERED": "1",
                "PYTHONHASHSEED": "0",
            }

            try:
                proc = subprocess.run(
                    [sys.executable, script_path],
                    cwd=tmpdir,
                    env=clean_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout,
                    text=True,
                )
                duration = time.time() - start_time
                stderr = proc.stderr
                exit_code = proc.returncode

                sec_violation: Optional[str] = None
                oom = False
                if "Security violation: Outbound network access" in stderr or ("PermissionError" in stderr and "network" in stderr.lower()):
                    sec_violation = "Network access prohibited"
                elif "Security violation: Write outside ephemeral sandbox" in stderr or ("PermissionError" in stderr and "sandbox" in stderr.lower()):
                    sec_violation = "Filesystem write outside sandbox prohibited"
                elif "Memory limit exceeded" in stderr or "MemoryError" in stderr:
                    oom = True

                success = (exit_code == 0) and (sec_violation is None) and not oom

                return PatchResult(
                    success=success,
                    exit_code=exit_code,
                    stdout=proc.stdout,
                    stderr=stderr,
                    duration_sec=round(duration, 4),
                    timed_out=False,
                    oom_killed=oom,
                    security_violation=sec_violation,
                    backend="test_only_subprocess_harness",
                )
            except subprocess.TimeoutExpired:
                duration = time.time() - start_time
                return PatchResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Execution timed out after {self.timeout}s",
                    duration_sec=round(duration, 4),
                    timed_out=True,
                    backend="test_only_subprocess_harness",
                )
            except Exception as e:
                duration = time.time() - start_time
                return PatchResult(
                    success=False,
                    exit_code=1,
                    stdout="",
                    stderr=str(e),
                    duration_sec=round(duration, 4),
                    backend="test_only_subprocess_harness",
                )
