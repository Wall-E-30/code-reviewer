"""
tests/test_bench_real_annotation.py

Unit tests for human annotation tooling, Cohen's kappa agreement engine,
and disagreement extraction (REAL-02).
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from bench_real.annotation.agreement import compute_cohens_kappa, extract_disagreements
from bench_real.annotation.tool import AnnotationSession


def test_annotation_session_lifecycle(tmp_path: Path):
    """Verify AnnotationSession loads candidates, records votes, and resumes cleanly."""
    candidates_file = tmp_path / "candidates.json"
    dummy_candidates = [
        {
            "case_id": "case-001",
            "repo_owner": "tornadoweb",
            "repo_name": "tornado",
            "pr_number": 1,
            "license": "Apache-2.0",
            "language": "python",
            "diff": "@@ -1,2 +1,3 @@\n+x = 1\n",
            "source_type": "review_flagged_bug",
            "is_clean_diff": False,
        },
        {
            "case_id": "case-002",
            "repo_owner": "aio-libs",
            "repo_name": "aiohttp",
            "pr_number": 2,
            "license": "Apache-2.0",
            "language": "python",
            "diff": "@@ -5,2 +5,3 @@\n+y = 2\n",
            "source_type": "clean_merged_pr",
            "is_clean_diff": True,
        },
    ]
    with open(candidates_file, "w", encoding="utf-8") as f:
        json.dump(dummy_candidates, f)

    out_file = tmp_path / "labels_ann1.json"
    session = AnnotationSession(
        annotator_id="annotator_1",
        candidates_file=candidates_file,
        output_file=out_file,
    )

    stats = session.get_progress()
    assert stats["total_candidates"] == 2
    assert stats["labeled_count"] == 0

    # Record first vote
    vote1 = session.record_vote("case-001", actionable=True, category="bug", notes="Confirmed logic bug")
    assert vote1.actionable is True
    assert vote1.annotator_id == "annotator_1"
    session.save()

    assert out_file.exists()

    # Re-instantiate session to verify resumption
    resumed = AnnotationSession(
        annotator_id="annotator_1",
        candidates_file=candidates_file,
        output_file=out_file,
    )
    assert resumed.get_progress()["labeled_count"] == 1
    assert "case-001" in resumed.labels


def test_cohens_kappa_perfect_agreement():
    """Verify kappa is exactly 1.0 when annotators agree on every case."""
    labels_1 = {
        "c1": {"actionable": True, "category": "bug"},
        "c2": {"actionable": False, "category": "clean"},
        "c3": {"actionable": True, "category": "security"},
        "c4": {"actionable": False, "category": "clean"},
    }
    labels_2 = {
        "c1": {"actionable": True, "category": "bug"},
        "c2": {"actionable": False, "category": "clean"},
        "c3": {"actionable": True, "category": "security"},
        "c4": {"actionable": False, "category": "clean"},
    }

    metrics = compute_cohens_kappa(labels_1, labels_2)
    assert metrics["n_common_cases"] == 4
    assert metrics["observed_agreement"] == 1.0
    assert metrics["cohens_kappa"] == 1.0
    assert metrics["category_agreement_rate"] == 1.0
    assert "Almost perfect" in metrics["interpretation"]


def test_cohens_kappa_chance_and_partial_agreement():
    """Verify kappa handles partial agreement and chance distributions correctly."""
    # Annotators agree on 3 out of 4 (75% observed)
    labels_1 = {
        "c1": {"actionable": True, "category": "bug"},
        "c2": {"actionable": True, "category": "bug"},
        "c3": {"actionable": False, "category": "clean"},
        "c4": {"actionable": False, "category": "clean"},
    }
    labels_2 = {
        "c1": {"actionable": True, "category": "bug"},
        "c2": {"actionable": False, "category": "clean"},  # Disagreement
        "c3": {"actionable": False, "category": "clean"},
        "c4": {"actionable": False, "category": "clean"},
    }

    metrics = compute_cohens_kappa(labels_1, labels_2)
    assert metrics["n_common_cases"] == 4
    assert metrics["observed_agreement"] == 0.75
    assert 0.0 < metrics["cohens_kappa"] < 1.0
    assert metrics["contingency_table"]["b_yes_no"] == 1


def test_extract_disagreements():
    """Verify extract_disagreements captures both actionability and category conflicts."""
    labels_1 = {
        "c1": {"actionable": True, "category": "bug", "notes": "Memory leak"},
        "c2": {"actionable": True, "category": "bug", "notes": "Logic error"},
        "c3": {"actionable": False, "category": "clean", "notes": "Refactoring"},
    }
    labels_2 = {
        "c1": {"actionable": False, "category": "clean", "notes": "Looks harmless"},  # Actionability mismatch
        "c2": {"actionable": True, "category": "security", "notes": "SQL injection"}, # Category mismatch
        "c3": {"actionable": False, "category": "clean", "notes": "Harmless"},        # Agreement
    }

    disagreements = extract_disagreements(labels_1, labels_2)
    assert len(disagreements) == 2

    cids = {d["case_id"] for d in disagreements}
    assert cids == {"c1", "c2"}

    conflict_types = {d["case_id"]: d["conflict_type"] for d in disagreements}
    assert conflict_types["c1"] == "actionability_mismatch"
    assert conflict_types["c2"] == "category_mismatch"


def test_cohens_kappa_empty_overlap():
    """Verify empty case overlap safely returns 0 without zero-division error."""
    labels_1 = {"c1": {"actionable": True}}
    labels_2 = {"c2": {"actionable": False}}

    metrics = compute_cohens_kappa(labels_1, labels_2)
    assert metrics["n_common_cases"] == 0
    assert metrics["cohens_kappa"] == 0.0
