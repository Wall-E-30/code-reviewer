"""
tests/test_sandbox_escape.py

Automated sandbox escape and isolation test suite (RL-03):
Verifies that the ephemeral sandbox strictly enforces:
1. Outbound network isolation (blocking sockets / external calls).
2. Filesystem write confinement (forbidding writes outside ephemeral directory).
3. CPU timeout enforcement (terminating infinite loops within limit).
4. Memory allocation ceiling (preventing RAM exhaustion attacks).
5. Safe valid execution of verified patches.
"""

import os
import pytest
from rl.sandbox.container import SandboxRunner


def test_network_isolation():
    """
    Attempt to open outbound socket connection inside sandbox.
    Must raise security violation or fail with network error.
    """
    runner = SandboxRunner()
    code = (
        "import socket\n"
        "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "s.connect(('8.8.8.8', 53))\n"
    )

    result = runner.run_code(code)

    assert not result.success
    assert result.exit_code != 0
    assert (
        result.security_violation == "Network access prohibited"
        or "network" in result.stderr.lower()
        or "permissionerror" in result.stderr.lower()
    )


def test_filesystem_confinement():
    """
    Attempt to write a file outside the sandbox directory boundary.
    Must raise security violation and forbid write.
    """
    runner = SandboxRunner()
    code = (
        "import os\n"
        "target = os.path.abspath('../escaped_payload.txt')\n"
        "with open(target, 'w') as f:\n"
        "    f.write('hacked')\n"
    )

    result = runner.run_code(code)

    assert not result.success
    assert result.exit_code != 0
    assert (
        result.security_violation == "Filesystem write outside sandbox prohibited"
        or "outside ephemeral sandbox" in result.stderr.lower()
        or "permissionerror" in result.stderr.lower()
    )


def test_cpu_timeout_enforcement():
    """
    Attempt to run an infinite loop inside the sandbox.
    Must terminate within the configured timeout window.
    """
    timeout_sec = 2.0
    runner = SandboxRunner(timeout=timeout_sec)
    code = (
        "import time\n"
        "while True:\n"
        "    pass\n"
    )

    result = runner.run_code(code)

    assert result.timed_out is True
    assert not result.success
    assert result.duration_sec >= timeout_sec
    assert result.duration_sec <= (timeout_sec + 3.0)


def test_memory_limit_enforcement():
    """
    Attempt to allocate 1GB in a sandbox configured with 512MB RAM ceiling.
    Must raise MemoryError / OOM before host exhaustion.
    """
    runner = SandboxRunner(memory_limit_mb=512)
    code = (
        "big_buffer = bytearray(1024 * 1024 * 1024)  # 1GB allocation\n"
        "print('ALLOCATED_1GB')\n"
    )

    result = runner.run_code(code)

    assert not result.success
    assert result.oom_killed is True or "memory" in result.stderr.lower()
    assert "ALLOCATED_1GB" not in result.stdout


def test_valid_execution_in_sandbox():
    """
    Verify benign code executes cleanly and writes to ephemeral sandbox directory.
    """
    runner = SandboxRunner()
    code = (
        "with open('ephemeral_test.txt', 'w') as f:\n"
        "    f.write('SANDBOX_OK')\n"
        "with open('ephemeral_test.txt', 'r') as f:\n"
        "    print(f.read())\n"
    )

    result = runner.run_code(code)

    assert result.success is True
    assert result.exit_code == 0
    assert "SANDBOX_OK" in result.stdout
    assert result.security_violation is None


def test_run_patch_verification():
    """
    Verify standard patch verification helper.
    """
    runner = SandboxRunner()
    original_code = "def add(a, b):\n    return a - b\n"
    patch = "def add(a, b):\n    return a + b\n"

    result = runner.run_patch_verification(original_code, patch)

    assert result.success is True
    assert "SANDBOX_PATCH_VERIFIED" in result.stdout
