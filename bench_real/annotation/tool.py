"""
bench_real/annotation/tool.py

Human annotation tool for real-world PR evaluation cases (REAL-02).
Allows independent review of diff candidates, records actionability and category votes,
and serializes independent label files without cross-annotator contamination.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from bench_real.schema import AnnotatorVote, RealBenchmarkCase

logger = logging.getLogger(__name__)


class AnnotationSession:
    """Manages an annotator's independent labeling session."""

    def __init__(
        self,
        annotator_id: str,
        candidates_file: Path | str,
        output_file: Optional[Path | str] = None,
    ) -> None:
        self.annotator_id = annotator_id.strip()
        self.candidates_file = Path(candidates_file)
        self.output_file = Path(output_file or f"bench_real/data/labels_{self.annotator_id}.json")
        self.cases: List[RealBenchmarkCase] = []
        self.labels: Dict[str, Dict[str, Any]] = {}

        self._load_candidates()
        self._load_existing_labels()

    def _load_candidates(self) -> None:
        if not self.candidates_file.exists():
            raise FileNotFoundError(f"Candidates file not found: {self.candidates_file}")
        with open(self.candidates_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.cases = [RealBenchmarkCase(**item) for item in raw]
        logger.info("Loaded %d candidates for annotation by %s", len(self.cases), self.annotator_id)

    def _load_existing_labels(self) -> None:
        if self.output_file.exists():
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    self.labels = json.load(f)
                logger.info("Resumed session with %d existing labels.", len(self.labels))
            except Exception as e:
                logger.warning("Could not read existing labels from %s: %s", self.output_file, e)

    def record_vote(
        self,
        case_id: str,
        actionable: bool,
        category: str = "bug",
        target_line: Optional[int] = None,
        notes: str = "",
    ) -> AnnotatorVote:
        """Records an annotator's vote for a given case."""
        vote = AnnotatorVote(
            annotator_id=self.annotator_id,
            actionable=actionable,
            category=category,
            notes=notes,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        vote_dict = vote.model_dump()
        if target_line is not None:
            vote_dict["target_line"] = target_line

        self.labels[case_id] = vote_dict
        return vote

    def save(self) -> Path:
        """Saves current labels to disk."""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.labels, f, indent=2)
        logger.info("Saved %d labels to %s", len(self.labels), self.output_file)
        return self.output_file

    def get_progress(self) -> Dict[str, int]:
        """Returns labeling progress statistics."""
        return {
            "total_candidates": len(self.cases),
            "labeled_count": len(self.labels),
            "remaining": len(self.cases) - len(self.labels),
        }

    def run_cli_interactive(self) -> None:
        """Runs interactive command line annotation loop."""
        print(f"\n=== Aion Human Annotation Session: {self.annotator_id} ===")
        print(f"Candidates file: {self.candidates_file}")
        print(f"Output file:     {self.output_file}")
        stats = self.get_progress()
        print(f"Progress: {stats['labeled_count']}/{stats['total_candidates']} labeled\n")

        for i, case in enumerate(self.cases, 1):
            if case.case_id in self.labels:
                continue

            print(f"[{i}/{len(self.cases)}] Case: {case.case_id} | Repo: {case.repository}")
            print(f"Source Type: {case.source_type.value} | PR: {case.pr_url or 'N/A'}")
            print("-" * 60)
            print("DIFF HUNK:")
            print(case.diff[:1000])
            print("-" * 60)

            act_input = input("Is this change actionable / does it contain an issue? (y/n/skip/quit): ").strip().lower()
            if act_input == "quit":
                break
            if act_input == "skip":
                continue

            actionable = act_input in ("y", "yes", "1", "true")
            cat = "clean"
            if actionable:
                cat_input = input("Category [bug/security/performance/style] (default: bug): ").strip().lower()
                cat = cat_input or "bug"

            notes = input("Optional notes/rationale: ").strip()

            self.record_vote(case.case_id, actionable=actionable, category=cat, notes=notes)
            self.save()
            print(f"Saved vote for {case.case_id}.\n")

        print("\nSession finished. Current labels saved to:", self.output_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aion bench_real human annotation tool (REAL-02)")
    parser.add_argument("--annotator", required=True, help="Annotator unique identifier (e.g. annotator_1)")
    parser.add_argument("--input", default="bench_real/data/candidates.json", help="Path to candidates.json")
    parser.add_argument("--output", default=None, help="Path to export label JSON file")
    args = parser.parse_args()

    session = AnnotationSession(
        annotator_id=args.annotator,
        candidates_file=args.input,
        output_file=args.output,
    )
    session.run_cli_interactive()


if __name__ == "__main__":
    main()

