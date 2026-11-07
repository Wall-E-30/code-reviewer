"""
action/verifier.py

Precision verifier gate for Aion Code Reviewer.
Filters candidate review comments through multi-stage gates:
1. Line sanity check: confines comments to modified lines.
2. Confidence threshold: discards findings below threshold (default: 0.7).
3. Nitpick suppression: eliminates subjective stylistic feedback.
4. Suggestion validation: ensures actionable, non-duplicate, valid code replacements.
5. Deduplication: merges overlapping linter and LLM comments.
6. Hard ceiling: guarantees at most 5 highest-impact comments per PR.
"""

from __future__ import annotations

import ast
import re
import textwrap
from typing import Any, Dict, List, Optional, Set, Tuple

from action.providers import CandidateComment

NITPICK_PATTERNS = re.compile(
    r"\b(nit:|nitpick|consider renaming|naming convention|redundant comment|"
    r"formatting taste|variable name choice|cosmetic|add docstring|typing hint)\b",
    re.IGNORECASE,
)

SEVERITY_WEIGHTS = {
    "critical": 3,
    "major": 2,
    "minor": 1,
    "info": 0,
}


class PrecisionVerifier:
    """
    Rigorously filters candidate comments to produce high-precision,
    low-noise code review output.
    """

    def __init__(
        self,
        default_max_comments: int = 5,
        default_min_confidence: float = 0.7,
        category_thresholds: Optional[Dict[str, float]] = None,
        verifier_model: Optional[Any] = None,
        actionability_threshold: float = 0.60,
    ) -> None:
        self.default_max_comments = default_max_comments
        self.default_min_confidence = default_min_confidence
        self.category_thresholds = category_thresholds or {}
        self.verifier_model = verifier_model
        self.actionability_threshold = actionability_threshold

    def is_valid_suggestion(
        self,
        candidate: CandidateComment,
        file_content: Optional[str] = None,
    ) -> bool:
        """
        Validate that candidate comment includes a concrete, non-duplicate,
        and syntactically valid suggestion block.
        """
        if not candidate.suggestion or not candidate.suggestion.strip():
            return False

        suggestion_stripped = candidate.suggestion.strip()

        # Check for no-op duplicates against original code
        if file_content:
            lines = file_content.splitlines()
            if 1 <= candidate.line_number <= len(lines):
                orig_line = lines[candidate.line_number - 1].strip()
                if suggestion_stripped == orig_line:
                    return False

        # If Python code, verify the suggestion is syntactically valid
        if candidate.file_path.endswith(".py"):
            try:
                # Dedent in case the suggestion has leading indentation
                dedented = textwrap.dedent(candidate.suggestion)
                ast.parse(dedented)
            except SyntaxError:
                return False

        return True

    def is_nitpick(self, candidate: CandidateComment) -> bool:
        """Identify subjective style preferences or trivial nitpicks."""
        cat = candidate.category.lower()
        if cat == "nitpick":
            return True

        sev = candidate.severity.lower()
        if cat == "style" and sev in ("minor", "info"):
            return True

        if NITPICK_PATTERNS.search(candidate.comment) and sev in ("minor", "info"):
            return True

        return False

    def filter_candidates(
        self,
        candidates: List[CandidateComment],
        modified_lines: Set[int],
        max_comments: Optional[int] = None,
        min_confidence: Optional[float] = None,
        file_content: Optional[str] = None,
        category_thresholds: Optional[Dict[str, float]] = None,
        actionability_threshold: Optional[float] = None,
    ) -> List[CandidateComment]:
        """
        Filter and rank candidate comments according to strict precision criteria.

        Parameters:
            candidates: Raw comments from LLM providers and static linters
            modified_lines: Added or modified line numbers where inline comments can be placed
            max_comments: Hard ceiling limit (default: 5)
            min_confidence: Minimum confidence cutoff (default: 0.7)
            file_content: Optional modified file content for syntax & duplicate checks
            category_thresholds: Optional per-category dynamic thresholds from bandit
            actionability_threshold: Optional actionability cutoff from verifier model (TRAIN-02)

        Returns:
            Filtered, deduplicated list capped at <= max_comments.
        """
        ceiling = max_comments if max_comments is not None else self.default_max_comments
        threshold = (
            min_confidence if min_confidence is not None else self.default_min_confidence
        )
        cat_thresh_map = (
            category_thresholds
            if category_thresholds is not None
            else self.category_thresholds
        )
        act_thresh = (
            actionability_threshold
            if actionability_threshold is not None
            else self.actionability_threshold
        )

        filtered: List[CandidateComment] = []

        for c in candidates:
            # Stage 1: Line sanity check
            if modified_lines and (c.line_number not in modified_lines):
                continue

            # Stage 2: Confidence threshold (category-specific bandit or fallback default)
            cat_thresh = (
                cat_thresh_map.get(c.category.lower(), threshold)
                if cat_thresh_map
                else threshold
            )
            if c.confidence < cat_thresh:
                continue

            # Stage 3: Nitpick suppression
            if self.is_nitpick(c):
                continue

            # Stage 4: Suggestion validation
            if not self.is_valid_suggestion(c, file_content=file_content):
                continue

            # Stage 4.5: Actionability verifier model scoring (TRAIN-02)
            if self.verifier_model is not None:
                p_act = self.verifier_model.predict_proba(
                    diff_hunk="",
                    comment=c.comment,
                    suggestion=c.suggestion,
                    category=c.category,
                )
                if p_act < act_thresh:
                    continue

            filtered.append(c)

        # Stage 5: Deduplication (group by file_path and line_number)
        grouped: Dict[Tuple[str, int], List[CandidateComment]] = {}
        for c in filtered:
            key = (c.file_path, c.line_number)
            grouped.setdefault(key, []).append(c)

        def _score(item: CandidateComment) -> float:
            sev = SEVERITY_WEIGHTS.get(item.severity.lower(), 1)
            act_bonus = 1.0
            if self.verifier_model is not None:
                act_bonus = self.verifier_model.predict_proba(
                    diff_hunk="",
                    comment=item.comment,
                    suggestion=item.suggestion,
                    category=item.category,
                )
            return sev * 10.0 + item.confidence * 2.0 + act_bonus

        deduped: List[CandidateComment] = []
        for _, items in grouped.items():
            if len(items) == 1:
                deduped.append(items[0])
            else:
                best = max(items, key=_score)
                deduped.append(best)

        # Stage 6: Hard ceiling ranking
        deduped.sort(key=_score, reverse=True)

        return deduped[:ceiling]

