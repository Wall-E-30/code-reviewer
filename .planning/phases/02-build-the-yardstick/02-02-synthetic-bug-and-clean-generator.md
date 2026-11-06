---
phase: 02-build-the-yardstick
plan: 02
type: execute
wave: 2
depends_on:
  - 02-01
files_modified:
  - bench/generator/__init__.py
  - bench/generator/injector.py
  - bench/generator/clean.py
  - bench/generator/synthesize.py
  - bench/mined/__init__.py
  - bench/mined/miner.py
  - tests/test_bench_generators.py
autonomous: true
requirements:
  - BENCH-02
  - BENCH-03
must_haves:
  truths:
    - Synthetic bug injector programmatically generates reproducible logic, security, and performance bugs in Python and TypeScript/JS with precise ground-truth line anchors.
    - Clean-diff negative generator produces valid, non-buggy code changes (refactoring, docstrings, typing) with is_clean_diff=True to directly penalize false-positive hallucinations.
    - Real-review miner parses human PR reviews with subsequent corrective commits, filtering out conversational noise (LGTM, thanks) to isolate actionable code review comments.
    - Dataset synthesis generates at least 200 verifiable benchmark cases that fully validate against BenchmarkCase schema.
  artifacts:
    - bench/generator/injector.py
    - bench/generator/clean.py
    - bench/generator/synthesize.py
    - bench/mined/miner.py
    - tests/test_bench_generators.py
  key_links:
    - bench/generator/injector.py transforms valid code into buggy cases with GroundTruthFinding records.
    - bench/generator/clean.py generates true negative cases for FPR calibration.
    - bench/mined/miner.py normalizes real PR review comments into the benchmark case schema.
    - bench/generator/synthesize.py combines all sources into the raw benchmark dataset.
---

<objective>
Build the synthetic bug mutation engine, the clean-diff negative generator, and the real PR review ingestion pipeline. Generate a rich, diverse evaluation corpus of at least 200 verifiable test cases spanning injected bugs, clean negative controls, and real human PR reviews.

Purpose: Provide objective ground truth for bug detection while preventing reviewer spam through clean-diff negative controls that measure False-Positive Rate.
Output: Mutation generator, clean diff synthesizer, real review miner, and test dataset generator.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/02-build-the-yardstick/RESEARCH.md
@.planning/phases/02-build-the-yardstick/02-01-benchmark-schema-and-runner.md
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Deterministic AST Bug Injector in bench/generator/injector.py</name>
  <files>bench/generator/__init__.py, bench/generator/injector.py</files>
  <action>
1. Create `bench/generator/__init__.py`.
2. In `bench/generator/injector.py`, implement an AST-driven code mutation engine:
   - Provide concrete mutation operators:
     a. `InvertComparison`: Inverts boolean and comparison operators (`<` to `>=`, `==` to `!=`, `in` to `not in`, `and` to `or`).
     b. `OffByOne`: Mutates loop boundaries and slice indices (e.g. `range(n)` to `range(n + 1)` or `[:n]` to `[:n-1]`).
     c. `NoneDereference`: Removes `.get(k, default)` or `if var is not None:` guards, exposing unsafe attribute access.
     d. `ResourceLeak`: Replaces context-managed `with open(...)` or network sessions with unclosed variables.
     e. `UnsafeCommandSink`: Alters `subprocess.run` or DB queries to use raw string formatting with `shell=True`.
     f. `SwallowedException`: Changes explicit exception handlers to bare `except: pass` or removes re-raises.
   - For TypeScript/JavaScript:
     Provide regex and structural transformers for `==` vs `===` loose equality bugs, missing `await` on asynchronous promises, and unhandled promise rejections.
   - Each mutation must compute the unified diff between original and mutated code, locate the exact mutated line numbers, and construct a `GroundTruthFinding` with severity, category, description, and suggested fix.
  </action>
  <verify>
python -c "from bench.generator.injector import BugInjector; inj = BugInjector(); case = inj.inject_bug('def check(x):\n    if x > 0:\n        return True\n    return False\n', 'invert_comparison', language='python'); assert len(case.ground_truth) > 0; assert case.is_clean_diff is False; print('Injector verified:', case.ground_truth[0].description)"
  </verify>
</task>

<task>
  <name>Build Clean-Diff Negative Generator in bench/generator/clean.py</name>
  <files>bench/generator/clean.py</files>
  <action>
1. In `bench/generator/clean.py`, implement the clean-diff negative synthesizer:
   - Generates valid, non-regressing code modifications that an AI reviewer should NOT flag as bugs:
     a. `ReformatWhitespace`: PEP 8 indentation and newline normalization.
     b. `AddDocstringsAndComments`: Adds Google/NumPy-style docstrings, comments, or module documentation.
     c. `AddTypeHints`: Annotates Python functions with type hints (`def func(a: int) -> str:`).
     d. `SafeRename`: Renames local variables to clearer descriptive names across all AST references.
     e. `AddUnitTests`: Appends valid unit test functions testing existing code.
   - For all clean diffs:
     - `is_clean_diff = True`.
     - `ground_truth = []`.
     - Produces clean unified diff and valid `BenchmarkCase`.
  </action>
  <verify>
python -c "from bench.generator.clean import CleanDiffGenerator; gen = CleanDiffGenerator(); case = gen.generate_clean_diff('def add(a, b):\n    return a + b\n', 'add_type_hints', language='python'); assert case.is_clean_diff is True; assert len(case.ground_truth) == 0; print('Clean generator verified')"
  </verify>
</task>

<task>
  <name>Build Real PR Review Miner & Corpus Synthesizer</name>
  <files>bench/mined/__init__.py, bench/mined/miner.py, bench/generator/synthesize.py, tests/test_bench_generators.py</files>
  <action>
1. Create `bench/mined/__init__.py`.
2. In `bench/mined/miner.py`:
   - Implement ingestion for real GitHub PR review comment datasets (CodeReviewer dataset format and GitHub Archive PR review records).
   - Filtering heuristic:
     - Match review comment line to the diff hunks.
     - Keep only comments accompanied by a subsequent corrective commit on that file or line.
     - Filter out conversational chatter (`"LGTM"`, `"thanks!"`, `"fixed"`, `"done"`, `"approved"`).
     - Categorize findings into `bug`, `security`, `performance`, or `style`.
   - Provide offline bundled sample of real PR review cases for reliable offline tests without external network dependencies.
3. In `bench/generator/synthesize.py`:
   - CLI script (`python -m bench.generator.synthesize --target 250 --output data/benchmark_cases_raw.json`) that combines:
     - Injected bugs (~50% of dataset).
     - Clean-diff negatives (~30% of dataset, essential for False-Positive Rate measurement).
     - Mined real PR reviews (~20% of dataset).
   - Guarantees at least 200 total cases generated across Python and TypeScript.
4. In `tests/test_bench_generators.py`:
   - Unit tests covering mutation accuracy, clean diff generation, schema validation on generated cases, and miner filtering.
  </action>
  <verify>
python -m pytest tests/test_bench_generators.py -v
  </verify>
</task>

</tasks>

