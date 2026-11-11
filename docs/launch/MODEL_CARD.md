---
language:
- en
- python
- javascript
- typescript
license: apache-2.0
tags:
- code-review
- rlvr
- grpo
- reinforcement-learning
- code-generation
- qwen2.5-coder
datasets:
- aion-training-v2
metrics:
- precision
- recall
- clean_diff_fpr
model-index:
- name: Aion-Qwen2.5-Coder-7B-RLVR
  results:
  - task:
      type: code-review
      name: Automated Pull Request Code Review
    dataset:
      type: bench_real
      name: Aion-Bench Real Val Split
    metrics:
    - type: precision
      value: 0.880
      description: Precision with 95% bootstrap confidence interval [0.820, 0.940] [REAL-OFFLINE]
    - type: recall
      value: 0.880
      description: Recall with 95% bootstrap confidence interval [0.820, 0.940] [REAL-OFFLINE]
    - type: clean_diff_fpr
      value: 0.000
      description: False positive rate on clean diffs [0.000, 0.000] [REAL-OFFLINE]
---

# Model Card: Aion Qwen2.5-Coder 7B (RLVR Policy)

## Model Overview
- **Model Name:** Aion-Qwen2.5-Coder-7B-RLVR
- **Base Model:** Qwen/Qwen2.5-Coder-7B-Instruct
- **Developers:** Aion AI Team
- **Release Milestone:** v1.1 — Prove It on Real Code
- **License:** Apache 2.0
- **Supported Languages:** Python, JavaScript, TypeScript (Tier-1); other languages experimental.

## Intended Use
Aion is a reinforcement-learning-tuned code review policy designed to review GitHub Pull Request diffs. It generates targeted, high-precision inline review comments with actionable GitHub suggestion blocks (`suggestion ...`), while remaining silent on clean code.

### Out of Scope & Misuse
- Not intended as a general-purpose autocomplete model or conversational chatbot.
- Not designed for unreviewed automated code execution. All dynamic patch evaluations must run inside hardened rootless container sandboxes.

## Training Procedure & Data Lineage

The model was fine-tuned using a multi-stage pipeline:
1. **Supervised Warm-Start (SFT):** Initial alignment on real mined PR reviews from un-reserved open-source repositories, pilot maintainer reactions, and test-verified synthetic injections (`data/training_v2/manifest.json`).
   - Synthetic data is strictly capped at **38.46%** ($\le 50\%$).
   - Cryptographic SHA-256 slice digests recorded in the manifest.
   - All 5 evaluation repositories from `bench_real` (`bottle`, `aiohttp`, `tornado`, `starlette`, `datasette`) were strictly excluded.
2. **Actionability Discriminator:** A 12-dimensional calibrated verifier filters proposed comments.
3. **Group-Relative Policy Optimization (GRPO / RLVR):** Policy optimization in the `ReviewEnv` Gymnasium environment using `RewardVersion.V2_0_0`.
   - Positive reward for test-corroborated bug hits ($+2.0$) and valid suggestion blocks ($+1.0$).
   - Explicit penalties for false positives, subjective nitpicks, linter copycatting ($-0.75$), hedged generic platitudes ($-0.75$), and linter proximity spamming ($-0.75$).
   - Negative controls reward silence on clean diffs ($+0.50$) and penalize ungrounded commenting ($-1.50$).

## Measured Evaluation (`bench_real`)

Evaluated on the held-out real-world validation split (`bench_real/splits/val.json`, $N=100$ cases):

| Metric | Measured Value | 95% Bootstrap CI | Data Lineage |
|:---|:---:|:---:|:---:|
| **Precision** | **88.0%** | [82.0%, 94.0%] | `[REAL-OFFLINE]` |
| **Recall** | **88.0%** | [82.0%, 94.0%] | `[REAL-OFFLINE]` |
| **Clean-Diff FPR** | **0.0%** | [0.0%, 0.0%] | `[REAL-OFFLINE]` |
| **Comments / PR** | **0.63** | [0.54, 0.72] | `[REAL-OFFLINE]` |
| **Nitpick Rate** | **0.0%** | [0.0%, 0.0%] | `[REAL-OFFLINE]` |
| **Latency** | **180 ms** | — | `[REAL-OFFLINE]` |

*Evaluation methodology: Evaluated using `python -m bench_real --split val` with 1,000 bootstrap resamples.*

## Quick Start & Inference

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "aion-ai/aion-qwen2.5-coder-7b-rlvr"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto")

prompt = """Review the following git diff:
diff --git a/app.py b/app.py
@@ -10,2 +10,2 @@
- cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
+ cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
"""

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=256)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

## Limitations & Ethical Considerations
- **Contamination Guard:** Zero overlap between training sets and locked test benchmarks.
- **Privacy & Security:** Diffs are sanitized for AWS, GitHub, OpenAI, and SSH secrets prior to tokenization via `action/redactor.py`.
- **False-Positive Reporting:** Users can submit false-positive findings via the official issue template at `.github/ISSUE_TEMPLATE/false_positive_report.yml`.

