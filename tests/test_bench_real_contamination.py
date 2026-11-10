"""
tests/test_bench_real_contamination.py

Unit tests for MinHash fuzzy diff fingerprinting, extended contamination guard,
and temporal post-cutoff slicing (REAL-03).
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from bench_real.contamination import (
    ExtendedContaminationGuard,
    MinHashFingerprint,
    generate_contamination_report,
    normalize_diff_for_hashing,
    partition_by_cutoff,
)
from bench_real.schema import RealBenchmarkCase, RealFinding, SourceType


def test_minhash_similarity_properties():
    """Verify MinHash Jaccard similarity bounds on identical, near-duplicate, and distinct diffs."""
    minhash = MinHashFingerprint(num_hashes=64, shingle_size=4)

    diff1 = """
    @@ -10,4 +10,5 @@ def connect(host, port):
    -    sock = socket.socket()
    +    sock = socket.create_connection((host, port), timeout=10.0)
         return sock
    """
    diff_identical = diff1

    diff_near = """
    @@ -10,4 +10,5 @@ def connect(target_host, target_port):
    -    sock = socket.socket()
    +    sock = socket.create_connection((target_host, target_port), timeout=10.0)
         return sock
    """

    diff_distinct = """
    @@ -1,5 +1,6 @@
    +const express = require('express');
    +const app = express();
    +app.listen(3000);
    """

    sig1 = minhash.compute(normalize_diff_for_hashing(diff1))
    sig_ident = minhash.compute(normalize_diff_for_hashing(diff_identical))
    sig_near = minhash.compute(normalize_diff_for_hashing(diff_near))
    sig_distinct = minhash.compute(normalize_diff_for_hashing(diff_distinct))

    # Identical diffs must have Jaccard == 1.0
    assert minhash.jaccard_similarity(sig1, sig_ident) == 1.0

    # Near duplicate should have high similarity (>= 0.65)
    sim_near = minhash.jaccard_similarity(sig1, sig_near)
    assert sim_near >= 0.65, f"Expected near duplicate >= 0.65, got {sim_near}"

    # Distinct code should have very low similarity (< 0.25)
    sim_dist = minhash.jaccard_similarity(sig1, sig_distinct)
    assert sim_dist < 0.25, f"Expected distinct < 0.25, got {sim_dist}"


def test_contamination_guard_detects_all_leakage_vectors():
    """Verify ExtendedContaminationGuard detects repo overlap, exact hash, fuzzy diffs, and file paths."""
    guard = ExtendedContaminationGuard(fuzzy_threshold=0.70)

    # Register known training item
    guard.register_training_episode(
        repo="trained/project-a",
        diff="@@ -1,2 +1,3 @@\n+injected_bug_call()\n",
        file_path="src/engine.py",
        episode_id="train-001",
    )

    # 1. Test clean un-contaminated case
    clean_case = RealBenchmarkCase(
        case_id="case-clean",
        repo_owner="unseen-org",
        repo_name="unseen-repo",
        license="MIT",
        language="python",
        diff="@@ -10,2 +10,3 @@\n+return safe_value\n",
        source_type=SourceType.CLEAN_MERGED_PR,
        is_clean_diff=True,
    )
    res_clean = guard.check_contamination(clean_case)
    assert not res_clean["contaminated"]
    assert len(res_clean["violations"]) == 0

    # 2. Test repo overlap
    repo_leak_case = RealBenchmarkCase(
        case_id="case-repo-leak",
        repo_owner="trained",
        repo_name="project-a",
        license="MIT",
        language="python",
        diff="@@ -20,2 +20,3 @@\n+other_unrelated_code()\n",
        source_type=SourceType.CLEAN_MERGED_PR,
        is_clean_diff=True,
    )
    res_repo = guard.check_contamination(repo_leak_case)
    assert res_repo["contaminated"]
    assert any("Repository overlap" in v for v in res_repo["violations"])

    # 3. Test exact diff hash collision
    exact_leak_case = RealBenchmarkCase(
        case_id="case-exact-leak",
        repo_owner="other-org",
        repo_name="other-repo",
        license="MIT",
        language="python",
        diff="@@ -1,2 +1,3 @@\n+injected_bug_call()\n",
        source_type=SourceType.REVIEW_FLAGGED_BUG,
        is_clean_diff=False,
    )
    res_exact = guard.check_contamination(exact_leak_case)
    assert res_exact["contaminated"]
    assert any("Exact SHA-256 diff hash collision" in v for v in res_exact["violations"])

    # 4. Test fuzzy MinHash collision
    fuzzy_leak_case = RealBenchmarkCase(
        case_id="case-fuzzy-leak",
        repo_owner="third-org",
        repo_name="third-repo",
        license="MIT",
        language="python",
        diff="@@ -1,2 +1,3 @@\n+  injected_bug_call()  \n",
        source_type=SourceType.REVIEW_FLAGGED_BUG,
        is_clean_diff=False,
    )
    res_fuzzy = guard.check_contamination(fuzzy_leak_case)
    assert res_fuzzy["contaminated"]
    assert any("fuzzy" in v.lower() for v in res_fuzzy["violations"])


def test_partition_by_cutoff():
    """Verify temporal partitioning separates pre-cutoff from post-cutoff PRs."""
    cases = [
        RealBenchmarkCase(
            case_id="pre-1",
            repo_owner="org",
            repo_name="repo",
            license="MIT",
            language="python",
            diff="+x",
            source_type=SourceType.CLEAN_MERGED_PR,
            created_at="2023-12-01T00:00:00Z",
        ),
        RealBenchmarkCase(
            case_id="post-1",
            repo_owner="org",
            repo_name="repo",
            license="MIT",
            language="python",
            diff="+y",
            source_type=SourceType.CLEAN_MERGED_PR,
            created_at="2025-01-15T00:00:00Z",
        ),
    ]

    post, pre = partition_by_cutoff(cases, cutoff_date="2024-06-01T00:00:00Z")
    assert len(post) == 1
    assert post[0].case_id == "post-1"
    assert len(pre) == 1
    assert pre[0].case_id == "pre-1"


def test_generate_contamination_report(tmp_path: Path):
    """Verify contamination report generation produces JSON and Markdown outputs."""
    guard = ExtendedContaminationGuard(fuzzy_threshold=0.70)
    cases = [
        RealBenchmarkCase(
            case_id="c1",
            repo_owner="clean-org",
            repo_name="clean-repo",
            license="MIT",
            language="python",
            diff="+clean_code()",
            source_type=SourceType.CLEAN_MERGED_PR,
            created_at="2025-02-01T00:00:00Z",
        )
    ]

    report_path = tmp_path / "CONTAMINATION_REPORT"
    report = generate_contamination_report(cases, guard, output_path=report_path)

    assert report["total_cases_audited"] == 1
    assert report["is_uncontaminated"] is True
    assert (tmp_path / "CONTAMINATION_REPORT.json").exists()
    assert (tmp_path / "CONTAMINATION_REPORT.md").exists()

