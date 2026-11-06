---
phase: 02-build-the-yardstick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - bench/__init__.py
  - bench/schema.py
  - bench/evaluator/__init__.py
  - bench/evaluator/matcher.py
  - bench/evaluator/metrics.py
  - bench/runner.py
  - tests/test_bench_runner.py
autonomous: true
requirements:
  - BENCH-01
must_haves:
  truths:
    - Benchmark case schema accurately defines input code, diffs, ground-truth findings, and clean-diff status using Pydantic.
    - Ground-truth matcher pairs reviewer comments to ground-truth findings using configurable line proximity windows and finding categories.
    - Evaluation metrics engine correctly computes Precision, Recall, FPR on clean diffs, Comments per PR, Nitpick Rate, and Latency.
    - CLI runner executes a benchmark split (dev, test_locked, gold) or custom JSON path with `python -m bench.runner` and outputs structured JSON and Markdown summary reports.
  artifacts:
    - bench/schema.py
    - bench/evaluator/matcher.py
    - bench/evaluator/metrics.py
    - bench/runner.py
    - tests/test_bench_runner.py
  key_links:
    - bench/schema.py supplies models for test cases, findings, comments, and benchmark metrics.
    - bench/runner.py loads splits, evaluates comments using bench/evaluator/, and outputs formatted benchmark reports.
---

<objective>
Build the core Aion-Bench framework: strict Pydantic schemas for test cases and ground-truth findings, an objective line-window matcher and metrics calculation engine, and a one-command CLI runner (`python -m bench.runner`) that produces JSON and Markdown reports.

Purpose: Provide the foundational evaluation harness required to objectively benchmark any reviewer engine without manual grading or external cloud dependencies.
Output: `bench/` package with schema, evaluator, runner, and test suite.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/02-build-the-yardstick/RESEARCH.md
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Aion-Bench Schema Models in bench/schema.py</name>
  <files>bench/__init__.py, bench/schema.py</files>
  <action>
1. Create `bench/__init__.py` making `bench` an importable Python package.
2. In `bench/schema.py`, implement standard Pydantic models:
   - `FindingCategory(str, Enum)`: `bug`, `security`, `performance`, `style`, `nitpick`.
   - `FindingSeverity(str, Enum)`: `critical`, `major`, `minor`, `info`.
   - `GroundTruthFinding(BaseModel)`: `finding_id: str`, `line_start: int`, `line_end: int`, `category: FindingCategory`, `severity: FindingSeverity`, `description: str`, `fix_suggestion: Optional[str]`, `rule_id: Optional[str]`.
   - `BenchmarkCase(BaseModel)`: `case_id: str`, `repository: str`, `language: str`, `file_path: str`, `original_code: str`, `modified_code: str`, `diff: str`, `split: str` (e.g. "dev", "gold", "test_locked"), `is_clean_diff: bool`, `ground_truth: List[GroundTruthFinding] = []`, `metadata: Dict[str, Any] = {}`.
   - `ReviewComment(BaseModel)`: `file_path: str`, `line_number: int`, `category: FindingCategory`, `comment: str`, `suggestion: Optional[str] = None`, `confidence: float = 1.0`.
   - `CaseEvaluation(BaseModel)`: `case_id: str`, `comments_posted: int`, `true_positives: int`, `false_positives: int`, `false_negatives: int`, `is_clean_diff: bool`, `clean_diff_violation: bool`, `matched_findings: List[Dict[str, Any]]`, `duration_ms: float`.
   - `BenchmarkMetrics(BaseModel)`: `split: str`, `total_cases: int`, `clean_cases: int`, `buggy_cases: int`, `precision: float`, `recall: float`, `false_positive_rate: float`, `avg_comments_per_pr: float`, `nitpick_rate: float`, `avg_latency_ms: float`, `total_duration_sec: float`.
3. Provide serialization helpers (`to_json`, `from_json`, `to_dict`) and ensure JSON schema export works cleanly.
  </action>
  <verify>
python -c "from bench.schema import BenchmarkCase, GroundTruthFinding, FindingCategory, FindingSeverity; c = BenchmarkCase(case_id='test-1', repository='test/repo', language='python', file_path='main.py', original_code='x=1', modified_code='x=2', diff='', split='dev', is_clean_diff=True); assert c.is_clean_diff is True; print('Schema verified')"
  </verify>
</task>

<task>
  <name>Build Ground-Truth Matcher and Metrics Calculator in bench/evaluator/</name>
  <files>bench/evaluator/__init__.py, bench/evaluator/matcher.py, bench/evaluator/metrics.py</files>
  <action>
1. Create `bench/evaluator/matcher.py`:
   - Implement `match_comments_to_findings(comments: List[ReviewComment], findings: List[GroundTruthFinding], line_window: int = 3) -> Tuple[List[MatchedPair], List[ReviewComment], List[GroundTruthFinding]]`.
   - Matching criteria:
     a. Same file path.
     b. Proximity check: `finding.line_start - line_window <= comment.line_number <= finding.line_end + line_window`.
     c. Category congruence: If finding is `bug` or `security`, comment cannot be classified as `nitpick` or `style`.
     d. Greedy / optimal 1-to-1 matching so one comment cannot claim multiple distinct ground truth findings, nor can multiple comments overcount the same bug.
2. In `bench/evaluator/metrics.py`:
   - Implement `evaluate_case(case: BenchmarkCase, comments: List[ReviewComment], duration_ms: float) -> CaseEvaluation`.
     - Count `true_positives` (matched pairs), `false_positives` (unmatched comments), and `false_negatives` (unmatched ground-truth findings).
     - On clean diffs (`case.is_clean_diff == True`), assert that `ground_truth == []`. Any posted comment on a clean diff is a `false_positive` and sets `clean_diff_violation = True`.
   - Implement `calculate_benchmark_metrics(evaluations: List[CaseEvaluation], split_name: str, total_duration_sec: float) -> BenchmarkMetrics`:
     - Precision: `TP / (TP + FP)` (or 1.0 if no comments posted and no bugs, 0.0 if FP > 0 and TP == 0).
     - Recall: `TP / (TP + FN)` (or 1.0 if no ground truth findings, 0.0 if findings exist and TP == 0).
     - False-Positive Rate on clean diffs: `count(clean_diff_violation) / total_clean_cases`.
     - Avg comments per PR: `total_comments / total_cases`.
     - Nitpick rate: `nitpick_comments / total_comments`.
     - Avg latency: mean `duration_ms`.
  </action>
  <verify>
python -c "from bench.evaluator.matcher import match_comments_to_findings; from bench.schema import ReviewComment, GroundTruthFinding, FindingCategory, FindingSeverity; c = ReviewComment(file_path='a.py', line_number=10, category=FindingCategory.BUG, comment='bug'); f = GroundTruthFinding(finding_id='1', line_start=9, line_end=11, category=FindingCategory.BUG, severity=FindingSeverity.CRITICAL, description='test'); matched, fps, fns = match_comments_to_findings([c], [f]); assert len(matched) == 1 and len(fps) == 0; print('Matcher verified')"
  </verify>
</task>

<task>
  <name>Build CLI Runner and Markdown Formatter in bench/runner.py</name>
  <files>bench/runner.py, tests/test_bench_runner.py</files>
  <action>
1. Implement `bench/runner.py` with `argparse`:
   - Arguments:
     - `--split`: Target split name (`dev`, `test_locked`, `gold`) or path to a custom `.json` file of `BenchmarkCase`s. Default: `dev`.
     - `--engine`: Reviewer engine to evaluate (`mock`, `prototype`, `linters`). Default: `mock`.
     - `--output`: Filepath to write structured JSON results. Default: `bench/results/<split>_<engine>_results.json`.
     - `--format`: Output format (`text`, `json`, `markdown`, `all`). Default: `all`.
     - `--line-window`: Proximity tolerance for matching ground truth (default: 3 lines).
     - `--limit`: Optional integer to limit the run to first $N$ cases.
   - Built-in review engines for benchmarking:
     - `MockReviewer`: Returns preset comments or clean responses for rapid test verification.
     - `PrototypeReviewer`: Adapts existing Aion engine (`inference.py` / `env.py`) to generate `ReviewComment` objects from unified diffs.
     - `LinterReviewer`: Runs Ruff and Bandit against the modified file content to produce baseline comments.
   - Report generation:
     - Outputs console summary table.
     - Saves full JSON results containing all case evaluations and aggregate `BenchmarkMetrics`.
     - Generates Markdown report with summary badges, metric cards, confusion table, and detailed case-by-case findings.
2. Create unit tests in `tests/test_bench_runner.py`:
   - Test schema validation, matching proximity edge cases, clean-diff false positive penalty, metrics calculations, and CLI execution via `subprocess` or programmatic runner invocation.
  </action>
  <verify>
python -m pytest tests/test_bench_runner.py -v
  </verify>
</task>

</tasks>

