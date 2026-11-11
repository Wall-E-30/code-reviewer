#!/usr/bin/env python3
"""
scripts/sample_pilot_comments.py - Stratified Pilot Review Comment Sampler.

Extracts posted/candidate review comments across pilot repositories for a target week
and produces stratified samples in JSON and CSV format for human maintainer auditing (PILOT-04).
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Optional, Tuple


def load_candidate_comments(input_path: str | Path) -> List[Dict[str, Any]]:
    """Load review comments from a JSONL file or directory of JSONL files."""
    path = Path(input_path)
    comments: List[Dict[str, Any]] = []

    files_to_read: List[Path] = []
    if path.is_file():
        files_to_read.append(path)
    elif path.is_dir():
        files_to_read.extend(sorted(path.glob("**/*.jsonl")))
    else:
        # File doesn't exist yet, return empty list
        return comments

    for p in files_to_read:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    # Support both shadow review format and raw comment dictionaries
                    if "candidate_comments" in entry:
                        for c in entry["candidate_comments"]:
                            c_dict = dict(c)
                            c_dict.setdefault("repo", entry.get("repository", entry.get("repo", "unknown/repo")))
                            c_dict.setdefault("pr_number", entry.get("pr_number", 0))
                            comments.append(c_dict)
                    elif "comments" in entry and isinstance(entry["comments"], list):
                        for c in entry["comments"]:
                            c_dict = dict(c)
                            c_dict.setdefault("repo", entry.get("repo", "unknown/repo"))
                            c_dict.setdefault("pr_number", entry.get("pr_number", 0))
                            comments.append(c_dict)
                    elif "file_path" in entry:
                        comments.append(entry)
                except Exception:
                    continue

    return comments


def stratified_sample(
    comments: List[Dict[str, Any]],
    sample_size: int = 50,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Perform stratified sampling across finding categories (bug, security, performance, style).
    Ensures minority categories (e.g. security) are adequately represented.
    """
    if not comments:
        return []

    if len(comments) <= sample_size:
        # Return all comments with assigned sample IDs
        rng = random.Random(seed)
        shuffled = list(comments)
        rng.shuffle(shuffled)
        for idx, item in enumerate(shuffled, 1):
            item["sample_id"] = f"AUDIT-SAMPLE-{idx:03d}"
            item.setdefault("audit_label", "")  # human label: accurate | false_positive
            item.setdefault("applied", "")      # human label: yes | no
            item.setdefault("auditor_notes", "")
        return shuffled

    rng = random.Random(seed)
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for c in comments:
        cat = str(c.get("category", "bug")).lower()
        by_category.setdefault(cat, []).append(c)

    categories = list(by_category.keys())
    per_category_target = max(1, sample_size // len(categories))

    sampled: List[Dict[str, Any]] = []
    remaining_pool: List[Dict[str, Any]] = []

    for cat, items in by_category.items():
        rng.shuffle(items)
        take = min(len(items), per_category_target)
        sampled.extend(items[:take])
        remaining_pool.extend(items[take:])

    # If shortfall due to small categories, sample from remaining pool
    shortfall = sample_size - len(sampled)
    if shortfall > 0 and remaining_pool:
        rng.shuffle(remaining_pool)
        sampled.extend(remaining_pool[:shortfall])

    rng.shuffle(sampled)
    for idx, item in enumerate(sampled, 1):
        item["sample_id"] = f"AUDIT-SAMPLE-{idx:03d}"
        item.setdefault("audit_label", "")  # accurate | false_positive
        item.setdefault("applied", "")      # yes | no
        item.setdefault("auditor_notes", "")

    return sampled


def export_sample_csv(samples: List[Dict[str, Any]], output_path: str | Path) -> Path:
    """Export audit sample to CSV for spreadsheet-based human annotation."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "sample_id",
        "repo",
        "pr_number",
        "category",
        "severity",
        "file_path",
        "line_number",
        "confidence",
        "comment",
        "suggestion",
        "audit_label",
        "applied",
        "auditor_notes",
    ]

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in samples:
            writer.writerow(item)

    return out


def export_sample_json(samples: List[Dict[str, Any]], output_path: str | Path) -> Path:
    """Export audit sample to formatted JSON."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)

    return out


def sample_pilot_comments(
    input_path: str | Path = ".aion/shadow_reviews.jsonl",
    output_dir: str | Path = "docs/pilots/audit_samples",
    sample_size: int = 50,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], Path, Path]:
    """Execute stratified sampling and write both JSON and CSV files."""
    comments = load_candidate_comments(input_path)
    samples = stratified_sample(comments, sample_size=sample_size, seed=seed)

    out_dir = Path(output_dir)
    json_path = out_dir / "weekly_audit_sample.json"
    csv_path = out_dir / "weekly_audit_sample.csv"

    export_sample_json(samples, json_path)
    export_sample_csv(samples, csv_path)

    return samples, json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Sample pilot review comments for human auditing.")
    parser.add_argument(
        "--input",
        default=".aion/shadow_reviews.jsonl",
        help="Input JSONL file or directory containing review logs.",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/pilots/audit_samples",
        help="Directory to write weekly_audit_sample.json and .csv.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=50,
        help="Number of comments to sample. Default: 50.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic stratified sampling.",
    )

    args = parser.parse_args()

    samples, json_path, csv_path = sample_pilot_comments(
        input_path=args.input,
        output_dir=args.output_dir,
        sample_size=args.sample_size,
        seed=args.seed,
    )

    print(f"Sampled {len(samples)} comments across categories:")
    counts: Dict[str, int] = {}
    for s in samples:
        c = s.get("category", "unknown")
        counts[c] = counts.get(c, 0) + 1
    for cat, cnt in counts.items():
        print(f"  {cat}: {cnt}")
    print(f"JSON Output: {json_path}")
    print(f"CSV Output : {csv_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
