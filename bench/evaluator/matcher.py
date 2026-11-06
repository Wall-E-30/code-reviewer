"""
bench/evaluator/matcher.py

Objective ground-truth matching engine for code review comments (BENCH-05).
Pairs reviewer comments with ground-truth findings using configurable
line proximity windows and semantic category congruence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import List, Optional, Set, Tuple

from bench.schema import FindingCategory, GroundTruthFinding, ReviewComment

SUBSTANTIVE_CATEGORIES = {
    FindingCategory.BUG,
    FindingCategory.SECURITY,
    FindingCategory.PERFORMANCE,
}

COSMETIC_CATEGORIES = {
    FindingCategory.STYLE,
    FindingCategory.NITPICK,
}


@dataclass
class MatchedPair:
    """A matched pairing between a ReviewComment and a GroundTruthFinding."""
    comment: ReviewComment
    finding: GroundTruthFinding
    line_distance: int


def _normalize_path(path_str: str) -> str:
    """Normalize file paths across operating systems and relative prefixes."""
    if not path_str:
        return ""
    normalized = path_str.replace("\\", "/").strip().lstrip("./")
    # If path starts with git diff prefix like "a/" or "b/", normalize it
    if normalized.startswith("a/") or normalized.startswith("b/"):
        normalized = normalized[2:]
    return PurePosixPath(normalized).as_posix().lower()


def are_paths_compatible(path1: str, path2: str) -> bool:
    """Check if two file paths refer to the same source file."""
    norm1 = _normalize_path(path1)
    norm2 = _normalize_path(path2)
    if not norm1 or not norm2:
        return False
    if norm1 == norm2:
        return True
    if norm1.endswith("/" + norm2) or norm2.endswith("/" + norm1):
        return True
    return False


def are_categories_compatible(comment_cat: FindingCategory, finding_cat: FindingCategory) -> bool:
    """
    Verify category congruence between comment and ground-truth finding.
    Rules:
    - If finding is substantive (BUG, SECURITY, PERFORMANCE), comment cannot be cosmetic (STYLE, NITPICK).
    - If finding is cosmetic (STYLE, NITPICK), comment cannot be substantive (BUG, SECURITY, PERFORMANCE).
    - Categories match if they belong to the same category group.
    """
    if finding_cat in SUBSTANTIVE_CATEGORIES and comment_cat in COSMETIC_CATEGORIES:
        return False
    if finding_cat in COSMETIC_CATEGORIES and comment_cat in SUBSTANTIVE_CATEGORIES:
        return False
    return True


def compute_line_distance(comment_line: int, line_start: int, line_end: int) -> int:
    """
    Compute absolute distance in lines between a comment and a ground-truth line span.
    Returns 0 if the comment falls within [line_start, line_end].
    """
    if line_start <= comment_line <= line_end:
        return 0
    if comment_line < line_start:
        return line_start - comment_line
    return comment_line - line_end


def match_comments_to_findings(
    comments: List[ReviewComment],
    findings: List[GroundTruthFinding],
    line_window: int = 3,
) -> Tuple[List[MatchedPair], List[ReviewComment], List[GroundTruthFinding]]:
    """
    Match review comments to ground-truth findings using 1-to-1 greedy matching.

    Args:
        comments: List of ReviewComment objects emitted by reviewer engine.
        findings: List of GroundTruthFinding objects defined in benchmark case.
        line_window: Allowable line proximity delta (default +-3 lines).

    Returns:
        Tuple of:
        - matched_pairs: List of MatchedPair objects
        - unmatched_comments: List of false positive comments
        - unmatched_findings: List of false negative findings
    """
    if not comments:
        return [], [], list(findings)
    if not findings:
        return [], list(comments), []

    candidates = []

    for c_idx, comment in enumerate(comments):
        for f_idx, finding in enumerate(findings):
            # 1. File path match (if finding specifies a file_path, enforce compatibility)
            finding_path = getattr(finding, "file_path", None)
            if finding_path and comment.file_path:
                if not are_paths_compatible(comment.file_path, finding_path):
                    continue

            # 2. Category congruence
            if not are_categories_compatible(comment.category, finding.category):
                continue

            # 3. Proximity window check
            distance = compute_line_distance(comment.line_number, finding.line_start, finding.line_end)
            if distance > line_window:
                continue

            # Exact category preference (0 if identical category, 1 if compatible cross-category)
            exact_cat_penalty = 0 if comment.category == finding.category else 1

            # Candidate key: (line_distance, exact_cat_penalty, c_idx, f_idx)
            candidates.append((distance, exact_cat_penalty, c_idx, f_idx))

    # Sort candidates greedily: lowest distance first, exact category first
    candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3]))

    matched_pairs: List[MatchedPair] = []
    matched_comments: Set[int] = set()
    matched_findings: Set[int] = set()

    for distance, _, c_idx, f_idx in candidates:
        if c_idx in matched_comments or f_idx in matched_findings:
            continue

        matched_comments.add(c_idx)
        matched_findings.add(f_idx)
        matched_pairs.append(
            MatchedPair(
                comment=comments[c_idx],
                finding=findings[f_idx],
                line_distance=distance,
            )
        )

    unmatched_comments = [c for idx, c in enumerate(comments) if idx not in matched_comments]
    unmatched_findings = [f for idx, f in enumerate(findings) if idx not in matched_findings]

    return matched_pairs, unmatched_comments, unmatched_findings
