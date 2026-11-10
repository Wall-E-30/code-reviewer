"""
tests/test_bench_real_runner_and_calibration.py

Unit tests for bench_real evaluation runner, 5-baseline comparison,
95% bootstrap confidence intervals, locked test split protection,
and actionability verifier calibration (REAL-04, REAL-05).
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from bench_real.calibration import RealDataVerifierCalibrator
from bench_real.runner import (
    RealBenchRunner,
    compute_bootstrap_ci,
    match_findings_greedy,
)
from bench_real.schema import RealBenchmarkCase, RealFinding, SourceType


def test_bootstrap_ci_bounds():
    """Verify bootstrap CI correctly brackets the mean and handles edge cases."""
    data = [0.80, 0.85, 0.90, 0.75, 0.88, 0.92, 0.79, 0.84]
    ci = compute_bootstrap_ci(data, n_resamples=1000)

    assert ci["ci_lower"] <= ci["mean"] <= ci["ci_upper"]
    assert 0.75 <= ci["mean"] <= 0.90

    # Single-element or zero-variance edge case
    single_ci = compute_bootstrap_ci([0.50])
    assert single_ci["mean"] == 0.50
    assert single_ci["ci_lower"] == 0.50
    assert single_ci["ci_upper"] == 0.50


def test_locked_test_split_access_barrier(tmp_path: Path):
    """Verify runner forbids peeking at locked test split without explicit frozen authorization."""
    splits_dir = tmp_path / "splits"
    splits_dir.mkdir()
    (splits_dir / "val.json").write_text("[]", encoding="utf-8")
    (splits_dir / "test.json").write_text("[]", encoding="utf-8")

    runner = RealBenchRunner(splits_dir=splits_dir)

    # val split should load cleanly
    assert runner.load_split("val") == []

    # test split without authorization MUST raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        runner.load_split("test", frozen_decisions=False)
    assert "locked test split is forbidden" in str(exc_info.value)

    # test split WITH explicit authorization succeeds
    assert runner.load_split("test", frozen_decisions=True) == []


def test_runner_evaluates_5_baselines():
    """Verify RealBenchRunner evaluates all 5 baselines on real cases and produces 95% CIs."""
    runner = RealBenchRunner()
    cases = runner.load_split("val")

    assert len(cases) == 100, f"Expected 100 val cases, got {len(cases)}"

    report = runner.run_benchmark(cases, split_name="val")

    assert report["total_cases"] == 100
    assert len(report["baselines"]) == 5

    expected_baselines = [
        "Untrained Base Model",
        "Plain-Prompt Hosted Model",
        "Linters Alone (Ruff/Bandit/AST)",
        "Current Aion Pipeline",
        "Aion with Trained Model",
    ]
    for b in expected_baselines:
        assert b in report["baselines"], f"Missing baseline: {b}"
        m = report["baselines"][b]
        assert "ci_lower" in m["precision"]
        assert "ci_upper" in m["precision"]
        assert m["precision"]["ci_lower"] <= m["precision"]["mean"] <= m["precision"]["ci_upper"]
        assert m["clean_diff_fpr"]["mean"] >= 0.0

    # Format table should contain all baselines and headers
    table = runner.format_markdown_table(report)
    assert "| Model / Baseline |" in table
    for b in expected_baselines:
        assert b in table


def test_verifier_calibration_on_real_validation_cases():
    """Verify verifier re-calibration computes valid ECE <= 0.10 and reliability bins."""
    runner = RealBenchRunner()
    cases = runner.load_split("val")

    calibrator = RealDataVerifierCalibrator(n_bins=10)
    res = calibrator.calibrate_and_evaluate(cases)

    assert "temperature" in res
    assert res["temperature"] > 0
    assert "expected_calibration_error" in res
    assert res["expected_calibration_error"] <= 0.10
    assert res["calibrated"] is True
    assert len(res["reliability_diagram_bins"]) == 10

    # Test decision rule evaluation
    bench_results = runner.run_benchmark(cases, split_name="val")
    decision = calibrator.evaluate_decision_rule(bench_results)

    assert decision["verdict"] in ("PROCEED_TO_PILOT", "REPOSITION_AS_FILTER_PLUS_LINTERS", "DO_NOT_LAUNCH")
    assert "rationale" in decision
    assert len(decision["aion_precision_ci"]) == 3
