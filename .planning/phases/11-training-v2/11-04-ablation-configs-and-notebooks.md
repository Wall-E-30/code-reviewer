---
phase: 11-training-v2
plan: 04
type: execute
wave: 4
depends_on:
  - 11-01
  - 11-02
  - 11-03
files_modified:
  - configs/training_v2/sft.yaml
  - configs/training_v2/verifier_filter.yaml
  - configs/training_v2/grpo.yaml
  - configs/training_v2/full_stack.yaml
  - notebooks/kaggle_training_v2_ablation.ipynb
  - notebooks/colab_training_v2_ablation.ipynb
  - rl/training_v2/ablation_runner.py
  - data/training_v2/ablation_results.json
  - tests/test_ablation_configs_and_runner.py
autonomous: true
requirements:
  - TRAIN2-04
must_haves:
  truths:
    - 4 ablation configs (sft, verifier_filter, grpo, full_stack) exist with model, data mixture, and training hyperparameters.
    - Kaggle and Google Colab Jupyter notebooks exist and are pre-configured for free-tier execution.
    - Ablation runner executes all 4 conditions and produces data/training_v2/ablation_results.json.
  artifacts:
    - configs/training_v2/full_stack.yaml
    - notebooks/colab_training_v2_ablation.ipynb
    - rl/training_v2/ablation_runner.py
    - tests/test_ablation_configs_and_runner.py
---

<objective>
Implement Ablation Configurations, Notebooks & Execution Runner (`TRAIN2-04`).
Prepare configs and Kaggle/Colab notebooks for SFT, verifier filter, GRPO, and full-stack ablations, with an automated ablation evaluator logging comparative metrics.
</objective>

<tasks>

<task type="tracer">
<name>Author Ablation Configurations and Notebooks</name>
<files>configs/training_v2/sft.yaml, configs/training_v2/verifier_filter.yaml, configs/training_v2/grpo.yaml, configs/training_v2/full_stack.yaml, notebooks/kaggle_training_v2_ablation.ipynb, notebooks/colab_training_v2_ablation.ipynb</files>
<action>
1. Create `configs/training_v2/`:
   - `sft.yaml`: Supervised fine-tuning only on training_v2 data.
   - `verifier_filter.yaml`: SFT + Verifier model actionability thresholding.
   - `grpo.yaml`: SFT + GRPO policy optimization with Reward v2.0.0.
   - `full_stack.yaml`: Complete stack with Real Data Mixing + SFT + Verifier + GRPO v2 + Sandbox.
2. Create `notebooks/`:
   - `kaggle_training_v2_ablation.ipynb`: Configured for Kaggle P100/T4 GPUs with pip install steps, data download, and 4-way evaluation.
   - `colab_training_v2_ablation.ipynb`: Configured for Google Colab with drive mounting, accelerator checks, and 4-way ablation execution.
</action>
<verify>
python -c "import yaml; yaml.safe_load(open('configs/training_v2/full_stack.yaml')); print('Configs verified')"
</verify>
</task>

<task>
<name>Implement Ablation Runner and Tests</name>
<files>rl/training_v2/ablation_runner.py, tests/test_ablation_configs_and_runner.py</files>
<action>
1. Create `rl/training_v2/ablation_runner.py`:
   - Runs comparative evaluation across the 4 ablation conditions on `bench_real/splits/val.json`.
   - Records precision, recall, F1, clean-diff FPR, and actionability score per condition.
   - Saves results to `data/training_v2/ablation_results.json`.
2. Create `tests/test_ablation_configs_and_runner.py`:
   - Validate YAML schema and hyperparameter presence across all 4 configs.
   - Verify notebooks are valid JSON format with proper metadata and cells.
   - Verify ablation runner executes and generates valid `ablation_results.json`.
</action>
<verify>
pytest tests/test_ablation_configs_and_runner.py -v
</verify>
</task>

</tasks>

