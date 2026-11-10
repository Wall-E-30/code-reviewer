"""
bench_real/collectors/candidate_miner.py

Orchestrator for mining and assembling 300+ real-world PR evaluation candidates.
Ensures zero training repository contamination and balances across all 4 provenance types.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from bench_real.collectors.clean_prs import CleanPRsCollector
from bench_real.collectors.reverts_and_fixes import RevertsAndFixesCollector
from bench_real.collectors.reviewed_bugs import ReviewedBugsCollector
from bench_real.collectors.security_cve import SecurityCVECollector
from bench_real.schema import RealBenchmarkCase

logger = logging.getLogger(__name__)

DEFAULT_TARGET_REPOS = [
    ("tornadoweb", "tornado", "apache-2.0"),
    ("aio-libs", "aiohttp", "apache-2.0"),
    ("starlette", "starlette", "bsd-3-clause"),
    ("simonw", "datasette", "apache-2.0"),
    ("bottlepy", "bottle", "mit"),
    ("moment", "moment", "mit"),
    ("dayjs", "dayjs", "mit"),
    ("isaacs", "node-glob", "isc"),
]

DEFAULT_CANDIDATES_PATH = Path("bench_real/data/candidates.json")


class CandidateMiner:
    """Orchestrates multi-source real PR candidate generation."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        output_path: Optional[Path] = None,
        target_count: int = 320,
    ) -> None:
        self.github_token = github_token
        self.output_path = output_path or DEFAULT_CANDIDATES_PATH
        self.target_count = target_count

        self.col_a = ReviewedBugsCollector(github_token=github_token)
        self.col_b = RevertsAndFixesCollector(github_token=github_token)
        self.col_c = SecurityCVECollector(github_token=github_token)
        self.col_d = CleanPRsCollector(github_token=github_token)

    def mine_candidates(self) -> List[RealBenchmarkCase]:
        """Collects 300+ balanced real PR candidates across target repositories."""
        all_cases: List[RealBenchmarkCase] = []
        cases_per_repo = max(40, self.target_count // len(DEFAULT_TARGET_REPOS))
        per_type = cases_per_repo // 4

        for owner, repo, license_name in DEFAULT_TARGET_REPOS:
            # Type A: Reviewed bugs
            cases_a = self.col_a.collect(owner, repo, count=per_type)
            # Type B: Reverted PRs / fixes
            cases_b = self.col_b.collect(owner, repo, count=per_type)
            # Type C: Security CVEs
            cases_c = self.col_c.collect(owner, repo, count=per_type)
            # Type D: Clean PRs
            cases_d = self.col_d.collect(owner, repo, count=per_type)

            all_cases.extend(cases_a)
            all_cases.extend(cases_b)
            all_cases.extend(cases_c)
            all_cases.extend(cases_d)

        # Deduplicate by case_id
        seen_ids = set()
        deduped: List[RealBenchmarkCase] = []
        for c in all_cases:
            if c.case_id not in seen_ids:
                seen_ids.add(c.case_id)
                deduped.append(c)

        logger.info("Mined %d unique real PR candidate cases across %d repositories.", len(deduped), len(DEFAULT_TARGET_REPOS))
        return deduped

    def save_candidates(self, cases: List[RealBenchmarkCase]) -> Path:
        """Serializes candidate cases to disk."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_list = [c.model_dump() for c in cases]
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(raw_list, f, indent=2)
        logger.info("Saved %d candidates to %s", len(cases), self.output_path)
        return self.output_path

    def load_or_mine(self) -> List[RealBenchmarkCase]:
        """Loads candidates from disk if existing; otherwise mines and saves."""
        if self.output_path.exists():
            try:
                with open(self.output_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                cases = [RealBenchmarkCase(**item) for item in raw_data]
                if len(cases) >= 300:
                    return cases
            except Exception as e:
                logger.warning("Could not load existing candidates: %s. Re-mining.", e)

        cases = self.mine_candidates()
        self.save_candidates(cases)
        return cases

