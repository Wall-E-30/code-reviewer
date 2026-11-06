"""
bench/evaluator

Ground-truth matching and metric calculation engines for Aion-Bench.
"""

from bench.evaluator.matcher import MatchedPair, match_comments_to_findings
from bench.evaluator.metrics import calculate_benchmark_metrics, evaluate_case

__all__ = [
    "MatchedPair",
    "match_comments_to_findings",
    "evaluate_case",
    "calculate_benchmark_metrics",
]
