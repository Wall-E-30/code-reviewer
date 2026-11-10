"""
bench_real/annotation/__init__.py

Annotation tooling and inter-annotator agreement metrics (REAL-02).
"""

from bench_real.annotation.agreement import compute_cohens_kappa, extract_disagreements
from bench_real.annotation.tool import AnnotationSession

__all__ = [
    "AnnotationSession",
    "compute_cohens_kappa",
    "extract_disagreements",
]

