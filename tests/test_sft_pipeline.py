"""
tests/test_sft_pipeline.py

Unit and integration tests for SFT warm-start training pipeline (TRAIN-01):
- ChatML formatting of clean and buggy episodes
- Stream conversion from raw episodes to instruction tuning dataset
- TrainingConfig defaults and serializability
- SFTWarmStartTrainer dry-run execution and artifact saving
- Diff comprehension and format adherence evaluation
"""

import json
import os
import tempfile
import pytest

from rl.training.config import TrainingConfig
from rl.training.formatter import ChatMLFormatter
from rl.training.sft import SFTWarmStartTrainer


def test_chatml_formatting_clean_diff():
    """Verify that clean diff episodes are formatted with empty comments array."""
    formatter = ChatMLFormatter()
    episode = {
        "case_id": "clean-case-01",
        "file_path": "services/auth.py",
        "language": "python",
        "diff": "@@ -1,2 +1,2 @@\n-x = 1\n+x = 2\n",
        "file_content": "x = 2\n",
        "is_clean_diff": True,
        "ground_truth": [],
        "active_conventions": ["Use type hints"],
    }

    formatted = formatter.format_episode(episode)
    assert formatted["case_id"] == "clean-case-01"
    assert formatted["is_clean_diff"] is True
    assert len(formatted["messages"]) == 3

    user_msg = formatted["messages"][1]["content"]
    assert "services/auth.py" in user_msg
    assert "Use type hints" in user_msg

    assistant_msg = formatted["messages"][2]["content"]
    parsed = json.loads(assistant_msg)
    assert parsed == {"comments": []}


def test_chatml_formatting_bug_injection():
    """Verify that bug injection episodes serialize findings with line anchors and suggestions."""
    formatter = ChatMLFormatter()
    episode = {
        "case_id": "vuln-case-01",
        "file_path": "api/users.py",
        "language": "python",
        "diff": "@@ -5,1 +5,1 @@\n-safe_call()\n+eval(user_input)\n",
        "file_content": "eval(user_input)\n",
        "is_clean_diff": False,
        "ground_truth": [
            {
                "line_start": 5,
                "category": "security",
                "description": "Unsafe dynamic code execution via eval",
                "fix_suggestion": "safe_call(user_input)\n",
            }
        ],
    }

    formatted = formatter.format_episode(episode)
    assert formatted["is_clean_diff"] is False
    assistant_msg = formatted["messages"][2]["content"]
    parsed = json.loads(assistant_msg)
    assert "comments" in parsed
    assert len(parsed["comments"]) == 1

    comment = parsed["comments"][0]
    assert comment["line_number"] == 5
    assert comment["category"] == "security"
    assert "eval" in comment["comment"]
    assert "safe_call" in comment["suggestion"]


def test_stream_conversion_sample():
    """Verify converting an episodes stream to SFT jsonl file."""
    formatter = ChatMLFormatter()
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = os.path.join(tmpdir, "episodes.jsonl")
        output_file = os.path.join(tmpdir, "sft.jsonl")

        # Write 5 sample raw episodes
        sample_episodes = [
            {
                "case_id": f"ep-{i}",
                "file_path": "main.py",
                "language": "python",
                "diff": "@@ -1 +1 @@\n-a\n+b\n",
                "file_content": "b = 1\n",
                "is_clean_diff": (i % 2 == 0),
                "ground_truth": [] if (i % 2 == 0) else [{"line_start": 1, "category": "bug", "description": "err"}],
            }
            for i in range(5)
        ]

        with open(input_file, "w", encoding="utf-8") as f:
            for ep in sample_episodes:
                f.write(json.dumps(ep) + "\n")

        converted_count = formatter.convert_stream_to_sft_jsonl(input_file, output_file)
        assert converted_count == 5
        assert os.path.exists(output_file)

        with open(output_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f]
            assert len(lines) == 5
            for line in lines:
                assert "messages" in line
                assert len(line["messages"]) == 3


def test_sft_config_defaults():
    """Verify default hyperparameters and configuration dict conversion."""
    cfg = TrainingConfig()
    assert cfg.base_model_name == "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    assert cfg.lora_r == 16
    assert cfg.lora_alpha == 32
    assert cfg.learning_rate == 2e-4
    assert cfg.max_seq_length == 2048

    d = cfg.to_dict()
    assert d["base_model_name"] == cfg.base_model_name

    cfg2 = TrainingConfig.from_dict(d)
    assert cfg2.lora_r == 16


def test_sft_dry_run_training_execution():
    """Verify SFT trainer runs in dry_run mode, executes, and writes artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_data = os.path.join(tmpdir, "train.jsonl")
        out_dir = os.path.join(tmpdir, "model_out")

        # Create dummy training data
        with open(input_data, "w", encoding="utf-8") as f:
            for i in range(3):
                f.write(
                    json.dumps(
                        {
                            "case_id": f"c-{i}",
                            "file_path": "app.py",
                            "language": "python",
                            "diff": "@@ -1 +1 @@",
                            "file_content": "x = 1\n",
                            "is_clean_diff": True,
                            "ground_truth": [],
                        }
                    )
                    + "\n"
                )

        cfg = TrainingConfig(dry_run=True, max_samples=3)
        trainer = SFTWarmStartTrainer(cfg)
        summary = trainer.train(input_data, out_dir)

        assert summary["status"] == "completed"
        assert summary["train_samples"] == 3
        assert "train_loss" in summary
        assert os.path.exists(os.path.join(out_dir, "adapter_config.json"))
        assert os.path.exists(os.path.join(out_dir, "training_summary.json"))


def test_diff_comprehension_format_adherence():
    """Verify evaluation of format validity, suggestion syntax, and clean compliance."""
    trainer = SFTWarmStartTrainer()
    formatter = ChatMLFormatter()

    ep_clean = formatter.format_episode(
        {
            "case_id": "c-clean",
            "file_path": "a.py",
            "language": "python",
            "diff": "@@",
            "file_content": "pass\n",
            "is_clean_diff": True,
            "ground_truth": [],
        }
    )

    ep_bug = formatter.format_episode(
        {
            "case_id": "c-bug",
            "file_path": "b.py",
            "language": "python",
            "diff": "@@",
            "file_content": "eval(x)\n",
            "is_clean_diff": False,
            "ground_truth": [
                {
                    "line_start": 1,
                    "category": "security",
                    "description": "vuln",
                    "fix_suggestion": "safe(x)\n",
                }
            ],
        }
    )

    metrics = trainer.evaluate_diff_comprehension([ep_clean, ep_bug])
    assert metrics["format_validity_rate"] == 1.0
    assert metrics["clean_diff_compliance"] == 1.0
    assert metrics["suggestion_syntax_validity"] == 1.0
    assert metrics["mean_comments_per_pr"] == 0.5

