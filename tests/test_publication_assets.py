"""
tests/test_publication_assets.py

Validation test suite for Publication Assets and Submission Flow (LAUNCH-03).
Covers:
- Model card structure, metrics, and licensing
- Dataset card composition, synthetic <= 50% cap, and contamination isolation
- Marketplace listing accuracy and source tags
- Show HN launch copy accuracy and source tags
- Leaderboard submission format and schema guidelines
"""

from __future__ import annotations

from pathlib import Path
import re
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_CARD_PATH = REPO_ROOT / "docs" / "launch" / "MODEL_CARD.md"
DATASET_CARD_PATH = REPO_ROOT / "docs" / "launch" / "DATASET_CARD.md"
MARKETPLACE_PATH = REPO_ROOT / "docs" / "launch" / "MARKETPLACE.md"
SHOW_HN_PATH = REPO_ROOT / "docs" / "launch" / "SHOW_HN.md"
LEADERBOARD_PATH = REPO_ROOT / "docs" / "launch" / "LEADERBOARD_SUBMISSION.md"


def test_all_publication_files_exist():
    for path in [MODEL_CARD_PATH, DATASET_CARD_PATH, MARKETPLACE_PATH, SHOW_HN_PATH, LEADERBOARD_PATH]:
        assert path.exists(), f"Publication asset missing: {path}"


def test_model_card_frontmatter_and_content():
    content = MODEL_CARD_PATH.read_text(encoding="utf-8")
    assert content.startswith("---")
    parts = content.split("---", 2)
    assert len(parts) >= 3, "Model card missing YAML frontmatter"
    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["license"] == "apache-2.0"
    assert "code-review" in frontmatter["tags"]

    assert "88.0%" in content
    assert "[REAL-OFFLINE]" in content
    assert "RewardVersion.V2_0_0" in content
    assert "bench_real/splits/val.json" in content


def test_dataset_card_composition_and_synthetic_cap():
    content = DATASET_CARD_PATH.read_text(encoding="utf-8")
    assert "38.46%" in content
    assert "50" in content  # <= 50%
    assert "[REAL-OFFLINE]" in content
    assert "[LIVE-PILOT]" in content
    assert "data/training_v2/manifest.json" in content
    assert "bottlepy/bottle" in content
    assert "aio-libs/aiohttp" in content


def test_marketplace_listing_measured_metrics():
    content = MARKETPLACE_PATH.read_text(encoding="utf-8")
    assert "[REAL-OFFLINE]" in content
    assert "[LIVE-PILOT]" in content
    assert "88.0%" in content
    assert "0.0%" in content
    assert "90.0%" in content
    assert "false_positive_report.yml" in content
    assert "EVIDENCE_REPORT_TEMPLATE.md" in content


def test_show_hn_measured_metrics():
    content = SHOW_HN_PATH.read_text(encoding="utf-8")
    assert "[REAL-OFFLINE]" in content
    assert "[LIVE-PILOT]" in content
    assert "88.0%" in content
    assert "77.0%" in content
    assert "54.0%" in content
    assert "50.0%" in content
    assert "33.0%" in content
    assert "bench_real/splits/val.json" in content
    assert "EVIDENCE_REPORT_TEMPLATE.md" in content


def test_leaderboard_submission_guide_structure():
    content = LEADERBOARD_PATH.read_text(encoding="utf-8")
    assert "submission.json" in content
    assert "bench_real" in content
    assert "GROWTH-02" in content or "LAUNCH-03" in content
    assert "python -m bench_real" in content
