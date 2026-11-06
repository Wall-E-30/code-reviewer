# Aion-Bench Evaluation Report: `benchmark_cases_raw`

> **Reviewer Engine:** `mock`  
> **Evaluated Cases:** `20` (`10` buggy, `10` clean)  
> **Execution Duration:** `0.00s` (`0.00ms/case`)  
> **Generated:** `2026-11-05 15:53:42 UTC`

## 1. Summary Metrics

| Metric | Measured Score | Target Threshold | Status |
|---|:---:|:---:|:---:|
| **Precision** | `100.00%` | $\ge 85.0\%$ | **PASS** |
| **Recall** | `100.00%` | $\ge 80.0\%$ | **PASS** |
| **Clean Diff FPR** | `0.00%` | $\le 5.0\%$ | **PASS** |
| **Comments / PR** | `0.50` | $1.0 - 3.0$ | **INFO** |
| **Nitpick Rate** | `0.00%` | $\le 15.0\%$ | **INFO** |
| **Avg Latency** | `0.00 ms` | $\le 500$ ms | **PASS** |

## 2. Confusion Breakdown

| Metric | Count | Description |
|---|:---:|---|
| **True Positives (TP)** | `10` | Real bugs correctly identified within proximity window |
| **False Positives (FP)** | `0` | Reviewer comments posted with no matching bug |
| **False Negatives (FN)** | `0` | Ground-truth findings missed by the reviewer |
| **Clean Diff Violations** | `0` | Clean diffs where reviewer hallucinated $\ge 1$ comment |

## 3. Case-by-Case Evaluations

| Case ID | Type | Comments | TP | FP | FN | Clean Violation | Duration (ms) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `mined-ts-playwright-45` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `clean-ts-add_type_hints-12` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
| `inj-py-none_dereference-60` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `clean-ts-reformat_whitespace-37` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
| `clean-ts-add_unit_tests-35` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
| `inj-py-invert_comparison-43` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `mined-py-rich-10` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `inj-py-off_by_one-52` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `inj-ts-missing_await-11` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `clean-ts-safe_rename-27` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
| `mined-py-httpx-04` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `clean-py-reformat_whitespace-2` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
| `mined-ts-lodash-16` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `clean-ts-add_docstrings-3` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
| `inj-ts-loose_equality-23` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `clean-py-add_type_hints-36` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
| `clean-ts-reformat_whitespace-29` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
| `mined-py-urllib3-22` | Buggy | 1 | 1 | 0 | 0 | - | 0.0 |
| `clean-ts-add_docstrings-17` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
| `clean-ts-add_type_hints-19` | Clean | 0 | 0 | 0 | 0 | - | 0.0 |
