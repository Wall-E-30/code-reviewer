"""
tests/test_issue_template.py

Validation test suite for False-Positive GitHub Issue Form Template (LAUNCH-02).
Ensures YAML validity, GitHub Issue Form schema conformance, and required fields.
"""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "false_positive_report.yml"


def test_issue_template_exists():
    assert TEMPLATE_PATH.exists(), f"Issue template missing at {TEMPLATE_PATH}"


def test_issue_template_valid_yaml():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "Template root must be a YAML dictionary"


def test_issue_template_top_level_keys():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    assert "name" in data
    assert "description" in data
    assert "title" in data
    assert "labels" in data
    assert "body" in data

    assert data["name"] == "False Positive Review Report"
    assert "false-positive" in data["labels"]
    assert "triage" in data["labels"]


def test_issue_template_body_structure():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    body = data["body"]
    assert isinstance(body, list)
    assert len(body) >= 7

    # Collect element IDs
    element_ids = [item.get("id") for item in body if isinstance(item, dict) and "id" in item]
    expected_ids = [
        "repository",
        "pr_link",
        "location",
        "comment_text",
        "reason",
        "diff_context",
        "explanation",
        "acknowledgements",
    ]
    for expected_id in expected_ids:
        assert expected_id in element_ids, f"Missing required body field ID: {expected_id}"


def test_dropdown_options():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    reason_field = next(item for item in data["body"] if item.get("id") == "reason")
    assert reason_field["type"] == "dropdown"
    options = reason_field["attributes"]["options"]
    assert len(options) >= 5

    # Check that core false positive categories are present
    options_text = " ".join(options).lower()
    assert "logic" in options_text
    assert "suggestion" in options_text
    assert "nitpick" in options_text
    assert "known" in options_text
    assert "scope" in options_text

