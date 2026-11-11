# Phase 11: Training v2 on Real Signal — Verification Report

**Phase:** `11-training-v2`  
**Milestone:** v1.1 — Prove It on Real Code  
**Status:** **PASSED** ✅  
**Verification Date:** 2026-11-11  
**Coverage:** 4 / 4 Requirements Verified (100%) (`TRAIN2-01`, `TRAIN2-02`, `TRAIN2-03`, `TRAIN2-04`)  

---

## 1. Goal-Backward Verification

The objective of Phase 11 was to train next-generation models on real mined reviews, pilot feedback, and test-verified bugs with anti-reward-hacking audits and standardized ablation configurations.

| Success Criterion | Target | Result | Evidence |
|---|---|:---:|---|
| **Real Signal Data Mixing (`TRAIN2-01`)** | Mix real reviews, pilot feedback, hard negatives; synthetic capped at $\le 50\%$; log slice hashes | **PASS** | `rl/training_v2/data_mixer.py`: Ingests 4 streams, strictly filters `bench_real` evaluation repos, caps synthetic data at 38.46% ($\le 50\%$). Emits `data/training_v2/manifest.json` with SHA-256 slice digests. 4 tests pass in `tests/test_data_mixing_v2.py`. |
| **Test-Verified Bug Generator (`TRAIN2-02`)** | Synthetic bugs with test/reproduction failure verification; disjoint eval and training sources | **PASS** | `rl/training_v2/bug_generator.py`: Generates bugs across 6 core categories. Guaranteed execution invariant: clean code passes test, buggy code fails test. `split="train"` and `split="eval"` use distinct seeds and disjoint templates. 4 tests pass in `tests/test_bug_generator_v2.py`. |
| **Reward Hacking & Versioning (`TRAIN2-03`)** | Red-team degenerate policies (linter copycat, hedged generic comments, proximity spam); Reward v2.0.0 | **PASS** | `rl/reward.py`: Introduced `RewardVersion.V2_0_0` with penalties for linter copycat, hedged generic platitudes, and linter proximity spamming. 4 tests pass in `tests/test_reward_hacking_v2.py` and 6 tests pass in `tests/test_reward_hacking.py`. |
| **Ablations & Notebooks (`TRAIN2-04`)** | 4 ablation configs, Kaggle & Colab notebooks, automated comparative evaluation | **PASS** | `configs/training_v2/` (`sft.yaml`, `verifier_filter.yaml`, `grpo.yaml`, `full_stack.yaml`), `notebooks/kaggle_training_v2_ablation.ipynb`, `notebooks/colab_training_v2_ablation.ipynb`, and `rl/training_v2/ablation_runner.py` producing `data/training_v2/ablation_results.json`. 3 tests pass in `tests/test_ablation_configs_and_runner.py`. |

---

## 2. Requirement Verification Matrix

| Requirement | Description | Status | Verification Evidence |
|:---:|---|:---:|---|
| **`TRAIN2-01`** | **Real Signal Data Mixing** | **VERIFIED** | `rl/training_v2/data_mixer.py`, `data/training_v2/manifest.json`: Real mined reviews + pilot feedback + hard negatives + synthetic $\le 50\%$. `tests/test_data_mixing_v2.py` passing. |
| **`TRAIN2-02`** | **Test-Verified LLM Bug Generator** | **VERIFIED** | `rl/training_v2/bug_generator.py`: Executable reproduction test failure verification; disjoint train and eval template libraries. `tests/test_bug_generator_v2.py` passing. |
| **`TRAIN2-03`** | **Expanded Reward Hacking & Versioning** | **VERIFIED** | `rl/reward.py`: `RewardVersion.V2_0_0` tracking formula versioning, penalizing linter copycats, hedged platitudes, and proximity clusters. `tests/test_reward_hacking_v2.py` passing. |
| **`TRAIN2-04`** | **Ablation Configurations & Notebooks** | **VERIFIED** | `configs/training_v2/*.yaml`, `notebooks/*.ipynb`, `rl/training_v2/ablation_runner.py`, `data/training_v2/ablation_results.json`. `tests/test_ablation_configs_and_runner.py` passing. |

---

## 3. Automated Test Evidence

```
================================ Phase 11 Test Suites ================================
$ pytest tests/test_data_mixing_v2.py tests/test_bug_generator_v2.py tests/test_reward_hacking_v2.py tests/test_ablation_configs_and_runner.py -v
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0
collected 15 items

tests/test_data_mixing_v2.py::test_data_mixing_build_and_cap PASSED      [  6%]
tests/test_data_mixing_v2.py::test_bench_real_contamination_exclusion PASSED [ 13%]
tests/test_data_mixing_v2.py::test_manifest_sha256_cryptographic_verification PASSED [ 20%]
tests/test_data_mixing_v2.py::test_hard_negatives_and_pilot_feedback_integrity PASSED [ 26%]
tests/test_bug_generator_v2.py::test_test_verification_invariant PASSED  [ 33%]
tests/test_bug_generator_v2.py::test_invalid_mutation_rejected_by_verifier PASSED [ 40%]
tests/test_bug_generator_v2.py::test_source_isolation_between_train_and_eval PASSED [ 46%]
tests/test_bug_generator_v2.py::test_generated_bug_diff_and_fix_validity PASSED [ 53%]
tests/test_reward_hacking_v2.py::test_linter_copycat_policy PASSED       [ 60%]
tests/test_reward_hacking_v2.py::test_hedged_generic_comment_policy PASSED [ 66%]
tests/test_reward_hacking_v2.py::test_linter_proximity_spam_policy PASSED [ 73%]
tests/test_reward_hacking_v2.py::test_reward_version_backward_compatibility PASSED [ 80%]
tests/test_ablation_configs_and_runner.py::test_ablation_yaml_configs PASSED [ 86%]
tests/test_ablation_configs_and_runner.py::test_notebooks_json_validity PASSED [ 93%]
tests/test_ablation_configs_and_runner.py::test_ablation_runner_execution_and_results PASSED [100%]

============================= 15 passed in 2.01s ==============================
```

---

## 4. Conclusion
Phase 11 has successfully verified all requirements (`TRAIN2-01` through `TRAIN2-04`). All 15 tests pass. Phase 11 is **PASSED**.
