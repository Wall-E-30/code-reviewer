"""
rl/training/formatter.py

ChatML instruction dataset formatter for Aion code reviewer training (TRAIN-01).
Transforms raw training episodes (bugs, clean negatives, replays) into standardized
instruction-tuning conversation format suitable for open code models (e.g., Qwen2.5-Coder).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Aion, an expert automated code reviewer. "
    "Analyze the pull request diff, modified file context, and repository conventions.\n"
    "Post at most 5 high-impact inline comments with actionable replacement code. "
    "If the diff is clean or defect-free, emit an empty review: {\"comments\": []}."
)


class ChatMLFormatter:
    """Formats training episodes into ChatML instruction-following examples."""

    def __init__(self, system_prompt: str = SYSTEM_PROMPT) -> None:
        self.system_prompt = system_prompt

    def format_episode(self, episode_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a raw episode dictionary into a 3-turn ChatML conversation:
        - System: Role instructions, precision constraints, format specifications.
        - User: Conventions, file path, language, diff, and modified code.
        - Assistant: Structured JSON review payload.
        """
        file_path = episode_dict.get("file_path", "unknown")
        language = episode_dict.get("language", "unknown")
        diff = episode_dict.get("diff", "")
        file_content = episode_dict.get("file_content", "")
        is_clean_diff = bool(episode_dict.get("is_clean_diff", False))
        active_conventions = episode_dict.get("active_conventions", [])

        # Format conventions section
        if active_conventions:
            conv_str = "\n".join(f"- {c}" for c in active_conventions)
        else:
            conv_str = "None specified. Follow standard best practices."

        user_content = (
            f"REPOSITORY CONVENTIONS:\n{conv_str}\n\n"
            f"FILE: {file_path} ({language})\n"
            f"DIFF:\n{diff}\n\n"
            f"MODIFIED FILE CONTENT:\n{file_content}"
        )

        ground_truth = episode_dict.get("ground_truth", [])

        # Negative control: clean diff or no defects must emit empty array
        if is_clean_diff or not ground_truth:
            assistant_payload = {"comments": []}
        else:
            comments: List[Dict[str, Any]] = []
            for gt in ground_truth:
                if isinstance(gt, dict):
                    line_start = gt.get("line_start", 1)
                    category = gt.get("category", "bug")
                    desc = gt.get("description", "Potential defect detected")
                    suggestion = gt.get("fix_suggestion")
                else:
                    line_start = getattr(gt, "line_start", 1)
                    cat_val = getattr(gt, "category", "bug")
                    category = cat_val.value if hasattr(cat_val, "value") else str(cat_val)
                    desc = getattr(gt, "description", "Potential defect detected")
                    suggestion = getattr(gt, "fix_suggestion", None)

                comment_item: Dict[str, Any] = {
                    "line_number": int(line_start),
                    "category": str(category).lower(),
                    "comment": str(desc),
                }
                if suggestion:
                    comment_item["suggestion"] = str(suggestion)
                comments.append(comment_item)

            # Cap at at most 5 comments per specification
            assistant_payload = {"comments": comments[:5]}

        assistant_content = json.dumps(assistant_payload, indent=2)

        return {
            "case_id": episode_dict.get("case_id", ""),
            "language": language,
            "is_clean_diff": is_clean_diff,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ],
        }

    def convert_stream_to_sft_jsonl(
        self,
        input_jsonl_path: str,
        output_jsonl_path: str,
        max_records: Optional[int] = None,
    ) -> int:
        """
        Stream episodes from disk, format into ChatML records, and write to output file.
        Returns the number of records converted.
        """
        if not os.path.exists(input_jsonl_path):
            raise FileNotFoundError(f"Input stream not found at {input_jsonl_path}")

        os.makedirs(os.path.dirname(output_jsonl_path) or ".", exist_ok=True)
        count = 0

        with open(input_jsonl_path, "r", encoding="utf-8") as fin, open(
            output_jsonl_path, "w", encoding="utf-8"
        ) as fout:
            for line in fin:
                if not line.strip():
                    continue
                try:
                    episode = json.loads(line)
                    record = self.format_episode(episode)
                    fout.write(json.dumps(record) + "\n")
                    count += 1
                    if max_records is not None and count >= max_records:
                        break
                except Exception as exc:
                    logger.warning("Failed to format episode line: %s", exc)

        return count

