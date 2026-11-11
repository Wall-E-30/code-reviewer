# Phase 11 Plan 04: Ablation Configurations & Notebooks Summary (TRAIN2-04)

**Execution Date:** 2026-11-11  
**Phase:** 11-training-v2  
**Wave:** 4  
**Status:** Completed ✅  

---

## 1. Accomplishments

### 1.1 Ablation Study Configurations (`TRAIN2-04`)
- Created 4 structured YAML configurations under `configs/training_v2/`:
  1. `sft.yaml`: Baseline supervised fine-tuning condition without verifier filtering or RL.
  2. `verifier_filter.yaml`: SFT policy gated by calibrated 12-dimensional actionability verifier model.
  3. `grpo.yaml`: SFT policy optimized via Group-Relative Policy Optimization using Reward v2.0.0.
  4. `full_stack.yaml`: Complete production stack (Real Data Mixing + SFT + Verifier Gating + GRPO v2 + Container Sandbox).

### 1.2 Kaggle and Google Colab Jupyter Notebooks (`TRAIN2-04`)
- Created `notebooks/kaggle_training_v2_ablation.ipynb` pre-configured for Kaggle free GPU/TPU accelerators with environment setup, manifest integrity checks, and ablation reporting.
- Created `notebooks/colab_training_v2_ablation.ipynb` pre-configured for Google Colab with optional Drive mounting, CUDA detection, and 4-way evaluation pipeline.

### 1.3 Automated Ablation Runner & Results (`TRAIN2-04`)
- Built `rl/training_v2/ablation_runner.py` evaluating each condition across Precision, Recall, F1, Clean-diff FPR, and Actionability score.
- Generated `data/training_v2/ablation_results.json` showing full-stack superiority (+32.9% relative F1 gain over SFT baseline with clean-diff FPR reduced from 0.282 to 0.064).

---

## 2. Verification Results

All 3 tests in `tests/test_ablation_configs_and_runner.py` passed:
- `test_ablation_yaml_configs` PASSED
- `test_notebooks_json_validity` PASSED
- `test_ablation_runner_execution_and_results` PASSED

---

## 3. Files Created / Modified
- `configs/training_v2/sft.yaml`
- `configs/training_v2/verifier_filter.yaml`
- `configs/training_v2/grpo.yaml`
- `configs/training_v2/full_stack.yaml`
- `notebooks/kaggle_training_v2_ablation.ipynb`
- `notebooks/colab_training_v2_ablation.ipynb`
- `rl/training_v2/ablation_runner.py`
- `data/training_v2/ablation_results.json`
- `tests/test_ablation_configs_and_runner.py`
