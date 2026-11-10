---
phase: 08-truth-and-hardening
plan: 03
type: execute
wave: 3
depends_on:
  - 08-01
  - 08-02
files_modified:
  - legacy/README.md
  - legacy/env.py
  - legacy/train_rl.py
  - legacy/train_autoregressive_rl.py
  - server/app.py
  - frontend/src/App.jsx
  - bench/evaluator.py
  - rl/bandit.py
  - docs/ARCHITECTURE.md
  - tests/test_legacy_deprecation_and_consistency.py
autonomous: true
requirements:
  - HARD-04
  - HARD-05
must_haves:
  truths:
    - Legacy prototype files (env.py, train_rl.py, train_autoregressive_rl.py) are archived under legacy/ with a comprehensive README explaining reward hacking.
    - server/app.py re-routes /reset and /step to ReviewEnv; unmeasured polynomial speedup and memory percentages are purged from API responses.
    - UI in frontend/src/App.jsx displays verified static findings and review comments rather than synthetic speedup metrics.
    - Documentation and code consistently describe the benchmark CLI (python -m bench.runner), greedy line-distance matcher, and Beta-Bernoulli Thompson sampling bandit.
  artifacts:
    - legacy/README.md
    - server/app.py
    - frontend/src/App.jsx
    - tests/test_legacy_deprecation_and_consistency.py
---

<objective>
Deprecate Legacy AST Prototype Files, Clean Synthetic Metrics (`HARD-04`), and Reconcile Doc/Code Inconsistencies (`HARD-05`).
Purge reward-hackable prototype code, point all execution surfaces to `ReviewEnv`, and guarantee that all documentation matches real implementation algorithms.
</objective>

<tasks>

<task type="tracer">
  <name>Archive Legacy Files and Migrate Server Endpoints to ReviewEnv</name>
  <files>legacy/README.md, server/app.py, frontend/src/App.jsx</files>
  <action>
1. Move `env.py`, `train_rl.py`, `train_autoregressive_rl.py` to `legacy/`.
2. Author `legacy/README.md` detailing the reward-hacking vulnerability of the node-count heuristic and pointing to `ReviewEnv` (`rl/env.py`).
3. In `server/app.py`:
   - Point `/reset` and `/step` to `rl.env.ReviewEnv`.
   - Remove synthetic speedup/memory fields or set them to honest labels.
4. In `frontend/src/App.jsx`:
   - Replace synthetic polynomial speedup cards with honest static analysis and AST review metrics.
  </action>
  <verify>
python -c "import os; assert os.path.exists('legacy/README.md') and os.path.exists('legacy/env.py'); print('Legacy migration tracer verified')"
  </verify>
</task>

<task>
  <name>Reconcile Benchmark CLI, Matcher, and Bandit Descriptions</name>
  <files>bench/evaluator.py, rl/bandit.py, docs/ARCHITECTURE.md</files>
  <action>
1. In `bench/evaluator.py`:
   - Ensure the docstring and comments explicitly describe the matching algorithm as Greedy Bipartite Line-Distance Matching within the line tolerance window.
2. In `rl/bandit.py`:
   - Ensure docstrings, variable names, and comments describe the threshold optimizer as Per-Category Beta-Bernoulli Thompson Sampling with strict boundary clamps $[0.50, 0.95]$.
3. In `docs/ARCHITECTURE.md` (or `docs/BENCHMARK.md`):
   - Standardize benchmark CLI command to `python -m bench.runner`.
  </action>
  <verify>
pytest tests/test_legacy_deprecation_and_consistency.py -v
  </verify>
</task>

</tasks>
