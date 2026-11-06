# Phase 02 Plan 02: Synthetic Bug Injector, Clean Diff Generator & Real Review Miner Summary

**Plan ID:** `02-02`  
**Phase:** `02-build-the-yardstick`  
**Requirements Satisfied:** `BENCH-02`, `BENCH-03`  
**Execution Date:** 2026-11-05  
**Status:** Completed & Fully Verified  

---

## 1. Executive Summary

Plan 02-02 implemented the multi-source data generation and mining engine for **Aion-Bench**:
1. **Deterministic Bug Injector (`bench/generator/injector.py`)**: Implemented AST and structural mutation operators across Python and TypeScript/JavaScript. Injected bugs include inverted comparisons, off-by-one boundary errors, None/null dereferences, resource leaks, unsafe command sinks (command/SQL injection), swallowed exceptions, loose equality (`==` vs `===`), missing `await` keywords, and unhandled promises.
2. **Clean-Diff Negative Control Generator (`bench/generator/clean.py`)**: Implemented non-buggy code transformers (whitespace normalization, docstring/comment addition, type annotation, safe identifier renaming, unit test additions) that carry `is_clean_diff = True` and empty ground truth (`ground_truth = []`) to directly penalize hallucinated false-positive comments (FPR).
3. **Real PR Review Miner (`bench/mined/miner.py`)**: Implemented an ingestion pipeline for human pull request reviews. Filters out conversational chatter (`"LGTM"`, `"thanks!"`, `"approved"`), retains comments accompanied by subsequent corrective commits, categorizes comments into `bug`, `security`, `performance`, or `style`, and provides a bundled offline collection of 50 verified real-world PR reviews.
4. **Corpus Synthesizer (`bench/generator/synthesize.py`)**: Built a CLI synthesizer (`python -m bench.generator.synthesize --target 250 --output data/benchmark_cases_raw.json`) that combines ~50% injected bugs, ~30% clean-diff negatives, and ~20% mined PR reviews into a rich, schema-validated corpus of 250 benchmark cases balanced across Python and TypeScript.

---

## 2. Files Created & Modified

| File | Purpose |
|---|---|
| [`bench/generator/__init__.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/generator/__init__.py) | Exports `BugInjector` and `CleanDiffGenerator`. |
| [`bench/generator/injector.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/generator/injector.py) | Concrete AST/structural mutation operators with unified diff calculation and ground-truth line anchors. |
| [`bench/generator/clean.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/generator/clean.py) | Non-buggy code transformation engine generating true negatives (`is_clean_diff=True`) for FPR measurement. |
| [`bench/mined/__init__.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/mined/__init__.py) | Exports `ReviewMiner`. |
| [`bench/mined/miner.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/mined/miner.py) | PR review ingestion, chatter filtering, subsequent commit validation, and 50 curated real-world cases. |
| [`bench/generator/synthesize.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/generator/synthesize.py) | CLI synthesizer combining mutations, clean controls, and mined reviews into 250 validated cases. |
| [`data/benchmark_cases_raw.json`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/data/benchmark_cases_raw.json) | 250 synthesized benchmark cases (125 injected, 75 clean negatives, 50 mined). |
| [`tests/test_bench_generators.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/tests/test_bench_generators.py) | 23 comprehensive unit and integration tests for injectors, clean generators, miner, and synthesizer. |

---

## 3. Dataset Distribution Summary

Execution of `python -m bench.generator.synthesize --target 250 --output data/benchmark_cases_raw.json`:

```text
=================================================================
 AION-BENCH CORPUS SYNTHESIS SUMMARY
=================================================================
 Total Synthesized Cases: 250   
 Clean-Diff Negatives:    75     (30.0%) [FPR Control]
 Buggy Diffs:             175    (70.0%) [Recall Target]
-----------------------------------------------------------------
 Language Distribution:
   - typescript    : 126   (50.4%)
   - python        : 124   (49.6%)
-----------------------------------------------------------------
 Source Distribution:
   - mined_pr_review     : 50    (20.0%)
   - CleanDiffGenerator  : 75    (30.0%)
   - BugInjector         : 125   (50.0%)
=================================================================
```

All 250 cases strictly validate against `BenchmarkCase` Pydantic models with complete diffs, code contexts, and precise line anchors.

---

## 4. Verification & Test Results

### 4.1 Task 1: Bug Injector Verification
Command:
```bash
python -c "from bench.generator.injector import BugInjector; inj = BugInjector(); case = inj.inject_bug('def check(x):\n    if x > 0:\n        return True\n    return False\n', 'invert_comparison', language='python'); assert len(case.ground_truth) > 0; assert case.is_clean_diff is False; print('Injector verified:', case.ground_truth[0].description)"
```
**Output:** `Injector verified: Inverted comparison operator: Changed '>' to '<=', reversing branch logic.` (Exit code 0)

### 4.2 Task 2: Clean Diff Generator Verification
Command:
```bash
python -c "from bench.generator.clean import CleanDiffGenerator; gen = CleanDiffGenerator(); case = gen.generate_clean_diff('def add(a, b):\n    return a + b\n', 'add_type_hints', language='python'); assert case.is_clean_diff is True; assert len(case.ground_truth) == 0; print('Clean generator verified')"
```
**Output:** `Clean generator verified` (Exit code 0)

### 4.3 Task 3: Comprehensive Test Suite
Command:
```bash
python -m pytest tests/test_bench_generators.py -v
```
**Output:** `23 passed in 0.54s` (Exit code 0)

Combined test suite run (`tests/test_bench_runner.py` + `tests/test_bench_generators.py`):
```bash
python -m pytest tests/test_bench_runner.py tests/test_bench_generators.py -v
```
**Output:** `38 passed in 0.78s` (Exit code 0)

Code quality check:
```bash
ruff check bench/ tests/
```
**Output:** `All checks passed!` (Exit code 0)

---

## 5. Downstream Readiness for Wave 3

The synthetic corpus and real mined review assets are ready for Plan 02-03 (`02-03-gold-set-and-baseline-calibration.md`):
- `data/benchmark_cases_raw.json` supplies the 250 diverse raw benchmark cases.
- Plan 02-03 will partition these cases into stratified splits:
  - `dev.json` (40% development set)
  - `gold.json` (100–200 hand-audited calibration cases)
  - `test_locked.json` (cryptographically isolated test set)
  - `manifest.json` (SHA-256 immutability hashes for leakage guard `DATA-02`)
- Day-one baseline calibration runs can now benchmark the existing Aion prototype and linters using `bench/runner.py`.
