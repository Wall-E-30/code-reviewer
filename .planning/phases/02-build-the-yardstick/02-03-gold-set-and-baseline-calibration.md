---
phase: 02-build-the-yardstick
plan: 03
type: execute
wave: 3
depends_on:
  - 02-01
  - 02-02
files_modified:
  - bench/splits/__init__.py
  - bench/splits/splitter.py
  - bench/splits/dev.json
  - bench/splits/gold.json
  - bench/splits/test_locked.json
  - bench/splits/manifest.json
  - bench/baselines/__init__.py
  - bench/baselines/run_baselines.py
  - bench/baselines/BASELINE_DAY_ONE.md
  - tests/test_benchmark_isolation.py
autonomous: true
requirements:
  - BENCH-04
  - BENCH-05
must_haves:
  truths:
    - Gold set contains 100-200 hand-audited, high-signal code review test cases with validated ground truth findings.
    - Test split (test_locked.json) is strictly isolated and locked with a cryptographic SHA-256 manifest, preventing data leakage into training sets.
    - Leakage prevention test suite verifies zero overlap between splits and ensures manifest immutability.
    - Day-one baseline calibration measures Precision, Recall, FPR on clean diffs, Comments per PR, Nitpick Rate, and Latency for the current Aion prototype, static linters (Ruff/Bandit), and a plain LLM reviewer.
    - Baseline measurements are permanently documented in bench/baselines/BASELINE_DAY_ONE.md as the objective reference for future phases.
  artifacts:
    - bench/splits/dev.json
    - bench/splits/gold.json
    - bench/splits/test_locked.json
    - bench/splits/manifest.json
    - bench/splits/splitter.py
    - bench/baselines/run_baselines.py
    - bench/baselines/BASELINE_DAY_ONE.md
    - tests/test_benchmark_isolation.py
  key_links:
    - bench/splits/splitter.py splits synthesized cases into dev, gold, and test_locked splits.
    - tests/test_benchmark_isolation.py asserts cryptographic isolation and zero data contamination across splits.
    - bench/baselines/run_baselines.py executes bench/runner.py against all three baseline systems and generates BASELINE_DAY_ONE.md.
---

<objective>
Partition the benchmark corpus into stratified splits (`dev`, hand-audited `gold`, and cryptographically locked `test_locked`), enforce strict data leakage guards with SHA-256 manifests, and record day-one baseline calibrations across the current Aion prototype, static linters, and plain LLMs.

Purpose: Guarantee zero benchmark contamination, provide the ultimate gold-standard calibration ground, and establish immutable day-one metrics before Phase 3 review pipelines or Phase 5 model training.
Output: Stratified splits, cryptographic manifest, leakage test suite, baseline harness, and BASELINE_DAY_ONE.md.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/02-build-the-yardstick/RESEARCH.md
@.planning/phases/02-build-the-yardstick/02-01-benchmark-schema-and-runner.md
@.planning/phases/02-build-the-yardstick/02-02-synthetic-bug-and-clean-generator.md
</execution_context>

<tasks>

<task type="tracer">
  <name>Build Splitter and Stratify dev, gold, and test_locked Splits</name>
  <files>bench/splits/__init__.py, bench/splits/splitter.py, bench/splits/dev.json, bench/splits/gold.json, bench/splits/test_locked.json, bench/splits/manifest.json</files>
  <action>
1. Create `bench/splits/__init__.py`.
2. In `bench/splits/splitter.py`:
   - Implement `partition_benchmark(raw_cases_file: str, output_dir: str = "bench/splits") -> Dict[str, int]`:
     - Stratifies cases across `dev` (unlocked training/dev set), `gold` (100–200 curated, hand-audited cases), and `test_locked` (held-out private evaluation set).
     - Balances language representation (Python, TypeScript/JS) and case types (injected bugs, clean diffs, real reviews) across splits.
     - Ensures `gold.json` has between 100 and 200 high-confidence cases with complete ground-truth annotations and rationale.
     - Computes SHA-256 cryptographic hashes for every case payload in `test_locked.json` and `gold.json`, writing `manifest.json`.
3. Generate the splits:
   - Run partitioner on the synthesized cases to produce `dev.json`, `gold.json`, `test_locked.json`, and `manifest.json`.
  </action>
  <verify>
python -c "import json; gold = json.load(open('bench/splits/gold.json')); locked = json.load(open('bench/splits/test_locked.json')); assert 100 <= len(gold) <= 200; assert len(locked) > 0; print(f'Splits verified: gold={len(gold)}, locked={len(locked)}')"
  </verify>
</task>

<task>
  <name>Implement Leakage Guard and Split Isolation Tests</name>
  <files>tests/test_benchmark_isolation.py</files>
  <action>
1. Create `tests/test_benchmark_isolation.py`:
   - Test 1: Assert disjoint case IDs across `dev.json`, `gold.json`, and `test_locked.json` ($A \cap B = \emptyset, A \cap C = \emptyset, B \cap C = \emptyset$).
   - Test 2: Assert zero exact diff or modified_code overlap between `dev` and `test_locked` to prevent data memorization.
   - Test 3: Verify cryptographic checksums in `manifest.json` match current contents of `test_locked.json` and `gold.json`.
   - Test 4: Assert all test cases conform strictly to `BenchmarkCase` Pydantic validation.
   - Test 5: Verify clean diffs (`is_clean_diff == True`) have empty ground-truth findings, and buggy diffs have at least 1 ground-truth finding.
  </action>
  <verify>
python -m pytest tests/test_benchmark_isolation.py -v
  </verify>
</task>

<task>
  <name>Run Day-One Baseline Calibrations & Record BASELINE_DAY_ONE.md</name>
  <files>bench/baselines/__init__.py, bench/baselines/run_baselines.py, bench/baselines/BASELINE_DAY_ONE.md</files>
  <action>
1. Create `bench/baselines/__init__.py`.
2. In `bench/baselines/run_baselines.py`:
   - Harness that runs `bench.runner` across three baseline reviewer implementations on `gold.json` and `dev.json`:
     a. **Aion Prototype Baseline:** Existing AST rules and MockOpenAI agent from `inference.py` / `env.py`.
     b. **Static Linters Baseline:** Combines `ruff check` and `bandit` mapped to line-level findings.
     c. **Plain LLM Baseline:** Zero-shot reviewer prompt without verification or filtering.
   - Measures and records for each baseline:
     - Precision (%)
     - Recall on injected/mined bugs (%)
     - False-Positive Rate on clean diffs (%)
     - Average Comments per PR
     - Nitpick Rate (%)
     - Latency per Case (ms)
3. Execute `run_baselines.py` and write the comprehensive report to `bench/baselines/BASELINE_DAY_ONE.md`:
   - Executive comparison table.
   - Qualitative analysis of why each baseline fails or succeeds (e.g. static linters miss logic bugs, prototype AST overfits style, plain LLM hallucinates on clean diffs).
   - Milestone targets for Phase 3 (Wedge) and Phase 5 (GRPO Model).
  </action>
  <verify>
python -c "import os; assert os.path.exists('bench/baselines/BASELINE_DAY_ONE.md'); content = open('bench/baselines/BASELINE_DAY_ONE.md').read(); assert 'Precision' in content and 'Recall' in content and 'False-Positive Rate' in content; print('Baseline documentation verified')"
  </verify>
</task>

</tasks>

