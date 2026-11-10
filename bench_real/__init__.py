"""
bench_real/__init__.py

Package root for Aion Real-Data Evaluation Benchmark (Milestone v1.1, REAL-01).
"""

from bench_real.schema import (
    AnnotatorVote,
    RealBenchmarkCase,
    RealFinding,
    SourceType,
)

__all__ = [
    "AnnotatorVote",
    "RealBenchmarkCase",
    "RealFinding",
    "SourceType",
]
