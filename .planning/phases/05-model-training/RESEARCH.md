# Phase 05: Model Training (SFT Warm-Start & GRPO / RLVR Policy Optimization) — Research & Technical Specification

**Phase:** `05-model-training`  
**Milestone:** v1.0 — Path to the No. 1 Code Reviewer (Zero-Budget, RL-Driven)  
**Date:** 2026-11-07  
**Requirements Covered:** `TRAIN-01`, `TRAIN-02`, `TRAIN-03`, `TRAIN-04`  

---

## 1. Executive Summary & Strategic Rationale

Phase 5 transitions Aion from a prompt-engineered, bandit-tuned system into a specialized, fine-tuned open code model. The overarching goal is to achieve state-of-the-art review precision on open code models (1.5B–7B parameters, e.g., Qwen2.5-Coder) under a **strict zero-budget operational regime** (runnable on free Kaggle/Colab T4/P100 GPUs and verifiable in headless CPU CI environments).

Automated code review fails when models suffer from:
1. **Hallucinated defects on clean code** (high False-Positive Rate).
2. **Subjective nitpicking** (stylistic noise causing maintainer fatigue).
3. **Invalid or broken code suggestions** (syntax errors in proposed fixes).

Phase 5 addresses these failure modes through a three-stage training and release pipeline:
- **SFT Warm-Start (`TRAIN-01`):** Supervised fine-tuning using QLoRA/Unsloth on 10,000 verified episodes generated in Phase 4 (`data/episodes/`), teaching the model structured review formatting, diff context localization, and actionable suggestion syntax.
- **Actionability Verifier Model (`TRAIN-02`):** A calibrated discriminator model that scores the probability that a proposed comment is substantive, actionable, and accepted by maintainers, filtering out nitpicks and false positives.
- **Group-Relative Policy Optimization (`TRAIN-03`):** Reinforcement Learning with Verifiable Rewards (RLVR) via GRPO. By sampling groups of candidate reviews per diff and normalizing rewards within the group, GRPO eliminates the memory-heavy Critic/Value network, fitting comfortably in 16GB VRAM while driving clean-diff FPR $<10\%$ and producing bootstrap-validated precision gains over baseline.
- **Quantization & Open Release (`TRAIN-04`):** Exporting 4-bit/5-bit GGUF and AWQ checkpoints with Ollama `Modelfile` and Hugging Face model cards for zero-cost community adoption.

---

## 2. Technical Architecture & Component Flow

```
   ┌──────────────────────────────────────────────────────────────┐
   │         10,000 Verified Training Episodes (Phase 4)          │
   │  (52% Injected Bugs, 30% Clean Negatives, 18% Mined Replays) │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ 1. SFT Warm-Start Pipeline (TRAIN-01)                        │
   │    - ChatML instruction formatter (Diff + File + Conventions)│
   │    - QLoRA 4-bit / Unsloth parameter-efficient adapter       │
   │    - Emits structured review JSON with suggestion blocks     │
   └───────────────┬──────────────────────────────┬───────────────┘
                   │                              │
                   │ Warm Policy Weights          │ Positive/Negative Pairs
                   ▼                              ▼
   ┌──────────────────────────────┐   ┌───────────────────────────┐
   │ 3. GRPO / RLVR Loop (TRAIN-03│   │ 2. Actionability Verifier │
   │    - ReviewEnv MDP Rollouts  │   │    Model (TRAIN-02)       │
   │    - Group Sampling (G=4..8) │   │  - Calibrated Probability │
   │    - Relative Advantage Norm │   │  - Nitpick / FP Classifier│
   │    - Multi-Tier Reward Engine│   │  - Temperature Scaling    │
   │    - Clean Diff FPR < 10%    │   └─────────────┬─────────────┘
   └───────────────┬──────────────┘                 │
                   │                                │ Verifier Reward Component
                   │ Optimized Policy Checkpoint    │
                   ▼                                │
   ┌────────────────────────────────────────────────▼─────────────┐
   │ 4. Evaluation, Quantization & Open Release (TRAIN-04)        │
   │    - Bootstrap Confidence Intervals vs Day-One Baselines     │
   │    - GGUF Export (Q4_K_M, Q5_K_M) + Ollama Modelfile        │
   │    - AWQ 4-Bit Export for vLLM & HF Model Card               │
   └──────────────────────────────────────────────────────────────┘
```

---

## 3. Deep-Dive Specifications

### 3.1 SFT Warm-Start Pipeline (`TRAIN-01`)

#### 3.1.1 Base Model Selection
- **Primary Target:** `Qwen/Qwen2.5-Coder-1.5B-Instruct` (ultra-lean, runs on CPU/edge/free T4) and `Qwen/Qwen2.5-Coder-7B-Instruct` (flagship accuracy).
- **Secondary Fallback:** `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`.
- **Input Formatting (ChatML):**
  ```
  <|im_start|>system
  You are Aion, an expert automated code reviewer. Analyze the pull request diff, modified file context, and repository conventions.
  Post at most 5 high-impact inline comments with actionable replacement code. If the diff is clean or defect-free, emit an empty review: {"comments": []}.
  <|im_end|>
  <|im_start|>user
  REPOSITORY CONVENTIONS:
  {conventions}

  FILE: {file_path} ({language})
  DIFF:
  {diff}

  MODIFIED FILE CONTENT:
  {file_content}
  <|im_end|>
  <|im_start|>assistant
  {
    "comments": [
      {
        "line_number": 42,
        "category": "security",
        "comment": "Unsanitized user input passed to SQL execute leads to SQL injection vulnerability.",
        "suggestion": "    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
      }
    ]
  }
  <|im_end|>
  ```

#### 3.1.2 Training Methodology
- **Parameter-Efficient Fine-Tuning:** QLoRA 4-bit (`bitsandbytes` NF4) with `r=16`, `lora_alpha=32`, `lora_dropout=0.05`, targeting all attention projection layers (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`).
- **Unsloth Acceleration:** Where available (Linux/CUDA), Unsloth speeds up gradient computation by $2\times$ and reduces VRAM usage by $60\%$.
- **Environment Adaptability:** Provide a modular `SFTTrainerConfig` and training runner (`rl/training/sft.py`) that executes in:
  1. Full GPU mode (CUDA, bf16/fp16, QLoRA).
  2. CPU/Test mock mode (runs in $<10$ seconds on test virtual environments for CI verification).

---

### 3.2 Actionability Verifier Model (`TRAIN-02`)

#### 3.2.1 Problem Formulation
Not all detected defects warrant interrupting developers. The actionability verifier predicts:
$$P(\text{actionable} \mid \text{diff}, \text{line}, \text{comment}, \text{suggestion}) \in [0, 1]$$

Where an actionable comment satisfies:
1. Target line is truly buggy or vulnerable.
2. Rationale is clear, technically precise, and non-subjective.
3. Suggestion is syntactically valid and solves the defect without side effects.
4. Clean diffs always yield $P(\text{actionable}) \approx 0.0$.

#### 3.2.2 Architecture & Calibration
- **Model Architecture:** Cross-encoder discriminator or lightweight sequence classification head over code representations. Takes tokenized input:
  `[CLS] DIFF_HUNK [SEP] COMMENT [SEP] SUGGESTION [SEP]`
- **Calibration (Temperature Scaling):** Uncalibrated neural networks are typically overconfident. We calibrate logits using learned temperature $T$:
  $$\hat{p} = \sigma\left(\frac{z}{T}\right)$$
  Optimizing negative log-likelihood on a validation split to minimize Expected Calibration Error (ECE $<0.05$).
- **Inference Integration:** Packaged in `rl/training/verifier_model.py` and connected directly to `action/verifier.py` to gate inline comment emission.

---

### 3.3 Group-Relative Policy Optimization (`TRAIN-03`)

#### 3.3.1 Mathematical Formulation of GRPO
Standard PPO requires maintaining a separate Critic network $V_\phi(s)$ with parameter size equivalent to the actor, consuming prohibitive VRAM on free GPUs. GRPO (Shao et al., 2024) computes baseline rewards directly across a group of sampled responses for the same input query.

For each task $q \sim \mathcal{D}$ (a PR diff from `ReviewEnv`):
1. Sample a group of $G$ review trajectories $\{o_1, o_2, \dots, o_G\} \sim \pi_{\theta_{\text{old}}}(o \mid q)$.
2. Compute scalar rewards $\{r_1, r_2, \dots, r_G\}$ using `VerifiableRewardCalculator` (`rl/reward.py`) augmented with the actionability verifier.
3. Compute standardized advantages:
   $$A_i = \frac{r_i - \bar{r}}{\sigma_r + \epsilon}, \quad \text{where } \bar{r} = \frac{1}{G}\sum_{j=1}^G r_j, \quad \sigma_r = \sqrt{\frac{1}{G}\sum_{j=1}^G (r_j - \bar{r})^2}$$
4. Update policy parameters $\theta$ by maximizing the clipped surrogate objective:
   $$\mathcal{L}_{\text{GRPO}}(\theta) = \frac{1}{G}\sum_{i=1}^G \left[ \min\left( \frac{\pi_\theta(o_i \mid q)}{\pi_{\theta_{\text{old}}}(o_i \mid q)} A_i, \text{clip}\left(\frac{\pi_\theta(o_i \mid q)}{\pi_{\theta_{\text{old}}}(o_i \mid q)}, 1-\epsilon_{\text{clip}}, 1+\epsilon_{\text{clip}}\right) A_i \right) - \beta D_{KL}(\pi_\theta \parallel \pi_{\text{ref}}) \right]$$
   where $D_{KL}(\pi_\theta \parallel \pi_{\text{ref}}) = \frac{\pi_{\text{ref}}(o_i \mid q)}{\pi_\theta(o_i \mid q)} - \log\frac{\pi_{\text{ref}}(o_i \mid q)}{\pi_\theta(o_i \mid q)} - 1$ (Schulman approximation).

#### 3.3.2 Enforcing Clean-Diff FPR $< 10\%$
Clean PR diffs constitute $30\%$ of the rollout distribution.
- When $q$ is clean, if $o_i$ contains any comment, `VerifiableRewardCalculator` returns $r_i = -1.50$ (clean violation penalty).
- If $o_i$ contains zero comments (`terminate_review()`), $r_i = +0.50$ (clean compliance reward).
- Within any group on a clean diff, the empty review receives advantage $A \gg 0$, aggressively penalizing any false alarms until clean-diff FPR drops below $10\%$.

#### 3.3.3 Bootstrap Precision Evaluation
To guarantee statistically significant performance improvements on the held-out test split:
- Run $B = 1,000$ bootstrap iterations resampling evaluation cases with replacement.
- Compute $95\%$ empirical confidence intervals for Precision, Recall, and FPR:
  $$\Delta \text{Precision} = \text{Precision}_{\text{GRPO}} - \text{Precision}_{\text{Baseline}}$$
  Verify that the lower bound $\Delta \text{Precision}_{\text{lower}} > 0$.

---

### 3.4 Model Quantization & Release Pipeline (`TRAIN-04`)

#### 3.4.1 GGUF Conversion (llama.cpp)
- Merge LoRA adapter into base model: `merged_model = model.merge_and_unload()`.
- Export FP16 weights to llama.cpp format.
- Quantize to `Q4_K_M` (medium 4-bit, optimal size/quality tradeoff: ~1.1GB for 1.5B, ~4.4GB for 7B) and `Q5_K_M` (5-bit high precision).
- Emit Ollama `Modelfile`:
  ```dockerfile
  FROM ./aion-coder-1.5b-q4_k_m.gguf
  TEMPLATE """{{ if .System }}<|im_start|>system
  {{ .System }}<|im_end|>
  {{ end }}{{ if .Prompt }}<|im_start|>user
  {{ .Prompt }}<|im_end|>
  {{ end }}<|im_start|>assistant
  """
  PARAMETER stop "<|im_end|>"
  PARAMETER temperature 0.2
  PARAMETER top_p 0.95
  ```

#### 3.4.2 AWQ 4-Bit Export & Hugging Face Release
- Run AutoAWQ with GEMM kernel optimization on calibration set from `data/episodes/`.
- Generate Hugging Face model card (`MODEL_CARD.md`) documenting training data lineage, evaluation benchmarks, zero-leakage hash proof, and sample usage scripts.

---

## 4. Hardware & Free-Tier Compute Feasibility

| Stage | Memory / Compute | Free Platform | Wall Time (Est.) | Fallback / CI Strategy |
|---|---|---|---|---|
| **SFT Warm-Start** | 1.5B QLoRA: ~6GB VRAM<br>7B QLoRA: ~14GB VRAM | Kaggle (2x T4 16GB) / Colab (1x T4 15GB) | 1.5B: 45 min<br>7B: 2.5 hours | Micro-dataset CPU dry-run in CI (`--dry-run` flag, $<15$s) |
| **Verifier Training** | ~2GB VRAM or CPU | Any CPU/GPU (Kaggle, Colab, CI runner) | 10-20 min | Scikit-learn / PyTorch CPU training fully functional in CI |
| **GRPO RLVR** | 1.5B GRPO (G=4): ~9GB VRAM | Kaggle T4 / Colab T4 | 1.5B: 1.5 hours | Simulation mode executing full forward/advantage loop on CPU synthetic tensors |
| **Quantization** | ~4GB RAM | Standard CPU runner | 5 min | Pre-packaged conversion script with stub check in CI |

---

## 5. File Map & Wave Decomposition for Phase 5

```
rl/
├── training/
│   ├── __init__.py
│   ├── config.py              # Hyperparameter & compute profile configurations
│   ├── formatter.py           # ChatML / instruction dataset formatter for episodes
│   ├── sft.py                 # SFT warm-start pipeline (QLoRA / Unsloth / CPU fallback)
│   ├── verifier_model.py      # Actionability discriminator model & calibration
│   ├── grpo.py                # Group-Relative Policy Optimization loop over ReviewEnv
│   ├── bootstrap_eval.py      # Bootstrap statistical significance & FPR evaluator
│   └── quantize.py            # GGUF / AWQ quantization & Ollama export runner
models/
├── Modelfile                  # Ollama configuration
└── MODEL_CARD.md              # Hugging Face model card & benchmark lineage
tests/
├── test_sft_pipeline.py       # SFT dataset format & dry-run training tests
├── test_verifier_model.py     # Actionability verifier & calibration tests
├── test_grpo_training.py      # GRPO advantage normalization & RL step tests
└── test_quantization.py       # Quantization, Modelfile & release export tests
```

---

## 6. Wave Breakdown Plan

- **Wave 1 (Plan 05-01): SFT Warm-Start Pipeline & Dataset Formatter (`TRAIN-01`)**
  - Formatter transforming `data/episodes/` into ChatML instruction-tuning format with clean-diff negative handling.
  - SFT training runner with QLoRA/PEFT configs and rapid CPU/dry-run mode for CI testing.
  - Diff comprehension and format adherence evaluation harness.

- **Wave 2 (Plan 05-02): Actionability Verifier Model & Calibration (`TRAIN-02`)**
  - Discriminator model predicting comment actionability $P(\text{actionable})$.
  - Temperature scaling calibration ensuring ECE $<0.05$.
  - Integration into `action/verifier.py` and `rl/reward.py`.

- **Wave 3 (Plan 05-03): GRPO / RLVR Training Loop, Benchmark Validation & Quantization (`TRAIN-03`, `TRAIN-04`)**
  - GRPO policy optimization loop sampling groups over `ReviewEnv` MDP with verifiable reward normalization.
  - Clean-diff negative penalty driving FPR $<10\%$.
  - Bootstrap confidence interval calculator comparing GRPO against baselines on held-out split.
  - GGUF/AWQ model quantization exporter, Ollama `Modelfile`, and Hugging Face model card.

