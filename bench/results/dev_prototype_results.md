# Aion-Bench Evaluation Report: `dev`

> **Reviewer Engine:** `prototype`  
> **Evaluated Cases:** `2` (`1` buggy, `1` clean)  
> **Execution Duration:** `0.00s` (`0.20ms/case`)  
> **Generated:** `2026-11-05 15:35:18 UTC`

## 1. Summary Metrics

| Metric | Measured Score | Target Threshold | Status |
|---|:---:|:---:|:---:|
| **Precision** | `100.00%` | $\ge 85.0\%$ | **PASS** |
| **Recall** | `100.00%` | $\ge 80.0\%$ | **PASS** |
| **Clean Diff FPR** | `0.00%` | $\le 5.0\%$ | **PASS** |
| **Comments / PR** | `0.50` | $1.0 - 3.0$ | **INFO** |
| **Nitpick Rate** | `0.00%` | $\le 15.0\%$ | **INFO** |
| **Avg Latency** | `0.20 ms` | $\le 500$ ms | **PASS** |

## 2. Confusion Breakdown

| Metric | Count | Description |
|---|:---:|---|
| **True Positives (TP)** | `1` | Real bugs correctly identified within proximity window |
| **False Positives (FP)** | `0` | Reviewer comments posted with no matching bug |
| **False Negatives (FN)** | `0` | Ground-truth findings missed by the reviewer |
| **Clean Diff Violations** | `0` | Clean diffs where reviewer hallucinated $\ge 1$ comment |

## 3. Case-by-Case Evaluations

| Case ID | Type | Comments | TP | FP | FN | Clean Violation | Duration (ms) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `seed-dev-001` | Buggy | 1 | 1 | 0 | 0 | - | 0.2 |
| `seed-dev-002` | Clean | 0 | 0 | 0 | 0 | - | 0.2 |
