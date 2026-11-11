"""
tests/test_pilot_audit_workflow.py

Test suite for Pilot Comment Audit Workflow and Telemetry Precision Gate (PILOT-04).
Covers:
- Weekly comment extraction and stratified sampling
- CSV / JSON export with auditor columns
- Audited live precision computation with 95% bootstrap confidence intervals
- Acceptance rate, applied suggestion rate, mute rate, and cost estimation
- Precision gate hardening: strict refusal to report passed on simulated data
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import pytest

from scripts.pilot_audit_report import (
    compute_audit_metrics,
    compute_bootstrap_precision_ci,
    generate_audit_markdown,
    run_pilot_audit,
)
from scripts.sample_pilot_comments import (
    export_sample_csv,
    export_sample_json,
    sample_pilot_comments,
    stratified_sample,
)
from server.precision_gate import MultiRepoTelemetryAggregator, RepoReviewRecord


# ---------------------------------------------------------------------------
# Test 1: Stratified Comment Sampling (PILOT-04)
# ---------------------------------------------------------------------------
def test_stratified_comment_sampling():
    categories = ["bug", "security", "performance", "style"]
    mock_comments = []
    for idx in range(100):
        cat = categories[idx % len(categories)]
        mock_comments.append({
            "repo": f"org/repo-{idx % 5}",
            "pr_number": 10 + (idx % 3),
            "category": cat,
            "severity": "high",
            "file_path": f"src/{cat}_{idx}.py",
            "line_number": idx + 1,
            "comment": f"Sample comment for {cat} defect {idx}",
            "suggestion": f"fix_{cat}()",
            "confidence": 0.85,
        })

    sampled = stratified_sample(mock_comments, sample_size=40, seed=42)
    assert len(sampled) == 40

    # Ensure all 4 categories are represented in stratified sample
    sampled_cats = {s["category"] for s in sampled}
    assert sampled_cats == set(categories)

    # Check sample IDs and human auditor fields
    for s in sampled:
        assert "sample_id" in s
        assert "audit_label" in s
        assert "applied" in s
        assert "auditor_notes" in s


def test_sampling_export_lifecycle(tmp_path):
    shadow_log = tmp_path / "shadow_reviews.jsonl"
    with open(shadow_log, "w", encoding="utf-8") as f:
        for i in range(20):
            f.write(
                json.dumps({
                    "repository": "pilot/repo-a",
                    "pr_number": 100 + i,
                    "candidate_comments": [
                        {
                            "category": "security" if i % 2 == 0 else "bug",
                            "severity": "high",
                            "file_path": f"file_{i}.py",
                            "line_number": 10,
                            "comment": f"Finding {i}",
                            "suggestion": "fix()",
                            "confidence": 0.90,
                        }
                    ],
                })
                + "\n"
            )

    out_dir = tmp_path / "audit_samples"
    samples, json_path, csv_path = sample_pilot_comments(
        input_path=shadow_log,
        output_dir=out_dir,
        sample_size=10,
        seed=42,
    )

    assert len(samples) == 10
    assert json_path.exists()
    assert csv_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        loaded_json = json.load(f)
        assert len(loaded_json) == 10

    csv_text = csv_path.read_text(encoding="utf-8")
    assert "sample_id,repo,pr_number,category" in csv_text
    assert "pilot/repo-a" in csv_text


# ---------------------------------------------------------------------------
# Test 2: Bootstrap Confidence Intervals & Audit Metrics (PILOT-04)
# ---------------------------------------------------------------------------
def test_bootstrap_precision_ci_properties():
    # 90 accurate, 10 false_positive => precision = 0.90
    labels = ["accurate"] * 90 + ["false_positive"] * 10
    pe, low, high = compute_bootstrap_precision_ci(labels, num_resamples=500, seed=42)

    assert pe == 0.90
    assert 0.80 <= low <= pe
    assert pe <= high <= 0.98

    # Edge cases
    assert compute_bootstrap_precision_ci([]) == (0.0, 0.0, 0.0)
    assert compute_bootstrap_precision_ci(["accurate"] * 10) == (1.0, 1.0, 1.0)


def test_audit_report_generation(tmp_path):
    audited_data = [
        {
            "sample_id": f"AUDIT-{i:03d}",
            "repo": "pilot/repo-1",
            "category": "bug" if i < 15 else "security",
            "audit_label": "accurate" if i < 18 else "false_positive",
            "applied": "yes" if i < 12 else "no",
            "suggestion": "fix()",
        }
        for i in range(20)
    ]
    # 18 accurate out of 20 => precision = 0.90
    # 12 applied out of 20 => applied_rate = 0.60

    json_input = tmp_path / "audited_sample.json"
    with open(json_input, "w", encoding="utf-8") as f:
        json.dump(audited_data, f)

    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    metrics = run_pilot_audit(
        input_path=json_input,
        output_md=out_md,
        output_json=out_json,
        total_enrolled_repos=10,
        muted_repo_count=1,
    )

    assert metrics["audited_live_precision"] == 0.90
    assert metrics["applied_suggestion_rate"] == 0.60
    assert metrics["repo_mute_rate"] == 0.10
    assert metrics["provenance"] == "audited_pilot"
    assert out_md.exists()
    assert out_json.exists()

    md_text = out_md.read_text(encoding="utf-8")
    assert "90.0%" in md_text
    assert "audited_pilot" in md_text
    assert "Estimated Inference Cost/PR" in md_text


# ---------------------------------------------------------------------------
# Test 3: Precision Gate Hardening Against Simulated Data (PILOT-04)
# ---------------------------------------------------------------------------
def test_precision_gate_rejects_simulated_telemetry():
    agg = MultiRepoTelemetryAggregator()
    now = datetime.now(timezone.utc)

    # 105 repos with simulated provenance
    for i in range(105):
        agg.record_event(
            RepoReviewRecord(
                repo_id=f"sim/repo-{i}",
                timestamp=now - timedelta(days=2),
                comments_posted=5,
                comments_accepted=4,
                comments_rejected=1,
                is_real=False,
                provenance="simulated",
            )
        )

    # Rolling precision reports PENDING_PILOT_DATA
    metrics = agg.compute_rolling_precision(window_days=30, reference_time=now)
    assert metrics["status"] == "PENDING_PILOT_DATA"
    assert metrics["has_simulated_telemetry"] is True
    assert metrics["simulated_records_count"] == 105

    # assert_precision_gate strictly raises ValueError refusing to pass on simulated data
    with pytest.raises(ValueError, match="strictly refuses to report 'passed' on simulated data"):
        agg.assert_precision_gate(window_days=30, reference_time=now)


def test_precision_gate_passes_on_live_telemetry():
    agg = MultiRepoTelemetryAggregator()
    now = datetime.now(timezone.utc)

    # 105 repos with verified real/live data
    for i in range(105):
        agg.record_event(
            RepoReviewRecord(
                repo_id=f"real/repo-{i}",
                timestamp=now - timedelta(days=2),
                comments_posted=5,
                comments_accepted=4,
                comments_rejected=1,
                is_real=True,
                provenance="live",
            )
        )

    metrics = agg.compute_rolling_precision(window_days=30, reference_time=now)
    assert metrics["status"] == "PASS"
    assert metrics["has_simulated_telemetry"] is False
    assert metrics["simulated_records_count"] == 0

    assert agg.assert_precision_gate(window_days=30, reference_time=now) is True
