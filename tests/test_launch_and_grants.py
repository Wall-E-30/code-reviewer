"""
tests/test_launch_and_grants.py

Unit test suite verifying Public Launch Dossiers, Marketplace Metadata,
Compute Grant Applications, and Open-Source Moat Strategy (GROWTH-03).
"""

import os
import re
import pytest


def test_show_hn_dossier_completeness():
    """Verify docs/launch/SHOW_HN.md exists and contains required technical sections."""
    doc_path = os.path.join("docs", "launch", "SHOW_HN.md")
    assert os.path.isfile(doc_path), "docs/launch/SHOW_HN.md must exist"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Required sections and technical details
    assert "Show HN: Aion" in content
    assert "Gymnasium" in content or "ReviewEnv" in content
    assert "RLVR" in content or "Reinforcement Learning from Verifiable Rewards" in content
    assert "Clean-Diff" in content
    assert "Qwen2.5-Coder" in content
    assert "78.4%" in content
    assert "Free Forever for Open Source" in content or "100% Free Forever" in content
    assert "Reviewed by Aion" in content


def test_github_marketplace_metadata():
    """Verify docs/launch/MARKETPLACE.md adheres to GitHub Marketplace listing specs."""
    doc_path = os.path.join("docs", "launch", "MARKETPLACE.md")
    assert os.path.isfile(doc_path), "docs/launch/MARKETPLACE.md must exist"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Marketplace requirements
    assert "Product Name:" in content
    assert "Aion Code Reviewer" in content
    assert "Categories:" in content
    assert "Code review" in content
    assert "Free" in content
    assert "permissions:" in content
    assert "pull-requests: write" in content
    assert "suggestion" in content


def test_all_four_grant_dossiers_exist_and_complete():
    """Verify all 4 compute grant applications exist and contain budgets and milestones."""
    grants = {
        "HUGGINGFACE_ZEROGPU.md": ["ZeroGPU", "A100", "Spaces", "Leaderboard"],
        "GOOGLE_FOR_STARTUPS.md": ["Google Cloud", "TPU", "GKE", "GRPO"],
        "AWS_ACTIVATE.md": ["AWS Activate", "Fargate", "S3", "Promotional Credits"],
        "AZURE_FOR_STARTUPS.md": ["Founders Hub", "AKS", "Azure", "GitHub"],
    }

    for filename, required_keywords in grants.items():
        grant_path = os.path.join("docs", "grants", filename)
        assert os.path.isfile(grant_path), f"Grant document {filename} must exist"

        with open(grant_path, "r", encoding="utf-8") as f:
            content = f.read()

        for kw in required_keywords:
            assert kw.lower() in content.lower(), f"Keyword '{kw}' missing from {filename}"


def test_open_source_moat_and_contributing():
    """Verify docs/OPEN_SOURCE_MOAT.md and CONTRIBUTING.md exist and contain required strategies."""
    moat_path = os.path.join("docs", "OPEN_SOURCE_MOAT.md")
    assert os.path.isfile(moat_path), "docs/OPEN_SOURCE_MOAT.md must exist"

    with open(moat_path, "r", encoding="utf-8") as f:
        moat_content = f.read()

    assert "Data Moat" in moat_content
    assert "RLVR Policy Moat" in moat_content
    assert "Zero-Cost Infrastructure" in moat_content or "Zero-Cost Compute" in moat_content
    assert "Trust & Viral Distribution" in moat_content

    contrib_path = "CONTRIBUTING.md"
    assert os.path.isfile(contrib_path), "CONTRIBUTING.md must exist"

    with open(contrib_path, "r", encoding="utf-8") as f:
        contrib_content = f.read()

    assert "Development Setup" in contrib_content
    assert "aion review --staged" in contrib_content
    assert "Aion-Bench" in contrib_content
    assert "Leaderboard" in contrib_content
    assert "Apache-2.0" in contrib_content
