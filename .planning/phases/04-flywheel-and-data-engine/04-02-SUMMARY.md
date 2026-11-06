# Phase 04 Plan 02: Gymnasium ReviewEnv, Verifiable Reward & Container Sandbox — Summary

**Execution Date:** 2026-11-06  
**Phase:** `04-flywheel-and-data-engine`  
**Plan:** `02` (`04-02-gymnasium-reviewenv-and-sandbox.md`)  
**Status:** Completed  
**Requirements Satisfied:** `RL-01`, `RL-02`, `RL-03`, `RL-04`

---

## 1. Overview & Key Accomplishments

Plan 04-02 transitions Aion Code Reviewer from static heuristics to a production-grade Reinforcement Learning environment and verifiable evaluation infrastructure:

1. **Gymnasium ReviewEnv (`rl/env.py`, `RL-01`):**
   - Implemented standard Gymnasium `gym.Env` architecture modeling code review as a multi-step MDP.
   - Observation space: Unified git diff, full file context, file path, language, and active repository conventions.
   - Action space: `post_comment` with line anchor, category, explanation, suggestion, and `terminate` to complete review.
   - Truncation on step limit (`max_steps=10`) and natural termination on `terminate` action.
   - Exportable OpenEnv specification helper (`export_openenv_spec()`) supporting seamless training harness integration.

2. **Objective Verifiable Reward Engine (`rl/reward.py`, `RL-02`):**
   - Multi-tier verifiable reward function:
     - $+1.00$ for ground-truth logic / performance bug hits (within line window $\pm 3$).
     - $+1.50$ for critical security vulnerability hits.
     - $-0.75$ for false positive comments on non-buggy code.
     - $-1.50$ for clean-diff violations (posting comments on clean pull requests).
     - $-0.25$ for subjective nitpicks or cosmetic distractions on real bugs.
     - $+0.50$ bonus for syntactically valid, actionable code replacements.
     - $-0.50$ penalty for zero-delta copy-paste suggestions.
     - $-0.50$ penalty for missed bugs (false negatives).
   - Coercion helpers for transparent compatibility with `ReviewComment`, `CandidateComment`, and dict payloads.

3. **Reward Hacking Red-Team Audit (`tests/test_reward_hacking.py`, `RL-04`):**
   - Evaluated degenerate agent policies:
     - *Empty policy:* Scores $\le 0.0$ on buggy diffs due to missed bugs penalties while scoring $0.0$ on clean diffs.
     - *All-line spam policy:* Indiscriminately commenting on every line incurs heavy false-positive penalties resulting in deeply negative net rewards ($R < -5.0$).
     - *Generic text policy ("Please fix this"):* Fails suggestion validity checks and incurs nitpick/FP penalties.
     - *Copy-paste suggestion policy:* Detected as zero-delta duplication and penalized.

4. **Ephemeral Container Sandbox (`rl/sandbox/container.py`, `RL-03`):**
   - Ephemeral sandbox runner enforcing:
     - Resource limits: 512MB RAM, 1.0 CPU, 10-second timeout.
     - Security isolation: `--network none` outbound socket blocking, read-only root with isolated ephemeral tmpfs.
     - Graceful fallback: Rootless subprocess execution within restricted temporary directories when container runtimes (Docker/Podman) are inactive, strictly blocking socket calls, confining writes, and limiting allocations.
   - Automated escape test suite (`tests/test_sandbox_escape.py`):
     - Blocks outbound socket creation/connections.
     - Forbids writing files outside the sandbox directory boundary.
     - Enforces CPU timeout on infinite loops.
     - Prevents memory exhaustion attacks (> 512MB).

---

## 2. Files Created and Modified

| File | Status | Description |
|---|---|---|
| `rl/env.py` | Created | Gymnasium `ReviewEnv` MDP environment and OpenEnv specification helper (`RL-01`). |
| `rl/reward.py` | Created | Objective multi-tier verifiable reward function and suggestion validation (`RL-02`). |
| `rl/sandbox/__init__.py` | Created | Module exports for sandbox execution (`RL-03`). |
| `rl/sandbox/container.py` | Created | `SandboxRunner` with container execution and rootless restricted subprocess fallback (`RL-03`). |
| `rl/__init__.py` | Modified | Exported `ReviewEnv`, `VerifiableRewardCalculator`, `SandboxRunner`, `PatchResult`, `export_openenv_spec`. |
| `tests/test_review_env.py` | Created | Unit test suite for `ReviewEnv` reset, step, termination, truncation, and OpenEnv export. |
| `tests/test_reward_hacking.py` | Created | Red-team test suite auditing empty, spam, generic, and zero-delta policies (`RL-04`). |
| `tests/test_sandbox_escape.py` | Created | Automated escape test suite verifying network, filesystem, timeout, and memory isolation (`RL-03`). |

---

## 3. Verification & Test Results

### Automated Verification Commands
```bash
# Task 1: ReviewEnv Verification
python -c "from rl.env import ReviewEnv; env = ReviewEnv(); obs, info = env.reset(); assert 'diff' in obs; obs, r, term, trunc, info = env.step({'action_type': 'terminate'}); assert term is True; print('ReviewEnv verified')"
# Output: ReviewEnv verified

# Task 2: Reward Hacking Red-Team Audit
python -m pytest tests/test_reward_hacking.py -v
# Output: 6 passed in 0.64s

# Task 3: Sandbox Escape Suite & ReviewEnv
python -m pytest tests/test_review_env.py tests/test_reward_hacking.py tests/test_sandbox_escape.py -v
# Output: 19 passed in 10.81s

# Combined RL & Flywheel Test Suite
python -m pytest tests/test_review_env.py tests/test_reward_hacking.py tests/test_sandbox_escape.py tests/test_flywheel.py -v
# Output: 33 passed in 12.59s

# Linter Quality Gate
python -m ruff check rl/ tests/
# Output: All checks passed!
```

---

## 4. Downstream Readiness

The completion of Plan 04-02 satisfies requirements `RL-01`, `RL-02`, `RL-03`, and `RL-04`.
Wave 3 readiness:
- **Plan 04-03:** Verifiable Data Engine: Synthesizing $\ge 10,000$ verified episodes (`DATA-01`) and cryptographic leakage guard ensuring zero overlap with Aion-Bench (`DATA-02`).
