"""
tests/test_ablation_configs_and_runner.py

Verification suite for Plan 11-04 (TRAIN2-04: Ablation Configurations & Notebooks):
- 4 YAML configuration specifications (sft, verifier_filter, grpo, full_stack)
- Kaggle and Google Colab Jupyter notebooks valid JSON structure
- Automated ablation runner execution & comparative results logging
- Full-stack performance superiority over SFT baseline
"""

import json
import os
from pathlib import Path
import pytest
import yaml

from rl.training_v2.ablation_runner import AblationRunner


def test_ablation_yaml_configs():
    """All 4 ablation configs must exist, parse validly, and have distinct ablation toggles."""
    config_dir = Path("configs/training_v2")
    expected_configs = ["sft.yaml", "verifier_filter.yaml", "grpo.yaml", "full_stack.yaml"]

    for cfg_name in expected_configs:
        cfg_path = config_dir / cfg_name
        assert cfg_path.exists(), f"Configuration file {cfg_path} missing"

        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        assert "condition" in cfg
        assert "model" in cfg
        assert "data" in cfg
        assert "ablation_toggles" in cfg

        toggles = cfg["ablation_toggles"]
        if cfg_name == "sft.yaml":
            assert toggles["use_verifier_filter"] is False
            assert toggles["use_grpo"] is False
        elif cfg_name == "verifier_filter.yaml":
            assert toggles["use_verifier_filter"] is True
            assert toggles["use_grpo"] is False
        elif cfg_name == "grpo.yaml":
            assert toggles["use_grpo"] is True
            assert toggles["reward_version"] == "2.0.0"
        elif cfg_name == "full_stack.yaml":
            assert toggles["use_verifier_filter"] is True
            assert toggles["use_grpo"] is True
            assert toggles["sandbox_verification"] is True


def test_notebooks_json_validity():
    """Kaggle and Colab notebooks must be valid Jupyter Notebook JSON files."""
    notebooks_dir = Path("notebooks")
    for nb_name in ["kaggle_training_v2_ablation.ipynb", "colab_training_v2_ablation.ipynb"]:
        nb_path = notebooks_dir / nb_name
        assert nb_path.exists(), f"Notebook {nb_path} missing"

        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)

        assert "cells" in nb
        assert "metadata" in nb
        assert "nbformat" in nb
        assert len(nb["cells"]) >= 4

        # Check cell types
        cell_types = [c.get("cell_type") for c in nb["cells"]]
        assert "markdown" in cell_types
        assert "code" in cell_types


def test_ablation_runner_execution_and_results():
    """AblationRunner must evaluate all 4 conditions and save data/training_v2/ablation_results.json."""
    runner = AblationRunner()
    results = runner.run_all_ablations()

    assert "ablations" in results
    ablations = results["ablations"]
    assert "sft" in ablations
    assert "verifier_filter" in ablations
    assert "grpo" in ablations
    assert "full_stack" in ablations

    # Verify metrics monotonicity & improvements
    sft_metrics = ablations["sft"]
    fs_metrics = ablations["full_stack"]

    assert fs_metrics["f1"] > sft_metrics["f1"], "Full stack F1 must exceed SFT baseline"
    assert fs_metrics["precision"] > sft_metrics["precision"], "Full stack precision must exceed SFT baseline"
    assert fs_metrics["clean_fpr"] < sft_metrics["clean_fpr"], "Full stack clean FPR must be lower than SFT baseline"
    assert fs_metrics["actionability_score"] > sft_metrics["actionability_score"]

    # Verify saved file
    output_file = Path("data/training_v2/ablation_results.json")
    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    assert saved_data["version"] == "2.0.0"
    assert "conclusion" in saved_data
