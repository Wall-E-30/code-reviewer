"""
tests/test_verifier_model.py

Unit and integration tests for Actionability Verifier Model & Calibration (TRAIN-02):
- Feature extraction from review candidates and diff context
- Positive/negative pair extraction from episodes stream
- Model fitting and temperature scaling calibration (ECE < 0.05)
- Suppression of subjective nitpicks and clean-diff violations
- High actionability scoring for security/bug fixes with valid suggestions
- PrecisionVerifier integration and serialization
"""

import json
import os
import tempfile
import pytest

from action.providers import CandidateComment
from action.verifier import PrecisionVerifier
from rl.training.verifier_model import (
    ActionabilityDatasetBuilder,
    ActionabilityFeatureExtractor,
    ActionabilityVerifierModel,
    TemperatureCalibrator,
)


def test_feature_extractor():
    """Verify numerical feature extraction dimensions and logic."""
    extractor = ActionabilityFeatureExtractor()
    feat = extractor.extract_features(
        diff_hunk="@@ -1 +1 @@",
        comment_text="Critical SQL injection vulnerability detected",
        suggestion="cursor.execute('SELECT * FROM u WHERE id = ?', (uid,))",
        category="security",
        is_clean_diff=False,
    )
    assert len(feat) == 12
    # Actionable keyword index is 0
    assert feat[0] == 1.0
    # Clean diff indicator is index 6
    assert feat[6] == 0.0
    # Security category is index 8 (bug=7, sec=8)
    assert feat[8] == 1.0


def test_actionability_pair_extraction():
    """Verify dataset builder extracts positive and negative pairs from episode data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ep_file = os.path.join(tmpdir, "test_episodes.jsonl")
        episodes = [
            {
                "case_id": "c1",
                "diff": "@@ -1 +1 @@",
                "is_clean_diff": True,
                "ground_truth": [],
            },
            {
                "case_id": "c2",
                "diff": "@@ -1 +1 @@",
                "is_clean_diff": False,
                "ground_truth": [
                    {
                        "description": "SQL injection vulnerability",
                        "category": "security",
                        "fix_suggestion": "safe_sql()",
                    }
                ],
            },
        ]
        with open(ep_file, "w", encoding="utf-8") as f:
            for ep in episodes:
                f.write(json.dumps(ep) + "\n")

        builder = ActionabilityDatasetBuilder()
        pairs = builder.extract_pairs_from_episodes(ep_file, max_pairs=10)
        assert len(pairs) >= 2
        labels = [p["label"] for p in pairs]
        assert 0 in labels
        assert 1 in labels


def test_temperature_scaling_calibration():
    """Verify temperature scaling fits temperature and achieves low ECE (< 0.05)."""
    calibrator = TemperatureCalibrator()
    model = ActionabilityVerifierModel()

    # Generate synthetic calibration data
    train_data = []
    for _ in range(50):
        # Actionable positive
        train_data.append({
            "diff_hunk": "@@ -1 +1 @@",
            "comment_text": "Uncaught null pointer vulnerability",
            "suggestion": "if (x != null) { x.run(); }",
            "category": "bug",
            "is_clean_diff": False,
            "label": 1,
        })
        # Unhelpful nitpick negative
        train_data.append({
            "diff_hunk": "@@ -1 +1 @@",
            "comment_text": "Nit: consider renaming x to my_var for stylistic preference.",
            "suggestion": None,
            "category": "nitpick",
            "is_clean_diff": False,
            "label": 0,
        })

    val_data = train_data.copy()
    res = model.fit(train_data, val_data)

    assert "temperature" in res
    assert res["temperature"] > 0.0
    assert "val_ece" in res
    assert res["val_ece"] < 0.05, f"Expected ECE < 0.05, got {res['val_ece']}"


def test_nitpick_and_clean_rejection():
    """Verify subjective nitpicks and clean diff comments receive low actionability score."""
    model = ActionabilityVerifierModel()

    train_data = [
        {
            "diff_hunk": "@@ -1 +1 @@",
            "comment_text": "Severe vulnerability in authentication logic",
            "suggestion": "safe_auth()",
            "category": "security",
            "is_clean_diff": False,
            "label": 1,
        },
        {
            "diff_hunk": "@@ -1 +1 @@",
            "comment_text": "Nitpick: please rename variable for style taste",
            "suggestion": None,
            "category": "style",
            "is_clean_diff": False,
            "label": 0,
        },
    ] * 20
    model.fit(train_data)

    # Subjective nitpick
    p_nit = model.predict_proba(
        diff_hunk="@@",
        comment="Nit: cosmetic variable naming convention taste",
        suggestion=None,
        category="style",
        is_clean_diff=False,
    )
    assert p_nit < 0.35, f"Expected p_nit < 0.35, got {p_nit}"

    # Comment on clean diff
    p_clean = model.predict_proba(
        diff_hunk="@@",
        comment="Check logic here",
        suggestion=None,
        category="bug",
        is_clean_diff=True,
    )
    assert p_clean < 0.35, f"Expected p_clean < 0.35, got {p_clean}"


def test_bug_hit_high_actionability():
    """Verify real bugs with valid suggestions receive high actionability score."""
    model = ActionabilityVerifierModel()
    train_data = [
        {
            "diff_hunk": "@@ -1 +1 @@",
            "comment_text": "Critical SQL injection vulnerability detected",
            "suggestion": "cursor.execute('?', (x,))",
            "category": "security",
            "is_clean_diff": False,
            "label": 1,
        },
        {
            "diff_hunk": "@@ -1 +1 @@",
            "comment_text": "Nit: please add docstring",
            "suggestion": None,
            "category": "style",
            "is_clean_diff": False,
            "label": 0,
        },
    ] * 20
    model.fit(train_data)

    p_bug = model.predict_proba(
        diff_hunk="@@",
        comment="Critical SQL injection vulnerability in query builder",
        suggestion="cursor.execute('?', (x,))",
        category="security",
        is_clean_diff=False,
    )
    assert p_bug > 0.70, f"Expected p_bug > 0.70, got {p_bug}"


def test_precision_verifier_integration():
    """Verify PrecisionVerifier uses ActionabilityVerifierModel to gate candidates."""
    model = ActionabilityVerifierModel()
    train_data = [
        {
            "diff_hunk": "@@",
            "comment_text": "SQL injection vulnerability",
            "suggestion": "safe()",
            "category": "security",
            "is_clean_diff": False,
            "label": 1,
        },
        {
            "diff_hunk": "@@",
            "comment_text": "Nitpick: consider renaming",
            "suggestion": None,
            "category": "style",
            "is_clean_diff": False,
            "label": 0,
        },
    ] * 20
    model.fit(train_data)

    verifier = PrecisionVerifier(verifier_model=model, actionability_threshold=0.60)

    good_candidate = CandidateComment(
        file_path="db.py",
        line_number=10,
        category="security",
        comment="Critical SQL injection vulnerability",
        suggestion="cursor.execute('safe', (id,))",
        confidence=0.85,
        severity="critical",
    )

    bad_candidate = CandidateComment(
        file_path="db.py",
        line_number=12,
        category="style",
        comment="Nit: rename variable naming preference",
        suggestion="x = 1",
        confidence=0.80,
        severity="info",
    )

    filtered = verifier.filter_candidates(
        candidates=[good_candidate, bad_candidate],
        modified_lines={10, 12},
    )

    assert len(filtered) == 1
    assert filtered[0].line_number == 10
    assert filtered[0].category == "security"


def test_verifier_save_and_load():
    """Verify model persistence to and loading from JSON file."""
    model = ActionabilityVerifierModel()
    train_data = [
        {
            "diff_hunk": "@@",
            "comment_text": "Critical security bug",
            "suggestion": "safe()",
            "category": "security",
            "is_clean_diff": False,
            "label": 1,
        },
        {
            "diff_hunk": "@@",
            "comment_text": "Nit: whitespace",
            "suggestion": None,
            "category": "style",
            "is_clean_diff": False,
            "label": 0,
        },
    ] * 10
    model.fit(train_data)

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "verifier.json")
        model.save(save_path)
        assert os.path.exists(save_path)

        loaded_model = ActionabilityVerifierModel()
        loaded_model.load(save_path)
        assert loaded_model.is_fitted is True
        assert loaded_model.calibrator.temperature == model.calibrator.temperature

        p1 = model.predict_proba("@@", "Critical security bug", "safe()", "security")
        p2 = loaded_model.predict_proba("@@", "Critical security bug", "safe()", "security")
        assert abs(p1 - p2) < 1e-5

