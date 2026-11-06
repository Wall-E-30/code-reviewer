"""
tests/test_bench_runner.py

Unit and integration tests for Aion-Bench evaluation suite:
- Schema validation and serialization
- Ground-truth line-window and category matcher
- Metric calculations (Precision, Recall, FPR on clean diffs, Nitpick rate)
- Built-in Reviewers (Mock, Prototype, Linters)
- CLI runner and Markdown/JSON report generation
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bench.evaluator.matcher import (
    MatchedPair,
    are_categories_compatible,
    are_paths_compatible,
    compute_line_distance,
    match_comments_to_findings,
)
from bench.evaluator.metrics import calculate_benchmark_metrics, evaluate_case
from bench.runner import (
    LinterReviewer,
    MockReviewer,
    PrototypeReviewer,
    format_console_report,
    format_markdown_report,
    main,
    run_benchmark,
)
from bench.schema import (
    BenchmarkCase,
    BenchmarkMetrics,
    CaseEvaluation,
    FindingCategory,
    FindingSeverity,
    GroundTruthFinding,
    ReviewComment,
    load_cases_from_file,
    save_cases_to_file,
)


# =====================================================================
# 1. Schema Tests
# =====================================================================

def test_benchmark_case_creation_and_defaults():
    case = BenchmarkCase(
        case_id="case-001",
        repository="org/repo",
        language="python",
        file_path="src/main.py",
        original_code="def run(): pass",
        modified_code="def run(): return 1",
        diff="@@ -1 +1 @@\n-def run(): pass\n+def run(): return 1",
        split="dev",
        is_clean_diff=True,
    )
    assert case.case_id == "case-001"
    assert case.is_clean_diff is True
    assert case.ground_truth == []
    assert case.metadata == {}


def test_ground_truth_finding_creation():
    finding = GroundTruthFinding(
        finding_id="find-101",
        line_start=15,
        line_end=18,
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.CRITICAL,
        description="SQL injection vulnerability in query builder",
        fix_suggestion="Use query parameters",
        rule_id="SEC-SQL-01",
    )
    assert finding.finding_id == "find-101"
    assert finding.category == FindingCategory.SECURITY
    assert finding.severity == FindingSeverity.CRITICAL
    assert finding.fix_suggestion == "Use query parameters"


def test_schema_json_and_dict_serialization(tmp_path):
    finding = GroundTruthFinding(
        finding_id="f1",
        line_start=10,
        line_end=12,
        category=FindingCategory.BUG,
        severity=FindingSeverity.MAJOR,
        description="Unchecked None dereference",
    )
    case = BenchmarkCase(
        case_id="c1",
        repository="org/repo",
        language="python",
        file_path="app.py",
        original_code="a = None",
        modified_code="a = None\nprint(a.val)",
        diff="...",
        split="dev",
        is_clean_diff=False,
        ground_truth=[finding],
    )

    # To / From Dict
    d = case.to_dict()
    assert d["case_id"] == "c1"
    case_from_d = BenchmarkCase.from_dict(d)
    assert len(case_from_d.ground_truth) == 1
    assert case_from_d.ground_truth[0].description == "Unchecked None dereference"

    # To / From JSON
    json_str = case.to_json()
    case_from_json = BenchmarkCase.from_json(json_str)
    assert case_from_json.case_id == "c1"

    # File save and load
    file_path = tmp_path / "cases.json"
    save_cases_to_file([case], file_path)
    loaded = load_cases_from_file(file_path)
    assert len(loaded) == 1
    assert loaded[0].case_id == "c1"
    assert loaded[0].ground_truth[0].finding_id == "f1"


# =====================================================================
# 2. Matcher Tests
# =====================================================================

def test_path_compatibility():
    assert are_paths_compatible("src/main.py", "src/main.py")
    assert are_paths_compatible("src\\main.py", "src/main.py")
    assert are_paths_compatible("a/src/main.py", "src/main.py")
    assert are_paths_compatible("./src/main.py", "src/main.py")
    assert not are_paths_compatible("src/main.py", "src/other.py")


def test_category_congruence():
    # Substantive to cosmetic mismatch
    assert not are_categories_compatible(FindingCategory.NITPICK, FindingCategory.BUG)
    assert not are_categories_compatible(FindingCategory.STYLE, FindingCategory.SECURITY)
    assert not are_categories_compatible(FindingCategory.STYLE, FindingCategory.PERFORMANCE)

    # Cosmetic to substantive mismatch
    assert not are_categories_compatible(FindingCategory.BUG, FindingCategory.STYLE)

    # Substantive to substantive compatible
    assert are_categories_compatible(FindingCategory.BUG, FindingCategory.BUG)
    assert are_categories_compatible(FindingCategory.BUG, FindingCategory.SECURITY)
    assert are_categories_compatible(FindingCategory.SECURITY, FindingCategory.BUG)

    # Cosmetic to cosmetic compatible
    assert are_categories_compatible(FindingCategory.STYLE, FindingCategory.STYLE)
    assert are_categories_compatible(FindingCategory.NITPICK, FindingCategory.STYLE)


def test_line_distance():
    # Inside span
    assert compute_line_distance(10, 10, 15) == 0
    assert compute_line_distance(12, 10, 15) == 0
    assert compute_line_distance(15, 10, 15) == 0

    # Before start
    assert compute_line_distance(8, 10, 15) == 2

    # After end
    assert compute_line_distance(18, 10, 15) == 3


def test_matcher_window_and_category():
    finding = GroundTruthFinding(
        finding_id="f1",
        line_start=20,
        line_end=22,
        category=FindingCategory.BUG,
        severity=FindingSeverity.MAJOR,
        description="Logical error",
        file_path="module.py",
    )

    # 1. Exact match within window
    comment_exact = ReviewComment(
        file_path="module.py",
        line_number=21,
        category=FindingCategory.BUG,
        comment="Bug here",
    )
    matched, fps, fns = match_comments_to_findings([comment_exact], [finding], line_window=3)
    assert len(matched) == 1
    assert len(fps) == 0
    assert len(fns) == 0
    assert matched[0].line_distance == 0

    # 2. Match at window boundary (+3 lines)
    comment_boundary = ReviewComment(
        file_path="module.py",
        line_number=25,
        category=FindingCategory.BUG,
        comment="Boundary bug",
    )
    matched, fps, fns = match_comments_to_findings([comment_boundary], [finding], line_window=3)
    assert len(matched) == 1
    assert matched[0].line_distance == 3

    # 3. Beyond window (+4 lines) -> No match
    comment_far = ReviewComment(
        file_path="module.py",
        line_number=26,
        category=FindingCategory.BUG,
        comment="Too far",
    )
    matched, fps, fns = match_comments_to_findings([comment_far], [finding], line_window=3)
    assert len(matched) == 0
    assert len(fps) == 1
    assert len(fns) == 1

    # 4. Nitpick comment on bug finding -> Incongruent category rejection
    comment_nitpick = ReviewComment(
        file_path="module.py",
        line_number=21,
        category=FindingCategory.NITPICK,
        comment="Please rename this variable",
    )
    matched, fps, fns = match_comments_to_findings([comment_nitpick], [finding], line_window=3)
    assert len(matched) == 0
    assert len(fps) == 1
    assert len(fns) == 1


def test_matcher_greedy_one_to_one():
    f1 = GroundTruthFinding(
        finding_id="f1",
        line_start=10,
        line_end=10,
        category=FindingCategory.BUG,
        severity=FindingSeverity.MAJOR,
        description="Bug 1",
        file_path="app.py",
    )
    f2 = GroundTruthFinding(
        finding_id="f2",
        line_start=20,
        line_end=20,
        category=FindingCategory.BUG,
        severity=FindingSeverity.MAJOR,
        description="Bug 2",
        file_path="app.py",
    )

    # Two comments competing for f1, none for f2
    c1 = ReviewComment(file_path="app.py", line_number=10, category=FindingCategory.BUG, comment="On target")
    c2 = ReviewComment(file_path="app.py", line_number=11, category=FindingCategory.BUG, comment="Slightly off")

    matched, fps, fns = match_comments_to_findings([c1, c2], [f1, f2], line_window=3)
    # Only 1 match allowed for f1; second comment becomes FP, f2 remains FN
    assert len(matched) == 1
    assert matched[0].finding.finding_id == "f1"
    assert matched[0].comment.line_number == 10
    assert len(fps) == 1
    assert fps[0].line_number == 11
    assert len(fns) == 1
    assert fns[0].finding_id == "f2"


# =====================================================================
# 3. Evaluator and Metrics Tests
# =====================================================================

def test_evaluate_case_clean_diff_negative_control():
    clean_case = BenchmarkCase(
        case_id="clean-1",
        repository="test",
        language="python",
        file_path="clean.py",
        original_code="a = 1",
        modified_code="a = 1\n# comment",
        diff="...",
        split="dev",
        is_clean_diff=True,
        ground_truth=[],
    )

    # Zero comments -> Clean pass (no FP, no violation)
    eval_clean = evaluate_case(clean_case, comments=[], duration_ms=10.0)
    assert eval_clean.true_positives == 0
    assert eval_clean.false_positives == 0
    assert eval_clean.clean_diff_violation is False

    # Hallucinated comment -> Instant false-positive penalty
    hallucinated = ReviewComment(
        file_path="clean.py",
        line_number=2,
        category=FindingCategory.BUG,
        comment="Phantom bug detected",
    )
    eval_violation = evaluate_case(clean_case, comments=[hallucinated], duration_ms=12.0)
    assert eval_violation.true_positives == 0
    assert eval_violation.false_positives == 1
    assert eval_violation.clean_diff_violation is True


def test_calculate_benchmark_metrics():
    # 2 Buggy Cases, 2 Clean Cases
    # Case 1: 1 TP, 0 FP, 0 FN (buggy)
    e1 = CaseEvaluation(
        case_id="b1",
        comments_posted=1,
        true_positives=1,
        false_positives=0,
        false_negatives=0,
        is_clean_diff=False,
        clean_diff_violation=False,
        duration_ms=50.0,
        nitpick_comments=0,
    )
    # Case 2: 1 TP, 1 FP, 1 FN (buggy, 1 nitpick)
    e2 = CaseEvaluation(
        case_id="b2",
        comments_posted=2,
        true_positives=1,
        false_positives=1,
        false_negatives=1,
        is_clean_diff=False,
        clean_diff_violation=False,
        duration_ms=60.0,
        nitpick_comments=1,
    )
    # Case 3: Clean passed (0 comments)
    e3 = CaseEvaluation(
        case_id="c1",
        comments_posted=0,
        true_positives=0,
        false_positives=0,
        false_negatives=0,
        is_clean_diff=True,
        clean_diff_violation=False,
        duration_ms=20.0,
        nitpick_comments=0,
    )
    # Case 4: Clean violated (1 hallucinated comment)
    e4 = CaseEvaluation(
        case_id="c2",
        comments_posted=1,
        true_positives=0,
        false_positives=1,
        false_negatives=0,
        is_clean_diff=True,
        clean_diff_violation=True,
        duration_ms=30.0,
        nitpick_comments=0,
    )

    metrics = calculate_benchmark_metrics([e1, e2, e3, e4], split_name="dev", total_duration_sec=0.16)

    # TP=2, FP=2, FN=1
    # Precision = 2 / (2 + 2) = 0.5
    assert metrics.precision == 0.5
    # Recall = 2 / (2 + 1) = 0.6667
    assert metrics.recall == pytest.approx(0.6667, rel=1e-3)
    # Clean cases = 2, clean violations = 1 -> FPR = 1 / 2 = 0.5
    assert metrics.false_positive_rate == 0.5
    # Total comments = 4, Total cases = 4 -> 1.0 comment / PR
    assert metrics.avg_comments_per_pr == 1.0
    # Nitpick rate = 1 nitpick / 4 comments = 0.25
    assert metrics.nitpick_rate == 0.25
    assert metrics.total_cases == 4
    assert metrics.clean_cases == 2
    assert metrics.buggy_cases == 2
    assert metrics.avg_latency_ms == pytest.approx(40.0, rel=1e-2)


# =====================================================================
# 4. Reviewer Engines Tests
# =====================================================================

def test_mock_reviewer_modes():
    finding = GroundTruthFinding(
        finding_id="f1",
        line_start=5,
        line_end=5,
        category=FindingCategory.BUG,
        severity=FindingSeverity.MAJOR,
        description="Divide by zero",
    )
    buggy_case = BenchmarkCase(
        case_id="bug-1",
        repository="r",
        language="python",
        file_path="math.py",
        original_code="return 1",
        modified_code="return 1 / 0",
        diff="...",
        split="dev",
        is_clean_diff=False,
        ground_truth=[finding],
    )
    clean_case = BenchmarkCase(
        case_id="clean-1",
        repository="r",
        language="python",
        file_path="math.py",
        original_code="return 1",
        modified_code="return 1",
        diff="",
        split="dev",
        is_clean_diff=True,
    )

    # Perfect mode: matches buggy ground truth, clean gets 0 comments
    perfect = MockReviewer(mode="perfect")
    assert len(perfect.review_case(buggy_case)) == 1
    assert len(perfect.review_case(clean_case)) == 0

    # Empty mode: returns 0 comments for everything
    empty = MockReviewer(mode="empty")
    assert len(empty.review_case(buggy_case)) == 0
    assert len(empty.review_case(clean_case)) == 0

    # Noisy mode: emits comment on clean case
    noisy = MockReviewer(mode="noisy")
    assert len(noisy.review_case(clean_case)) == 1
    assert noisy.review_case(clean_case)[0].category == FindingCategory.NITPICK


def test_prototype_reviewer_python_ast():
    reviewer = PrototypeReviewer()

    code_with_bugs = (
        "import os\n"
        "import sys # Unused\n"
        "def query_db(uid, items=[]):\n"  # Mutable default
        "    try:\n"
        "        cursor.execute(f'SELECT * FROM users WHERE id = {uid}')\n"  # SQL Injection
        "    except:\n"  # Bare except
        "        pass\n"
        "    for a in items:\n"
        "        for b in items:\n"  # Nested loops
        "            pass\n"
        "    eval('2+2')\n"  # Unsafe eval
    )

    case = BenchmarkCase(
        case_id="proto-1",
        repository="r",
        language="python",
        file_path="vuln.py",
        original_code="",
        modified_code=code_with_bugs,
        diff="",
        split="dev",
        is_clean_diff=False,
    )

    comments = reviewer.review_case(case)
    categories = {c.category for c in comments}

    assert FindingCategory.SECURITY in categories  # SQL Injection & eval
    assert FindingCategory.BUG in categories       # Bare except & mutable default
    assert FindingCategory.PERFORMANCE in categories  # Nested loops
    assert FindingCategory.STYLE in categories     # Unused import


def test_linter_reviewer_ruff():
    reviewer = LinterReviewer()
    python_code = "import sys\nimport os\nx = 1\n"
    case = BenchmarkCase(
        case_id="lint-1",
        repository="r",
        language="python",
        file_path="test_lint.py",
        original_code="",
        modified_code=python_code,
        diff="",
        split="dev",
        is_clean_diff=False,
    )
    comments = reviewer.review_case(case)
    assert len(comments) >= 1
    # Check that unused imports were flagged
    msgs = " ".join(c.comment for c in comments)
    assert "imported but unused" in msgs or "unused-import" in msgs or "F401" in msgs


# =====================================================================
# 5. End-to-End Benchmark Runner & Reporting Tests
# =====================================================================

def test_run_benchmark_programmatic(tmp_path):
    finding = GroundTruthFinding(
        finding_id="f1",
        line_start=3,
        line_end=3,
        category=FindingCategory.BUG,
        severity=FindingSeverity.CRITICAL,
        description="Critical error",
        file_path="main.py",
    )
    case_buggy = BenchmarkCase(
        case_id="e2e-bug",
        repository="org/repo",
        language="python",
        file_path="main.py",
        original_code="x = 1",
        modified_code="x = 1\ny = 0\nz = x / y",
        diff="...",
        split="dev",
        is_clean_diff=False,
        ground_truth=[finding],
    )
    case_clean = BenchmarkCase(
        case_id="e2e-clean",
        repository="org/repo",
        language="python",
        file_path="main.py",
        original_code="x = 1",
        modified_code="x = 1\n# clean update",
        diff="...",
        split="dev",
        is_clean_diff=True,
        ground_truth=[],
    )

    cases_file = tmp_path / "test_split.json"
    save_cases_to_file([case_buggy, case_clean], cases_file)

    output_json = tmp_path / "results.json"

    metrics, evaluations = run_benchmark(
        cases_or_split=cases_file,
        engine="mock",
        line_window=3,
        output_path=output_json,
        output_format="all",
    )

    assert metrics.total_cases == 2
    assert metrics.clean_cases == 1
    assert metrics.buggy_cases == 1
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.false_positive_rate == 0.0

    # Verify JSON result output
    assert output_json.exists()
    with open(output_json, "r", encoding="utf-8") as f:
        res = json.load(f)
        assert res["metrics"]["precision"] == 1.0
        assert len(res["evaluations"]) == 2

    # Verify Markdown report output
    output_md = output_json.with_suffix(".md")
    assert output_md.exists()
    md_content = output_md.read_text(encoding="utf-8")
    assert "Aion-Bench Evaluation Report" in md_content
    assert "Precision" in md_content
    assert "e2e-bug" in md_content


def test_cli_runner_execution(tmp_path):
    case = BenchmarkCase(
        case_id="cli-1",
        repository="repo",
        language="python",
        file_path="a.py",
        original_code="",
        modified_code="",
        diff="",
        split="dev",
        is_clean_diff=True,
    )
    cases_file = tmp_path / "cli_cases.json"
    save_cases_to_file([case], cases_file)
    output_json = tmp_path / "cli_results.json"

    # Test invoking main() directly with CLI arguments
    exit_code = main([
        "--cases", str(cases_file),
        "--engine", "mock",
        "--output", str(output_json),
        "--format", "json",
    ])
    assert exit_code == 0
    assert output_json.exists()
