"""
rl/training/verifier_model.py

Actionability Verifier Model & Calibration for Aion Code Reviewer (TRAIN-02).
Trains and calibrates a discriminator model predicting P(actionable | diff, comment, suggestion) in [0, 1].
Suppresses subjective nitpicks, clean-diff violations, and invalid suggestions.
"""

from __future__ import annotations

import ast
import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from sklearn.linear_model import LogisticRegression

logger = logging.getLogger(__name__)

NITPICK_KEYWORDS = re.compile(
    r"\b(nit:|nitpick|consider renaming|naming convention|redundant comment|"
    r"formatting taste|variable name choice|cosmetic|add docstring|typing hint)\b",
    re.IGNORECASE,
)

ACTIONABLE_KEYWORDS = re.compile(
    r"\b(vulnerability|sql injection|cve|xss|overflow|null pointer|memory leak|"
    r"syntaxerror|attributeerror|typeerror|unhandled exception|infinite loop|deadlock|"
    r"security|race condition|resource leak|bypass|unauthenticated)\b",
    re.IGNORECASE,
)


class ActionabilityFeatureExtractor:
    """Extracts numerical features from review candidates and diff context."""

    CATEGORIES = ["bug", "security", "performance", "style", "nitpick"]

    def extract_features(
        self,
        diff_hunk: str,
        comment_text: str,
        suggestion: Optional[str] = None,
        category: str = "bug",
        is_clean_diff: bool = False,
    ) -> np.ndarray:
        """
        Extract numerical feature vector:
        1. Actionable keyword score
        2. Nitpick keyword score
        3. Comment length log-scaled
        4. Has suggestion indicator
        5. Suggestion syntax validity (AST parseable)
        6. Suggestion non-empty & non-trivial
        7. Clean diff penalty indicator
        8-12. One-hot category indicators
        """
        feats: List[float] = []

        # 1. Actionable keywords
        has_actionable = 1.0 if ACTIONABLE_KEYWORDS.search(comment_text) else 0.0
        feats.append(has_actionable)

        # 2. Nitpick keywords
        has_nitpick = 1.0 if NITPICK_KEYWORDS.search(comment_text) else 0.0
        feats.append(has_nitpick)

        # 3. Comment length
        comment_len = math.log1p(len(comment_text))
        feats.append(comment_len)

        # 4. Has suggestion
        has_sugg = 1.0 if (suggestion and suggestion.strip()) else 0.0
        feats.append(has_sugg)

        # 5. Suggestion syntax validity
        syntax_valid = 0.0
        if has_sugg:
            try:
                ast.parse(suggestion.strip())
                syntax_valid = 1.0
            except SyntaxError:
                syntax_valid = -1.0
        feats.append(syntax_valid)

        # 6. Suggestion length
        sugg_len = math.log1p(len(suggestion.strip())) if has_sugg else 0.0
        feats.append(sugg_len)

        # 7. Clean diff indicator
        feats.append(1.0 if is_clean_diff else 0.0)

        # 8-12. Category one-hot
        cat_lower = str(category).lower()
        for c in self.CATEGORIES:
            feats.append(1.0 if c == cat_lower else 0.0)

        return np.array(feats, dtype=np.float32)


class ActionabilityDatasetBuilder:
    """Extracts balanced positive and negative pairs from training episodes."""

    def __init__(self) -> None:
        self.extractor = ActionabilityFeatureExtractor()

    def extract_pairs_from_episodes(
        self,
        episodes_path: str,
        max_pairs: int = 2000,
    ) -> List[Dict[str, Any]]:
        """
        Extract positive (y=1) and negative (y=0) instances:
        - Positives: Bug/security hits with valid suggestions.
        - Negatives: Comments on clean diffs, subjective nitpicks, invalid suggestions.
        """
        if not os.path.exists(episodes_path):
            raise FileNotFoundError(f"Episodes file not found: {episodes_path}")

        positives: List[Dict[str, Any]] = []
        negatives: List[Dict[str, Any]] = []
        target_per_class = max_pairs // 2

        with open(episodes_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                is_clean = bool(item.get("is_clean_diff", False))
                diff = item.get("diff", "")
                ground_truth = item.get("ground_truth", [])

                if is_clean and len(negatives) < target_per_class:
                    # Clean diff negative example: any comment on clean diff is false alarm
                    negatives.append({
                        "diff_hunk": diff[:500],
                        "comment_text": "Consider reviewing this change.",
                        "suggestion": None,
                        "category": "style",
                        "is_clean_diff": True,
                        "label": 0,
                    })
                elif ground_truth and len(positives) < target_per_class:
                    for gt in ground_truth:
                        desc = gt.get("description", "Bug detected")
                        cat = gt.get("category", "bug")
                        sugg = gt.get("fix_suggestion", "")
                        positives.append({
                            "diff_hunk": diff[:500],
                            "comment_text": desc,
                            "suggestion": sugg,
                            "category": cat,
                            "is_clean_diff": False,
                            "label": 1,
                        })
                        if len(positives) >= target_per_class:
                            break

                # Add synthetic nitpick negative
                if len(negatives) < target_per_class:
                    negatives.append({
                        "diff_hunk": diff[:500],
                        "comment_text": "Nit: consider renaming this variable for better readability.",
                        "suggestion": None,
                        "category": "nitpick",
                        "is_clean_diff": is_clean,
                        "label": 0,
                    })

                if len(positives) >= target_per_class and len(negatives) >= target_per_class:
                    break

        dataset = positives + negatives
        return dataset


class TemperatureCalibrator:
    """Calibrates classifier logits using temperature scaling."""

    def __init__(self, initial_temp: float = 1.0) -> None:
        self.temperature = max(initial_temp, 0.01)

    def fit(self, logits: np.ndarray, y_true: np.ndarray) -> float:
        """
        Find optimal temperature T > 0 minimizing negative log-likelihood via grid search / line search.
        """
        best_t = 1.0
        best_nll = float("inf")

        for t in np.linspace(0.1, 5.0, 100):
            scaled_logits = logits / t
            # Sigmoid probabilities with numerical stability
            probs = 1.0 / (1.0 + np.exp(-np.clip(scaled_logits, -30.0, 30.0)))
            probs = np.clip(probs, 1e-7, 1.0 - 1e-7)
            nll = -np.mean(y_true * np.log(probs) + (1.0 - y_true) * np.log(1.0 - probs))
            if nll < best_nll:
                best_nll = nll
                best_t = t

        self.temperature = float(best_t)
        return self.temperature

    def scale_prob(self, logit: float) -> float:
        """Return calibrated probability from logit."""
        scaled = logit / self.temperature
        return float(1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, scaled)))))


class ActionabilityVerifierModel:
    """
    Discriminator model predicting whether a proposed review comment will be acted upon.
    Calibrated with temperature scaling to ensure low Expected Calibration Error (ECE < 0.05).
    """

    def __init__(self) -> None:
        self.extractor = ActionabilityFeatureExtractor()
        self.classifier = LogisticRegression(C=1.0, max_iter=200, random_state=42)
        self.calibrator = TemperatureCalibrator()
        self.is_fitted = False

    def fit(
        self,
        train_data: List[Dict[str, Any]],
        val_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, float]:
        """
        Fit model on training instances and calibrate temperature on validation set.
        """
        if not train_data:
            raise ValueError("Training data cannot be empty")

        X_train = np.array([
            self.extractor.extract_features(
                diff_hunk=d.get("diff_hunk", ""),
                comment_text=d.get("comment_text", ""),
                suggestion=d.get("suggestion"),
                category=d.get("category", "bug"),
                is_clean_diff=d.get("is_clean_diff", False),
            )
            for d in train_data
        ])
        y_train = np.array([int(d.get("label", 0)) for d in train_data])

        self.classifier.fit(X_train, y_train)
        self.is_fitted = True

        # Validation calibration
        eval_data = val_data or train_data
        X_val = np.array([
            self.extractor.extract_features(
                diff_hunk=d.get("diff_hunk", ""),
                comment_text=d.get("comment_text", ""),
                suggestion=d.get("suggestion"),
                category=d.get("category", "bug"),
                is_clean_diff=d.get("is_clean_diff", False),
            )
            for d in eval_data
        ])
        y_val = np.array([int(d.get("label", 0)) for d in eval_data])

        # Raw logits from decision function
        logits_val = self.classifier.decision_function(X_val)
        temp = self.calibrator.fit(logits_val, y_val)

        # Compute post-calibration probabilities & ECE
        calibrated_probs = [self.calibrator.scale_prob(l) for l in logits_val]
        ece = self.compute_ece(y_val.tolist(), calibrated_probs)

        return {
            "temperature": round(temp, 4),
            "val_ece": round(ece, 4),
            "train_samples": len(train_data),
            "val_samples": len(eval_data),
        }

    def predict_proba(
        self,
        diff_hunk: str,
        comment: str,
        suggestion: Optional[str] = None,
        category: str = "bug",
        is_clean_diff: bool = False,
    ) -> float:
        """
        Predict calibrated probability P(actionable) in [0.0, 1.0].
        """
        if not self.is_fitted:
            # Fallback heuristic if not yet fitted
            if is_clean_diff or NITPICK_KEYWORDS.search(comment):
                return 0.15
            if ACTIONABLE_KEYWORDS.search(comment) or (suggestion and suggestion.strip()):
                return 0.85
            return 0.50

        x = self.extractor.extract_features(
            diff_hunk=diff_hunk,
            comment_text=comment,
            suggestion=suggestion,
            category=category,
            is_clean_diff=is_clean_diff,
        ).reshape(1, -1)

        raw_logit = float(self.classifier.decision_function(x)[0])
        return self.calibrator.scale_prob(raw_logit)

    def compute_ece(
        self,
        y_true: List[int],
        y_prob: List[float],
        n_bins: int = 10,
    ) -> float:
        """
        Compute empirical Expected Calibration Error (ECE) across bins.
        """
        if not y_true or not y_prob:
            return 0.0

        y_t = np.array(y_true)
        y_p = np.array(y_prob)
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        n_samples = len(y_true)

        for i in range(n_bins):
            bin_mask = (y_p >= bin_edges[i]) & (y_p < bin_edges[i + 1])
            if i == n_bins - 1:
                bin_mask = bin_mask | (y_p == bin_edges[i + 1])

            bin_size = np.sum(bin_mask)
            if bin_size > 0:
                bin_acc = np.mean(y_t[bin_mask])
                bin_conf = np.mean(y_p[bin_mask])
                ece += (bin_size / n_samples) * abs(bin_acc - bin_conf)

        return float(ece)

    def save(self, save_path: str) -> None:
        """Serialize model parameters to JSON format."""
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        state = {
            "is_fitted": self.is_fitted,
            "temperature": self.calibrator.temperature,
            "coef": self.classifier.coef_.tolist() if self.is_fitted else [],
            "intercept": self.classifier.intercept_.tolist() if self.is_fitted else [],
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def load(self, load_path: str) -> None:
        """Load model parameters from JSON format."""
        with open(load_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.is_fitted = bool(state.get("is_fitted", False))
        self.calibrator.temperature = float(state.get("temperature", 1.0))
        if self.is_fitted and state.get("coef"):
            self.classifier.coef_ = np.array(state["coef"])
            self.classifier.intercept_ = np.array(state["intercept"])
            self.classifier.classes_ = np.array([0, 1])

