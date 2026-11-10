# Phase 8 Plan 03: Legacy Prototype Deprecation & Code/Doc Consistency Summary (HARD-04, HARD-05)

**Execution Date:** 2026-11-10  
**Phase:** 08-truth-and-hardening  
**Wave:** 3  
**Status:** Completed ✅  

---

## 1. Accomplishments

### 1.1 Legacy Prototype Files Archived (`HARD-04`)
- Archived early v0.1 AST node-counting prototype scripts into `legacy/`:
  - `legacy/env.py` (`CodeReviewEnv`)
  - `legacy/train_rl.py` (Prototype REINFORCE)
  - `legacy/train_autoregressive_rl.py` (Prototype autoregressive GPT-2)
- Added comprehensive `legacy/README.md` detailing the reward-hacking vulnerabilities of heuristic AST node count differences (node padding, fake loop complexity claims, lack of clean-diff negative controls).
- Added explicit deprecation warnings to root `env.py`, `train_rl.py`, and `train_autoregressive_rl.py` pointing maintainers and external users to `rl.env.ReviewEnv` and `rl/training/`.

### 1.2 Server Endpoints Migrated to ReviewEnv (`HARD-04`)
- Replaced legacy `CodeReviewEnv` dependency in `server/app.py` with `ServerReviewEnv` subclassing `ReviewEnv` (`rl/env.py`).
- Mapped standard task IDs (`style-cleanup`, `efficiency-boost`, `security-audit`) to concrete `BenchmarkCase` objects in `ServerReviewEnv`.
- Ensured `/reset`, `/step`, and `/state` execute through `ReviewEnv` Gymnasium spaces and verifiable rewards.

### 1.3 Purged Unmeasured Polynomial Speedup & Memory Percentages (`HARD-04`)
- Purged fabricated percentage calculations (`(score_diff * 90.0) + ...`) from `/optimize` and `/optimize_full` in `server/app.py`.
- Replaced synthetic claims with honest tags:
  - `perf_gain`: `"Static Analysis Verified [STATIC]"`
  - `mem_reduction`: `"AST Diagnostics [HEURISTIC]"`
- Updated `frontend/src/App.jsx` UI telemetry cards to display verified static analysis and AST diagnostics instead of synthetic speedup percentages.

### 1.4 Code and Documentation Reconciliation (`HARD-05`)
- In `bench/evaluator/matcher.py`: Explicitly documented matching algorithm as **Greedy Bipartite Line-Distance Matching within the line tolerance window** (specifically not Hungarian/Kuhn-Munkres).
- In `rl/bandit.py`: Explicitly documented threshold optimizer as **Per-Category Beta-Bernoulli Thompson Sampling with strict boundary clamps $[0.50, 0.95]$**.
- In `docs/ARCHITECTURE.md`: Created comprehensive architectural specification standardizing the benchmark CLI to `python -m bench.runner`, documenting `ReviewEnv`, the greedy matcher, and Thompson sampling bandit.

---

## 2. Verification Results

All 8 tests in `tests/test_legacy_deprecation_and_consistency.py` passed:
```
tests/test_legacy_deprecation_and_consistency.py::test_legacy_prototype_files_archived PASSED
tests/test_legacy_deprecation_and_consistency.py::test_root_deprecation_warnings PASSED
tests/test_legacy_deprecation_and_consistency.py::test_server_env_is_review_env_subclass PASSED
tests/test_legacy_deprecation_and_consistency.py::test_server_reset_and_step_endpoints PASSED
tests/test_legacy_deprecation_and_consistency.py::test_unmeasured_speedup_purged_from_optimize PASSED
tests/test_legacy_deprecation_and_consistency.py::test_matcher_greedy_bipartite_documentation PASSED
tests/test_legacy_deprecation_and_consistency.py::test_bandit_thompson_sampling_documentation PASSED
tests/test_legacy_deprecation_and_consistency.py::test_architecture_doc_consistency PASSED
============================== 8 passed in 4.93s ==============================
```
Full server test suite `tests/test_api.py` (14 tests) also passed cleanly with zero regressions.

---

## 3. Files Created / Modified
- `legacy/README.md`
- `legacy/env.py`
- `legacy/train_rl.py`
- `legacy/train_autoregressive_rl.py`
- `env.py`
- `train_rl.py`
- `train_autoregressive_rl.py`
- `server/app.py`
- `frontend/src/App.jsx`
- `bench/evaluator/matcher.py`
- `rl/bandit.py`
- `docs/ARCHITECTURE.md`
- `tests/test_legacy_deprecation_and_consistency.py`
