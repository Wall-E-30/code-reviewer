"""
bench/leaderboard.py

Public Aion-Bench Leaderboard Engine (GROWTH-02).
Manages community benchmark submissions, metric validation, ranking,
and persistent leaderboard state.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

DEFAULT_LEADERBOARD_PATH = os.path.join("data", "leaderboard.json")


class LeaderboardEntry(BaseModel):
    """A verified benchmark evaluation entry for the public Aion-Bench leaderboard."""

    model_id: str = Field(..., description="Unique slug for the model (e.g. aion-qwen2.5-coder-7b-grpo)")
    display_name: str = Field(..., description="Human-readable model name")
    organization: str = Field(..., description="Authoring organization or research lab")
    license: str = Field(..., description="Open-source license or proprietary")
    model_type: str = Field(
        ...,
        description="Type: open-weights, commercial-api, static-tool, or hybrid",
    )
    precision: float = Field(..., ge=0.0, le=1.0, description="Precision score on held-out test split")
    recall: float = Field(..., ge=0.0, le=1.0, description="Recall score on known ground-truth bugs")
    false_positive_rate: float = Field(..., ge=0.0, le=1.0, description="FPR on clean negative diffs")
    nitpick_rate: float = Field(..., ge=0.0, le=1.0, description="Fraction of comments marked as nitpicks")
    avg_latency_ms: float = Field(..., ge=0.0, description="Average review latency per PR diff in ms")
    submission_date: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        description="Date of evaluation submission (YYYY-MM-DD)",
    )
    verified: bool = Field(default=False, description="Whether evaluation was replicated by Aion maintainers")
    replication_recipe: str = Field(
        default="",
        description="URL or command to replicate evaluation results",
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @field_validator("model_type")
    @classmethod
    def validate_model_type(cls, v: str) -> str:
        valid_types = {"open-weights", "commercial-api", "static-tool", "hybrid"}
        norm = v.strip().lower()
        if norm not in valid_types:
            raise ValueError(f"Invalid model_type '{v}'. Must be one of: {sorted(valid_types)}")
        return norm


DEFAULT_BASELINES = [
    LeaderboardEntry(
        model_id="aion-qwen2.5-coder-7b-grpo",
        display_name="Aion Qwen2.5-Coder 7B (GRPO / RLVR)",
        organization="Aion Open Source Project",
        license="Apache-2.0",
        model_type="open-weights",
        precision=0.784,
        recall=0.712,
        false_positive_rate=0.065,
        nitpick_rate=0.038,
        avg_latency_ms=420.0,
        submission_date="2026-11-07",
        verified=True,
        replication_recipe="aion review --model aion-qwen2.5-coder-7b --bench test_split",
    ),
    LeaderboardEntry(
        model_id="claude-3-5-sonnet",
        display_name="Claude 3.5 Sonnet (Prompt Baseline)",
        organization="Anthropic",
        license="Proprietary",
        model_type="commercial-api",
        precision=0.678,
        recall=0.721,
        false_positive_rate=0.146,
        nitpick_rate=0.115,
        avg_latency_ms=1820.0,
        submission_date="2026-11-05",
        verified=True,
        replication_recipe="python -m bench.runner --model claude-3-5-sonnet --split test",
    ),
    LeaderboardEntry(
        model_id="gpt-4o",
        display_name="GPT-4o (Prompt Baseline)",
        organization="OpenAI",
        license="Proprietary",
        model_type="commercial-api",
        precision=0.642,
        recall=0.685,
        false_positive_rate=0.182,
        nitpick_rate=0.141,
        avg_latency_ms=1450.0,
        submission_date="2026-11-05",
        verified=True,
        replication_recipe="python -m bench.runner --model gpt-4o --split test",
    ),
    LeaderboardEntry(
        model_id="deepseek-coder-6.7b-sft",
        display_name="DeepSeek-Coder 6.7B (Base SFT)",
        organization="DeepSeek",
        license="DeepSeek Open License",
        model_type="open-weights",
        precision=0.581,
        recall=0.593,
        false_positive_rate=0.224,
        nitpick_rate=0.189,
        avg_latency_ms=510.0,
        submission_date="2026-11-05",
        verified=True,
        replication_recipe="python -m bench.runner --model deepseek-ai/deepseek-coder-6.7b-instruct --split test",
    ),
    LeaderboardEntry(
        model_id="llama-3.1-8b-instruct",
        display_name="Llama-3.1 8B Instruct",
        organization="Meta AI",
        license="Llama 3.1 Community",
        model_type="open-weights",
        precision=0.526,
        recall=0.554,
        false_positive_rate=0.281,
        nitpick_rate=0.243,
        avg_latency_ms=620.0,
        submission_date="2026-11-05",
        verified=True,
        replication_recipe="python -m bench.runner --model meta-llama/Llama-3.1-8B-Instruct --split test",
    ),
    LeaderboardEntry(
        model_id="ruff-bandit-static",
        display_name="Static Linters (Ruff + Bandit)",
        organization="Astral / PyCQA",
        license="MIT / Apache-2.0",
        model_type="static-tool",
        precision=0.912,
        recall=0.245,
        false_positive_rate=0.021,
        nitpick_rate=0.000,
        avg_latency_ms=45.0,
        submission_date="2026-11-05",
        verified=True,
        replication_recipe="python -m bench.runner --static-only --split test",
    ),
]


class LeaderboardManager:
    """
    Manages loading, validation, ranking, and persistence for the public leaderboard.
    """

    def __init__(self, storage_path: str = DEFAULT_LEADERBOARD_PATH) -> None:
        self.storage_path = storage_path
        self.entries: List[LeaderboardEntry] = []
        self.load_or_seed()

    def load_or_seed(self) -> None:
        """Load entries from disk if present, otherwise initialize with default baselines."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.entries = [LeaderboardEntry.model_validate(item) for item in data]
                return
            except Exception as e:
                logger.warning("Failed to load leaderboard from %s: %s. Using default baselines.", self.storage_path, e)

        self.entries = list(DEFAULT_BASELINES)
        self.save()

    def save(self) -> None:
        """Persist entries to storage file."""
        os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)
        data = [entry.model_dump() for entry in self.entries]
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_ranked_entries(self, model_type: Optional[str] = None) -> List[LeaderboardEntry]:
        """
        Return entries sorted primarily by precision (descending),
        secondarily by false_positive_rate (ascending), and thirdly by recall (descending).
        """
        filtered = self.entries
        if model_type:
            mt = model_type.strip().lower()
            filtered = [e for e in self.entries if e.model_type == mt]

        return sorted(
            filtered,
            key=lambda e: (-e.precision, e.false_positive_rate, -e.recall),
        )

    def submit_entry(self, entry: LeaderboardEntry) -> LeaderboardEntry:
        """
        Validate and ingest a community evaluation submission.
        """
        # Check for existing model_id
        for idx, existing in enumerate(self.entries):
            if existing.model_id == entry.model_id:
                # Replace with updated evaluation
                self.entries[idx] = entry
                self.save()
                return entry

        self.entries.append(entry)
        self.save()
        return entry

    def get_summary_stats(self) -> Dict[str, Any]:
        """Return aggregate summary metrics for public display."""
        ranked = self.get_ranked_entries()
        top_model = ranked[0] if ranked else None
        avg_precision = (
            sum(e.precision for e in self.entries) / len(self.entries)
            if self.entries
            else 0.0
        )

        return {
            "total_models": len(self.entries),
            "open_weights_count": sum(1 for e in self.entries if e.model_type == "open-weights"),
            "commercial_api_count": sum(1 for e in self.entries if e.model_type == "commercial-api"),
            "top_model": top_model.display_name if top_model else "N/A",
            "top_precision": f"{top_model.precision:.1%}" if top_model else "N/A",
            "average_precision": f"{avg_precision:.1%}",
            "benchmark_split": "Aion-Bench Held-Out Test Split (Locked)",
        }

