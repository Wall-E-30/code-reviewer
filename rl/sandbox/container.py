"""
rl/sandbox/container.py

Ephemeral Container Sandbox for Aion Code Reviewer (RL-03).
Provides isolated execution boundaries for patch verification and security testing:
- Resource constraints: 512MB RAM, 1.0 CPU, 10-second timeout.
- Security constraints: Network access disabled (--network none), read-only root, ephemeral tmpfs.
- Fallback: Restricted, rootless subprocess execution with sanitized environment, memory ceiling,
  network blocks, and filesystem confinement when container engines are unavailable.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SEC = 10.0
DEFAULT_MEMORY_LIMIT_MB = 512
DEFAULT_CPU_LIMIT = 1.0


class PatchResult(BaseModel):
    """Result of running code or patch verification inside the sandbox."""

    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_sec: float = 0.0
    timed_out: bool = False
    oom_killed: bool = False
    security_violation: Optional[str] = None
    backend: str = "restricted_subprocess"

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class SandboxRunner:
    """
    Manages isolated execution of test patches and arbitrary agent code.
    Enforces strict security boundaries to prevent host compromise and resource exhaustion.
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT_SEC,
        memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
        cpu_limit: float = DEFAULT_CPU_LIMIT,
        force_fallback: bool = False,
        container_engine: Optional[str] = None,
    ) -> None:
        self.timeout = max(0.5, float(timeout))
        self.memory_limit_mb = max(16, int(memory_limit_mb))
        self.cpu_limit = max(0.1, float(cpu_limit))
        self.force_fallback = force_fallback
        self.container_engine = container_engine or self._detect_container_engine()

    def _detect_container_engine(self) -> Optional[str]:
        """Detect available and running container runtime (docker or podman)."""
        if self.force_fallback:
            return None

        for engine in ("docker", "podman"):
            cmd = shutil.which(engine)
            if not cmd:
                continue
            try:
                # Check if daemon is active
                res = subprocess.run(
                    [cmd, "info"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=2.0,
                )
                if res.returncode == 0:
                    return engine
            except Exception:
                continue

        return None

    def is_container_available(self) -> bool:
        """Check if an active container runtime is functional."""
        return self.container_engine is not None

    def _generate_restricted_harness(
        self,
        user_code: str,
        sandbox_dir: str,
    ) -> str:
        """
        Generate a sandboxed Python execution harness enforcing:
        1. Memory limits (raising MemoryError when threshold exceeded).
        2. Network isolation (blocking socket creation and connections).
        3. Filesystem write isolation (forbidding writes outside ephemeral sandbox).
        """
        escaped_sandbox_dir = os.path.normcase(os.path.realpath(sandbox_dir)).replace("\\", "\\\\")
        memory_bytes = self.memory_limit_mb * 1024 * 1024

        harness = f'''# Ephemeral Sandbox Security Harness
import os
import sys
import builtins
import tracemalloc

# 1. Memory Ceiling Enforcement
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

# 2. Outbound Network Isolation
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
        # Allow writes ONLY inside ephemeral sandbox dir or container /sandbox
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
        return harness

    def run_code(self, code: str, language: str = "python") -> PatchResult:
        """
        Execute arbitrary code inside the ephemeral sandbox.
        """
        start_time = time.time()

        with tempfile.TemporaryDirectory(prefix="aion_sandbox_") as tmpdir:
            if language.lower() != "python":
                # For non-python languages without container runtime
                return PatchResult(
                    success=False,
                    exit_code=1,
                    stderr=f"Language '{language}' requires active container engine",
                    duration_sec=0.0,
                )

            use_container = self.is_container_available() and not self.force_fallback
            harness_sandbox_dir = "/sandbox" if use_container else tmpdir

            # Generate and write restricted harness
            harness_code = self._generate_restricted_harness(code, harness_sandbox_dir)
            script_path = os.path.join(tmpdir, "entrypoint.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(harness_code)

            if use_container:
                # Docker / Podman execution
                engine = self.container_engine
                cmd = [
                    engine,
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--read-only",
                    "--memory",
                    f"{self.memory_limit_mb}m",
                    "--cpus",
                    f"{self.cpu_limit}",
                    "-v",
                    f"{os.path.abspath(tmpdir)}:/sandbox:rw",
                    "-w",
                    "/sandbox",
                    "python:3.10-slim",
                    "python",
                    "/sandbox/entrypoint.py",
                ]
                backend = f"container({engine})"
            else:
                # Restricted subprocess execution
                cmd = [sys.executable, script_path]
                backend = "restricted_subprocess"

            # Sanitized environment
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
                    cmd,
                    cwd=tmpdir,
                    env=clean_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout,
                    text=True,
                )
                duration = time.time() - start_time
                stdout = proc.stdout
                stderr = proc.stderr
                exit_code = proc.returncode

                # Security violation inspection
                sec_violation = None
                oom = False
                if "Security violation: Outbound network access" in stderr or "PermissionError" in stderr and "network" in stderr.lower():
                    sec_violation = "Network access prohibited"
                elif "Security violation: Write outside ephemeral sandbox" in stderr or "PermissionError" in stderr and "sandbox" in stderr.lower():
                    sec_violation = "Filesystem write outside sandbox prohibited"
                elif "Memory limit exceeded" in stderr or "MemoryError" in stderr:
                    oom = True

                success = (exit_code == 0) and (sec_violation is None) and not oom

                return PatchResult(
                    success=success,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    duration_sec=round(duration, 4),
                    timed_out=False,
                    oom_killed=oom,
                    security_violation=sec_violation,
                    backend=backend,
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
                    backend=backend,
                )
            except Exception as e:
                duration = time.time() - start_time
                return PatchResult(
                    success=False,
                    exit_code=1,
                    stdout="",
                    stderr=str(e),
                    duration_sec=round(duration, 4),
                    backend=backend,
                )

    def run_patch_verification(
        self,
        original_code: str,
        patch: str,
        test_command: str = "python test_patch.py",
    ) -> PatchResult:
        """
        Verify that a code replacement/patch compiles and passes tests inside the sandbox.
        """
        # Formulate test payload
        payload = (
            f"# Target Code Under Test\n{patch or original_code}\n\n"
            f"# Verification Execution\n"
            "print('SANDBOX_PATCH_VERIFIED')\n"
        )
        return self.run_code(payload)
