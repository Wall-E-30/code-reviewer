"""
bench_real/calibration.py

Actionability Verifier Calibration on Real Validation Data (REAL-05).
Re-fits temperature scaling on real-world validation PRs, computes reliability curves,
empirical Expected Calibration Error (ECE), Brier score, and evaluates the decision rule.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from bench_real.runner import RealBenchRunner
from bench_real.schema import RealBenchmarkCase
from rl.training.verifier_model import (
    ActionabilityFeatureExtractor,
    ActionabilityVerifierModel,
    TemperatureCalibrator,
)

logger = logging.getLogger(__name__)


class RealDataVerifierCalibrator:
    """Re-fits and checks verifier calibration on real validation PR cases."""

    def __init__(self, n_bins: int = 10) -> None:
        self.n_bins = n_bins
        self.extractor = ActionabilityFeatureExtractor()
        self.model = ActionabilityVerifierModel()

    def build_dataset_from_cases(
        self,
        cases: List[RealBenchmarkCase],
    ) -> List[Dict[str, Any]]:
        """Constructs labeled evaluation instances from real PR cases."""
        dataset: List[Dict[str, Any]] = []

        for case in cases:
            if case.is_clean_diff:
                # Negative control: comments on clean PR are false positives
                dataset.append({
                    "diff_hunk": case.diff[:500],
                    "comment_text": "Consider reviewing this change.",
                    "suggestion": None,
                    "category": "style",
                    "is_clean_diff": True,
                    "label": 0,
                })
            else:
                for finding in case.ground_truth_findings:
                    # Positive instance: actionable ground-truth finding
                    dataset.append({
                        "diff_hunk": case.diff[:500],
                        "comment_text": finding.description,
                        "suggestion": finding.fix_suggestion,
                        "category": finding.category,
                        "is_clean_diff": False,
                        "label": 1,
                    })
                # Add synthetic nitpick negative for realism
                dataset.append({
                    "diff_hunk": case.diff[:500],
                    "comment_text": "Nit: consider renaming this variable for better readability.",
                    "suggestion": None,
                    "category": "nitpick",
                    "is_clean_diff": False,
                    "label": 0,
                })

        return dataset

    def calibrate_and_evaluate(
        self,
        cases: List[RealBenchmarkCase],
        train_split_ratio: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Fits verifier on train slice and calibrates on validation slice of real data.
        Returns calibration metrics, reliability curve bins, and ECE.
        """
        data = self.build_dataset_from_cases(cases)
        if len(data) < 10:
            raise ValueError(f"Insufficient cases for calibration: {len(data)}")

        split_idx = int(len(data) * train_split_ratio)
        train_data = data[:split_idx]
        val_data = data[split_idx:]

        fit_stats = self.model.fit(train_data, val_data=val_data)

        # Predict calibrated probabilities on validation set
        y_true: List[int] = [int(d["label"]) for d in val_data]
        y_prob: List[float] = [
            self.model.predict_proba(
                diff_hunk=d["diff_hunk"],
                comment=d["comment_text"],
                suggestion=d["suggestion"],
                category=d["category"],
                is_clean_diff=d["is_clean_diff"],
            )
            for d in val_data
        ]

        # 1. Compute empirical ECE
        ece = self.model.compute_ece(y_true, y_prob, n_bins=self.n_bins)

        # 2. Compute Brier score: mean((prob - true)^2)
        brier_score = float(np.mean([(p - y) ** 2 for p, y in zip(y_prob, y_true)]))

        # 3. Construct reliability curve bins
        bin_edges = np.linspace(0.0, 1.0, self.n_bins + 1)
        reliability_bins: List[Dict[str, Any]] = []

        y_t = np.array(y_true)
        y_p = np.array(y_prob)

        for i in range(self.n_bins):
            bin_mask = (y_p >= bin_edges[i]) & (y_p < bin_edges[i + 1])
            if i == self.n_bins - 1:
                bin_mask = bin_mask | (y_p == bin_edges[i + 1])

            count = int(np.sum(bin_mask))
            if count > 0:
                acc = float(np.mean(y_t[bin_mask]))
                conf = float(np.mean(y_p[bin_mask]))
            else:
                acc = 0.0
                conf = float((bin_edges[i] + bin_edges[i + 1]) / 2.0)

            reliability_bins.append({
                "bin_index": i,
                "bin_range": f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}",
                "sample_count": count,
                "mean_confidence": round(conf, 4),
                "empirical_accuracy": round(acc, 4),
                "gap": round(abs(acc - conf), 4),
            })

        return {
            "temperature": fit_stats["temperature"],
            "expected_calibration_error": round(ece, 4),
            "brier_score": round(brier_score, 4),
            "train_samples": len(train_data),
            "val_samples": len(val_data),
            "reliability_diagram_bins": reliability_bins,
            "calibrated": ece <= 0.10,
        }

    def evaluate_decision_rule(
        self,
        benchmark_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluates the agreed milestone decision rule:
        - beats best baseline with non-overlapping 95% CIs -> PROCEED_TO_PILOT
        - matches -> REPOSITION_AS_FILTER_PLUS_LINTERS
        - loses -> DO_NOT_LAUNCH (error analysis required)
        """
        baselines = benchmark_results.get("baselines", {})
        aion_metrics = baselines.get("Aion with Trained Model") or baselines.get("Current Aion Pipeline")
        if not aion_metrics:
            return {"verdict": "ERROR", "reason": "Aion baseline metrics missing"}

        aion_ci = aion_metrics["precision"]
        aion_lower = aion_ci["ci_lower"]
        aion_mean = aion_ci["mean"]

        other_baselines = {
            k: v for k, v in baselines.items()
            if "Aion" not in k
        }

        # Find best alternative baseline by precision mean
        best_name = None
        best_ci = None
        for name, m in other_baselines.items():
            if best_ci is None or m["precision"]["mean"] > best_ci["mean"]:
                best_name = name
                best_ci = m["precision"]

        if not best_ci:
            return {"verdict": "ERROR", "reason": "No comparative baselines found"}

        best_upper = best_ci["ci_upper"]
        best_mean = best_ci["mean"]

        if aion_lower > best_upper:
            verdict = "PROCEED_TO_PILOT"
            rationale = (
                f"Aion lower 95% CI bound ({aion_lower:.1%}) strictly exceeds {best_name} "
                f"upper 95% CI bound ({best_upper:.1%}). Statistical superiority verified with non-overlapping CIs."
            )
        elif aion_mean >= best_mean:
            verdict = "REPOSITION_AS_FILTER_PLUS_LINTERS"
            rationale = (
                f"Aion precision ({aion_mean:.1%}) matches {best_name} ({best_mean:.1%}) with overlapping CIs. "
                "Reposition as precision filter plus linters."
            )
        else:
            verdict = "DO_NOT_LAUNCH"
            rationale = (
                f"Aion precision ({aion_mean:.1%}) is inferior to {best_name} ({best_mean:.1%}). "
                "Do not launch; conduct deep error analysis first."
            )

        return {
            "verdict": verdict,
            "rationale": rationale,
            "aion_precision_ci": [aion_ci["ci_lower"], aion_ci["mean"], aion_ci["ci_upper"]],
            "best_baseline": best_name,
            "best_baseline_ci": [best_ci["ci_lower"], best_ci["mean"], best_ci["ci_upper"]],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Aion Verifier Calibration on Real Data (REAL-05)")
    parser.add_argument("--split", default="val", help="Evaluation split (default: val)")
    parser.add_argument("--splits-dir", default="bench_real/splits", help="Directory with split JSON files")
    parser.add_argument("--output", default="bench_real/data/CALIBRATION_REPORT.json", help="Path for report output")
    args = parser.parse_args()

    runner = RealBenchRunner(splits_dir=Path(args.splits_dir))
    cases = runner.load_split(args.split)
    print(f"Loaded {len(cases)} cases from split '{args.split}' for verifier calibration...")

    calibrator = RealDataVerifierCalibrator()
    cal_results = calibrator.calibrate_and_evaluate(cases)

    print("\n=== Verifier Calibration Report on Real Validation PRs ===")
    print(f"Optimal Temperature (T):        {cal_results['temperature']}")
    print(f"Expected Calibration Error (ECE): {cal_results['expected_calibration_error']:.4f}")
    print(f"Brier Score:                    {cal_results['brier_score']:.4f}")
    print(f"Calibrated (ECE <= 0.10):        {'✅ YES' if cal_results['calibrated'] else '❌ NO'}\n")

    # Run benchmark to evaluate decision rule
    bench_results = runner.run_benchmark(cases, split_name=args.split)
    decision = calibrator.evaluate_decision_rule(bench_results)

    print("=== Milestone Decision Rule Evaluation ===")
    print(f"Verdict:   {decision['verdict']}")
    print(f"Rationale: {decision['rationale']}\n")

    out_file = Path(args.output)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    full_report = {
        "calibration": cal_results,
        "decision_rule": decision,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"Saved calibration report to {out_file}")


if __name__ == "__main__":
    main()

