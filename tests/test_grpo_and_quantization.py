"""
tests/test_grpo_and_quantization.py

Unit and integration tests for GRPO policy optimization loop, bootstrap evaluator,
clean-diff FPR gate, and model quantization & release packaging (TRAIN-03, TRAIN-04):
- Group-Relative advantage standardization
- Clean-diff penalty driving false-positive rate < 10%
- GRPO policy optimization training step
- 1,000-resample bootstrap confidence intervals and statistical significance
- Model quantizer LoRA merge, GGUF/AWQ export, and Ollama Modelfile generation
"""

import json
import os
import tempfile
import pytest

from bench.schema import BenchmarkCase, BenchmarkMetrics, CaseEvaluation, FindingCategory, FindingSeverity, GroundTruthFinding, ReviewComment
from rl.training.bootstrap_eval import BootstrapEvaluator
from rl.training.grpo import GRPOConfig, GRPOTrainer, compute_group_advantages
from rl.training.quantize import ModelQuantizer


def test_grpo_advantage_normalization():
    """Verify group-relative advantage normalization and zero-variance handling."""
    # Varied rewards
    rewards = [1.5, -0.75, 0.5, -1.5]
    advantages = compute_group_advantages(rewards)
    assert len(advantages) == 4
    # Standardized mean should be zero
    assert abs(sum(advantages)) < 1e-4
    # Highest reward should have highest advantage
    assert advantages[0] > advantages[1]
    assert advantages[0] > advantages[2]
    assert advantages[0] > advantages[3]

    # Zero variance rewards (all performed identically)
    uniform_rewards = [1.0, 1.0, 1.0, 1.0]
    zero_adv = compute_group_advantages(uniform_rewards)
    assert zero_adv == [0.0, 0.0, 0.0, 0.0]


def test_clean_diff_heavy_penalty():
    """Verify that comments on clean diffs receive strong penalties while empty comments receive bonus."""
    trainer = GRPOTrainer()
    clean_case = BenchmarkCase(
        case_id="clean-test-01",
        repository="org/repo",
        language="python",
        file_path="app.py",
        original_code="x = 1\n",
        modified_code="x = 2\n",
        diff="@@ -1 +1 @@\n-x = 1\n+x = 2\n",
        split="dev",
        is_clean_diff=True,
    )

    # Empty review on clean diff -> bonus
    r_empty = trainer.evaluate_candidate_review(clean_case, [])
    assert r_empty > 0.0

    # Spurious comments on clean diff -> heavy penalty
    cand = ReviewComment(
        file_path="app.py",
        line_number=1,
        category=FindingCategory.STYLE,
        comment="Nit: format style",
        suggestion=None,
        confidence=0.80,
    )
    r_violation = trainer.evaluate_candidate_review(clean_case, [cand])
    assert r_violation <= -1.50
    assert r_empty > r_violation


def test_grpo_training_step():
    """Verify a complete GRPO rollout step over a batch of cases."""
    trainer = GRPOTrainer(GRPOConfig(group_size=4))

    clean_case = BenchmarkCase(
        case_id="c-clean",
        repository="org/repo",
        language="python",
        file_path="clean.py",
        original_code="a = 1\n",
        modified_code="a = 2\n",
        diff="@@ -1 +1 @@",
        split="dev",
        is_clean_diff=True,
    )

    bug_case = BenchmarkCase(
        case_id="c-bug",
        repository="org/repo",
        language="python",
        file_path="vuln.py",
        original_code="safe()\n",
        modified_code="eval(input)\n",
        diff="@@ -1 +1 @@\n-safe()\n+eval(input)\n",
        split="dev",
        is_clean_diff=False,
        ground_truth=[
            GroundTruthFinding(
                finding_id="f1",
                line_start=1,
                line_end=1,
                category=FindingCategory.SECURITY,
                severity=FindingSeverity.CRITICAL,
                description="Unsafe eval execution",
                file_path="vuln.py",
                fix_suggestion="safe()\n",
            )
        ],
    )

    res = trainer.train_step([clean_case, bug_case])
    assert res["batch_cases"] == 2
    assert res["total_trajectories"] == 8
    assert "policy_loss" in res
    assert "kl_divergence" in res
    assert "total_loss" in res
    assert "clean_diff_fpr" in res


def test_bootstrap_confidence_interval_computation():
    """Verify 1,000-resample bootstrap computation and statistical significance detection."""
    evaluator = BootstrapEvaluator()

    # Create synthetic baseline evaluations (lower precision)
    baseline_evals = [
        CaseEvaluation(
            case_id=f"b-{i}",
            comments_posted=2,
            true_positives=1 if i % 2 == 0 else 0,
            false_positives=1 if i % 2 == 0 else 2,
            false_negatives=0,
            is_clean_diff=(i % 3 == 0),
            clean_diff_violation=(i % 3 == 0),
            matched_findings=[],
            duration_ms=10.0,
            nitpick_comments=1,
        )
        for i in range(40)
    ]

    # Create synthetic candidate evaluations (higher precision, zero clean violations)
    candidate_evals = [
        CaseEvaluation(
            case_id=f"b-{i}",
            comments_posted=1 if not (i % 3 == 0) else 0,
            true_positives=1 if not (i % 3 == 0) else 0,
            false_positives=0,
            false_negatives=0,
            is_clean_diff=(i % 3 == 0),
            clean_diff_violation=False,
            matched_findings=[],
            duration_ms=8.0,
            nitpick_comments=0,
        )
        for i in range(40)
    ]

    res = evaluator.run_bootstrap_comparison(
        baseline_evals=baseline_evals,
        candidate_evals=candidate_evals,
        n_resamples=200,
        alpha=0.05,
    )

    assert "delta_precision_mean" in res
    assert res["delta_precision_mean"] > 0.0
    assert "delta_precision_ci" in res
    assert res["delta_precision_ci"][0] > 0.0, "Expected lower bound of 95% CI > 0"
    assert res["statistically_significant_gain"] is True
    assert res["delta_fpr_mean"] < 0.0  # FPR decreased significantly


def test_clean_diff_fpr_gate_enforcement():
    """Verify clean-diff FPR gate passes when FPR < 10% and fails when FPR >= 10%."""
    evaluator = BootstrapEvaluator()

    passing_metrics = BenchmarkMetrics(
        split="dev",
        total_cases=100,
        clean_cases=30,
        buggy_cases=70,
        precision=0.85,
        recall=0.75,
        false_positive_rate=0.065,  # 6.5% < 10%
        avg_comments_per_pr=3.5,
        nitpick_rate=0.02,
        avg_latency_ms=15.0,
        total_duration_sec=1.5,
    )
    assert evaluator.assert_clean_diff_fpr_gate(passing_metrics, max_fpr=0.10) is True

    failing_metrics = BenchmarkMetrics(
        split="dev",
        total_cases=100,
        clean_cases=30,
        buggy_cases=70,
        precision=0.70,
        recall=0.70,
        false_positive_rate=0.12,  # 12% >= 10%
        avg_comments_per_pr=4.0,
        nitpick_rate=0.05,
        avg_latency_ms=15.0,
        total_duration_sec=1.5,
    )
    with pytest.raises(AssertionError) as exc_info:
        evaluator.assert_clean_diff_fpr_gate(failing_metrics, max_fpr=0.10)
    assert "Clean-diff FPR gate failed" in str(exc_info.value)


def test_quantizer_lora_merge_and_modelfile_generation():
    """Verify LoRA weight merge simulation and Ollama Modelfile output."""
    quantizer = ModelQuantizer()

    with tempfile.TemporaryDirectory() as tmpdir:
        merged_dir = os.path.join(tmpdir, "merged")
        modelfile_path = os.path.join(tmpdir, "Modelfile")

        # 1. Merge
        merge_res = quantizer.merge_lora_weights(
            base_model_name_or_path="Qwen/Qwen2.5-Coder-1.5B-Instruct",
            lora_adapter_path="models/test_adapter",
            output_path=merged_dir,
            dry_run=True,
        )
        assert merge_res["status"] == "success"
        assert os.path.exists(os.path.join(merged_dir, "config.json"))

        # 2. Modelfile
        content = quantizer.generate_ollama_modelfile(
            gguf_file_path="./aion-coder-1.5b-q4_k_m.gguf",
            modelfile_dest=modelfile_path,
        )
        assert os.path.exists(modelfile_path)
        assert "FROM ./aion-coder-1.5b-q4_k_m.gguf" in content
        assert "PARAMETER temperature 0.2" in content
        assert "<|im_end|>" in content


def test_quantizer_gguf_and_awq_export():
    """Verify GGUF binary magic header and AWQ config export."""
    quantizer = ModelQuantizer()

    with tempfile.TemporaryDirectory() as tmpdir:
        gguf_path = os.path.join(tmpdir, "model.gguf")
        awq_dir = os.path.join(tmpdir, "awq")

        # GGUF export
        gguf_res = quantizer.export_gguf(
            merged_model_path=tmpdir,
            output_gguf_path=gguf_path,
            quant_type="Q4_K_M",
        )
        assert gguf_res["status"] == "success"
        assert os.path.exists(gguf_path)
        with open(gguf_path, "rb") as f:
            header = f.read(4)
            assert header == b"GGUF"

        # Unsupported GGUF type raises ValueError
        with pytest.raises(ValueError):
            quantizer.export_gguf(tmpdir, gguf_path, quant_type="INVALID_TYPE")

        # AWQ export
        awq_res = quantizer.export_awq(
            merged_model_path=tmpdir,
            output_awq_path=awq_dir,
            bits=4,
        )
        assert awq_res["status"] == "success"
        assert os.path.exists(os.path.join(awq_dir, "quant_config.json"))
        with open(os.path.join(awq_dir, "quant_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
            assert cfg["bits"] == 4
            assert cfg["quant_method"] == "awq"

