"""
tests/test_leaderboard.py

Unit test suite for public Aion-Bench Leaderboard (GROWTH-02).
Validates schema integrity, ranking algorithms, filtering, and API endpoints.
"""

import json
import os
import tempfile
import pytest
from pydantic import ValidationError

from bench.leaderboard import LeaderboardEntry, LeaderboardManager, DEFAULT_BASELINES
from server.app import get_leaderboard_endpoint, submit_leaderboard_endpoint, leaderboard_manager


def test_leaderboard_seed_data_integrity():
    """Verify default seed baselines are present and adhere to schema constraints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "leaderboard.json")
        mgr = LeaderboardManager(storage_path=storage_path)

        assert os.path.exists(storage_path)
        assert len(mgr.entries) >= 6

        # Check key baselines exist
        model_ids = [e.model_id for e in mgr.entries]
        assert "aion-qwen2.5-coder-7b-grpo" in model_ids
        assert "gpt-4o" in model_ids
        assert "claude-3-5-sonnet" in model_ids
        assert "ruff-bandit-static" in model_ids

        # Ensure all metrics in valid [0, 1] bounds
        for e in mgr.entries:
            assert 0.0 <= e.precision <= 1.0
            assert 0.0 <= e.recall <= 1.0
            assert 0.0 <= e.false_positive_rate <= 1.0
            assert 0.0 <= e.nitpick_rate <= 1.0
            assert e.avg_latency_ms >= 0.0


def test_ranking_algorithm():
    """Verify models are ranked strictly by precision descending, then clean FPR ascending."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "leaderboard.json")
        mgr = LeaderboardManager(storage_path=storage_path)
        ranked = mgr.get_ranked_entries()

        # Check precision is monotonically non-increasing
        for i in range(len(ranked) - 1):
            assert ranked[i].precision >= ranked[i + 1].precision or (
                ranked[i].precision == ranked[i + 1].precision
                and ranked[i].false_positive_rate <= ranked[i + 1].false_positive_rate
            )

        # Static tool (Ruff+Bandit) has 91.2% precision, followed by Aion at 78.4%
        assert ranked[0].model_id == "ruff-bandit-static"
        assert ranked[1].model_id == "aion-qwen2.5-coder-7b-grpo"


def test_community_submission_validation():
    """Verify invalid metrics or types raise ValidationError."""
    # Invalid precision > 1.0
    with pytest.raises(ValidationError):
        LeaderboardEntry(
            model_id="test-model",
            display_name="Test Model",
            organization="Test Org",
            license="MIT",
            model_type="open-weights",
            precision=1.25,  # Invalid
            recall=0.70,
            false_positive_rate=0.05,
            nitpick_rate=0.02,
            avg_latency_ms=100.0,
        )

    # Invalid model_type
    with pytest.raises(ValidationError):
        LeaderboardEntry(
            model_id="test-model",
            display_name="Test Model",
            organization="Test Org",
            license="MIT",
            model_type="unknown-type",  # Invalid
            precision=0.75,
            recall=0.70,
            false_positive_rate=0.05,
            nitpick_rate=0.02,
            avg_latency_ms=100.0,
        )


def test_filtering_by_model_type():
    """Verify get_ranked_entries filters correctly by model_type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "leaderboard.json")
        mgr = LeaderboardManager(storage_path=storage_path)

        open_weights = mgr.get_ranked_entries(model_type="open-weights")
        assert len(open_weights) >= 3
        assert all(e.model_type == "open-weights" for e in open_weights)
        # Top open-weight model should be Aion Qwen2.5-Coder GRPO
        assert open_weights[0].model_id == "aion-qwen2.5-coder-7b-grpo"

        commercial = mgr.get_ranked_entries(model_type="commercial-api")
        assert len(commercial) >= 2
        assert all(e.model_type == "commercial-api" for e in commercial)


def test_api_endpoints_direct():
    """Verify get_leaderboard_endpoint and submit_leaderboard_endpoint in server/app.py."""
    # 1. Test GET /api/leaderboard
    res = get_leaderboard_endpoint()
    assert "summary" in res
    assert "entries" in res
    assert res["summary"]["total_models"] >= 6
    assert len(res["entries"]) >= 6

    # 2. Test POST /api/leaderboard/submit
    new_model = LeaderboardEntry(
        model_id="deepseek-v3-coder",
        display_name="DeepSeek V3 Coder (Fine-Tuned)",
        organization="DeepSeek Community",
        license="MIT",
        model_type="open-weights",
        precision=0.795,
        recall=0.740,
        false_positive_rate=0.058,
        nitpick_rate=0.035,
        avg_latency_ms=390.0,
        submission_date="2026-11-07",
        verified=False,
    )

    submit_res = submit_leaderboard_endpoint(new_model)
    assert submit_res["status"] == "accepted"
    assert submit_res["model_id"] == "deepseek-v3-coder"
    assert submit_res["precision"] == 0.795
    assert submit_res["rank"] >= 1

