"""
bench/splits

Benchmark dataset splits and cryptographic manifest for Aion-Bench (BENCH-04).
"""

from bench.splits.splitter import compute_case_hash, compute_file_hash, partition_benchmark

__all__ = [
    "partition_benchmark",
    "compute_case_hash",
    "compute_file_hash",
]
