"""
bench_real/schema.py

Pydantic schemas for the Aion Real-Data Evaluation Suite (bench_real).
Adheres strictly to requirement REAL-01 and Milestone v1.1 standards.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Origin taxonomy for real-world PR evaluation cases."""
    REVIEW_FLAGGED_BUG = "review_flagged_bug"       # Type A: reviewer flagged bug, later commit amended
    REVERTED_OR_FIXED_PR = "reverted_or_fixed_pr"   # Type B: PR later reverted or followed by linked bug-fix
    SECURITY_ADVISORY_CVE = "security_advisory_cve" # Type C: CVE/security advisory fix (pre-fix diff as input)
    CLEAN_MERGED_PR = "clean_merged_pr"             # Type D: Clean merged PR never reverted or amended


class AnnotatorVote(BaseModel):
    """Individual human or external annotator assessment."""
    annotator_id: str
    actionable: bool
    category: str = "bug"
    notes: Optional[str] = ""
    timestamp: Optional[str] = None


class RealFinding(BaseModel):
    """Ground-truth issue located within a diff hunk."""
    file: str
    line: int
    end_line: Optional[int] = None
    category: str = "bug"
    description: str
    fix_suggestion: Optional[str] = None


class RealBenchmarkCase(BaseModel):
    """
    Standardized schema for real-data benchmark cases in bench_real/.
    Tracks provenance, legal licensing, diffs, ground-truth labels, and independent annotator votes.
    """
    case_id: str
    repo_owner: str
    repo_name: str
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    base_sha: Optional[str] = None
    head_sha: Optional[str] = None
    commit_url: Optional[str] = None
    license: str = "MIT"
    language: str = "python"
    diff: str
    original_code: str = ""
    modified_code: str = ""
    source_type: SourceType
    ground_truth_findings: List[RealFinding] = Field(default_factory=list)
    is_clean_diff: bool = False
    annotator_labels: List[AnnotatorVote] = Field(default_factory=list)
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def repository(self) -> str:
        """Full repository slug."""
        return f"{self.repo_owner}/{self.repo_name}"

    def consensus_actionable(self) -> Optional[bool]:
        """
        Derive majority annotator actionability vote if annotators exist.
        Returns None if no human labels have been registered.
        """
        if not self.annotator_labels:
            return None
        true_votes = sum(1 for v in self.annotator_labels if v.actionable)
        return true_votes > (len(self.annotator_labels) / 2.0)
