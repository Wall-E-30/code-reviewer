"""
tests/test_precision_gate.py

Unit and integration tests for Multi-Repo Telemetry Aggregator & 30-Day Precision Gate (APP-02):
- Telemetry record serialization and ingestion
- Rolling 30-day window metrics calculation
- Weekly progression tracking showing adaptive precision improvements
- Gate enforcement: >= 70% live precision over 30 days across >= 100 repos
- Detailed Markdown report generation
"""

from datetime import datetime, timedelta, timezone
import json
import os
import tempfile
import pytest

from server.precision_gate import MultiRepoTelemetryAggregator, RepoReviewRecord


def test_record_ingestion_and_active_repo_count():
    """Verify records are ingested and unique active repos are counted accurately."""
    agg = MultiRepoTelemetryAggregator()
    now = datetime.now(timezone.utc)

    # 3 records for repo A, 2 for repo B, 1 for repo C (outside 30-day window)
    agg.record_event(RepoReviewRecord("repo-A", now - timedelta(days=2), 2, 2, 0, "bug"))
    agg.record_event(RepoReviewRecord("repo-A", now - timedelta(days=5), 1, 1, 0, "security"))
    agg.record_event(RepoReviewRecord("repo-B", now - timedelta(days=10), 3, 2, 1, "performance"))
    agg.record_event(RepoReviewRecord("repo-C", now - timedelta(days=45), 2, 1, 1, "style"))  # Out of window

    assert agg.get_active_repo_count(window_days=30, reference_time=now) == 2
    assert agg.get_active_repo_count(window_days=60, reference_time=now) == 3


def test_rolling_precision_calculation():
    """Verify live precision calculation across categories."""
    agg = MultiRepoTelemetryAggregator()
    now = datetime.now(timezone.utc)

    # 8 accepted, 2 rejected => 80% precision
    agg.record_event(RepoReviewRecord("repo-1", now - timedelta(days=1), 5, 4, 1, "security"))
    agg.record_event(RepoReviewRecord("repo-2", now - timedelta(days=2), 5, 4, 1, "bug"))

    metrics = agg.compute_rolling_precision(window_days=30, reference_time=now)
    assert metrics["active_repos"] == 2
    assert metrics["total_accepted"] == 8
    assert metrics["total_rejected"] == 2
    assert metrics["live_precision"] == 0.80
    assert metrics["category_precisions"]["security"] == 0.80
    assert metrics["category_precisions"]["bug"] == 0.80


def test_weekly_progression_trend():
    """Verify 4-week progression demonstrates improving precision as bandits adapt."""
    agg = MultiRepoTelemetryAggregator()
    now = datetime.now(timezone.utc)

    # Week 1 (earliest, 21-28 days ago): lower precision ~60%
    for i in range(10):
        agg.record_event(
            RepoReviewRecord(f"r-{i}", now - timedelta(days=25), 5, 3, 2, "bug")
        )

    # Week 4 (most recent, 0-7 days ago): higher precision ~80%
    for i in range(10):
        agg.record_event(
            RepoReviewRecord(f"r-{i}", now - timedelta(days=3), 5, 4, 1, "bug")
        )

    weekly = agg.compute_weekly_progression(num_weeks=4, reference_time=now)
    assert len(weekly) == 4
    # Week 1 should be around 0.60
    assert abs(weekly[0]["precision"] - 0.60) < 0.05
    # Week 4 should be around 0.80
    assert abs(weekly[3]["precision"] - 0.80) < 0.05
    assert weekly[3]["precision"] > weekly[0]["precision"]


def test_precision_gate_passing_100_repos():
    """Verify precision gate passes with 105 active repos and 75% precision."""
    agg = MultiRepoTelemetryAggregator()
    now = datetime.now(timezone.utc)

    # Populate 105 distinct repositories within 30 days
    for i in range(105):
        # 3 accepted, 1 rejected per repo => 75% precision
        agg.record_event(
            RepoReviewRecord(
                repo_id=f"org/repo-{i}",
                timestamp=now - timedelta(days=(i % 28) + 1),
                comments_posted=4,
                comments_accepted=3,
                comments_rejected=1,
                category="bug" if i % 2 == 0 else "security",
            )
        )

    assert agg.assert_precision_gate(
        window_days=30,
        min_repos=100,
        min_precision=0.70,
        reference_time=now,
    ) is True


def test_precision_gate_failing_insufficient_repos():
    """Verify precision gate raises AssertionError when active repos < 100."""
    agg = MultiRepoTelemetryAggregator()
    now = datetime.now(timezone.utc)

    # Only 50 repos
    for i in range(50):
        agg.record_event(
            RepoReviewRecord(
                repo_id=f"org/repo-{i}",
                timestamp=now - timedelta(days=5),
                comments_posted=4,
                comments_accepted=4,
                comments_rejected=0,
            )
        )

    with pytest.raises(AssertionError) as exc_info:
        agg.assert_precision_gate(window_days=30, min_repos=100, min_precision=0.70, reference_time=now)

    assert "observed 50 active repos" in str(exc_info.value)
    assert "required >= 100" in str(exc_info.value)


def test_precision_gate_failing_low_precision():
    """Verify precision gate raises AssertionError when precision < 70%."""
    agg = MultiRepoTelemetryAggregator()
    now = datetime.now(timezone.utc)

    # 105 repos, but only 50% accepted
    for i in range(105):
        agg.record_event(
            RepoReviewRecord(
                repo_id=f"org/repo-{i}",
                timestamp=now - timedelta(days=10),
                comments_posted=4,
                comments_accepted=2,
                comments_rejected=2,  # 50%
            )
        )

    with pytest.raises(AssertionError) as exc_info:
        agg.assert_precision_gate(window_days=30, min_repos=100, min_precision=0.70, reference_time=now)

    assert "observed 50.0%" in str(exc_info.value)
    assert "required >= 70.0%" in str(exc_info.value)


def test_markdown_report_generation():
    """Verify markdown report generation produces properly formatted tables and metrics."""
    agg = MultiRepoTelemetryAggregator()
    now = datetime.now(timezone.utc)

    for i in range(105):
        agg.record_event(
            RepoReviewRecord(
                repo_id=f"repo-{i}",
                timestamp=now - timedelta(days=5),
                comments_posted=4,
                comments_accepted=3,
                comments_rejected=1,
                category="bug",
            )
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "report.md")
        content = agg.generate_precision_report(output_markdown_path=out_file, reference_time=now)

        assert os.path.exists(out_file)
        assert "# Aion Multi-Repository 30-Day Precision Report (APP-02)" in content
        assert "Active Repositories (30-day):** 105" in content
        assert "PASS ✅" in content
