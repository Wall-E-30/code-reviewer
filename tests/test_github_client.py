"""
tests/test_github_client.py

Unit tests for Phase 3 Plan 02:
- GitHub REST API Client (urllib request mocking, diff retrieval, review posting, 422 fallback)
- Inline comment and review summary formatting
- End-to-end action/main.py pipeline execution in mock mode
"""

import json
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import pytest

from action.formatter import (
    format_inline_comment,
    format_review_summary,
)
from action.github_client import GitHubClient
from action.main import parse_action_inputs, run_action
from action.providers import CandidateComment


# ============================================================================
# 1. GitHubClient Unit Tests
# ============================================================================


def test_github_client_headers() -> None:
    client = GitHubClient(token="ghp_test_token123")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer ghp_test_token123"
    assert "User-Agent" in headers
    assert headers["Accept"] == "application/vnd.github.v3+json"


def test_github_client_get_pull_request_diff() -> None:
    client = GitHubClient(token="mock_token")
    mock_diff = "--- a/foo.py\n+++ b/foo.py\n@@ -1,2 +1,2 @@\n-a = 1\n+a = 2\n"

    with patch.object(
        client, "_request", return_value=(200, mock_diff.encode("utf-8"), {})
    ) as mock_req:
        diff = client.get_pull_request_diff("owner/repo", 42)
        assert diff == mock_diff
        mock_req.assert_called_once()
        call_url = mock_req.call_args[0][0]
        assert "owner/repo/pulls/42" in call_url


def test_github_client_get_pull_request_diff_error() -> None:
    client = GitHubClient(token="mock_token")
    with patch.object(client, "_request", return_value=(404, b"Not Found", {})):
        diff = client.get_pull_request_diff("owner/repo", 404)
        assert diff == ""


def test_github_client_get_pull_request_info() -> None:
    client = GitHubClient(token="mock_token")
    mock_payload = {"title": "Feature PR", "head": {"sha": "abcdef12345"}}

    with patch.object(
        client,
        "_request",
        return_value=(200, json.dumps(mock_payload).encode("utf-8"), {}),
    ):
        info = client.get_pull_request_info("owner/repo", 10)
        assert info["title"] == "Feature PR"
        assert info["head"]["sha"] == "abcdef12345"


def test_github_client_get_existing_review_comments() -> None:
    client = GitHubClient(token="mock_token")
    mock_comments = [
        {"id": 1, "path": "test.py", "line": 15, "body": "Fix this bug"}
    ]

    with patch.object(
        client,
        "_request",
        return_value=(200, json.dumps(mock_comments).encode("utf-8"), {}),
    ):
        comments = client.get_existing_review_comments("owner/repo", 10)
        assert len(comments) == 1
        assert comments[0]["path"] == "test.py"
        assert comments[0]["line"] == 15


def test_github_client_post_review_success() -> None:
    client = GitHubClient(token="mock_token")
    mock_resp = {"id": 999, "state": "COMMENTED"}

    with patch.object(
        client,
        "_request",
        return_value=(200, json.dumps(mock_resp).encode("utf-8"), {}),
    ) as mock_req:
        inline_comments = [
            {"path": "foo.py", "line": 5, "side": "RIGHT", "body": "Suggested fix"}
        ]
        resp = client.post_review(
            repo="owner/repo",
            pr_number=1,
            commit_sha="c0ffee",
            body="Review summary",
            comments=inline_comments,
        )
        assert resp["id"] == 999
        mock_req.assert_called_once()
        posted_data = json.loads(mock_req.call_args[1]["data"].decode("utf-8"))
        assert posted_data["commit_id"] == "c0ffee"
        assert posted_data["body"] == "Review summary"
        assert len(posted_data["comments"]) == 1


def test_github_client_post_review_fallback_on_422() -> None:
    client = GitHubClient(token="mock_token")
    first_call_done = False

    def fake_request(url, method="GET", headers=None, data=None):
        nonlocal first_call_done
        if not first_call_done:
            first_call_done = True
            # Reject inline comments with 422
            return 422, b'{"message": "Unprocessable Entity"}', {}
        # Fallback summary review succeeds
        return 200, b'{"id": 1001, "state": "COMMENTED"}', {}

    with patch.object(client, "_request", side_effect=fake_request):
        inline_comments = [
            {"path": "foo.py", "line": 99, "side": "RIGHT", "body": "Bad line"}
        ]
        resp = client.post_review(
            repo="owner/repo",
            pr_number=1,
            commit_sha="c0ffee",
            body="Review summary",
            comments=inline_comments,
        )
        assert resp["id"] == 1001
        assert first_call_done is True


# ============================================================================
# 2. Formatter Unit Tests
# ============================================================================


def test_format_inline_comment_rendering() -> None:
    c = CandidateComment(
        file_path="src/calc.py",
        line_number=25,
        category="security",
        severity="critical",
        comment="Insecure deserialization vulnerability",
        suggestion="safe_load(data)",
        confidence=0.98,
        rule_id="sec-deserialization",
    )
    rendered = format_inline_comment(c)
    assert "### 🛡️ Aion Finding: Security Vulnerability (`sec-deserialization`)" in rendered
    assert "**Confidence:** 98% | **Severity:** Critical" in rendered
    assert "Insecure deserialization vulnerability" in rendered
    assert "```suggestion" in rendered
    assert "safe_load(data)" in rendered
    assert "```" in rendered
    assert "Data & Privacy Policy" in rendered


def test_format_review_summary_clean() -> None:
    summary = format_review_summary(
        results=[],
        files_analyzed=3,
        linter_count=1,
        duration_sec=0.45,
    )
    assert "### 🛡️ Aion Code Review Report" in summary
    assert "Passed — No actionable defects" in summary
    assert "**Files Analyzed** | `3`" in summary
    assert "**Actionable Findings** | `0`" in summary
    assert "Zero-Retention Guarantee" in summary


def test_format_review_summary_with_findings() -> None:
    findings = [
        CandidateComment(
            file_path="foo.py",
            line_number=12,
            category="bug",
            severity="critical",
            comment="Null pointer dereference when cache is empty",
            suggestion="    if cache is not None:\n        return cache.get()",
            confidence=0.92,
            rule_id="null-pointer",
        )
    ]
    summary = format_review_summary(
        results=findings,
        files_analyzed=1,
        linter_count=1,
        duration_sec=1.12,
    )
    assert "1 Actionable Finding Detected" in summary
    assert "`foo.py:12`" in summary
    assert "Critical" in summary
    assert "Null pointer dereference" in summary


# ============================================================================
# 3. Action Entrypoint & Pipeline Tests
# ============================================================================


def test_parse_action_inputs_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INPUT_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)

    cfg = parse_action_inputs()
    assert cfg["provider"] == "mock"
    assert cfg["model"] == "qwen-2.5-coder-32b"
    assert cfg["max_comments"] == 5
    assert cfg["min_confidence"] == 0.7
    assert cfg["enable_telemetry"] is True


def test_run_action_skip_when_not_pr() -> None:
    # No repo or pr_number provided
    exit_code = run_action(config={"repo": "", "pr_number": None})
    assert exit_code == 0


def test_run_action_mock_pipeline_execution() -> None:
    fake_diff = """--- a/service.py
+++ b/service.py
@@ -1,3 +1,3 @@
 def run():
-    eval("1+1")
+    x = 1
     return x
"""
    mock_client = MagicMock(spec=GitHubClient)
    mock_client.get_pull_request_diff.return_value = fake_diff
    mock_client.get_existing_review_comments.return_value = []
    mock_client.post_review.return_value = {"id": 123, "state": "COMMENTED"}

    config = {
        "repo": "acme/backend",
        "pr_number": 7,
        "commit_sha": "abcdef7890",
        "token": "fake_token",
        "provider": "mock",
        "model": "qwen-2.5-coder-32b",
        "max_comments": 5,
        "min_confidence": 0.7,
    }

    exit_code = run_action(config=config, client=mock_client, custom_diff=fake_diff)
    assert exit_code == 0
    mock_client.post_review.assert_called_once()
    call_args = mock_client.post_review.call_args[1]
    assert call_args["repo"] == "acme/backend"
    assert call_args["pr_number"] == 7
    assert call_args["commit_sha"] == "abcdef7890"
    assert "Aion Code Review Report" in call_args["body"]
    assert len(call_args["comments"]) >= 1
    assert call_args["comments"][0]["path"] == "service.py"
    assert "```suggestion" in call_args["comments"][0]["body"]


def test_run_action_deduplicates_existing_comments() -> None:
    fake_diff = """--- a/service.py
+++ b/service.py
@@ -1,3 +1,3 @@
 def run():
-    old_val = 1
+    x = 1
     return x
"""
    mock_client = MagicMock(spec=GitHubClient)
    mock_client.get_pull_request_diff.return_value = fake_diff
    # Comment already posted on service.py:2
    mock_client.get_existing_review_comments.return_value = [
        {"path": "service.py", "line": 2, "body": "Already commented"}
    ]
    mock_client.post_review.return_value = {"id": 124, "state": "COMMENTED"}

    config = {
        "repo": "acme/backend",
        "pr_number": 8,
        "commit_sha": "1234567890",
        "token": "fake_token",
        "provider": "mock",
        "model": "qwen-2.5-coder-32b",
        "max_comments": 5,
        "min_confidence": 0.7,
    }

    exit_code = run_action(config=config, client=mock_client, custom_diff=fake_diff)
    assert exit_code == 0
    mock_client.post_review.assert_called_once()
    call_args = mock_client.post_review.call_args[1]
    # Inline comment on line 2 should be skipped to prevent duplicate noise!
    assert len(call_args["comments"]) == 0
    assert "Passed — No actionable defects" in call_args["body"]

