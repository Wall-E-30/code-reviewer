"""
rl/training/bootstrap_eval.py

Bootstrap Statistical Significance & Clean-Diff FPR Evaluator (TRAIN-03).
Evaluates policy precision, recall, and false-positive rate on clean diffs against
Aion-Bench splits, computing 95% empirical bootstrap confidence intervals across 1,000 resamples.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from bench.evaluator.metrics import evaluate_case
from bench.schema import BenchmarkCase, BenchmarkMetrics, CaseEvaluation, ReviewComment

logger = logging.getLogger(__name__)


class BootstrapEvaluator:
    """
    Computes benchmark metrics and bootstrap confidence intervals to verify
    statistically significant precision gains over baselines with clean-diff FPR < 10%.
    """

    def compute_metrics_from_evaluations(
        self,
        evaluations: List[CaseEvaluation],
        split: str = "dev",
    ) -> BenchmarkMetrics:
        """Calculate aggregate BenchmarkMetrics from a list of CaseEvaluations."""
        if not evaluations:
            return BenchmarkMetrics(
                split=split,
                total_cases=0,
                clean_cases=0,
                buggy_cases=0,
                precision=0.0,
                recall=0.0,
                false_positive_rate=0.0,
                avg_comments_per_pr=0.0,
                nitpick_rate=0.0,
                avg_latency_ms=0.0,
                total_duration_sec=0.0,
            )

        total_cases = len(evaluations)
        tp = sum(e.true_positives for e in evaluations)
        fp = sum(e.false_positives for e in evaluations)
        fn = sum(e.false_negatives for e in evaluations)
        clean_cases = [e for e in evaluations if e.is_clean_diff]
        clean_violations = sum(1 for e in clean_cases if e.clean_diff_violation)
        clean_count = len(clean_cases)
        buggy_count = total_cases - clean_count
        total_comments = sum(e.comments_posted for e in evaluations)
        total_nitpicks = sum(e.nitpick_comments for e in evaluations)
        total_latency = sum(e.duration_ms for e in evaluations)
        total_duration_sec = total_latency / 1000.0

        precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fp == 0 else 0.0)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        fpr = clean_violations / clean_count if clean_count > 0 else 0.0
        avg_comments = total_comments / total_cases if total_cases > 0 else 0.0
        nitpick_rate = total_nitpicks / total_comments if total_comments > 0 else 0.0
        avg_latency = total_latency / total_cases if total_cases > 0 else 0.0

        return BenchmarkMetrics(
            split=split,
            total_cases=total_cases,
            clean_cases=clean_count,
            buggy_cases=buggy_count,
            precision=round(float(precision), 4),
            recall=round(float(recall), 4),
            false_positive_rate=round(float(fpr), 4),
            avg_comments_per_pr=round(float(avg_comments), 2),
            nitpick_rate=round(float(nitpick_rate), 4),
            avg_latency_ms=round(float(avg_latency), 2),
            total_duration_sec=round(float(total_duration_sec), 3),
        )

    def evaluate_split(
        self,
        policy_fn: Callable[[BenchmarkCase], List[ReviewComment]],
        cases: List[BenchmarkCase],
    ) -> Tuple[BenchmarkMetrics, List[CaseEvaluation]]:
        """Run policy function across cases and return aggregate metrics and evaluations."""
        evals: List[CaseEvaluation] = []
        for case in cases:
            comments = policy_fn(case)
            case_eval = evaluate_case(case, comments, duration_ms=15.0)
            evals.append(case_eval)

        metrics = self.compute_metrics_from_evaluations(evals)
        return metrics, evals

    def run_bootstrap_comparison(
        self,
        baseline_evals: List[CaseEvaluation],
        candidate_evals: List[CaseEvaluation],
        n_resamples: int = 1000,
        alpha: float = 0.05,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Run bootstrap resampling with replacement (B = 1,000 iterations).
        Computes empirical (1 - alpha) confidence intervals for:
        - Delta Precision
        - Delta Recall
        - Delta False Positive Rate
        """
        if len(baseline_evals) != len(candidate_evals):
            raise ValueError("Baseline and candidate evaluations must have the same length")

        n = len(baseline_evals)
        if n == 0:
            raise ValueError("Evaluations list cannot be empty")

        rng = np.random.default_rng(random_seed)
        delta_precisions: List[float] = []
        delta_recalls: List[float] = []
        delta_fprs: List[float] = []

        for _ in range(n_resamples):
            indices = rng.integers(0, n, size=n)
            b_sample = [baseline_evals[i] for i in indices]
            c_sample = [candidate_evals[i] for i in indices]

            b_m = self.compute_metrics_from_evaluations(b_sample)
            c_m = self.compute_metrics_from_evaluations(c_sample)

            delta_precisions.append(c_m.precision - b_m.precision)
            delta_recalls.append(c_m.recall - b_m.recall)
            delta_fprs.append(c_m.false_positive_rate - b_m.false_positive_rate)

        # Compute empirical percentiles
        low_p = (alpha / 2.0) * 100
        high_p = (1.0 - alpha / 2.0) * 100

        ci_precision = (
            round(float(np.percentile(delta_precisions, low_p)), 4),
            round(float(np.percentile(delta_precisions, high_p)), 4),
        )
        ci_recall = (
            round(float(np.percentile(delta_recalls, low_p)), 4),
            round(float(np.percentile(delta_recalls, high_p)), 4),
        )
        ci_fpr = (
            round(float(np.percentile(delta_fprs, low_p)), 4),
            round(float(np.percentile(delta_fprs, high_p)), 4),
        )

        statistically_significant = ci_precision[0] > 0.0

        return {
            "n_resamples": n_resamples,
            "alpha": alpha,
            "delta_precision_mean": round(float(np.mean(delta_precisions)), 4),
            "delta_precision_ci": ci_precision,
            "delta_recall_mean": round(float(np.mean(delta_recalls)), 4),
            "delta_recall_ci": ci_recall,
            "delta_fpr_mean": round(float(np.mean(delta_fprs)), 4),
            "delta_fpr_ci": ci_fpr,
            "statistically_significant_gain": statistically_significant,
        }

    def assert_clean_diff_fpr_gate(
        self,
        metrics: BenchmarkMetrics,
        max_fpr: float = 0.10,
    ) -> bool:
        """
        Enforce strict False-Positive Rate gate on clean diffs.
        Raises AssertionError if clean_diff_fpr >= max_fpr.
        """
        if metrics.false_positive_rate >= max_fpr:
            raise AssertionError(
                f"Clean-diff FPR gate failed: achieved {metrics.false_positive_rate:.2%}, "
                f"must be strictly < {max_fpr:.2%}"
            )
        return True

