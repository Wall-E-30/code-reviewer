"""
bench/evaluator/metrics.py

Evaluation metrics calculator for Aion-Bench (BENCH-05).
Computes Precision, Recall, False-Positive Rate on clean diffs,
Average comments per PR, Nitpick rate, and runtime latencies.
"""

from __future__ import annotations

from typing import List

from bench.evaluator.matcher import match_comments_to_findings
from bench.schema import (
    BenchmarkCase,
    BenchmarkMetrics,
    CaseEvaluation,
    FindingCategory,
    ReviewComment,
)


def evaluate_case(
    case: BenchmarkCase,
    comments: List[ReviewComment],
    duration_ms: float = 0.0,
    line_window: int = 3,
) -> CaseEvaluation:
    """
    Evaluate reviewer engine comments on a single BenchmarkCase.

    Args:
        case: Target BenchmarkCase containing ground truth.
        comments: List of ReviewComment objects emitted by reviewer engine.
        duration_ms: Time taken to review this case in milliseconds.
        line_window: Line proximity tolerance window.

    Returns:
        CaseEvaluation with True Positives, False Positives, False Negatives,
        clean diff violation flag, and list of matched findings.
    """
    comments_posted = len(comments)
    nitpick_count = sum(
        1 for c in comments if c.category in (FindingCategory.STYLE, FindingCategory.NITPICK)
    )

    # Negative Control: Clean diffs must receive ZERO comments.
    if case.is_clean_diff:
        clean_violation = comments_posted > 0
        return CaseEvaluation(
            case_id=case.case_id,
            comments_posted=comments_posted,
            true_positives=0,
            false_positives=comments_posted,
            false_negatives=0,
            is_clean_diff=True,
            clean_diff_violation=clean_violation,
            matched_findings=[],
            duration_ms=duration_ms,
            nitpick_comments=nitpick_count,
        )

    # For findings without explicit file_path, attach case file_path for matching
    prepared_findings = []
    for f in case.ground_truth:
        if not getattr(f, "file_path", None):
            f_copy = f.model_copy(update={"file_path": case.file_path})
            prepared_findings.append(f_copy)
        else:
            prepared_findings.append(f)

    # Match comments to ground-truth findings
    matched, fps, fns = match_comments_to_findings(
        comments=comments,
        findings=prepared_findings,
        line_window=line_window,
    )

    matched_records = [
        {
            "finding_id": m.finding.finding_id,
            "rule_id": m.finding.rule_id,
            "finding_category": m.finding.category.value,
            "finding_severity": m.finding.severity.value,
            "finding_lines": [m.finding.line_start, m.finding.line_end],
            "comment_line": m.comment.line_number,
            "comment_category": m.comment.category.value,
            "line_distance": m.line_distance,
            "comment_text": m.comment.comment,
        }
        for m in matched
    ]

    return CaseEvaluation(
        case_id=case.case_id,
        comments_posted=comments_posted,
        true_positives=len(matched),
        false_positives=len(fps),
        false_negatives=len(fns),
        is_clean_diff=False,
        clean_diff_violation=False,
        matched_findings=matched_records,
        duration_ms=duration_ms,
        nitpick_comments=nitpick_count,
    )


def calculate_benchmark_metrics(
    evaluations: List[CaseEvaluation],
    split_name: str,
    total_duration_sec: float,
) -> BenchmarkMetrics:
    """
    Calculate aggregate benchmark metrics across all evaluated cases in a split.

    Args:
        evaluations: List of CaseEvaluation objects.
        split_name: Name of the evaluated split (e.g. 'dev', 'gold', 'test_locked').
        total_duration_sec: Total execution time of the benchmark run in seconds.

    Returns:
        BenchmarkMetrics containing Precision, Recall, FPR, etc.
    """
    total_cases = len(evaluations)
    if total_cases == 0:
        return BenchmarkMetrics(
            split=split_name,
            total_cases=0,
            clean_cases=0,
            buggy_cases=0,
            precision=1.0,
            recall=1.0,
            false_positive_rate=0.0,
            avg_comments_per_pr=0.0,
            nitpick_rate=0.0,
            avg_latency_ms=0.0,
            total_duration_sec=round(total_duration_sec, 2),
        )

    clean_cases = sum(1 for e in evaluations if e.is_clean_diff)
    buggy_cases = total_cases - clean_cases

    tp_sum = sum(e.true_positives for e in evaluations)
    fp_sum = sum(e.false_positives for e in evaluations)
    fn_sum = sum(e.false_negatives for e in evaluations)

    clean_violations = sum(1 for e in evaluations if e.clean_diff_violation)
    total_comments = sum(e.comments_posted for e in evaluations)
    total_nitpicks = sum(e.nitpick_comments for e in evaluations)

    # Precision: TP / (TP + FP)
    # If no comments posted: 1.0 if no ground truth bugs existed, else 0.0
    if tp_sum + fp_sum > 0:
        precision = tp_sum / (tp_sum + fp_sum)
    else:
        precision = 1.0 if fn_sum == 0 else 0.0

    # Recall: TP / (TP + FN)
    # If no ground truth bugs exist across all cases, recall is vacuously 1.0
    if tp_sum + fn_sum > 0:
        recall = tp_sum / (tp_sum + fn_sum)
    else:
        recall = 1.0

    # False-Positive Rate on clean diffs
    fpr = (clean_violations / clean_cases) if clean_cases > 0 else 0.0

    # Average comments per PR
    avg_comments = total_comments / total_cases

    # Nitpick rate: proportion of all comments that are cosmetic/style/nitpick
    nitpick_rate = (total_nitpicks / total_comments) if total_comments > 0 else 0.0

    # Latency
    avg_latency = sum(e.duration_ms for e in evaluations) / total_cases

    return BenchmarkMetrics(
        split=split_name,
        total_cases=total_cases,
        clean_cases=clean_cases,
        buggy_cases=buggy_cases,
        precision=round(precision, 4),
        recall=round(recall, 4),
        false_positive_rate=round(fpr, 4),
        avg_comments_per_pr=round(avg_comments, 2),
        nitpick_rate=round(nitpick_rate, 4),
        avg_latency_ms=round(avg_latency, 2),
        total_duration_sec=round(total_duration_sec, 2),
    )
