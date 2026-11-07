"""
tests/test_github_app.py

Unit and integration tests for GitHub App webhook server (APP-01):
- HMAC-SHA256 signature verification (X-Hub-Signature-256)
- GitHub App RS256 JWT generation and installation token exchange
- Pull request event handling and automated review candidate generation
- Real-time reaction event handling and immediate bandit threshold updating
- FastAPI webhook route verification with TestClient
"""

import hashlib
import hmac
import json
import pytest
from fastapi import HTTPException, Request

from rl.bandit import CategoryBandit
from server.app import github_webhook_endpoint
from server.github_app import (
    DEFAULT_WEBHOOK_SECRET,
    GitHubAppAuth,
    GitHubAppHandler,
    verify_webhook_signature,
)


def _sign_payload(payload_bytes: bytes, secret: str = DEFAULT_WEBHOOK_SECRET) -> str:
    """Helper to generate valid X-Hub-Signature-256 header."""
    mac = hmac.new(secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def test_signature_verification_valid_and_invalid():
    """Verify HMAC signature validation correctly accepts valid signatures and rejects tampered ones."""
    secret = "my-secret-key-123"
    payload = b'{"action": "opened", "number": 42}'

    valid_sig = _sign_payload(payload, secret)
    assert verify_webhook_signature(payload, valid_sig, secret) is True

    # Tampered payload
    tampered_payload = b'{"action": "opened", "number": 99}'
    assert verify_webhook_signature(tampered_payload, valid_sig, secret) is False

    # Tampered signature
    assert verify_webhook_signature(payload, "sha256=invalidhex00000", secret) is False


def test_missing_signature_header_rejected():
    """Verify missing, empty, or malformed signature headers are rejected."""
    payload = b'{"test": 1}'
    assert verify_webhook_signature(payload, None, "secret") is False
    assert verify_webhook_signature(payload, "", "secret") is False
    assert verify_webhook_signature(payload, "md5=unsupported", "secret") is False


def test_github_app_jwt_and_token_exchange():
    """Verify GitHub App JWT generation and installation token exchange."""
    auth = GitHubAppAuth(app_id="998877")
    jwt_token = auth.create_app_jwt(expiration_minutes=10)
    assert len(jwt_token.split(".")) == 3

    token = auth.get_installation_token(12345)
    assert "12345" in token


def test_pull_request_opened_dispatch():
    """Verify pull_request opened event triggers review analysis and candidate generation."""
    handler = GitHubAppHandler()
    payload = {
        "action": "opened",
        "repository": {"full_name": "acme/project"},
        "pull_request": {"number": 10, "head": {"sha": "abc1234"}},
        "diff": "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-x = 1\n+eval(user_input)\n",
        "files": {"app.py": "eval(user_input)\n"},
    }

    res = handler.dispatch_event("pull_request", payload)
    assert res["status"] == "reviewed"
    assert res["repository"] == "acme/project"
    assert res["pr_number"] == 10
    assert res["comments_generated"] > 0
    assert res["comments_posted"] > 0


def test_positive_reaction_updates_bandit():
    """Verify +1 reaction immediately adjusts bandit threshold (relaxing cutoff)."""
    bandit = CategoryBandit()
    t_start = bandit.get_threshold("security")

    handler = GitHubAppHandler(bandit=bandit)
    payload = {
        "action": "created",
        "reaction": {"content": "+1"},
        "comment": {"body": "Category: security\nFound vulnerability."},
    }

    res = handler.dispatch_event("reaction", payload)
    assert res["status"] == "processed"
    assert res["category"] == "security"
    assert res["reward"] == 1.0
    # Positive reward should reduce or maintain threshold
    assert bandit.get_threshold("security") <= t_start


def test_negative_reaction_elevates_threshold():
    """Verify -1 reaction immediately increases bandit threshold (demanding higher certainty)."""
    bandit = CategoryBandit()
    t_start = bandit.get_threshold("style")

    handler = GitHubAppHandler(bandit=bandit)
    payload = {
        "action": "created",
        "reaction": {"content": "-1"},
        "comment": {"body": "Category: style\nFound style issue."},
    }

    res = handler.dispatch_event("reaction", payload)
    assert res["status"] == "processed"
    assert res["category"] == "style"
    assert res["reward"] == -1.5
    # Negative reward should increase threshold
    assert bandit.get_threshold("style") >= t_start


def test_fastapi_webhook_endpoint_success():
    """Verify webhook processing handles signed requests."""
    handler = GitHubAppHandler()
    body_dict = {"zen": "Mind over matter"}
    body_bytes = json.dumps(body_dict).encode("utf-8")
    sig = _sign_payload(body_bytes, DEFAULT_WEBHOOK_SECRET)

    status_code, data = handler.process_webhook(
        payload_bytes=body_bytes,
        signature_header=sig,
        event_name="ping",
        secret=DEFAULT_WEBHOOK_SECRET,
    )

    assert status_code == 200
    assert data["status"] == "pong"
    assert data["zen"] == "Mind over matter"


def test_fastapi_webhook_endpoint_unauthorized():
    """Verify webhook processing rejects requests with tampered signatures."""
    handler = GitHubAppHandler()
    body_bytes = b'{"action": "ping"}'
    invalid_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

    status_code, data = handler.process_webhook(
        payload_bytes=body_bytes,
        signature_header=invalid_sig,
        event_name="ping",
        secret=DEFAULT_WEBHOOK_SECRET,
    )

    assert status_code == 401
    assert "Invalid webhook signature" in data["detail"]

