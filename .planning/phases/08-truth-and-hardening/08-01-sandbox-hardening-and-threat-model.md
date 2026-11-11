---
phase: 08-truth-and-hardening
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - rl/sandbox/container.py
  - docs/SANDBOX_THREAT_MODEL.md
  - tests/test_sandbox_escape.py
  - tests/test_only_harness.py
autonomous: true
requirements:
  - HARD-01
  - HARD-02
must_haves:
  truths:
    - Untrusted code execution strictly refuses host fallback when container runtime is absent, falling back to static analysis only.
    - Container commands enforce --pids-limit 64, --cap-drop ALL, --security-opt no-new-privileges, --network none, and non-root user.
    - docs/SANDBOX_THREAT_MODEL.md details the 9-layer containment model and threat landscape.
    - Sandbox escape tests cover symlinks, /proc, fork bombs, disk quota, DNS, env tokens, and mount boundaries.
  artifacts:
    - rl/sandbox/container.py
    - docs/SANDBOX_THREAT_MODEL.md
    - tests/test_sandbox_escape.py
    - tests/test_only_harness.py
---

<objective>
Verify and enforce Zero Untrusted Host Execution (`HARD-01`) and the hardened container sandbox threat model (`HARD-02`).
Ensure that no PR code, patch, or reproduction ever runs directly on the host machine, and that container isolation is covered by comprehensive escape tests.
</objective>

<tasks>

<task type="tracer">
  <name>Verify Zero Host Subprocess Execution and Container Hardening</name>
  <files>rl/sandbox/container.py, docs/SANDBOX_THREAT_MODEL.md</files>
  <action>
1. Confirm `rl/sandbox/container.py` raises `RuntimeError` or returns `VerificationResult(success=False, error="...")` without attempting in-process subprocess execution when container engines are absent.
2. Confirm container command builder sets:
   - `--pids-limit 64`
   - `--cap-drop ALL`
   - `--security-opt no-new-privileges`
   - `--network none`
   - `--read-only` root with non-root user `1000:1000`
3. Confirm `docs/SANDBOX_THREAT_MODEL.md` exists and defines all 4 threat landscapes and containment layers.
  </action>
  <verify>
pytest tests/test_sandbox_escape.py -v
  </verify>
</task>

<task>
  <name>Execute Full Sandbox Hardening Test Suite</name>
  <files>tests/test_sandbox_escape.py, tests/test_only_harness.py</files>
  <action>
Run all 11 sandbox escape test cases and the test harness to verify complete protection against malicious payloads.
  </action>
  <verify>
pytest tests/test_sandbox_escape.py tests/test_only_harness.py -v
  </verify>
</task>

</tasks>

