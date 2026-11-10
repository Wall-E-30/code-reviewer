"""
tests/test_bench_real_schema_and_collectors.py

Unit and integration tests for bench_real schema, provenance collectors,
and 300+ candidate case mining (REAL-01).
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from bench_real.collectors.base import BaseCollector, BLACKLISTED_REPOSITORIES
from bench_real.collectors.candidate_miner import CandidateMiner, DEFAULT_TARGET_REPOS
from bench_real.collectors.clean_prs import CleanPRsCollector
from bench_real.collectors.reverts_and_fixes import RevertsAndFixesCollector
from bench_real.collectors.reviewed_bugs import ReviewedBugsCollector
from bench_real.collectors.security_cve import SecurityCVECollector
from bench_real.schema import (
    AnnotatorVote,
    RealBenchmarkCase,
    RealFinding,
    SourceType,
)


def test_schema_instantiation_and_validation():
    """Verify RealBenchmarkCase and nested schemas validate properly."""
    vote = AnnotatorVote(
        annotator_id="human_expert_1",
        actionable=True,
        category="security",
        notes="Confirmed header injection vulnerability",
        timestamp="2026-11-10T12:00:00Z",
    )
    finding = RealFinding(
        file="app/views.py",
        line=42,
        category="security",
        description="SQL injection in query filter",
        fix_suggestion="db.execute('SELECT * FROM t WHERE id = ?', (id,))",
    )
    case = RealBenchmarkCase(
        case_id="real-cve-test-01",
        repo_owner="pallets-extra",
        repo_name="sample-project",
        pr_number=101,
        pr_url="https://github.com/pallets-extra/sample-project/pull/101",
        license="MIT",
        language="python",
        diff="@@ -40,3 +40,4 @@\n+db.execute(f'SELECT * FROM t WHERE id = {id}')\n",
        source_type=SourceType.SECURITY_ADVISORY_CVE,
        ground_truth_findings=[finding],
        is_clean_diff=False,
        annotator_labels=[vote],
    )

    assert case.repository == "pallets-extra/sample-project"
    assert case.source_type == SourceType.SECURITY_ADVISORY_CVE
    assert len(case.ground_truth_findings) == 1
    assert case.consensus_actionable() is True


def test_base_collector_license_and_blacklist_enforcement():
    """Verify BaseCollector rejects non-OSI licenses and blacklisted training repositories."""
    collector = BaseCollector(offline_mode=True)

    # 1. Reject blacklisted repo from training/v1.0 test sets
    assert not collector.validate_repository("pallets", "flask", license_key="mit")
    assert not collector.validate_repository("aion", "synthetic-bench", license_key="mit")

    # 2. Reject non-OSI proprietary license
    assert not collector.validate_repository("valid-org", "valid-repo", license_key="proprietary-eula")

    # 3. Accept clean unblacklisted permissive repo
    assert collector.validate_repository("tornadoweb", "tornado", license_key="apache-2.0")
    assert collector.validate_repository("moment", "moment", license_key="mit")


def test_individual_collectors_generate_valid_cases():
    """Verify each of the 4 collectors generates cases with correct provenance."""
    col_a = ReviewedBugsCollector(offline_mode=True)
    col_b = RevertsAndFixesCollector(offline_mode=True)
    col_c = SecurityCVECollector(offline_mode=True)
    col_d = CleanPRsCollector(offline_mode=True)

    cases_a = col_a.collect("tornadoweb", "tornado", count=5)
    cases_b = col_b.collect("aio-libs", "aiohttp", count=5)
    cases_c = col_c.collect("starlette", "starlette", count=5)
    cases_d = col_d.collect("bottlepy", "bottle", count=5)

    assert len(cases_a) == 5
    assert all(c.source_type == SourceType.REVIEW_FLAGGED_BUG for c in cases_a)
    assert all(not c.is_clean_diff for c in cases_a)

    assert len(cases_b) == 5
    assert all(c.source_type == SourceType.REVERTED_OR_FIXED_PR for c in cases_b)

    assert len(cases_c) == 5
    assert all(c.source_type == SourceType.SECURITY_ADVISORY_CVE for c in cases_c)
    assert any("CVE" in c.case_id or "GHSA" in str(c.metadata) for c in cases_c)

    assert len(cases_d) == 5
    assert all(c.source_type == SourceType.CLEAN_MERGED_PR for c in cases_d)
    assert all(c.is_clean_diff for c in cases_d)
    assert all(len(c.ground_truth_findings) == 0 for c in cases_d)


def test_candidate_miner_produces_300_plus_cases(tmp_path: Path):
    """Verify CandidateMiner generates >= 300 cases, writes to disk, and has zero blacklist overlap."""
    out_file = tmp_path / "candidates.json"
    miner = CandidateMiner(output_path=out_file, target_count=320)
    cases = miner.load_or_mine()

    assert len(cases) >= 300, f"Expected >= 300 cases, got {len(cases)}"
    assert out_file.exists()

    # Verify case ID uniqueness
    case_ids = [c.case_id for c in cases]
    assert len(case_ids) == len(set(case_ids)), "Duplicate case IDs detected"

    # Verify distribution across all 4 provenance types
    type_counts = {}
    for c in cases:
        type_counts[c.source_type] = type_counts.get(c.source_type, 0) + 1

    assert type_counts[SourceType.REVIEW_FLAGGED_BUG] >= 50
    assert type_counts[SourceType.REVERTED_OR_FIXED_PR] >= 50
    assert type_counts[SourceType.SECURITY_ADVISORY_CVE] >= 50
    assert type_counts[SourceType.CLEAN_MERGED_PR] >= 50

    # Verify zero overlap with blacklisted training repos
    for c in cases:
        assert c.repository.lower() not in BLACKLISTED_REPOSITORIES

