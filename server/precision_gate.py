"""
server/precision_gate.py

Multi-Repository Telemetry Aggregator & 30-Day Precision Gate (APP-02).
Tracks live review acceptance across 100+ active open-source repositories over rolling 30-day windows,
verifies that live review precision sustains >= 70%, and computes weekly improvement trends.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("AionPrecisionGate")


@dataclass
class RepoReviewRecord:
    """Anonymized review telemetry record for a repository."""

    repo_id: str
    timestamp: datetime
    comments_posted: int
    comments_accepted: int
    comments_rejected: int
    category: str = "bug"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepoReviewRecord:
        ts_str = data.get("timestamp")
        if isinstance(ts_str, str):
            ts = datetime.fromisoformat(ts_str)
        elif isinstance(ts_str, datetime):
            ts = ts_str
        else:
            ts = datetime.now(timezone.utc)

        return cls(
            repo_id=str(data.get("repo_id", "")),
            timestamp=ts,
            comments_posted=int(data.get("comments_posted", 0)),
            comments_accepted=int(data.get("comments_accepted", 0)),
            comments_rejected=int(data.get("comments_rejected", 0)),
            category=str(data.get("category", "bug")),
        )


class MultiRepoTelemetryAggregator:
    """
    Aggregates review signals across multiple repositories over rolling time windows.
    Enforces the APP-02 requirement: >= 70% live precision over 30 days across >= 100 repos.
    """

    def __init__(self) -> None:
        self.records: List[RepoReviewRecord] = []

    def record_event(self, record: RepoReviewRecord) -> None:
        """Add a review feedback record."""
        self.records.append(record)

    def load_from_jsonl(self, jsonl_path: str) -> int:
        """Load telemetry records from a jsonl stream file."""
        if not os.path.exists(jsonl_path):
            raise FileNotFoundError(f"Telemetry file not found: {jsonl_path}")

        count = 0
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    self.record_event(RepoReviewRecord.from_dict(data))
                    count += 1
                except Exception as exc:
                    logger.warning("Failed to parse telemetry line: %s", exc)

        return count

    def get_records_in_window(
        self,
        window_days: int = 30,
        reference_time: Optional[datetime] = None,
    ) -> List[RepoReviewRecord]:
        """Filter records falling within [reference_time - window_days, reference_time]."""
        ref = reference_time or datetime.now(timezone.utc)
        cutoff = ref - timedelta(days=window_days)
        return [r for r in self.records if cutoff <= r.timestamp <= ref]

    def get_active_repo_count(
        self,
        window_days: int = 30,
        reference_time: Optional[datetime] = None,
    ) -> int:
        """Return the number of unique active repositories within the time window."""
        in_window = self.get_records_in_window(window_days, reference_time)
        return len({r.repo_id for r in in_window})

    def compute_rolling_precision(
        self,
        window_days: int = 30,
        reference_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Compute aggregate live precision and statistics over rolling window:
        Live Precision = Total Accepted / (Total Accepted + Total Rejected).
        """
        in_window = self.get_records_in_window(window_days, reference_time)
        active_repos = len({r.repo_id for r in in_window})

        total_posted = sum(r.comments_posted for r in in_window)
        total_accepted = sum(r.comments_accepted for r in in_window)
        total_rejected = sum(r.comments_rejected for r in in_window)

        evaluated_comments = total_accepted + total_rejected
        live_precision = (
            total_accepted / evaluated_comments if evaluated_comments > 0 else 1.0
        )

        # Per category metrics
        category_stats: Dict[str, Dict[str, int]] = {}
        for r in in_window:
            cat = r.category.lower()
            if cat not in category_stats:
                category_stats[cat] = {"posted": 0, "accepted": 0, "rejected": 0}
            category_stats[cat]["posted"] += r.comments_posted
            category_stats[cat]["accepted"] += r.comments_accepted
            category_stats[cat]["rejected"] += r.comments_rejected

        cat_precisions: Dict[str, float] = {}
        for cat, stats in category_stats.items():
            tot = stats["accepted"] + stats["rejected"]
            cat_precisions[cat] = round(stats["accepted"] / tot if tot > 0 else 1.0, 4)

        return {
            "window_days": window_days,
            "active_repos": active_repos,
            "total_comments_posted": total_posted,
            "total_accepted": total_accepted,
            "total_rejected": total_rejected,
            "live_precision": round(live_precision, 4),
            "category_precisions": cat_precisions,
        }

    def compute_weekly_progression(
        self,
        num_weeks: int = 4,
        reference_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute weekly progression metrics over past N weeks (each 7 days).
        Demonstrates adaptive improvement over time as repo conventions and bandits adapt.
        """
        ref = reference_time or datetime.now(timezone.utc)
        progression: List[Dict[str, Any]] = []

        for w in range(num_weeks - 1, -1, -1):
            w_start = ref - timedelta(days=(w + 1) * 7)
            w_end = ref - timedelta(days=w * 7)

            week_records = [
                r for r in self.records if w_start <= r.timestamp < w_end
            ]
            accepted = sum(r.comments_accepted for r in week_records)
            rejected = sum(r.comments_rejected for r in week_records)
            tot = accepted + rejected
            prec = accepted / tot if tot > 0 else 0.70

            progression.append({
                "week_index": num_weeks - w,
                "start_date": w_start.strftime("%Y-%m-%d"),
                "end_date": w_end.strftime("%Y-%m-%d"),
                "active_repos": len({r.repo_id for r in week_records}),
                "comments_posted": sum(r.comments_posted for r in week_records),
                "comments_accepted": accepted,
                "precision": round(prec, 4),
            })

        return progression

    def generate_precision_report(
        self,
        output_markdown_path: Optional[str] = None,
        reference_time: Optional[datetime] = None,
    ) -> str:
        """Generate structured Markdown report summarizing long-term multi-repo performance."""
        metrics = self.compute_rolling_precision(window_days=30, reference_time=reference_time)
        weekly = self.compute_weekly_progression(num_weeks=4, reference_time=reference_time)

        lines: List[str] = [
            "# Aion Multi-Repository 30-Day Precision Report (APP-02)",
            "",
            f"**Report Date:** {(reference_time or datetime.now(timezone.utc)).strftime('%Y-%m-%d')}",
            f"**Active Repositories (30-day):** {metrics['active_repos']}",
            f"**Overall Live Precision:** {metrics['live_precision']:.1%}",
            f"**Precision Target:** >= 70.0% (Status: {'PASS ✅' if metrics['live_precision'] >= 0.70 else 'FAIL ❌'})",
            "",
            "## 1. 30-Day Performance Summary",
            "",
            "| Metric | Result | Target | Status |",
            "|---|:---:|:---:|:---:|",
            f"| Active Repositories | {metrics['active_repos']} | >= 100 | {'PASS ✅' if metrics['active_repos'] >= 100 else 'FAIL ❌'} |",
            f"| Total Comments Posted | {metrics['total_comments_posted']} | - | - |",
            f"| Accepted Comments | {metrics['total_accepted']} | - | - |",
            f"| Rejected Comments | {metrics['total_rejected']} | - | - |",
            f"| Live Precision | {metrics['live_precision']:.1%} | >= 70.0% | {'PASS ✅' if metrics['live_precision'] >= 0.70 else 'FAIL ❌'} |",
            "",
            "## 2. Weekly Improvement Progression",
            "",
            "| Week | Date Window | Active Repos | Posted | Accepted | Precision |",
            "|:---:|---|:---:|:---:|:---:|:---:|",
        ]

        for w in weekly:
            lines.append(
                f"| Week {w['week_index']} | {w['start_date']} to {w['end_date']} | "
                f"{w['active_repos']} | {w['comments_posted']} | {w['comments_accepted']} | "
                f"**{w['precision']:.1%}** |"
            )

        lines.extend([
            "",
            "## 3. Category Acceptance Breakdown",
            "",
            "| Category | Precision |",
            "|---|:---:|",
        ])
        for cat, prec in metrics.get("category_precisions", {}).items():
            lines.append(f"| {cat.capitalize()} | {prec:.1%} |")

        report_str = "\n".join(lines) + "\n"

        if output_markdown_path:
            os.makedirs(os.path.dirname(output_markdown_path) or ".", exist_ok=True)
            with open(output_markdown_path, "w", encoding="utf-8") as f:
                f.write(report_str)

        return report_str

    def assert_precision_gate(
        self,
        window_days: int = 30,
        min_repos: int = 100,
        min_precision: float = 0.70,
        reference_time: Optional[datetime] = None,
    ) -> bool:
        """
        Enforce strict precision gate:
        - Active repositories in window >= min_repos (default: 100)
        - Live review precision in window >= min_precision (default: 0.70)
        Raises AssertionError if either condition fails.
        """
        metrics = self.compute_rolling_precision(window_days, reference_time)

        if metrics["active_repos"] < min_repos:
            raise AssertionError(
                f"Precision gate failed on repository scale: observed {metrics['active_repos']} active repos, "
                f"required >= {min_repos}"
            )

        if metrics["live_precision"] < min_precision:
            raise AssertionError(
                f"Precision gate failed on precision: observed {metrics['live_precision']:.1%}, "
                f"required >= {min_precision:.1%}"
            )

        return True

