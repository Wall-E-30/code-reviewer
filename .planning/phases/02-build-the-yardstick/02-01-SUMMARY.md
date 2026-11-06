# Phase 02 Plan 01: Benchmark Schema, Ground-Truth Matcher & CLI Runner Summary

**Plan ID:** `02-01`  
**Phase:** `02-build-the-yardstick`  
**Requirement Satisfied:** `BENCH-01`  
**Execution Date:** 2026-11-05  
**Status:** Completed & Fully Verified  

---

## 1. Executive Summary

Plan 02-01 established the foundational core of **Aion-Bench**: an open, reproducible, objective evaluation harness for automated code review that eliminates manual grading and unconstrained "LLM-as-a-judge" grading.

All three tasks have been implemented and verified:
1. **Pydantic Schema Architecture (`bench/schema.py`, `bench/__init__.py`)**: Implemented strict, validated Pydantic models for `BenchmarkCase`, `GroundTruthFinding`, `ReviewComment`, `CaseEvaluation`, and `BenchmarkMetrics`, complete with high-performance JSON and dictionary serialization helpers.
2. **Ground-Truth Matching & Metric Engine (`bench/evaluator/`)**: Implemented a greedy 1-to-1 matcher supporting line proximity windows (default $\pm 3$ lines), path normalization, semantic category congruence (`BUG`/`SECURITY`/`PERFORMANCE` vs `STYLE`/`NITPICK`), and comprehensive metrics computation (Precision, Recall, Clean Diff False Positive Rate, Comments/PR, Nitpick rate, and latencies).
3. **CLI Runner & Reviewer Baseline Adaptations (`bench/runner.py`)**: Built a one-command CLI runner (`python -m bench.runner`) with pluggable review engines (`MockReviewer`, `PrototypeReviewer`, `LinterReviewer`), producing console tables, structured JSON logs, and formatted Markdown reports.

---

## 2. Files Created & Modified

| File | Purpose |
|---|---|
| [`bench/__init__.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/__init__.py) | Package initialization exposing primary schemas, models, and loaders. |
| [`bench/schema.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/schema.py) | Pydantic v2 schemas for findings, benchmark cases, review comments, and metrics. |
| [`bench/evaluator/__init__.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/evaluator/__init__.py) | Evaluator package exports (`match_comments_to_findings`, `evaluate_case`, `calculate_benchmark_metrics`). |
| [`bench/evaluator/matcher.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/evaluator/matcher.py) | 1-to-1 greedy matcher with proximity window delta and category congruence checks. |
| [`bench/evaluator/metrics.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/evaluator/metrics.py) | Case and split-level metrics calculator enforcing clean-diff negative control penalties. |
| [`bench/runner.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/runner.py) | CLI runner with argument parsing, engine registry, and Markdown/JSON reporting. |
| [`bench/__main__.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/__main__.py) | Direct module invocation entrypoint (`python -m bench`). |
| [`bench/splits/dev.json`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/bench/splits/dev.json) | Seed development split with clean and buggy cases for out-of-the-box CLI execution. |
| [`tests/test_bench_runner.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/tests/test_bench_runner.py) | 15 comprehensive unit and integration tests covering all benchmark components. |

---

## 3. Verification & Test Results

### 3.1 Task 1: Schema Verification
Command:
```bash
python -c "from bench.schema import BenchmarkCase, GroundTruthFinding, FindingCategory, FindingSeverity; c = BenchmarkCase(case_id='test-1', repository='test/repo', language='python', file_path='main.py', original_code='x=1', modified_code='x=2', diff='', split='dev', is_clean_diff=True); assert c.is_clean_diff is True; print('Schema verified')"
```
**Output:** `Schema verified` (Exit code 0)

### 3.2 Task 2: Ground-Truth Matcher Verification
Command:
```bash
python -c "from bench.evaluator.matcher import match_comments_to_findings; from bench.schema import ReviewComment, GroundTruthFinding, FindingCategory, FindingSeverity; c = ReviewComment(file_path='a.py', line_number=10, category=FindingCategory.BUG, comment='bug'); f = GroundTruthFinding(finding_id='1', line_start=9, line_end=11, category=FindingCategory.BUG, severity=FindingSeverity.CRITICAL, description='test'); matched, fps, fns = match_comments_to_findings([c], [f]); assert len(matched) == 1 and len(fps) == 0; print('Matcher verified')"
```
**Output:** `Matcher verified` (Exit code 0)

### 3.3 Task 3: Test Suite & CLI Execution
Command:
```bash
python -m pytest tests/test_bench_runner.py -v
```
**Output:**
```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0
collected 15 items

tests/test_bench_runner.py::test_benchmark_case_creation_and_defaults PASSED [  6%]
tests/test_bench_runner.py::test_ground_truth_finding_creation PASSED    [ 13%]
tests/test_bench_runner.py::test_schema_json_and_dict_serialization PASSED [ 20%]
tests/test_bench_runner.py::test_path_compatibility PASSED               [ 26%]
tests/test_bench_runner.py::test_category_congruence PASSED              [ 33%]
tests/test_bench_runner.py::test_line_distance PASSED                    [ 40%]
tests/test_bench_runner.py::test_matcher_window_and_category PASSED      [ 46%]
tests/test_bench_runner.py::test_matcher_greedy_one_to_one PASSED        [ 53%]
tests/test_bench_runner.py::test_evaluate_case_clean_diff_negative_control PASSED [ 60%]
tests/test_bench_runner.py::test_calculate_benchmark_metrics PASSED      [ 66%]
tests/test_bench_runner.py::test_mock_reviewer_modes PASSED              [ 73%]
tests/test_bench_runner.py::test_prototype_reviewer_python_ast PASSED    [ 80%]
tests/test_bench_runner.py::test_linter_reviewer_ruff PASSED             [ 86%]
tests/test_bench_runner.py::test_run_benchmark_programmatic PASSED       [ 93%]
tests/test_bench_runner.py::test_cli_runner_execution PASSED             [100%]

============================= 15 passed in 0.48s ==============================
```

### 3.4 Linter & Code Quality Check
Command:
```bash
ruff check bench/ tests/test_bench_runner.py
```
**Output:** `All checks passed!`

---

## 4. Key Design Decisions & Guarantees

1. **Greedy 1-to-1 Matcher:** Candidate pairings are prioritized first by line proximity, second by exact semantic category agreement, avoiding duplicate TP inflation when a reviewer outputs multiple comments for the same bug.
2. **Clean-Diff Negative Control:** Every comment generated on a clean diff (`is_clean_diff == True`) immediately incurs a False Positive penalty and flags `clean_diff_violation = True`, directly populating the clean diff FPR metric.
3. **Robust Category Congruence:** Prevents cosmetic nitpicks (e.g. naming or whitespace suggestions) from falsely satisfying substantive logic or security findings.
4. **Three Native Reviewer Baselines:**
   - `MockReviewer`: Enables deterministic testing of edge cases (perfect, empty, noisy).
   - `PrototypeReviewer`: Adapts Aion's existing Python AST checks (bare excepts, mutable defaults, SQL injection f-strings, unsafe exec/eval, and nested loops).
   - `LinterReviewer`: Runs Ruff directly against file content with automated rule categorization into Security (`S`), Bug (`F`/`B`), Style (`E`/`W`), and Nitpicks.

---

## 5. Downstream Readiness for Wave 2

The framework is ready for Plan 02-02 (`02-02-synthetic-bugs-and-clean-negatives.md`):
- `bench/schema.py` provides the canonical `BenchmarkCase` and `GroundTruthFinding` data contracts.
- `bench/runner.py` is capable of loading any generated split (`dev.json`, `gold.json`, `test_locked.json`) and benchmarking it with a single command.
- `bench/results/` generates structured JSON metrics and human-readable Markdown reports out-of-the-box.
