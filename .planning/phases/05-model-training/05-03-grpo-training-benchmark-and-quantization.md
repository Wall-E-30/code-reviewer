---
phase: 05-model-training
plan: 03
type: execute
wave: 3
depends_on:
  - 05-01
  - 05-02
files_modified:
  - rl/training/grpo.py
  - rl/training/bootstrap_eval.py
  - rl/training/quantize.py
  - models/Modelfile
  - models/MODEL_CARD.md
  - tests/test_grpo_and_quantization.py
autonomous: true
requirements:
  - TRAIN-03
  - TRAIN-04
must_haves:
  truths:
    - GRPO policy optimization loop samples groups of candidate reviews per diff from ReviewEnv and computes standardized relative advantages without needing a separate critic network.
    - Policy optimization aggressively penalizes any comments emitted on clean diffs, driving clean-diff false-positive rate strictly below 10%.
    - Bootstrap evaluation on held-out test cases executes 1,000 resamples to verify statistically significant precision improvement (95% CI lower bound > 0).
    - Model export merges LoRA weights and generates quantized GGUF (Q4_K_M, Q5_K_M) and AWQ formats with Ollama Modelfile and Hugging Face model card.
  artifacts:
    - rl/training/grpo.py
    - rl/training/bootstrap_eval.py
    - rl/training/quantize.py
    - models/Modelfile
    - models/MODEL_CARD.md
    - tests/test_grpo_and_quantization.py
  key_links:
    - rl/training/grpo.py uses ReviewEnv (rl/env.py) and VerifiableRewardCalculator (rl/reward.py) from Phase 4, initialized with the SFT model from Plan 05-01 and verifier from Plan 05-02.
    - rl/training/bootstrap_eval.py validates against Aion-Bench metrics schema (bench/schema.py).
    - rl/training/quantize.py produces final deployable artifacts for Ollama and community release.
---

<objective>
Implement the Group-Relative Policy Optimization (GRPO / RLVR) loop over `ReviewEnv`, enforce the clean-diff FPR $<10\%$ gate, conduct bootstrap confidence interval validation on held-out test splits, and export quantized GGUF/AWQ models with Ollama `Modelfile` and Hugging Face documentation (`TRAIN-03`, `TRAIN-04`).

Purpose: Deliver the core RL-driven competitive advantage of Aion: high precision, zero hallucinated comments on clean PRs, and verifiable code improvements packaged for local and open-source inference.
Output: `rl/training/grpo.py`, `rl/training/bootstrap_eval.py`, `rl/training/quantize.py`, `models/Modelfile`, `models/MODEL_CARD.md`, and test suites.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-model-training/RESEARCH.md
@rl/env.py
@rl/reward.py
@rl/training/sft.py
@rl/training/verifier_model.py
@bench/schema.py
@bench/evaluator/metrics.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement GRPO Advantage Computation and Group Sampling Loop</name>
  <files>rl/training/grpo.py</files>
  <action>
1. In `rl/training/grpo.py`:
   - Implement `GRPOConfig` dataclass:
     - Group size: `group_size: int = 4` (or 8 for larger batches).
     - Clip ratio: `clip_eps: float = 0.2`.
     - KL penalty coefficient: `beta_kl: float = 0.04`.
     - Learning rate: `learning_rate: float = 1e-5`.
     - Epochs per rollout: `epochs_per_step: int = 1`.
     - Clean diff penalty multiplier: `clean_penalty_weight: float = 1.5`.
     - Simulation / dry-run mode: `dry_run: bool = False`.
   - Implement `compute_group_advantages(rewards: List[float], eps: float = 1e-8) -> List[float]`:
     - Computes mean $\bar{r}$ and standard deviation $\sigma_r$ across group rewards.
     - Normalizes: $A_i = (r_i - \bar{r}) / (\sigma_r + \epsilon)$.
     - Handles degenerate zero-variance case gracefully ($A_i = 0.0$).
   - Implement `GRPOTrainer`:
     - Connects with `ReviewEnv` (`rl/env.py`) and `VerifiableRewardCalculator` (`rl/reward.py`).
     - `sample_group(task: BenchmarkCase, group_size: int) -> List[ReviewTrajectory]`:
       - Generates $G$ candidate review responses for given PR diff.
     - `compute_loss(logprobs: torch.Tensor, old_logprobs: torch.Tensor, ref_logprobs: torch.Tensor, advantages: torch.Tensor) -> torch.Tensor`:
       - Calculates clipped surrogate objective with Schulman KL penalty against reference policy.
     - `train_step(batch_cases: List[BenchmarkCase]) -> Dict[str, float]`:
       - Samples groups, computes verifiable rewards, normalizes advantages, updates policy parameters, and records metrics.
  </action>
  <verify>
python -c "from rl.training.grpo import compute_group_advantages; adv = compute_group_advantages([1.5, -0.75, 0.5, -1.5]); assert len(adv) == 4 and abs(sum(adv)) < 1e-5; print('GRPO advantage tracer verified')"
  </verify>
</task>

<task>
  <name>Implement Clean-Diff FPR Gate and Bootstrap Significance Evaluator</name>
  <files>rl/training/bootstrap_eval.py</files>
  <action>
1. In `rl/training/bootstrap_eval.py`:
   - Implement `BootstrapEvaluator`:
     - `evaluate_split(policy, cases: List[BenchmarkCase]) -> BenchmarkMetrics`:
       - Evaluates policy across test cases using `bench.evaluator.metrics.evaluate_case`.
       - Computes Precision, Recall, FPR on clean diffs, and Nitpick rate.
     - `run_bootstrap_comparison(baseline_metrics: List[CaseEvaluation], candidate_metrics: List[CaseEvaluation], n_resamples: int = 1000, alpha: float = 0.05) -> Dict[str, Any]`:
       - Resamples case evaluations with replacement for $B = 1000$ iterations.
       - Computes empirical $(1 - \alpha)$ confidence intervals for:
         - $\Delta \text{Precision} = \text{Precision}_{\text{cand}} - \text{Precision}_{\text{base}}$
         - $\Delta \text{Recall} = \text{Recall}_{\text{cand}} - \text{Recall}_{\text{base}}$
         - $\Delta \text{FPR} = \text{FPR}_{\text{cand}} - \text{FPR}_{\text{base}}$
       - Evaluates whether precision improvement is statistically significant (lower bound of $95\%\text{ CI} > 0$).
     - `assert_clean_diff_fpr_gate(metrics: BenchmarkMetrics, max_fpr: float = 0.10) -> bool`:
       - Enforces strict gate: raises `AssertionError` if FPR on clean diffs $\ge 10\%$.
  </action>
  <verify>
python -c "from rl.training.bootstrap_eval import BootstrapEvaluator; from bench.schema import CaseEvaluation; b = BootstrapEvaluator(); c1 = [CaseEvaluation('1', 1, 1, 0, 0, False, False, [], 10.0, 0)]; res = b.run_bootstrap_comparison(c1, c1, n_resamples=50); assert 'delta_precision_ci' in res; print('Bootstrap evaluator verified')"
  </verify>
</task>

<task>
  <name>Implement Quantization Exporter, Ollama Modelfile, and Release Packaging</name>
  <files>rl/training/quantize.py, models/Modelfile, models/MODEL_CARD.md</files>
  <action>
1. In `rl/training/quantize.py`:
   - Implement `ModelQuantizer`:
     - `merge_lora_weights(base_model_path: str, lora_adapter_path: str, output_path: str)`: Merges parameter-efficient adapter into base model.
     - `export_gguf(merged_model_path: str, output_gguf_path: str, quant_type: str = "Q4_K_M")`:
       - Exports GGUF format for llama.cpp / Ollama compatibility (Q4_K_M, Q5_K_M, Q8_0).
       - Features dry-run / CPU simulation for CI environments.
     - `export_awq(merged_model_path: str, output_awq_path: str, bits: int = 4)`:
       - Packages AWQ 4-bit weights for high-throughput vLLM serving.
     - `generate_ollama_modelfile(gguf_file_path: str, modelfile_dest: str)`:
       - Generates standardized Ollama `Modelfile` with system prompts and ChatML template.
2. In `models/Modelfile`:
   - Create production Ollama Modelfile referencing GGUF model with proper stop tokens (`<|im_end|>`), temperature (0.2), and review prompt template.
3. In `models/MODEL_CARD.md`:
   - Document model architecture (Qwen2.5-Coder base + GRPO RLVR fine-tuning).
   - Document zero-leakage training lineage verified against Aion-Bench SHA-256 hashes.
   - Display benchmark metrics (Precision $\ge 70\%$, clean-diff FPR $<10\%$, latency $<1.5$s).
   - Provide minimal inference examples in Python, Ollama, and curl.
  </action>
  <verify>
python -c "from rl.training.quantize import ModelQuantizer; q = ModelQuantizer(); q.generate_ollama_modelfile('models/aion-coder-1.5b-q4_k_m.gguf', 'models/test_Modelfile'); import os; assert os.path.exists('models/test_Modelfile'); os.remove('models/test_Modelfile'); print('Quantization runner and Modelfile verified')"
  </verify>
</task>

<task>
  <name>Build GRPO Training and Quantization Comprehensive Test Suite</name>
  <files>tests/test_grpo_and_quantization.py</files>
  <action>
1. In `tests/test_grpo_and_quantization.py`, write complete test suite:
   - `test_grpo_advantage_normalization()`: Tests positive, negative, and zero-variance group advantage normalization.
   - `test_clean_diff_heavy_penalty()`: Verifies that comments on clean diffs receive strong negative advantage.
   - `test_grpo_dry_run_training_step()`: Verifies full rollout step with mock tensors without GPU dependency.
   - `test_bootstrap_confidence_interval_computation()`: Tests bootstrap resampling logic and CI calculation.
   - `test_clean_diff_fpr_gate_enforcement()`: Tests that FPR $\ge 10\%$ triggers assertion and FPR $<10\%$ passes.
   - `test_quantizer_lora_merge_and_modelfile_generation()`: Verifies Modelfile formatting and parameter checks.
  </action>
  <verify>
python -m pytest tests/test_grpo_and_quantization.py -v
  </verify>
</task>

</tasks>

