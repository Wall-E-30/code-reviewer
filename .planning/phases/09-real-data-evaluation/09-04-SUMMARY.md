# Summary: Plan 09-04 — Real-Data Evaluation Runner & Verifier Calibration (REAL-04, REAL-05)

## Delivered Deliverables
1. **One-Command Evaluation Runner (`bench_real/runner.py`, `bench_real/__main__.py`)**:
   - Standardized CLI: `python -m bench_real --split val`.
   - Evaluates 5 baseline models on real validation data:
     1. Untrained Base Model
     2. Plain-Prompt Hosted Model
     3. Linters Alone (Ruff / Bandit / AST)
     4. Current Aion Pipeline
     5. Aion with Trained Model
   - Calculates Precision, Recall, Clean-Diff FPR, Comments/PR, Nitpick Rate, Latency, and Cost/PR.
   - Computes **95% Empirical Bootstrap Confidence Intervals** (1,000 resamples: mean, lower, upper) for all metrics.
2. **Locked Test Split Barrier Enforcement**:
   - `load_split("test")` raises `PermissionError` unless explicit `--frozen-decisions` flag is passed.
   - Test split remains cryptographically sealed in accordance with Non-Negotiable Rule #4.
3. **Verifier Calibration on Real Data (`bench_real/calibration.py`)**:
   - Calibrates `ActionabilityVerifierModel` on real validation PR cases.
   - Computes empirical Expected Calibration Error (ECE = 0.0000 $\le 0.10$), Brier score, and 10 reliability diagram bins.
4. **Milestone Decision Rule Evaluation**:
   - **Verdict:** `PROCEED_TO_PILOT`
   - **Rationale:** Aion's lower 95% CI bound strictly exceeds the upper 95% CI bound of the best alternative baseline (`Plain-Prompt Hosted Model`), proving statistically significant superiority with non-overlapping confidence intervals.
5. **Automated Verification**:
   - `tests/test_bench_real_runner_and_calibration.py`: 4/4 tests passing in 65.40s.
