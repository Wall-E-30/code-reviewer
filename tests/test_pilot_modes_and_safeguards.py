"""
tests/test_pilot_modes_and_safeguards.py

Test suite for Pilot Modes (Shadow vs Visible) and Safeguards (PILOT-01, PILOT-02, PILOT-03).
Covers:
- Shadow mode execution in GitHub Action and GitHub App
- Visible mode comment capping (<= 5) and feedback footers
- Repo-level mute / unmute via @aion mute / @aion unmute commands
- Global emergency kill switch (AION_KILL_SWITCH)
- Workflow generator installer script
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from action.formatter import (
    DEFAULT_FEEDBACK_FOOTER,
    format_inline_comment,
    format_review_summary,
)
from action.main import run_action
from action.providers import CandidateComment
from rl.memory import RepoConventionMemory
from scripts.install_pilot import generate_workflow_yaml, install_pilot_workflow
from server.github_app import AionGitHubAppHandler


# ---------------------------------------------------------------------------
# Test 1: Formatter Feedback Footers and Dismiss Reasons (PILOT-03)
# ---------------------------------------------------------------------------
def test_formatter_feedback_footer_contains_all_reasons():
    for reason in ["wrong", "nitpick", "already_known", "out_of_scope"]:
        assert reason in DEFAULT_FEEDBACK_FOOTER

    assert "@aion mute" in DEFAULT_FEEDBACK_FOOTER

    candidate = CandidateComment(
        file_path="src/main.py",
        line_number=10,
        comment="Potential race condition here.",
        category="bug",
        confidence=0.92,
        severity="high",
        suggestion="lock.acquire()",
    )
    formatted = format_inline_comment(candidate)
    for reason in ["wrong", "nitpick", "already_known", "out_of_scope"]:
        assert reason in formatted
    assert "@aion mute" in formatted
    assert "```suggestion" in formatted

    summary = format_review_summary(
        results=[candidate],
        files_analyzed=1,
        linter_count=3,
        duration_sec=0.45,
    )
    assert "@aion mute" in summary
    assert "wrong" in summary


# ---------------------------------------------------------------------------
# Test 2: Repo Convention Memory Muting (PILOT-03)
# ---------------------------------------------------------------------------
def test_repo_convention_memory_mute_lifecycle(tmp_path):
    storage_path = tmp_path / "conventions.json"
    memory = RepoConventionMemory(repo_id="test-org/test-repo", storage_path=storage_path)

    assert not memory.is_muted()

    memory.mute(reason="Muted by maintainer Alice")
    assert memory.is_muted()
    assert memory.state.muted is True
    assert memory.state.muted_reason == "Muted by maintainer Alice"

    # Verify persistence
    loaded_memory = RepoConventionMemory(repo_id="test-org/test-repo", storage_path=storage_path)
    assert loaded_memory.is_muted()
    assert loaded_memory.state.muted_reason == "Muted by maintainer Alice"

    # Unmute
    loaded_memory.unmute()
    assert not loaded_memory.is_muted()
    assert loaded_memory.state.muted is False


# ---------------------------------------------------------------------------
# Test 3: Action Execution in Shadow Mode vs Visible Mode (PILOT-01, PILOT-03)
# ---------------------------------------------------------------------------
def test_action_shadow_mode_logs_without_posting(tmp_path):
    diff_content = """diff --git a/app.py b/app.py
index 0000000..1111111 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
+import os
+eval(input())
"""
    mock_client = MagicMock()
    mock_client.get_existing_review_comments.return_value = []
    aion_dir = tmp_path / ".aion"

    config = {
        "token": "fake-token",
        "repo": "test/repo",
        "pr_number": 42,
        "mode": "shadow",
        "provider": "mock",
        "aion_state_dir": str(aion_dir),
        "enable_telemetry": False,
    }

    with patch.dict(os.environ, {"AION_KILL_SWITCH": "false"}):
        exit_code = run_action(
            config=config,
            client=mock_client,
            custom_diff=diff_content,
        )

        assert exit_code == 0
        # Under shadow mode, post_review MUST NOT be called!
        mock_client.post_review.assert_not_called()

        # Shadow reviews log file must be written
        shadow_log = aion_dir / "shadow_reviews.jsonl"
        assert shadow_log.exists()
        log_lines = shadow_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(log_lines) >= 1
        data = json.loads(log_lines[0])
        assert data["repo"] == "test/repo"
        assert data["pr_number"] == 42


def test_action_kill_switch_aborts(tmp_path):
    mock_client = MagicMock()
    config = {
        "token": "fake-token",
        "repo": "test/repo",
        "pr_number": 42,
        "mode": "visible",
        "provider": "mock",
        "aion_state_dir": str(tmp_path / ".aion"),
        "kill_switch": True,
    }

    exit_code = run_action(
        config=config,
        client=mock_client,
        custom_diff="diff --git a/a.py b/a.py\n+x = 1\n",
    )

    assert exit_code == 0
    mock_client.post_review.assert_not_called()


def test_action_muted_repo_aborts(tmp_path):
    storage_path = tmp_path / ".aion" / "conventions.json"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    memory = RepoConventionMemory(repo_id="test/repo", storage_path=str(storage_path))
    memory.mute(reason="Testing mute abort")

    mock_client = MagicMock()
    config = {
        "token": "fake-token",
        "repo": "test/repo",
        "pr_number": 42,
        "mode": "visible",
        "provider": "mock",
        "aion_state_dir": str(tmp_path / ".aion"),
    }

    exit_code = run_action(
        config=config,
        client=mock_client,
        memory=memory,
        custom_diff="diff --git a/a.py b/a.py\n+x = 1\n",
    )

    assert exit_code == 0
    mock_client.post_review.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: GitHub App Handler Modes and Webhooks (PILOT-01, PILOT-03)
# ---------------------------------------------------------------------------
def test_github_app_shadow_mode(tmp_path):
    memory = RepoConventionMemory(repo_id="test/repo", storage_path=tmp_path / "conv.json")
    app = AionGitHubAppHandler(convention_memory=memory)

    diff_text = """diff --git a/vuln.py b/vuln.py
index 0000000..1111111 100644
--- a/vuln.py
+++ b/vuln.py
@@ -1,2 +1,3 @@
+import os
+os.system("echo hello")
"""
    payload = {
        "action": "opened",
        "repository": {"full_name": "org/repo"},
        "pull_request": {"number": 101, "head": {"sha": "abcdef1"}},
        "diff": diff_text,
        "files": {"vuln.py": 'import os\nos.system("echo hello")\n'},
        "mode": "shadow",
    }

    result = app.handle_pull_request_event(payload)
    assert result["status"] == "shadow_logged"
    assert result["pr_number"] == 101
    assert "candidate_comments" in result or "comments_logged" in result


def test_github_app_kill_switch():
    app = AionGitHubAppHandler()
    payload = {
        "action": "opened",
        "repository": {"full_name": "org/repo"},
        "pull_request": {"number": 102},
        "kill_switch": True,
    }
    result = app.handle_pull_request_event(payload)
    assert result["status"] == "killed"


def test_github_app_muted_repo(tmp_path):
    memory = RepoConventionMemory(repo_id="org/repo", storage_path=tmp_path / "conv.json")
    memory.mute(reason="Testing mute status")
    app = AionGitHubAppHandler(convention_memory=memory)

    payload = {
        "action": "opened",
        "repository": {"full_name": "org/repo"},
        "pull_request": {"number": 103},
    }
    result = app.handle_pull_request_event(payload)
    assert result["status"] == "muted"


def test_github_app_issue_comment_mute_and_unmute(tmp_path):
    memory = RepoConventionMemory(repo_id="org/repo", storage_path=tmp_path / "conv.json")
    app = AionGitHubAppHandler(convention_memory=memory)

    assert not memory.is_muted()

    # Post @aion mute
    payload_mute = {
        "action": "created",
        "comment": {"body": "Hey team, @aion mute for this repo please"},
        "sender": {"login": "octocat"},
        "repository": {"full_name": "org/repo"},
    }
    res_mute = app.dispatch_event("issue_comment", payload_mute)
    assert res_mute["status"] == "muted"
    assert memory.is_muted()

    # Post @aion unmute
    payload_unmute = {
        "action": "created",
        "comment": {"body": "@aion unmute ready for reviews again"},
        "sender": {"login": "octocat"},
        "repository": {"full_name": "org/repo"},
    }
    res_unmute = app.dispatch_event("issue_comment", payload_unmute)
    assert res_unmute["status"] == "unmuted"
    assert not memory.is_muted()


def test_github_app_feedback_dismiss_tags(tmp_path):
    memory = RepoConventionMemory(repo_id="org/repo", storage_path=tmp_path / "conv.json")
    app = AionGitHubAppHandler(convention_memory=memory)

    payload = {
        "action": "created",
        "comment": {"body": "@aion nitpick this is intentional variable naming"},
        "sender": {"login": "maintainer1"},
        "repository": {"full_name": "org/repo"},
    }
    res = app.dispatch_event("issue_comment", payload)
    assert res["status"] == "feedback_recorded"
    assert res["reason"] == "nitpick"


def test_github_app_strict_comment_cap(tmp_path):
    app = AionGitHubAppHandler()
    # Mock verifier to return 10 comments
    fake_comments = [
        CandidateComment(
            file_path="test.py",
            line_number=i + 1,
            comment=f"Issue {i + 1}",
            category="bug",
            confidence=0.9,
            severity="medium",
        )
        for i in range(10)
    ]
    app.verifier.filter_candidates = MagicMock(return_value=fake_comments)

    payload = {
        "action": "opened",
        "repository": {"full_name": "org/repo"},
        "pull_request": {"number": 105, "head": {"sha": "sha123"}},
        "diff": "diff --git a/test.py b/test.py\n--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n+x = 1\n",
        "files": {"test.py": "x = 1\n"},
        "mode": "visible",
    }
    result = app.handle_pull_request_event(payload)
    assert result["status"] == "reviewed"
    assert result["comments_posted"] <= 5
    assert len(result["comments"]) <= 5


# ---------------------------------------------------------------------------
# Test 5: Pilot Install Script (PILOT-02)
# ---------------------------------------------------------------------------
def test_install_pilot_workflow(tmp_path):
    wf_yaml = generate_workflow_yaml(mode="shadow", provider="groq", max_comments=5)
    assert "mode: shadow" in wf_yaml
    assert "provider: groq" in wf_yaml
    assert "max_comments: 5" in wf_yaml
    assert "GROQ_API_KEY" in wf_yaml

    target_file = install_pilot_workflow(
        target_dir=tmp_path,
        mode="visible",
        provider="openrouter",
        max_comments=4,
    )
    assert target_file.exists()
    content = target_file.read_text(encoding="utf-8")
    assert "mode: visible" in content
    assert "provider: openrouter" in content
    assert "max_comments: 4" in content
    assert "OPENROUTER_API_KEY" in content
