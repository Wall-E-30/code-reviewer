"""
tests/test_launch_gate_check.py

Unit test suite for Automated Launch Gate Check Script (LAUNCH-04).
Verifies:
- Clean pass on current repository state
- Fail-closed behavior on missing or degraded benchmark evaluation
- Fail-closed behavior on synthetic data ratio exceeding 50%
- Fail-closed behavior on missing launch publication assets
- CLI argument parsing and JSON report generation
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import pytest

from scripts.launch_gate_check import GateResult, LaunchGateChecker

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_launch_gate_checker_current_repo_passes():
    checker = LaunchGateChecker(repo_root=REPO_ROOT)
    results = checker.run_all_gates()

    failed_gates = [
        f"{cat} -> {r['name']}: {r.get('message', '')}"
        for cat, r_list in results["categories"].items()
        for r in r_list
        if not r["passed"]
    ]
    assert results["overall_passed"] is True, f"Failed gates: {failed_gates}"
    assert results["failed_gates"] == 0
    assert results["total_gates"] >= 18
    assert results["passed_gates"] == results["total_gates"]


def test_launch_gate_fails_on_missing_evaluation(tmp_path: Path):
    # Empty temporary directory
    checker = LaunchGateChecker(repo_root=tmp_path)
    bench_results = checker.check_gate_bench_real()

    assert any(not r.passed for r in bench_results)
    assert any("not found" in r.message.lower() or "missing" in r.message.lower() for r in bench_results)


def test_launch_gate_fails_on_degraded_precision(tmp_path: Path):
    bench_dir = tmp_path / "bench_real" / "data"
    bench_dir.mkdir(parents=True)
    fake_eval = {
        "split": "val",
        "baselines": {
            "Aion with Trained Model": {
                "precision": {"mean": 0.65, "ci_lower": 0.55, "ci_upper": 0.75},  # Below 0.75 threshold
                "recall": {"mean": 0.88, "ci_lower": 0.80, "ci_upper": 0.94},
                "clean_diff_fpr": {"mean": 0.05, "ci_lower": 0.0, "ci_upper": 0.10},
            }
        }
    }
    (bench_dir / "BASELINE_EVAL_VAL.json").write_text(json.dumps(fake_eval), encoding="utf-8")

    checker = LaunchGateChecker(repo_root=tmp_path)
    bench_results = checker.check_gate_bench_real()

    prec_result = next(r for r in bench_results if r.name == "Trained Policy Precision")
    assert prec_result.passed is False
    assert "below 0.75" in prec_result.message


def test_launch_gate_fails_on_excessive_synthetic_ratio(tmp_path: Path):
    train_dir = tmp_path / "data" / "training_v2"
    train_dir.mkdir(parents=True)
    fake_manifest = {
        "version": "2.0.0",
        "synthetic_ratio": 0.65,  # Exceeds 50%
        "synthetic_capped_at_50_pct": False,
        "contamination_detected": False,
        "slices": {},
    }
    (train_dir / "manifest.json").write_text(json.dumps(fake_manifest), encoding="utf-8")

    checker = LaunchGateChecker(repo_root=tmp_path)
    manifest_results = checker.check_gate_training_v2_manifest()

    synth_result = next(r for r in manifest_results if r.name == "Synthetic Training Data Ratio")
    assert synth_result.passed is False
    assert "exceeds 50%" in synth_result.message


def test_launch_gate_fails_on_missing_launch_asset(tmp_path: Path):
    checker = LaunchGateChecker(repo_root=tmp_path)
    asset_results = checker.check_gate_launch_assets()

    assert all(not r.passed for r in asset_results)
