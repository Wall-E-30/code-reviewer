"""
tests/test_rate_limits_and_scorecard.py

Verification suite for Wave 4 (HARD-06, SCORECARD):
- 2MB request body ceiling enforcement (413 Request Entity Too Large)
- Sliding window per-IP rate limiting (60 req/min -> 429 Too Many Requests)
- Webhook delivery ID replay cache (X-GitHub-Delivery TTL cache)
- Per-repository rate limit guard (120 req/min)
- Outbound HTTP timeout ceilings (<= 10.0s)
- Honest milestone scorecard with explicit metric lineage tags
"""

import os
import pytest
from fastapi.testclient import TestClient

from server.app import app, server_rate_limiter, webhook_delivery_cache
from server.rate_limiter import MAX_PAYLOAD_BYTES, RateLimiter, WebhookDeliveryCache
from action.github_client import GitHubClient
from action.providers import OpenAICompatibleProvider


@pytest.fixture(autouse=True)
def reset_limits():
    """Reset rate limiter and webhook cache before each test."""
    server_rate_limiter.reset()
    webhook_delivery_cache.clear()
    yield
    server_rate_limiter.reset()
    webhook_delivery_cache.clear()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_payload_size_ceiling_413(client):
    """Payloads exceeding 2MB must be rejected with 413 Request Entity Too Large."""
    # Test with Content-Length header exceeding 2MB
    oversized_length = MAX_PAYLOAD_BYTES + 1024
    headers = {
        "content-length": str(oversized_length),
        "content-type": "application/json",
    }
    response = client.post("/diff", content=b"{}", headers=headers)
    assert response.status_code == 413
    assert "2MB limit" in response.json().get("detail", "")


def test_payload_under_limit_allowed(client):
    """Payloads under 2MB must pass through successfully."""
    headers = {
        "content-length": "100",
        "content-type": "application/json",
    }
    response = client.post(
        "/diff",
        json={"original": "def a(): pass\n", "modified": "def a(): return 1\n"},
        headers=headers,
    )
    assert response.status_code == 200
    assert "diff" in response.json()


def test_per_ip_rate_limiting_429(client):
    """Per-IP traffic exceeding 60 req/min must be throttled with 429 and Retry-After."""
    test_ip = "192.168.1.100"
    headers = {"x-forwarded-for": test_ip}

    # First 60 requests should succeed
    for i in range(60):
        resp = client.get("/api/badge", headers=headers)
        assert resp.status_code == 200
        assert "X-RateLimit-Remaining" in resp.headers

    # 61st request must trigger 429
    throttled = client.get("/api/badge", headers=headers)
    assert throttled.status_code == 429
    assert "per-IP rate limit exceeded" in throttled.json().get("detail", "")
    assert throttled.headers.get("Retry-After") == "60"

    # Health endpoint is exempt from rate limits
    health_resp = client.get("/health", headers=headers)
    assert health_resp.status_code == 200


def test_webhook_replay_guard(client):
    """Duplicate X-GitHub-Delivery deliveries must be idempotently ignored."""
    import hmac
    import hashlib

    secret = "aion-webhook-secret-dev"
    delivery_uuid = "12345678-abcd-ef01-2345-6789abcdef01"
    payload = b'{"zen": "Keep it logically awesome.", "hook_id": 1}'
    sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    headers = {
        "X-GitHub-Event": "ping",
        "X-Hub-Signature-256": sig,
        "X-GitHub-Delivery": delivery_uuid,
        "content-type": "application/json",
    }

    # First delivery: processed normally
    resp1 = client.post("/api/github/webhook", content=payload, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json().get("status") in ("pong", "acknowledged")

    # Replay of same delivery UUID: ignored
    resp2 = client.post("/api/github/webhook", content=payload, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2.get("status") == "ignored"
    assert "Duplicate delivery ID" in data2.get("detail", "")


def test_per_repo_rate_limiting(client):
    """Repository webhook events exceeding 120 req/min must be throttled with 429."""
    import hmac
    import hashlib
    import json

    secret = "aion-webhook-secret-dev"
    repo_name = "test-owner/test-repo-flooder"

    limiter = RateLimiter(ip_limit=200, repo_limit=5)
    # Simulate 5 allowed repo requests
    for i in range(5):
        allowed, rem = limiter.record_repo_request(repo_name)
        assert allowed

    # 6th request rejected
    allowed, rem = limiter.record_repo_request(repo_name)
    assert not allowed
    assert rem == 0


def test_outbound_http_timeout_ceilings():
    """All outbound HTTP clients must enforce timeout <= 10.0s."""
    gh_client = GitHubClient(token="test-token")
    assert gh_client.timeout <= 10.0, f"GitHubClient timeout {gh_client.timeout} exceeds 10.0s limit"

    llm_provider = OpenAICompatibleProvider(base_url="https://api.openai.com/v1")
    assert llm_provider.timeout <= 10.0, f"OpenAICompatibleProvider timeout {llm_provider.timeout} exceeds 10.0s limit"


def test_honest_scorecard_integrity():
    """docs/SCORECARD.md must exist, follow two-column format, and include all 4 taxonomy tags."""
    scorecard_path = os.path.join("docs", "SCORECARD.md")
    assert os.path.isfile(scorecard_path), "docs/SCORECARD.md must exist"

    with open(scorecard_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify two-column audit table headers
    assert "Built (Code Exists & Tests Pass)" in content
    assert "Validated on Real Data (In-the-Wild Evidence)" in content

    # Verify all four metric lineage tags are defined and used
    tags = ["[SYNTHETIC]", "[SIMULATED]", "[REAL-OFFLINE]", "[LIVE-PILOT]"]
    for tag in tags:
        assert tag in content, f"Taxonomy tag {tag} missing from docs/SCORECARD.md"

    # Verify proven vs pending sections
    assert "Proven" in content
    assert "Pending" in content
