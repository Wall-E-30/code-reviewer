"""
rl/bandit.py

Adaptive Per-Category Bandit for Aion Code Reviewer (FLY-02, HARD-05).
Note: This is a per-category Beta-Bernoulli Thompson Sampling optimizer, NOT a contextual bandit,
as it does not condition on per-pull feature vectors.
Dynamically adjusts category-specific confidence thresholds theta_c in [0.50, 0.95]
based on maintainer reaction signals (resolved, dismissed, upvotes, downvotes).

Implements Thompson Sampling / Beta-Bernoulli updates:
- Resolving a comment or +1/rocket: positive reward -> decreases threshold (increases posting willingness).
- Dismissing a comment or -1/confused: negative reward -> elevates threshold (demands higher model certainty).
- Bounds strictly enforced: thresholds never drop below 0.50 or exceed 0.95.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = ["bug", "security", "performance", "style"]
MIN_THRESHOLD = 0.50
MAX_THRESHOLD = 0.95
DEFAULT_INITIAL_THRESHOLD = 0.70

# Prior parameters (alpha=5.0, beta=4.0 yields exactly 0.70 initial threshold with range [0.50, 0.95])
DEFAULT_ALPHA = 5.0
DEFAULT_BETA = 4.0


class CategoryArmState(BaseModel):
    """Maintainer reaction state and parameters for a single review finding category."""

    alpha: float = DEFAULT_ALPHA
    beta: float = DEFAULT_BETA
    pulls: int = 0
    total_reward: float = 0.0
    last_reward: Optional[float] = None
    updated_at: float = Field(default_factory=time.time)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class BanditState(BaseModel):
    """Serialized state containing arms for all categories."""

    categories: Dict[str, CategoryArmState] = Field(default_factory=dict)
    min_threshold: float = MIN_THRESHOLD
    max_threshold: float = MAX_THRESHOLD

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class CategoryBandit:
    """
    Online Multi-Armed Bandit managing confidence thresholds per finding category (FLY-02, HARD-05).
    Per-Category Beta-Bernoulli Thompson Sampling threshold optimizer with strict boundary clamps [0.50, 0.95].
    """

    def __init__(
        self,
        categories: Optional[List[str]] = None,
        min_threshold: float = MIN_THRESHOLD,
        max_threshold: float = MAX_THRESHOLD,
        auto_save_path: Optional[str] = None,
    ) -> None:
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.auto_save_path = auto_save_path

        cats = categories or DEFAULT_CATEGORIES
        self.state = BanditState(
            min_threshold=min_threshold,
            max_threshold=max_threshold,
            categories={
                cat.lower(): CategoryArmState(alpha=DEFAULT_ALPHA, beta=DEFAULT_BETA)
                for cat in cats
            },
        )

    def _ensure_category(self, category: str) -> str:
        """Normalize category name and initialize arm if not present."""
        norm_cat = (category or "general").strip().lower()
        if norm_cat not in self.state.categories:
            self.state.categories[norm_cat] = CategoryArmState(
                alpha=DEFAULT_ALPHA, beta=DEFAULT_BETA
            )
        return norm_cat

    def get_threshold(self, category: str, sample: bool = False) -> float:
        """
        Compute the current posting confidence threshold theta_c in [0.50, 0.95].

        Parameters:
            category: Finding category ('bug', 'security', 'performance', 'style', etc.)
            sample: If True, draws from posterior Beta(alpha, beta) using Thompson Sampling.
                    If False, uses posterior mean E[p] = alpha / (alpha + beta).

        Returns:
            Confidence threshold float clamped in [min_threshold, max_threshold].
        """
        cat = self._ensure_category(category)
        arm = self.state.categories[cat]

        if sample:
            # Thompson Sampling draw
            p = random.betavariate(max(0.1, arm.alpha), max(0.1, arm.beta))
        else:
            # Expected posterior acceptance rate
            p = arm.alpha / (arm.alpha + arm.beta)

        # Higher maintainer acceptance probability p -> Lower threshold required
        thresh_range = self.max_threshold - self.min_threshold
        raw_threshold = self.max_threshold - (p * thresh_range)

        # Enforce strict bounds
        clamped = max(self.min_threshold, min(self.max_threshold, raw_threshold))
        return round(clamped, 4)

    def get_all_thresholds(self, sample: bool = False) -> Dict[str, float]:
        """Return confidence thresholds for all tracked categories."""
        return {
            cat: self.get_threshold(cat, sample=sample)
            for cat in list(self.state.categories.keys())
        }

    def update(self, category: str, reward: float) -> float:
        """
        Update bandit parameters based on maintainer feedback signal.

        Parameters:
            category: Finding category
            reward: Maintainer feedback signal:
                    +1.0: Resolved comment or positive reaction (+1, rocket, heart)
                    -1.5: Dismissed comment or negative reaction (-1, confused)
                    (or any numeric reward)

        Returns:
            New confidence threshold for the category.
        """
        cat = self._ensure_category(category)
        arm = self.state.categories[cat]

        arm.pulls += 1
        arm.total_reward += reward
        arm.last_reward = reward
        arm.updated_at = time.time()

        if reward > 0:
            # Positive signal: increase alpha -> raises acceptance probability p -> lowers threshold
            arm.alpha += reward
        elif reward < 0:
            # Negative signal: increase beta -> lowers acceptance probability p -> raises threshold
            arm.beta += abs(reward)

        if self.auto_save_path:
            self.save(self.auto_save_path)

        new_thresh = self.get_threshold(cat, sample=False)
        logger.debug(
            "Bandit updated category '%s': reward=%.2f, alpha=%.2f, beta=%.2f -> threshold=%.4f",
            cat,
            reward,
            arm.alpha,
            arm.beta,
            new_thresh,
        )
        return new_thresh

    def save(self, path: str) -> None:
        """Persist bandit state to a JSON file."""
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(self.state.model_dump_json(indent=2))

    def load(self, path: str) -> None:
        """Load bandit state from a JSON file."""
        if not os.path.exists(path):
            logger.debug("Bandit state file %s does not exist. Initializing fresh.", path)
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.state = BanditState.model_validate(data)
        self.min_threshold = self.state.min_threshold
        self.max_threshold = self.state.max_threshold

    @classmethod
    def load_or_create(
        cls,
        path: str,
        categories: Optional[List[str]] = None,
    ) -> CategoryBandit:
        """Load bandit state from path if it exists, otherwise initialize fresh."""
        bandit = cls(categories=categories, auto_save_path=path)
        if os.path.exists(path):
            try:
                bandit.load(path)
            except Exception as e:
                logger.warning("Failed to load bandit state from %s: %s", path, e)
        return bandit
