"""
tests/test_secret_redaction_and_reactions.py

Unit test suite for Diff Secret Redaction, Minimal Context Extraction (HARD-03b),
and Verified GitHub Reaction Polling & App Fixture Processing (HARD-03).
"""

import hashlib
import hmac
import json
import os
from unittest.mock import MagicMock, patch
import pytest

from action.redactor import (
    extract_minimal_diff_context,
    redact_secrets_from_diff,
    sanitize_log_message,
)
from action.github_client import GitHubClient
from server.github_app import GitHubAppHandler, DEFAULT_WEBHOOK_SECRET


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Helper to generate valid X-Hub-Signature-256 for testing."""
    h = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={h}"


# ============================================================================
# 1. HARD-03b: Secret Redaction & Minimal Context
# ============================================================================

def test_redact_aws_and_cloud_keys():
    """Verify AWS access keys and secret tokens are redacted with type tags."""
    diff = """
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+AWS_ACCESS_KEY_ID = "AKIA1234567890ABCDEF"
+aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
"""
    redacted, types = redact_secrets_from_diff(diff)
    assert "AKIA1234567890ABCDEF" not in redacted
    assert "[REDACTED_SECRET:AWS_ACCESS_KEY]" in redacted
    assert "[REDACTED_SECRET:AWS_SECRET_KEY]" in redacted
    assert "AWS_ACCESS_KEY" in types
    assert "AWS_SECRET_KEY" in types


def test_redact_github_openai_and_anthropic_tokens():
    """Verify GitHub PATs and LLM provider API keys are redacted."""
    diff = """
+GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
+OPENAI_KEY = "sk-1234567890abcdef1234567890abcdef"
+ANTHROPIC_KEY = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"
"""
    redacted, types = redact_secrets_from_diff(diff)
    assert "ghp_" not in redacted
    assert "sk-" not in redacted
    assert "[REDACTED_SECRET:GITHUB_TOKEN]" in redacted
    assert "[REDACTED_SECRET:OPENAI_API_KEY]" in redacted
    assert "[REDACTED_SECRET:ANTHROPIC_API_KEY]" in redacted
    assert len(types) >= 3


def test_redact_private_keys():
    """Verify multiline private keys are replaced with redaction tag."""
    diff = """
+-----BEGIN RSA PRIVATE KEY-----
+MIIEowIBAAKCAQEA0Y123456789abcdefghijklmnopqrstuvwxyz
+-----END RSA PRIVATE KEY-----
"""
    redacted, types = redact_secrets_from_diff(diff)
    assert "MIIEowIBAAKCAQEA0Y123456789abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "[REDACTED_SECRET:PRIVATE_KEY]" in redacted
    assert "PRIVATE_KEY" in types


def test_extract_minimal_diff_context():
    """Verify diff context lines are bounded to maximum threshold."""
    # Generate diff with 100 unchanged lines around 1 modification
    long_diff = "--- a/test.py\n+++ b/test.py\n@@ -1,100 +1,101 @@\n"
    for i in range(50):
        long_diff += f" line_{i} = {i}\n"
    long_diff += "+modified_line = 999\n"
    for i in range(50, 100):
        long_diff += f" line_{i} = {i}\n"

    minimal = extract_minimal_diff_context(long_diff, max_surrounding_lines=10)
    lines = minimal.splitlines()

    # The minimal diff should be significantly shorter than 100 lines
    assert len(lines) <= 30
    assert "+modified_line = 999" in minimal


def test_sanitize_log_message():
    """Verify log messages are scrubbed of secrets before output."""
    raw_log = "Processing PR with token ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    clean_log = sanitize_log_message(raw_log)
    assert "ghp_abcdef" not in clean_log
    assert "[REDACTED_SECRET:GITHUB_TOKEN]" in clean_log


# ============================================================================
# 2. HARD-03: Verified Reaction Polling & Recorded App Fixtures
# ============================================================================

def test_github_client_get_comment_reactions():
    """Verify GitHubClient.get_comment_reactions calls official REST endpoint."""
    client = GitHubClient(token="mock-token")
    mock_reactions = [
        {"id": 1, "content": "+1", "user": {"login": "alice"}},
        {"id": 2, "content": "-1", "user": {"login": "bob"}},
    ]

    with patch.object(client, "_request") as mock_req:
        mock_req.return_value = (200, json.dumps(mock_reactions).encode("utf-8"), {})
        result = client.get_comment_reactions("aion-ai/demo-repo", 12345)

        assert len(result) == 2
        assert result[0]["content"] == "+1"
        assert result[1]["content"] == "-1"
        mock_req.assert_called_once_with(
            "https://api.github.com/repos/aion-ai/demo-repo/pulls/comments/12345/reactions",
            method="GET",
        )


def test_github_app_process_recorded_fixtures():
    """Verify GitHubAppHandler accurately dispatches recorded real GitHub event fixtures."""
    fixtures_dir = os.path.join("tests", "fixtures", "github_events")
    handler = GitHubAppHandler()

    # 1. Test recorded pull_request_opened fixture
    pr_path = os.path.join(fixtures_dir, "pull_request_opened.json")
    with open(pr_path, "rb") as f:
        pr_bytes = f.read()
    sig_pr = _sign_payload(pr_bytes, DEFAULT_WEBHOOK_SECRET)

    status, res_pr = handler.process_webhook(
        payload_bytes=pr_bytes,
        signature_header=sig_pr,
        event_name="pull_request",
        secret=DEFAULT_WEBHOOK_SECRET,
    )
    assert status == 200
    assert res_pr["status"] == "reviewed"
    assert res_pr["pr_number"] == 42
    assert res_pr["repository"] == "aion-ai/demo-repo"

    # 2. Test recorded reaction_created fixture
    rx_path = os.path.join(fixtures_dir, "reaction_created.json")
    with open(rx_path, "rb") as f:
        rx_bytes = f.read()
    sig_rx = _sign_payload(rx_bytes, DEFAULT_WEBHOOK_SECRET)

    status, res_rx = handler.process_webhook(
        payload_bytes=rx_bytes,
        signature_header=sig_rx,
        event_name="reaction",
        secret=DEFAULT_WEBHOOK_SECRET,
    )
    assert status == 200
    assert res_rx["status"] == "processed"
    assert res_rx["reaction"] == "+1"
    assert res_rx["reward"] == 1.0

    # 3. Test recorded review_comment_created fixture
    cmt_path = os.path.join(fixtures_dir, "review_comment_created.json")
    with open(cmt_path, "rb") as f:
        cmt_bytes = f.read()
    sig_cmt = _sign_payload(cmt_bytes, DEFAULT_WEBHOOK_SECRET)

    status, res_cmt = handler.process_webhook(
        payload_bytes=cmt_bytes,
        signature_header=sig_cmt,
        event_name="pull_request_review_comment",
        secret=DEFAULT_WEBHOOK_SECRET,
    )
    assert status == 200
    assert res_cmt["status"] == "comment_processed"
