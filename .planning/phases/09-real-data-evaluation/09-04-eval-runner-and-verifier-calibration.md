---
phase: 09-real-data-evaluation
plan: 04
type: execute
wave: 3
depends_on:
  - 09-01
  - 09-02
  - 09-03
files_modified:
  - bench_real/runner.py
  - bench_real/__main__.py
  - bench_real/calibration.py
  - tests/test_bench_real_runner_and_calibration.py
autonomous: true
requirements:
  - REAL-04
  - REAL-05
must_haves:
  truths:
    - bench_real runner executes with a single command (python -m bench_real --split val).
    - Baselines table includes: untrained base model, plain-prompt hosted model, linters alone, current Aion pipeline, and trained Aion model.
    - Metrics calculated include precision, recall, clean-diff FPR, comments/PR, nitpicks, latency, cost, and 95% bootstrap confidence intervals (1,000 resamples).
    - Locked test split is strictly protected: running on test split is blocked unless explicit frozen-confirmation flag is provided.
    - Verifier calibration is re-fitted on the real validation split, generating reliability diagrams, Expected Calibration Error (ECE), and Brier scores.
  artifacts:
    - bench_real/runner.py
    - bench_real/calibration.py
    - tests/test_bench_real_runner_and_calibration.py
---

<objective>
Build the one-command real-data evaluation runner and actionability verifier calibration suite (`REAL-04`, `REAL-05`).
Provide reproducible 5-baseline evaluation on real validation data with 95% bootstrap confidence intervals, protect the locked test split, and measure verifier calibration with reliability diagrams and ECE.
</objective>

<tasks>

<task type="tracer">
  <name>Build bench_real Runner with 5 Baselines and Bootstrap CIs</name>
  <files>bench_real/runner.py, bench_real/__main__.py</files>
  <action>
1. Implement `bench_real/runner.py`:
   - Single command entrypoint `python -m bench_real --split val`
   - Defines 5 evaluation baselines:
     1. Untrained Base Model (heuristic/stub baseline)
     2. Plain-Prompt Hosted Model (unfiltered candidate comments)
     3. Linters Alone (Ruff, Bandit, AST security sinks)
     4. Current Aion Pipeline (linters + verifier filter + convention memory + bandit)
     5. Aion Trained Model (RLVR policy)
   - Evaluates on `RealBenchmarkCase` objects with greedy bipartite line-distance matching.
   - Computes: Precision, Recall, Clean-Diff FPR, Comments/PR, Nitpick Rate, Latency, and Estimated Cost.
   - Computes 95% bootstrap confidence intervals (1,000 bootstrap resamples).
   - Enforces **Test Split Lock**: Attempts to run `--split test` without `--frozen-decisions` raise an explicit exception and halt.
2. Implement `bench_real/__main__.py` CLI dispatch.
  </action>
  <verify>
python -m bench_real --help
  </verify>
</task>

<task>
  <name>Implement Verifier Re-Calibration on Real Data and Test Suite</name>
  <files>bench_real/calibration.py, tests/test_bench_real_runner_and_calibration.py</files>
  <action>
1. Implement `bench_real/calibration.py`:
   - Extracts real-world features using `ActionabilityFeatureExtractor`.
   - Re-fits temperature calibration on the real validation split.
   - Computes empirical Expected Calibration Error (ECE), Brier score, and reliability curve bins.
   - Evaluates decision rule: compares CI overlap between Aion and best baseline.
2. Add `tests/test_bench_real_runner_and_calibration.py`:
   - Verifies 5-baseline runner outputs against real validation split fixture.
   - Verifies bootstrap CI calculation produces valid (lower, mean, upper) bounds.
   - Verifies test split access is blocked without authorization.
   - Verifies verifier re-calibration computes ECE $< 0.10$ and valid reliability curve data.
  </action>
  <verify>
python -m pytest tests/test_bench_real_runner_and_calibration.py -v
  </verify>
</task>

</tasks>
