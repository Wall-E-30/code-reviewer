---
language:
  - python
  - typescript
  - javascript
license: apache-2.0
tags:
  - code-review
  - reinforcement-learning
  - grpo
  - rlvr
  - qwen2.5-coder
  - automated-code-review
pipeline_tag: text-generation
---

# Aion Code Reviewer (v1.0)

Aion is an autonomous, RL-driven code reviewer fine-tuned on open code models (Qwen2.5-Coder 1.5B/7B) via **Group-Relative Policy Optimization (GRPO / RLVR)** over verifiable code execution and differential test environments.

## Model Highlights

- **Precision-First Reviewing:** Emits at most 5 high-impact inline comments with valid GitHub suggestion blocks.
- **Negative Control & Low Noise:** Penalizes hallucinated findings on clean code, driving clean-diff False-Positive Rate strictly below **10%**.
- **Actionability Discriminator:** Built-in temperature-calibrated verifier ($\text{ECE} < 0.05$) suppressing subjective nitpicks and styling complaints.
- **Zero Benchmark Contamination:** Training data derived from 10,000 verified episodes with cryptographic SHA-256 isolation from Aion-Bench locked splits.
- **Quantized Deployability:** Released in 4-bit/5-bit GGUF (`Q4_K_M`, `Q5_K_M`) for local execution via Ollama and AWQ for vLLM.

---

## Evaluation Benchmark Performance (Aion-Bench Held-Out Test Split)

| Model / Approach | Precision | Recall | Clean-Diff FPR | Comments / PR | Nitpick Rate | Latency |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Aion Prototype (Day One Baseline)** | 32.5% | 48.0% | 24.0% | 8.2 | 34.0% | 1.8s |
| **Plain-Prompt Qwen2.5-Coder-7B** | 51.2% | 61.5% | 18.5% | 6.4 | 22.0% | 2.1s |
| **Aion-1.5B (SFT Warm-Start)** | 62.8% | 68.4% | 12.0% | 4.8 | 11.5% | 0.9s |
| **Aion-1.5B (GRPO / RLVR Policy)** | **74.6%** | **71.2%** | **6.5%** | **3.8** | **3.2%** | **0.9s** |
| **$\Delta$ Gain vs Baseline (95% CI)** | **+42.1%** `[+37.5%, +46.8%]` | **+23.2%** `[+17.8%, +28.4%]` | **-17.5%** `[-22.0%, -13.2%]` | -4.4 | -30.8% | -50% |

*All precision and recall gains verified via 1,000-resample bootstrap statistical testing.*

---

## How to Run Locally with Ollama

```bash
# 1. Pull or create from Modelfile
ollama create aion-reviewer -f models/Modelfile

# 2. Run interactive review
ollama run aion-reviewer "FILE: app.py\nDIFF:\n@@ -1 +1 @@\n-eval(x)\n+safe_eval(x)"
```

## How to Use via Transformers / Python

```python
import json
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "aion-code-reviewer/aion-coder-1.5b"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto")

prompt = (
    "<|im_start|>system\nYou are Aion, an expert automated code reviewer.<|im_end|>\n"
    "<|im_start|>user\nDIFF:\n@@ -5 +5 @@\n-cursor.execute(f'SELECT * FROM u WHERE id={id}')\n"
    "+cursor.execute('SELECT * FROM u WHERE id=?', (id,))<|im_end|>\n"
    "<|im_start|>assistant\n"
)

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.2)
review = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
print(review)
```

## License

Apache-2.0. Free for open source forever.

