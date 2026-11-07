"""
tests/test_badge_and_quality.py

Unit test suite for Dynamic SVG Badge Generator, Repository Quality Dashboard,
and Open-Source Commitment Manifesto (GROWTH-01).
"""

import os
import re
from datetime import datetime, timezone
import pytest

from server.badge import (
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    generate_svg_badge,
    get_badge_for_precision,
)
from server.precision_gate import RepoReviewRecord
from server.app import get_repo_precision, telemetry_aggregator, repo_badge_endpoint, repo_quality_endpoint


def test_generate_svg_badge_structure():
    """Verify SVG badge generates well-formed SVG XML with title and tags."""
    svg = generate_svg_badge("Reviewed by Aion", "85% precision", COLOR_GREEN)

    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert "Reviewed by Aion: 85% precision" in svg
    assert COLOR_GREEN in svg
    assert 'fill="#555"' in svg


def test_badge_color_and_text_thresholds():
    """Verify badge color and text thresholds match specification."""
    # 1. High precision (>= 70%) -> Green
    svg_high = get_badge_for_precision(0.78)
    assert COLOR_GREEN in svg_high
    assert "78% precision" in svg_high

    svg_high_status = get_badge_for_precision(0.78, metric_type="status")
    assert COLOR_GREEN in svg_high_status
    assert "passing" in svg_high_status

    # 2. Moderate precision (50% - 69%) -> Yellow
    svg_mod = get_badge_for_precision(0.62)
    assert COLOR_YELLOW in svg_mod
    assert "62% precision" in svg_mod

    svg_mod_status = get_badge_for_precision(0.62, metric_type="status")
    assert COLOR_YELLOW in svg_mod_status
    assert "monitoring" in svg_mod_status

    # 3. Low precision (< 50%) -> Red
    svg_low = get_badge_for_precision(0.40)
    assert COLOR_RED in svg_low
    assert "40% precision" in svg_low

    svg_low_status = get_badge_for_precision(0.40, metric_type="status")
    assert COLOR_RED in svg_low_status
    assert "low precision" in svg_low_status

    # 4. No data -> Gray
    svg_none = get_badge_for_precision(None)
    assert COLOR_GRAY in svg_none
    assert "unverified" in svg_none


def test_badge_endpoint_direct():
    """Verify repo_badge_endpoint returns SVG response with caching headers."""
    # Ingest records for a test repo
    telemetry_aggregator.records.clear()
    now = datetime.now(timezone.utc)
    telemetry_aggregator.record_event(
        RepoReviewRecord(
            repo_id="testorg/demo-repo",
            timestamp=now,
            comments_posted=10,
            comments_accepted=8,
            comments_rejected=2,
            category="bug",
        )
    )

    resp = repo_badge_endpoint(owner="testorg", repo="demo-repo", metric="precision")
    assert resp.media_type == "image/svg+xml"
    assert "Cache-Control" in resp.headers
    assert "public, max-age=300" in resp.headers["Cache-Control"]

    content = resp.body.decode("utf-8") if isinstance(resp.body, bytes) else str(resp.body)
    assert "<svg" in content
    assert "80% precision" in content
    assert COLOR_GREEN in content


def test_repo_quality_endpoint():
    """Verify repo_quality_endpoint returns comprehensive metrics and embed snippets."""
    telemetry_aggregator.records.clear()
    now = datetime.now(timezone.utc)
    telemetry_aggregator.record_event(
        RepoReviewRecord(
            repo_id="octocat/hello-world",
            timestamp=now,
            comments_posted=5,
            comments_accepted=4,
            comments_rejected=1,
            category="security",
        )
    )

    data = repo_quality_endpoint(owner="octocat", repo="hello-world")
    assert data["repo_id"] == "octocat/hello-world"
    assert data["precision"] == 0.80
    assert data["precision_percentage"] == "80.0%"
    assert data["comments_posted"] == 5
    assert data["comments_accepted"] == 4
    assert data["comments_rejected"] == 1
    assert "PASS ✅" in data["status"]
    assert "badge_url" in data
    assert "badge_markdown" in data
    assert "Free for Open Source" in data["free_tier"]


def test_open_source_commitment_document():
    """Verify docs/OPEN_SOURCE_COMMITMENT.md exists and contains key guarantees."""
    doc_path = os.path.join("docs", "OPEN_SOURCE_COMMITMENT.md")
    assert os.path.isfile(doc_path), "docs/OPEN_SOURCE_COMMITMENT.md must exist"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Permanently Free for Public Open Source" in content
    assert "Reviewed by Aion" in content
    assert "OSI-approved" in content
    assert "No Private Code Exploitation" in content
