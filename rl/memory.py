"""
rl/memory.py

Per-Repository Convention Memory for Aion Code Reviewer (FLY-01).
Tracks maintainer dismissals, custom conventions, and suppressed patterns to:
1. Prevent recurring false positives and unwanted nitpicks without requiring model retraining.
2. Inject repository-specific preferences into BYOK LLM prompts.
3. Persist team conventions across runs in `.aion/conventions.json`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class SuppressedPattern(BaseModel):
    """A pattern or rule that has been dismissed by maintainers and marked for suppression."""

    pattern: str
    category: str = "general"
    rule_id: Optional[str] = None
    dismissal_count: int = 1
    reason: str = ""
    suppressed: bool = False
    created_at: float = Field(default_factory=time.time)
    last_dismissed_at: float = Field(default_factory=time.time)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class CustomRule(BaseModel):
    """Explicit convention or guideline defined by repository maintainers."""

    rule_text: str
    category: str = "general"
    created_at: float = Field(default_factory=time.time)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class RepoMemoryState(BaseModel):
    """Serialized state of per-repository convention memory."""

    suppressed_patterns: List[SuppressedPattern] = Field(default_factory=list)
    custom_rules: List[CustomRule] = Field(default_factory=list)
    suppressed_categories: List[str] = Field(default_factory=list)
    dismissal_threshold: int = 2
    muted: bool = False
    muted_reason: str = ""
    muted_at: Optional[float] = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class RepoConventionMemory:
    """
    Manages repository-specific conventions, dismissed comment patterns,
    and category suppressions.
    """

    def __init__(
        self,
        suppression_threshold: int = 2,
        auto_save_path: Optional[str] = None,
        storage_path: Optional[str] = None,
        repo_id: Optional[str] = None,
    ) -> None:
        self.repo_id = repo_id
        self.threshold = max(1, suppression_threshold)
        save_p = auto_save_path or storage_path
        self.auto_save_path = str(save_p) if save_p else None
        self.state = RepoMemoryState(dismissal_threshold=self.threshold)
        if self.auto_save_path and os.path.exists(self.auto_save_path):
            try:
                self.load(self.auto_save_path)
            except Exception:
                pass

    def record_dismissal(
        self,
        category: str,
        rule_id: Optional[str],
        pattern: str,
        reason: str = "",
    ) -> SuppressedPattern:
        """
        Record a maintainer dismissal for a category, rule, or text pattern.
        If dismissals reach or exceed the suppression threshold, automatically
        marks the pattern as suppressed.
        """
        pattern_str = (pattern or "").strip()
        cat_str = (category or "general").strip()
        rule_str = rule_id.strip() if rule_id else None

        # Look for existing pattern entry
        existing: Optional[SuppressedPattern] = None
        for item in self.state.suppressed_patterns:
            same_pattern = item.pattern.strip().lower() == pattern_str.lower()
            same_rule = (item.rule_id == rule_str) or (not item.rule_id and not rule_str)
            same_cat = (
                item.category.lower() == cat_str.lower()
                or item.category.lower() == "general"
                or cat_str.lower() == "general"
            )
            if same_pattern and same_rule and same_cat:
                existing = item
                break

        if existing:
            existing.dismissal_count += 1
            existing.last_dismissed_at = time.time()
            if reason and not existing.reason:
                existing.reason = reason
            if existing.dismissal_count >= self.threshold:
                existing.suppressed = True
            target = existing
        else:
            is_suppressed = 1 >= self.threshold
            target = SuppressedPattern(
                pattern=pattern_str,
                category=cat_str,
                rule_id=rule_str,
                dismissal_count=1,
                reason=reason,
                suppressed=is_suppressed,
            )
            self.state.suppressed_patterns.append(target)

        if self.auto_save_path:
            self.save(self.auto_save_path)

        return target

    def suppress_category(self, category: str) -> None:
        """Explicitly suppress an entire category of comments."""
        cat_norm = category.strip().lower()
        if cat_norm and cat_norm not in [c.lower() for c in self.state.suppressed_categories]:
            self.state.suppressed_categories.append(category.strip())
            if self.auto_save_path:
                self.save(self.auto_save_path)

    def add_convention(self, rule_text: str, category: str = "general") -> CustomRule:
        """
        Explicitly register team conventions (e.g. from CONTRIBUTING.md or .editorconfig).
        """
        text = rule_text.strip()
        cat = category.strip()

        for cr in self.state.custom_rules:
            if cr.rule_text.lower() == text.lower() and cr.category.lower() == cat.lower():
                return cr

        new_rule = CustomRule(rule_text=text, category=cat)
        self.state.custom_rules.append(new_rule)

        if self.auto_save_path:
            self.save(self.auto_save_path)

        return new_rule

    def mute(self, reason: str = "Maintainer mute command") -> None:
        """Mutes all review actions for this repository."""
        self.state.muted = True
        self.state.muted_reason = reason
        self.state.muted_at = time.time()
        logger.info("Repository convention memory marked muted: %s", reason)
        if self.auto_save_path:
            self.save(self.auto_save_path)

    def unmute(self) -> None:
        """Unmutes review actions for this repository."""
        self.state.muted = False
        self.state.muted_reason = ""
        self.state.muted_at = None
        logger.info("Repository convention memory unmuted.")
        if self.auto_save_path:
            self.save(self.auto_save_path)

    def is_muted(self) -> bool:
        """Check if repository reviews are muted."""
        return bool(self.state.muted)

    def is_suppressed(
        self,
        category: str,
        comment_text: str,
        rule_id: Optional[str] = None,
    ) -> bool:
        """
        Check whether a proposed review comment matches any suppressed pattern,
        rule ID, or suppressed category.
        """
        cat_lower = (category or "").strip().lower()
        cmt_lower = (comment_text or "").strip().lower()
        rule_lower = rule_id.strip().lower() if rule_id else None

        # 1. Check whole category suppression
        for sup_cat in self.state.suppressed_categories:
            sc = sup_cat.lower()
            if cat_lower == sc or cat_lower.startswith(f"{sc}/") or sc.startswith(f"{cat_lower}/"):
                return True

        # 2. Check suppressed patterns and rules
        for sp in self.state.suppressed_patterns:
            if not sp.suppressed:
                continue

            sp_cat = sp.category.lower()
            cat_match = (
                not sp_cat
                or sp_cat in ("general", "*", "all")
                or cat_lower == sp_cat
                or cat_lower.startswith(f"{sp_cat}/")
                or sp_cat.startswith(f"{cat_lower}/")
            )

            sp_rule = sp.rule_id.lower() if sp.rule_id else None
            rule_match = (
                sp_rule is None
                or rule_lower is None
                or sp_rule == rule_lower
            )

            # Rule ID exact match suppression
            if sp_rule and rule_lower and sp_rule == rule_lower and cat_match:
                if not sp.pattern or sp.pattern == "*":
                    return True

            # Pattern text matching
            pat_lower = sp.pattern.strip().lower()
            if pat_lower:
                # Substring check
                if (pat_lower in cmt_lower or cmt_lower in pat_lower) and cat_match and rule_match:
                    return True

                # Regex check if pattern is regex-shaped
                try:
                    if re.search(re.escape(pat_lower) if len(pat_lower) > 60 else pat_lower, cmt_lower, re.IGNORECASE):
                        if cat_match and rule_match:
                            return True
                except re.error:
                    pass

        return False

    def build_prompt_context(self) -> str:
        """
        Build a concise Markdown block summarizing team preferences, custom conventions,
        and suppressed feedback to inject into LLM review prompts.
        """
        has_rules = bool(self.state.custom_rules)
        active_suppressed = [sp for sp in self.state.suppressed_patterns if sp.suppressed]
        has_suppressed = bool(active_suppressed or self.state.suppressed_categories)

        if not has_rules and not has_suppressed:
            return ""

        lines = [
            "### REPOSITORY CONVENTIONS & GUIDELINES",
            "The repository maintainers enforce the following team conventions:",
        ]

        if self.state.custom_rules:
            lines.append("- **Preferred Conventions:**")
            for cr in self.state.custom_rules:
                lines.append(f"  * [{cr.category}] {cr.rule_text}")

        if has_suppressed:
            lines.append("- **Suppressed Topics (DO NOT report findings on these):**")
            if self.state.suppressed_categories:
                cats = ", ".join(self.state.suppressed_categories)
                lines.append(f"  * Suppressed Categories: {cats}")
            for sp in active_suppressed:
                target = f"Rule `{sp.rule_id}`" if sp.rule_id else f'Pattern "{sp.pattern}"'
                lines.append(f"  * Skip {target} ({sp.category})")

        return "\n".join(lines)

    def save(self, path: str) -> None:
        """Persist state to a JSON file."""
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(self.state.model_dump_json(indent=2))

    def load(self, path: str) -> None:
        """Load state from a JSON file."""
        if not os.path.exists(path):
            logger.debug("Convention memory file %s does not exist. Initializing fresh.", path)
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.state = RepoMemoryState.model_validate(data)
        self.threshold = self.state.dismissal_threshold

    @classmethod
    def load_or_create(
        cls,
        path: str,
        suppression_threshold: int = 2,
    ) -> RepoConventionMemory:
        """Load memory state from path if it exists, otherwise instantiate a new instance."""
        memory = cls(suppression_threshold=suppression_threshold, auto_save_path=path)
        if os.path.exists(path):
            try:
                memory.load(path)
            except Exception as e:
                logger.warning("Failed to load convention memory from %s: %s", path, e)
        return memory
