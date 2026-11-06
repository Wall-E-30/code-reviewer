"""
action/telemetry.py

Anonymized telemetry engine for Aion Code Reviewer.
Enforces strict privacy controls (DATA_POLICY.md):
- Salted SHA-256 hashing for repository and PR identifiers (no plain text names stored).
- Logs candidate volumes, verifier suppression rates, and category confidence vectors.
- Appends to .aion/telemetry.jsonl and writes to GITHUB_STEP_SUMMARY.
- Total opt-out when enable_telemetry is False.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

DEFAULT_TELEMETRY_PATH = ".aion/telemetry.jsonl"
DEFAULT_SALT = "aion-privacy-salt-2026"


def hash_identifier(raw: str, salt: str = DEFAULT_SALT) -> str:
    """
    Compute a one-way cryptographically salted SHA-256 hash of an identifier
    (repository name, PR number, or user ID) to guarantee anonymity.
    """
    if not raw:
        return ""
    salted = f"{salt}:{raw}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


class TelemetryEvent(BaseModel):
    """Anonymized review telemetry event."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    repo_hash: str
    pr_hash: str
    provider: str
    model: str
    candidates_generated: int
    comments_posted: int
    comments_suppressed: int
    finding_categories: List[str] = Field(default_factory=list)
    confidences: List[float] = Field(default_factory=list)
    reactions_summary: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to standard dictionary."""
        return self.model_dump()

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return self.model_dump_json()


class TelemetryLogger:
    """
    Manages telemetry logging to local jsonl ledger and GitHub Actions Step Summary.
    Respects user opt-out preferences.
    """

    def __init__(
        self,
        enabled: bool = True,
        output_path: str = DEFAULT_TELEMETRY_PATH,
        salt: str = DEFAULT_SALT,
    ) -> None:
        self.enabled = enabled
        self.output_path = Path(output_path)
        self.salt = salt

    def log_event(self, event: TelemetryEvent) -> bool:
        """
        Record a telemetry event if telemetry is enabled.

        Returns True if logged, False if skipped due to opt-out.
        """
        if not self.enabled:
            logger.info("Aion Telemetry is disabled by user configuration; skipping event logging.")
            return False

        try:
            # 1. Append to JSONL file
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_path, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")

            # 2. Write to GitHub Step Summary if running in GitHub Actions
            step_summary_path = os.getenv("GITHUB_STEP_SUMMARY")
            if step_summary_path and os.path.exists(os.path.dirname(step_summary_path)):
                self._append_to_step_summary(event, step_summary_path)

            return True
        except Exception as e:
            logger.warning("Failed to record telemetry event: %s", e)
            return False

    def _append_to_step_summary(self, event: TelemetryEvent, path: str) -> None:
        """Render a clean summary block to GitHub Step Summary."""
        try:
            markdown = (
                "\n### 📊 Aion Operational Telemetry\n"
                f"- **Engine**: `{event.provider}` (`{event.model}`)\n"
                f"- **Candidates Evaluated**: `{event.candidates_generated}`\n"
                f"- **Comments Posted**: `{event.comments_posted}` (Suppressed: `{event.comments_suppressed}`)\n"
                f"- **Categories**: {', '.join(f'`{c}`' for c in event.finding_categories) or 'None'}\n"
                "*(Anonymized per [DATA_POLICY.md](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/DATA_POLICY.md))*\n"
            )
            with open(path, "a", encoding="utf-8") as f:
                f.write(markdown)
        except Exception as e:
            logger.debug("Failed to write to GITHUB_STEP_SUMMARY: %s", e)

    def load_events(self) -> List[TelemetryEvent]:
        """Load all recorded telemetry events from the ledger."""
        if not self.output_path.exists():
            return []
        events: List[TelemetryEvent] = []
        with open(self.output_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        events.append(TelemetryEvent.model_validate_json(line_str))
                    except Exception as e:
                        logger.debug("Skipping unparseable telemetry line: %s", e)
        return events

