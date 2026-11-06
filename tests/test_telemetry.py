"""
tests/test_telemetry.py

Unit test suite for Phase 3 Plan 03:
- Cryptographic anonymization hashing (hash_identifier)
- Telemetry event model and serialization
- TelemetryLogger with complete opt-out enforcement
- GITHUB_STEP_SUMMARY markdown generation
- Subsequent-run reaction polling and resolution state tracking
"""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from action.github_client import GitHubClient
from action.main import run_action
from action.reactions import (
    ReactionSummary,
    is_aion_comment,
    poll_previous_reactions,
)
from action.telemetry import (
    TelemetryEvent,
    TelemetryLogger,
    hash_identifier,
)


# ============================================================================
# 1. Anonymization & Hashing Tests
# ============================================================================


def test_hash_identifier_sha256() -> None:
    raw_repo = "facebook/react"
    hashed = hash_identifier(raw_repo)
    assert len(hashed) == 64  # SHA-256 produces 64 hex characters
    assert raw_repo not in hashed
    assert "react" not in hashed

    # Same input and salt produce deterministic hash
    assert hash_identifier(raw_repo) == hashed

    # Different salt produces different hash
    assert hash_identifier(raw_repo, salt="custom-salt") != hashed

    # Empty string returns empty
    assert hash_identifier("") == ""


# ============================================================================
# 2. Telemetry Event & Logger Tests
# ============================================================================


def test_telemetry_event_serialization() -> None:
    event = TelemetryEvent(
        repo_hash="hash123",
        pr_hash="pr456",
        provider="groq",
        model="qwen-2.5-coder-32b",
        candidates_generated=4,
        comments_posted=2,
        comments_suppressed=2,
        finding_categories=["security", "bug"],
        confidences=[0.95, 0.88],
    )
    json_str = event.to_json()
    assert "hash123" in json_str
    assert "groq" in json_str

    loaded = TelemetryEvent.model_validate_json(json_str)
    assert loaded.repo_hash == "hash123"
    assert loaded.candidates_generated == 4
    assert loaded.confidences == [0.95, 0.88]


def test_telemetry_logger_records_event(tmp_path: Path) -> None:
    log_file = tmp_path / "telemetry.jsonl"
    logger = TelemetryLogger(enabled=True, output_path=str(log_file))

    event = TelemetryEvent(
        repo_hash="r1",
        pr_hash="p1",
        provider="mock",
        model="test-model",
        candidates_generated=2,
        comments_posted=1,
        comments_suppressed=1,
        finding_categories=["bug"],
        confidences=[0.90],
    )

    logged = logger.log_event(event)
    assert logged is True
    assert log_file.exists()

    events = logger.load_events()
    assert len(events) == 1
    assert events[0].repo_hash == "r1"
    assert events[0].comments_posted == 1


def test_telemetry_logger_opt_out(tmp_path: Path) -> None:
    log_file = tmp_path / "telemetry.jsonl"
    logger = TelemetryLogger(enabled=False, output_path=str(log_file))

    event = TelemetryEvent(
        repo_hash="r1",
        pr_hash="p1",
        provider="mock",
        model="test-model",
        candidates_generated=2,
        comments_posted=1,
        comments_suppressed=1,
    )

    logged = logger.log_event(event)
    assert logged is False
    assert not log_file.exists()
    assert logger.load_events() == []


def test_telemetry_step_summary_writing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_file = tmp_path / "telemetry.jsonl"
    step_summary_file = tmp_path / "step_summary.md"
    step_summary_file.write_text("", encoding="utf-8")

    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(step_summary_file))

    logger = TelemetryLogger(enabled=True, output_path=str(log_file))
    event = TelemetryEvent(
        repo_hash="r1",
        pr_hash="p1",
        provider="groq",
        model="llama-3.3-70b-versatile",
        candidates_generated=5,
        comments_posted=2,
        comments_suppressed=3,
        finding_categories=["security", "bug"],
        confidences=[0.99, 0.85],
    )
    logger.log_event(event)

    summary_text = step_summary_file.read_text(encoding="utf-8")
    assert "Aion Operational Telemetry" in summary_text
    assert "groq" in summary_text
    assert "llama-3.3-70b-versatile" in summary_text
    assert "`security`, `bug`" in summary_text


# ============================================================================
# 3. Reaction Polling Tests
# ============================================================================


def test_is_aion_comment() -> None:
    assert is_aion_comment("### 🛡️ Aion Finding: Security Issue") is True
    assert is_aion_comment("Reported by [Aion Code Reviewer](...)") is True
    assert is_aion_comment("Regular human code review comment.") is False
    assert is_aion_comment("") is False


def test_poll_previous_reactions_counts() -> None:
    mock_gh = MagicMock(spec=GitHubClient)
    # Simulate comments from previous run:
    # 1 Aion comment with +1 and rocket
    # 1 Aion comment with -1
    # 1 Human comment
    mock_gh.get_existing_review_comments.return_value = [
        {
            "id": 101,
            "path": "auth.py",
            "line": 42,
            "body": "### 🛡️ Aion Finding: Security Vulnerability\n```suggestion\nsafe()\n```",
            "reactions": {"+1": 2, "rocket": 1, "-1": 0},
        },
        {
            "id": 102,
            "path": "calc.py",
            "line": 10,
            "body": "### 🐛 Aion Finding: Logic Bug\nOff by one",
            "reactions": {"-1": 1, "confused": 1},
        },
        {
            "id": 103,
            "path": "calc.py",
            "line": 10,
            "body": "Human comment: looks fine to me",
            "reactions": {},
        },
        # Reply to 101: "done, fixed!"
        {
            "id": 104,
            "in_reply_to_id": 101,
            "body": "Fixed in latest commit, thanks!",
        },
    ]

    summary: ReactionSummary = poll_previous_reactions(
        github_client=mock_gh,
        repo="owner/repo",
        pr_number=5,
    )

    assert summary.total_tracked == 2  # 2 Aion comments
    assert summary.positive_reactions == 3  # 2 (+1) + 1 (rocket)
    assert summary.negative_reactions == 2  # 1 (-1) + 1 (confused)
    assert summary.resolved_count == 1  # 101 had a "fixed" reply


def test_poll_previous_reactions_code_amendment() -> None:
    mock_gh = MagicMock(spec=GitHubClient)
    mock_gh.get_existing_review_comments.return_value = [
        {
            "id": 201,
            "path": "service.py",
            "line": 15,
            "body": "### 🐛 Aion Finding: Potential Bug\nInvalid return type",
            "reactions": {},
        }
    ]

    # Current diff touches service.py:15
    modified_map = {"service.py": {14, 15, 16}}

    summary = poll_previous_reactions(
        github_client=mock_gh,
        repo="owner/repo",
        pr_number=9,
        modified_lines_map=modified_map,
    )

    assert summary.total_tracked == 1
    assert summary.resolved_count == 1


# ============================================================================
# 4. Pipeline Execution with Telemetry Logging
# ============================================================================


def test_run_action_records_telemetry_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    telemetry_file = tmp_path / "pipeline_telemetry.jsonl"
    monkeypatch.setattr("action.main.TelemetryLogger", lambda enabled: TelemetryLogger(enabled=enabled, output_path=str(telemetry_file)))

    fake_diff = """--- a/mod.py
+++ b/mod.py
@@ -1,2 +1,2 @@
 def foo():
-    eval("bad")
+    x = 1
"""
    mock_client = MagicMock(spec=GitHubClient)
    mock_client.get_pull_request_diff.return_value = fake_diff
    mock_client.get_existing_review_comments.return_value = []
    mock_client.post_review.return_value = {"id": 1, "state": "COMMENTED"}

    config = {
        "repo": "acme/corp",
        "pr_number": 99,
        "commit_sha": "abc12345",
        "token": "fake_token",
        "provider": "mock",
        "enable_telemetry": True,
    }

    exit_code = run_action(config=config, client=mock_client, custom_diff=fake_diff)
    assert exit_code == 0
    assert telemetry_file.exists()

    events = TelemetryLogger(output_path=str(telemetry_file)).load_events()
    assert len(events) == 1
    assert events[0].provider == "mock"
    assert events[0].comments_posted >= 1
    assert "acme/corp" not in events[0].repo_hash

