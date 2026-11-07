"""
bench/splits/splitter.py

Stratified dataset partitioning and cryptographic manifest generation for Aion-Bench (BENCH-04).
Partitions synthesized benchmark cases into:
  - dev.json (~70 cases): Open for prompt tuning, agent development, and regression testing.
  - gold.json (100-200 cases): Hand-audited, high-signal evaluation set for calibration.
  - test_locked.json (~60 cases): Cryptographically isolated held-out split to prevent leakage.
  - manifest.json: SHA-256 cryptographic checksums securing split immutability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from bench.schema import BenchmarkCase, load_cases_from_file, save_cases_to_file


def compute_case_hash(case: BenchmarkCase) -> str:
    """Compute deterministic SHA-256 checksum for a single benchmark case."""
    canonical_payload = json.dumps(case.to_dict(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def compute_file_hash(file_path: Union[str, Path]) -> str:
    """Compute SHA-256 checksum for an entire file, normalizing newlines (CRLF -> LF) for cross-platform determinism."""
    path = Path(file_path)
    with open(path, "rb") as f:
        content = f.read().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def partition_benchmark(
    raw_cases_file: Union[str, Path] = "data/benchmark_cases_raw.json",
    output_dir: Union[str, Path] = "bench/splits",
    seed: int = 42,
    gold_target: int = 120,
    dev_target: int = 70,
    test_locked_target: int = 60,
) -> Dict[str, int]:
    """
    Partition raw benchmark cases into stratified splits (dev, gold, test_locked)
    and generate a cryptographic SHA-256 manifest.

    Args:
        raw_cases_file: Path to raw benchmark cases JSON file.
        output_dir: Destination directory for splits and manifest.
        seed: Random seed for deterministic reproducibility.
        gold_target: Target number of cases for gold set (default: 120, must be 100-200).
        dev_target: Target number of cases for dev set (default: 70).
        test_locked_target: Target number of cases for test_locked set (default: 60).

    Returns:
        Dict mapping split names to case counts.
    """
    raw_path = Path(raw_cases_file)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw cases file not found: {raw_path}")

    cases = load_cases_from_file(raw_path)
    total_cases = len(cases)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Stratify by (language, is_clean_diff, source_group)
    strata: Dict[Tuple[str, bool, str], List[BenchmarkCase]] = {}
    for c in cases:
        src = c.metadata.get("source") or c.metadata.get("synthesizer") or "other"
        # Group clean refactors together
        if c.is_clean_diff:
            src_group = "clean"
        elif "mined" in src:
            src_group = "mined"
        else:
            src_group = "injected"

        key = (c.language.lower(), c.is_clean_diff, src_group)
        strata.setdefault(key, []).append(c)

    rng = random.Random(seed)

    gold_cases: List[BenchmarkCase] = []
    dev_cases: List[BenchmarkCase] = []
    locked_cases: List[BenchmarkCase] = []

    # Proportions: gold ~ 48%, dev ~ 28%, locked ~ 24%
    p_gold = gold_target / total_cases
    p_dev = dev_target / total_cases

    for key, stratum_cases in strata.items():
        rng.shuffle(stratum_cases)
        n = len(stratum_cases)

        n_gold = int(round(n * p_gold))
        n_dev = int(round(n * p_dev))

        # Ensure bounds
        n_gold = min(n_gold, n)
        n_dev = min(n_dev, n - n_gold)
        n_locked = n - n_gold - n_dev

        gold_cases.extend(stratum_cases[:n_gold])
        dev_cases.extend(stratum_cases[n_gold : n_gold + n_dev])
        locked_cases.extend(stratum_cases[n_gold + n_dev :])

    # Rebalance if slight rounding deviations occur
    all_assigned = gold_cases + dev_cases + locked_cases
    assert len(all_assigned) == total_cases, "Partitioning lost or duplicated cases"

    # Update case.split attribute
    for c in dev_cases:
        c.split = "dev"
    for c in gold_cases:
        c.split = "gold"
    for c in locked_cases:
        c.split = "test_locked"

    # Save split JSON files
    dev_file = out_path / "dev.json"
    gold_file = out_path / "gold.json"
    locked_file = out_path / "test_locked.json"

    save_cases_to_file(dev_cases, dev_file)
    save_cases_to_file(gold_cases, gold_file)
    save_cases_to_file(locked_cases, locked_file)

    # Generate Cryptographic Manifest for test_locked and gold sets
    manifest_payload = {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": total_cases,
        "splits": {
            "dev": {
                "total_cases": len(dev_cases),
                "file_sha256": compute_file_hash(dev_file),
            },
            "gold": {
                "total_cases": len(gold_cases),
                "file_sha256": compute_file_hash(gold_file),
                "case_hashes": {c.case_id: compute_case_hash(c) for c in gold_cases},
            },
            "test_locked": {
                "total_cases": len(locked_cases),
                "file_sha256": compute_file_hash(locked_file),
                "case_hashes": {c.case_id: compute_case_hash(c) for c in locked_cases},
            },
        },
    }

    manifest_file = out_path / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2, ensure_ascii=False)

    return {
        "dev": len(dev_cases),
        "gold": len(gold_cases),
        "test_locked": len(locked_cases),
    }


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aion-Bench Splitter: Stratifies cases into dev, gold, and test_locked splits."
    )
    parser.add_argument(
        "--raw-cases",
        type=str,
        default="data/benchmark_cases_raw.json",
        help="Path to raw benchmark cases JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="bench/splits",
        help="Destination directory for splits and manifest.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed (default: 42).",
    )
    return parser.parse_args(args)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    print(f"[*] Splitting benchmark cases from {args.raw_cases} -> {args.output_dir}...")
    counts = partition_benchmark(
        raw_cases_file=args.raw_cases,
        output_dir=args.output_dir,
        seed=args.seed,
    )
    print("[+] Partition complete:")
    for split_name, count in counts.items():
        print(f"    - {split_name:<12}: {count} cases")
    print(f"[+] Cryptographic manifest generated at {Path(args.output_dir) / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
