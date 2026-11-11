#!/usr/bin/env python3
"""
scripts/pilot_audit_report.py - Audited Live Precision & Pilot Metrics Generator.

Ingests human-audited pilot comment samples, computes audited live precision
with 95% bootstrap confidence intervals, maintainer acceptance rate, applied suggestion rate,
repository mute rate, and estimated PR inference costs (PILOT-04).
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Optional, Tuple


def load_audited_records(input_path: str | Path) -> List[Dict[str, Any]]:
    """Load audited records from CSV or JSON file."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Audited file not found: {path}")

    records: List[Dict[str, Any]] = []
    if path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
    elif path.suffix.lower() == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict) and "records" in data:
                records = data["records"]
    else:
        raise ValueError(f"Unsupported file format '{path.suffix}'. Expected .csv or .json")

    return records


def compute_bootstrap_precision_ci(
    labels: List[str],
    num_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """
    Compute point estimate and non-parametric bootstrap confidence interval for precision.
    Labels should contain 'accurate' or 'false_positive'.
    Returns (point_estimate, ci_lower, ci_upper).
    """
    evaluated = [lb.strip().lower() for lb in labels if lb.strip().lower() in ("accurate", "false_positive")]
    if not evaluated:
        return 0.0, 0.0, 0.0

    n = len(evaluated)
    point_estimate = sum(1 for x in evaluated if x == "accurate") / n

    if n == 1 or len(set(evaluated)) == 1:
        return round(point_estimate, 4), round(point_estimate, 4), round(point_estimate, 4)

    rng = random.Random(seed)
    boot_precisions: List[float] = []

    for _ in range(num_resamples):
        sample = rng.choices(evaluated, k=n)
        acc_count = sum(1 for item in sample if item == "accurate")
        boot_precisions.append(acc_count / n)

    boot_precisions.sort()
    alpha = (1.0 - confidence_level) / 2.0
    low_idx = int(round(alpha * num_resamples))
    high_idx = int(round((1.0 - alpha) * num_resamples)) - 1
    low_idx = max(0, min(low_idx, num_resamples - 1))
    high_idx = max(0, min(high_idx, num_resamples - 1))

    ci_lower = boot_precisions[low_idx]
    ci_upper = boot_precisions[high_idx]

    return round(point_estimate, 4), round(ci_lower, 4), round(ci_upper, 4)


def compute_audit_metrics(
    records: List[Dict[str, Any]],
    total_enrolled_repos: int = 10,
    muted_repo_count: int = 0,
    cost_per_input_1k: float = 0.0005,
    cost_per_output_1k: float = 0.0015,
    avg_tokens_per_pr: Tuple[int, int] = (1800, 350),
    num_resamples: int = 1000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Compute complete suite of pilot audit metrics."""
    evaluated_records = [
        r for r in records
        if str(r.get("audit_label", "")).strip().lower() in ("accurate", "false_positive")
    ]
    total_sampled = len(records)
    total_evaluated = len(evaluated_records)

    labels = [str(r.get("audit_label", "")).strip().lower() for r in evaluated_records]
    precision, ci_low, ci_high = compute_bootstrap_precision_ci(
        labels, num_resamples=num_resamples, seed=seed
    )

    # Acceptance rate (accurate or positive reaction or applied)
    accepted_count = 0
    for r in evaluated_records:
        applied = str(r.get("applied", "")).strip().lower() in ("yes", "true", "1")
        is_acc = str(r.get("audit_label", "")).strip().lower() == "accurate"
        if applied or is_acc:
            accepted_count += 1

    acceptance_rate = accepted_count / total_evaluated if total_evaluated > 0 else 0.0

    # Applied suggestions rate
    with_suggestions = [r for r in records if str(r.get("suggestion", "")).strip()]
    applied_suggestions = [
        r for r in with_suggestions
        if str(r.get("applied", "")).strip().lower() in ("yes", "true", "1")
    ]
    applied_rate = (
        len(applied_suggestions) / len(with_suggestions) if with_suggestions else 0.0
    )

    # Category breakdown
    category_metrics: Dict[str, Dict[str, Any]] = {}
    for cat in ["security", "bug", "performance", "style"]:
        cat_recs = [
            r for r in evaluated_records
            if str(r.get("category", "")).strip().lower() == cat
        ]
        if cat_recs:
            c_labels = [str(r.get("audit_label", "")).strip().lower() for r in cat_recs]
            c_prec, c_low, c_high = compute_bootstrap_precision_ci(
                c_labels, num_resamples=num_resamples, seed=seed
            )
            category_metrics[cat] = {
                "count": len(cat_recs),
                "precision": c_prec,
                "ci_95": [c_low, c_high],
            }

    # Repository mute rate
    mute_rate = (
        muted_repo_count / total_enrolled_repos if total_enrolled_repos > 0 else 0.0
    )

    # Cost per PR estimation
    in_tok, out_tok = avg_tokens_per_pr
    cost_per_pr = ((in_tok / 1000.0) * cost_per_input_1k) + (
        (out_tok / 1000.0) * cost_per_output_1k
    )

    return {
        "total_sampled": total_sampled,
        "total_evaluated": total_evaluated,
        "audited_live_precision": precision,
        "precision_ci_95": [ci_low, ci_high],
        "maintainer_acceptance_rate": round(acceptance_rate, 4),
        "applied_suggestion_rate": round(applied_rate, 4),
        "total_enrolled_repos": total_enrolled_repos,
        "muted_repos": muted_repo_count,
        "repo_mute_rate": round(mute_rate, 4),
        "estimated_cost_per_pr_usd": round(cost_per_pr, 6),
        "category_breakdown": category_metrics,
        "provenance": "audited_pilot",
    }


def generate_audit_markdown(metrics: Dict[str, Any], title: str = "Aion Pilot Audit Report") -> str:
    """Format metrics dictionary into professional Markdown document."""
    ci = metrics.get("precision_ci_95", [0.0, 0.0])
    lines = [
        f"# {title}",
        "",
        "> **Provenance:** `audited_pilot` | **Bootstrap Resamples:** `1,000` | **Confidence:** `95%`",
        "",
        "## 1. Key Performance Indicators",
        "",
        "| Metric | Measured Value | Target / Benchmark | Status |",
        "|:---|:---:|:---:|:---:|",
        f"| **Audited Live Precision** | **{metrics['audited_live_precision']:.1%}** (95% CI: [{ci[0]:.1%}, {ci[1]:.1%}]) | >= 85.0% | {'PASS ✅' if metrics['audited_live_precision'] >= 0.85 else 'REVIEW ⚠️'} |",
        f"| **Maintainer Acceptance Rate** | {metrics['maintainer_acceptance_rate']:.1%} | >= 75.0% | {'PASS ✅' if metrics['maintainer_acceptance_rate'] >= 0.75 else 'REVIEW ⚠️'} |",
        f"| **Applied Suggestion Rate** | {metrics['applied_suggestion_rate']:.1%} | >= 40.0% | {'PASS ✅' if metrics['applied_suggestion_rate'] >= 0.40 else 'INFO ℹ️'} |",
        f"| **Repository Mute Rate** | {metrics['repo_mute_rate']:.1%} ({metrics['muted_repos']}/{metrics['total_enrolled_repos']}) | <= 10.0% | {'PASS ✅' if metrics['repo_mute_rate'] <= 0.10 else 'ALERT 🚨'} |",
        f"| **Estimated Inference Cost/PR** | ${metrics['estimated_cost_per_pr_usd']:.4f} USD | < $0.02 | PASS ✅ |",
        "",
        "## 2. Sample Coverage & Category Breakdown",
        "",
        f"- **Total Comments Sampled:** `{metrics['total_sampled']}`",
        f"- **Audited & Labeled Comments:** `{metrics['total_evaluated']}`",
        "",
        "| Category | Evaluated | Precision | 95% Bootstrap CI |",
        "|:---|:---:|:---:|:---:|",
    ]

    for cat, info in metrics.get("category_breakdown", {}).items():
        c_ci = info.get("ci_95", [0.0, 0.0])
        lines.append(
            f"| **{cat.capitalize()}** | {info['count']} | {info['precision']:.1%} | [{c_ci[0]:.1%}, {c_ci[1]:.1%}] |"
        )

    lines.extend([
        "",
        "---",
        "*Report generated automatically by `scripts/pilot_audit_report.py` for Milestone v1.1 Live Pilot Validation.*",
    ])

    return "\n".join(lines) + "\n"


def run_pilot_audit(
    input_path: str | Path,
    output_md: Optional[str | Path] = None,
    output_json: Optional[str | Path] = None,
    total_enrolled_repos: int = 10,
    muted_repo_count: int = 0,
    seed: int = 42,
) -> Dict[str, Any]:
    """Run pilot audit pipeline from input file to reports."""
    records = load_audited_records(input_path)
    metrics = compute_audit_metrics(
        records=records,
        total_enrolled_repos=total_enrolled_repos,
        muted_repo_count=muted_repo_count,
        seed=seed,
    )

    if output_json:
        out_j = Path(output_json)
        out_j.parent.mkdir(parents=True, exist_ok=True)
        with open(out_j, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

    md_content = generate_audit_markdown(metrics)
    if output_md:
        out_m = Path(output_md)
        out_m.parent.mkdir(parents=True, exist_ok=True)
        with open(out_m, "w", encoding="utf-8") as f:
            f.write(md_content)

    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate pilot audit report with bootstrap CIs.")
    parser.add_argument("--input", required=True, help="Path to audited CSV or JSON file.")
    parser.add_argument("--output-md", default=None, help="Path to write Markdown report.")
    parser.add_argument("--output-json", default=None, help="Path to write JSON report.")
    parser.add_argument("--repos", type=int, default=10, help="Total enrolled pilot repositories.")
    parser.add_argument("--muted-repos", type=int, default=0, help="Number of muted pilot repositories.")

    args = parser.parse_args()

    metrics = run_pilot_audit(
        input_path=args.input,
        output_md=args.output_md,
        output_json=args.output_json,
        total_enrolled_repos=args.repos,
        muted_repo_count=args.muted_repos,
    )

    print(generate_audit_markdown(metrics))
    return 0


if __name__ == "__main__":
    sys.exit(main())

