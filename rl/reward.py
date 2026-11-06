"""
rl/reward.py

Objective Verifiable Multi-Tier Reward Function for Aion Code Reviewer (RL-02).
Mathematically scores code review actions against verifiable ground truth:
- Ground-truth bug hit: +1.00
- Critical security vulnerability hit: +1.50
- False positive (comment on non-buggy code): -0.75
- Clean-diff violation (commenting on a clean PR): -1.50
- Nitpick deduction (style/nitpick comment on substantive defect): -0.25
- Suggestion syntax validity / actionable bonus: +0.50
- Zero-delta suggestion penalty (copy of existing code): -0.50
- Missed bug (false negative) penalty: -0.50
"""

from __future__ import annotations

import ast
import logging
import textwrap
from typing import Any, Dict, List, Optional, Tuple, Union

from bench.evaluator.matcher import match_comments_to_findings
from bench.schema import FindingCategory, GroundTruthFinding, ReviewComment

logger = logging.getLogger(__name__)

# Standard reward weights
REWARD_BUG_HIT = 1.00
REWARD_SECURITY_HIT = 1.50
PENALTY_FALSE_POSITIVE = -0.75
PENALTY_CLEAN_VIOLATION = -1.50
PENALTY_NITPICK = -0.25
BONUS_SUGGESTION_VALID = 0.50
PENALTY_ZERO_DELTA = -0.50
PENALTY_MISSED_BUG = -0.50


def _coerce_to_review_comment(raw: Union[ReviewComment, Dict[str, Any], Any]) -> ReviewComment:
    """Coerce dict, CandidateComment, or ReviewComment into standard ReviewComment."""
    if isinstance(raw, ReviewComment):
        return raw

    if hasattr(raw, "file_path") and hasattr(raw, "line_number"):
        cat_str = getattr(raw, "category", "bug")
        try:
            category = FindingCategory(str(cat_str).lower())
        except ValueError:
            category = FindingCategory.BUG

        return ReviewComment(
            file_path=str(getattr(raw, "file_path", "")),
            line_number=int(getattr(raw, "line_number", 1)),
            category=category,
            comment=str(getattr(raw, "comment", "")),
            suggestion=getattr(raw, "suggestion", None),
            confidence=float(getattr(raw, "confidence", 1.0)),
        )

    if isinstance(raw, dict):
        cat_str = raw.get("category", "bug")
        try:
            category = FindingCategory(str(cat_str).lower())
        except ValueError:
            category = FindingCategory.BUG

        return ReviewComment(
            file_path=str(raw.get("file_path", "")),
            line_number=int(raw.get("line_number", 1)),
            category=category,
            comment=str(raw.get("comment", "")),
            suggestion=raw.get("suggestion"),
            confidence=float(raw.get("confidence", 1.0)),
        )

    raise ValueError(f"Cannot coerce object of type {type(raw)} to ReviewComment")


def _coerce_to_ground_truth(raw: Union[GroundTruthFinding, Dict[str, Any], Any]) -> GroundTruthFinding:
    """Coerce dict or GroundTruthFinding into standard GroundTruthFinding."""
    if isinstance(raw, GroundTruthFinding):
        return raw
    if isinstance(raw, dict):
        return GroundTruthFinding.model_validate(raw)
    raise ValueError(f"Cannot coerce object of type {type(raw)} to GroundTruthFinding")


class VerifiableRewardCalculator:
    """
    Computes objective, verifiable multi-tier rewards for code review actions.
    Eliminates subjective bias and protects against reward hacking.
    """

    def __init__(
        self,
        line_window: int = 3,
        bug_hit_reward: float = REWARD_BUG_HIT,
        security_hit_reward: float = REWARD_SECURITY_HIT,
        false_positive_penalty: float = PENALTY_FALSE_POSITIVE,
        clean_violation_penalty: float = PENALTY_CLEAN_VIOLATION,
        nitpick_penalty: float = PENALTY_NITPICK,
        suggestion_bonus: float = BONUS_SUGGESTION_VALID,
        zero_delta_penalty: float = PENALTY_ZERO_DELTA,
        missed_bug_penalty: float = PENALTY_MISSED_BUG,
    ) -> None:
        self.line_window = line_window
        self.bug_hit_reward = bug_hit_reward
        self.security_hit_reward = security_hit_reward
        self.false_positive_penalty = false_positive_penalty
        self.clean_violation_penalty = clean_violation_penalty
        self.nitpick_penalty = nitpick_penalty
        self.suggestion_bonus = suggestion_bonus
        self.zero_delta_penalty = zero_delta_penalty
        self.missed_bug_penalty = missed_bug_penalty

    def evaluate_suggestion(
        self,
        comment: ReviewComment,
        file_content: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """
        Evaluate code replacement suggestion.

        Returns:
            Tuple[is_valid_syntax, is_zero_delta]
        """
        if not comment.suggestion or not comment.suggestion.strip():
            return False, False

        suggestion_stripped = comment.suggestion.strip()

        # Check for zero-delta duplicate of original code line
        is_zero_delta = False
        if file_content:
            lines = file_content.splitlines()
            if 1 <= comment.line_number <= len(lines):
                orig_line = lines[comment.line_number - 1].strip()
                if suggestion_stripped == orig_line:
                    is_zero_delta = True

        # Check syntax validity for Python
        is_valid = True
        if comment.file_path.endswith(".py") or not comment.file_path:
            try:
                dedented = textwrap.dedent(comment.suggestion)
                ast.parse(dedented)
            except SyntaxError:
                is_valid = False

        return is_valid, is_zero_delta

    def compute_reward(
        self,
        comments: List[Union[ReviewComment, Dict[str, Any], Any]],
        ground_truth: List[Union[GroundTruthFinding, Dict[str, Any], Any]],
        is_clean_diff: bool = False,
        file_content: Optional[str] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Compute verifiable scalar reward and detailed metrics breakdown.

        Parameters:
            comments: Review comments emitted by agent / policy
            ground_truth: Known defect specifications
            is_clean_diff: True if PR diff contains no real defects
            file_content: Content of modified file for syntax & duplicate checks

        Returns:
            Tuple of (total_scalar_reward, metrics_dict)
        """
        typed_comments = [_coerce_to_review_comment(c) for c in comments]
        typed_findings = [_coerce_to_ground_truth(f) for f in ground_truth]

        total_reward = 0.0
        breakdown = {
            "bug_hits": 0,
            "security_hits": 0,
            "false_positives": 0,
            "clean_diff_violations": 0,
            "nitpicks": 0,
            "syntax_bonuses": 0,
            "zero_delta_penalties": 0,
            "missed_bugs": 0,
            "matched_pairs": 0,
        }

        # 1. Clean Diff Evaluation
        if is_clean_diff:
            if typed_comments:
                violations = len(typed_comments)
                breakdown["clean_diff_violations"] = violations
                total_reward += violations * self.clean_violation_penalty
            # If 0 comments on clean diff, reward is 0.0 (no penalty, perfect FP suppression)
            breakdown["total_reward"] = round(total_reward, 4)
            return round(total_reward, 4), breakdown

        # 2. Match comments against ground truth
        matched_pairs, unmatched_comments, unmatched_findings = match_comments_to_findings(
            comments=typed_comments,
            findings=typed_findings,
            line_window=self.line_window,
        )

        breakdown["matched_pairs"] = len(matched_pairs)

        # 3. Score Ground-Truth Matches
        for pair in matched_pairs:
            comm = pair.comment
            find = pair.finding

            if find.category == FindingCategory.SECURITY or comm.category == FindingCategory.SECURITY:
                breakdown["security_hits"] += 1
                total_reward += self.security_hit_reward
            else:
                breakdown["bug_hits"] += 1
                total_reward += self.bug_hit_reward

            # Check if substantive finding was degraded into a nitpick
            if comm.category in (FindingCategory.STYLE, FindingCategory.NITPICK):
                breakdown["nitpicks"] += 1
                total_reward += self.nitpick_penalty

        # 4. Score Unmatched Comments (False Positives)
        for u_comm in unmatched_comments:
            breakdown["false_positives"] += 1
            total_reward += self.false_positive_penalty

            if u_comm.category in (FindingCategory.STYLE, FindingCategory.NITPICK):
                breakdown["nitpicks"] += 1
                total_reward += self.nitpick_penalty

        # 5. Score Unmatched Findings (Missed Bugs / False Negatives)
        breakdown["missed_bugs"] = len(unmatched_findings)
        total_reward += len(unmatched_findings) * self.missed_bug_penalty

        # 6. Evaluate Actionable Suggestion Quality
        for comm in typed_comments:
            is_valid, is_zero_delta = self.evaluate_suggestion(comm, file_content=file_content)
            if is_zero_delta:
                breakdown["zero_delta_penalties"] += 1
                total_reward += self.zero_delta_penalty
            elif is_valid:
                breakdown["syntax_bonuses"] += 1
                total_reward += self.suggestion_bonus

        breakdown["total_reward"] = round(total_reward, 4)
        return round(total_reward, 4), breakdown
