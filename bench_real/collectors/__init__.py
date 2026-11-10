"""
bench_real/collectors/__init__.py

Collectors for real-world PR benchmarks across 4 provenance types.
"""

from bench_real.collectors.base import BaseCollector
from bench_real.collectors.reviewed_bugs import ReviewedBugsCollector
from bench_real.collectors.reverts_and_fixes import RevertsAndFixesCollector
from bench_real.collectors.security_cve import SecurityCVECollector
from bench_real.collectors.clean_prs import CleanPRsCollector
from bench_real.collectors.candidate_miner import CandidateMiner

__all__ = [
    "BaseCollector",
    "ReviewedBugsCollector",
    "RevertsAndFixesCollector",
    "SecurityCVECollector",
    "CleanPRsCollector",
    "CandidateMiner",
]
