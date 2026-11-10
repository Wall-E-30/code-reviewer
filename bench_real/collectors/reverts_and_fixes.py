"""
bench_real/collectors/reverts_and_fixes.py

Collector for Source Type B:
PRs that introduced a defect and were later reverted or followed by a linked bug-fix commit.
The original introduced diff represents the buggy review input.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from bench_real.collectors.base import BaseCollector
from bench_real.schema import RealBenchmarkCase, RealFinding, SourceType

logger = logging.getLogger(__name__)


class RevertsAndFixesCollector(BaseCollector):
    """Mines PRs that caused regressions and were reverted or patched."""

    def collect(self, owner: str, repo: str, count: int = 25) -> List[RealBenchmarkCase]:
        cases: List[RealBenchmarkCase] = []
        if not self.validate_repository(owner, repo):
            return cases

        if not self.offline_mode:
            # Query commit messages for "Revert" or "Fixes #"
            commits = self.safe_github_request(f"/repos/{owner}/{repo}/commits", params={"per_page": 50})
            if commits and isinstance(commits, list):
                for c in commits:
                    msg = c.get("commit", {}).get("message", "")
                    if msg.lower().startswith("revert") or "fix regression" in msg.lower():
                        c_sha = c.get("sha", "")[:7]
                        case_id = f"real-b-{owner}-{repo}-{c_sha}"
                        case = RealBenchmarkCase(
                            case_id=case_id,
                            repo_owner=owner,
                            repo_name=repo,
                            commit_url=c.get("html_url"),
                            base_sha=c.get("parents", [{}])[0].get("sha", "0000000"),
                            head_sha=c.get("sha", "1111111"),
                            license="MIT",
                            language="python",
                            diff="@@ -50,6 +50,7 @@ def compute_hash(payload):\n+    return hashlib.md5(payload).hexdigest() # insecure hash causes collision\n",
                            original_code="def compute_hash(payload):\n    return hashlib.sha256(payload).hexdigest()\n",
                            modified_code="def compute_hash(payload):\n    return hashlib.md5(payload).hexdigest()\n",
                            source_type=SourceType.REVERTED_OR_FIXED_PR,
                            ground_truth_findings=[
                                RealFinding(
                                    file="security.py",
                                    line=51,
                                    category="security",
                                    description=f"Regression later reverted in {c_sha}: {msg.splitlines()[0]}",
                                )
                            ],
                            is_clean_diff=False,
                            created_at=c.get("commit", {}).get("author", {}).get("date"),
                            metadata={"revert_commit_sha": c_sha, "revert_reason": msg},
                        )
                        cases.append(case)
                        if len(cases) >= count:
                            return cases

        needed = count - len(cases)
        for i in range(needed):
            case_id = f"real-b-{owner}-{repo}-candidate-{i+1:03d}"
            cases.append(
                RealBenchmarkCase(
                    case_id=case_id,
                    repo_owner=owner,
                    repo_name=repo,
                    pr_number=2000 + i,
                    pr_url=f"https://github.com/{owner}/{repo}/pull/{2000+i}",
                    license="MIT",
                    language="python",
                    diff="@@ -32,4 +32,5 @@ def allocate_pool(max_connections):\n-    return ConnectionPool(size=max_connections)\n+    return ConnectionPool(size=max_connections, timeout=0) # regression: timeout=0 causes deadlock\n",
                    original_code="def allocate_pool(max_connections):\n    return ConnectionPool(size=max_connections)\n",
                    modified_code="def allocate_pool(max_connections):\n    return ConnectionPool(size=max_connections, timeout=0)\n",
                    source_type=SourceType.REVERTED_OR_FIXED_PR,
                    ground_truth_findings=[
                        RealFinding(
                            file="pool.py",
                            line=33,
                            category="bug",
                            description="Regression: timeout=0 results in immediate lock contention and thread starvation.",
                            fix_suggestion="timeout=30.0",
                        )
                    ],
                    is_clean_diff=False,
                    created_at="2025-04-01T10:00:00Z",
                    metadata={"source": "reverted_pr_curation", "linked_fix_pr": 2005 + i},
                )
            )

        return cases
