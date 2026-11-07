# Show HN: Aion – No-nitpick AI code review trained with RLVR, open-source and free for GitHub

**URL:** https://github.com/aion-ai/aion  
**Live Leaderboard:** https://aion.openenv.org/leaderboard  
**Demo Video / App:** https://aion.openenv.org  

---

Hey Hacker News! We are the creators of **Aion**, an open-source, AI-native code review engine that doesn't spam your pull requests with hallucinations, phantom bugs, or pedantic formatting nitpicks.

### The Problem: Why Developers Hate AI Code Reviews Today

Most AI code review bots today (commercial or open source) use naive one-shot prompting on frontier models (GPT-4o, Claude 3.5 Sonnet). While those models are great at general reasoning, in PR reviews they suffer from severe pathology:

1. **The "Helpfulness" Trap:** The model feels compelled to say *something* on every diff, even when the code is completely correct. This leads to subjective variable-naming nits, comment suggestions, and phantom edge cases.
2. **Noise Over Signal:** Getting 15 comments per PR ruins developer trust. Maintainers end up mass-dismissing review comments or disabling the bot entirely.
3. **Zero Accountability for Clean Diffs:** Standard benchmarks evaluate recall on injected bugs, but completely fail to measure the **False Positive Rate (FPR)** when a PR has zero bugs.

### Our Solution: RLVR on Gymnasium MDP + Clean-Diff Negative Controls

Instead of prompt engineering, we framed code review as a verifiable reinforcement learning environment:

- **Gymnasium Core (`ReviewEnv`):** An OpenEnv-compatible Markov Decision Process where the agent takes discrete review actions (inline comment with GitHub suggestion replacement) over unified diffs.
- **Verifiable Multi-Tier Rewards:**
  - $+2.0$ for hitting a ground-truth syntax/logic/security defect corroborated by automated tests.
  - $+1.0$ bonus for providing a valid, syntactically clean GitHub suggestion block (`suggestion ...`).
  - $-0.50$ penalty for subjective nitpicks (detected by calibrated AST and lexical classifiers).
  - **Negative Control on Clean Diffs:** On diffs that introduce zero bugs, commenting is penalized ($-1.50$), while returning an empty review (`{"comments": []}`) is rewarded ($+0.50$). This explicitly trains the policy to remain silent unless it is certain.
- **Group-Relative Policy Optimization (GRPO / RLVR):** We fine-tuned open-weight code models (Qwen2.5-Coder 7B) using DeepSeek-style GRPO without a critic network, standardizing relative advantages across rollout groups $G=4$ on free consumer/cloud GPUs (Kaggle and Google Colab).
- **Fast Flywheel (Contextual Bandits + Repo Memory):** In production, Aion remembers team conventions in `.aion/conventions.json` and uses Thompson Sampling contextual bandits to dynamically raise thresholds on categories maintainers dismiss.

### Aion-Bench Evaluation Results (Held-Out Test Split)

We evaluated Aion against frontier prompt baselines on our locked, hand-audited test split:

| Model / Reviewer | Type | Precision | Recall | Clean-Diff FPR | Nitpick Rate | Latency |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Aion Qwen2.5-Coder 7B (GRPO)** | **Open-Weights** | **78.4%** | **71.2%** | **6.5%** | **3.8%** | **420ms** |
| Claude 3.5 Sonnet (Prompt Baseline) | Commercial API | 67.8% | 72.1% | 14.6% | 11.5% | 1820ms |
| GPT-4o (Prompt Baseline) | Commercial API | 64.2% | 68.5% | 18.2% | 14.1% | 1450ms |
| DeepSeek-Coder 6.7B (Base SFT) | Open-Weights | 58.1% | 59.3% | 22.4% | 18.9% | 510ms |
| Llama-3.1 8B Instruct | Open-Weights | 52.6% | 55.4% | 28.1% | 24.3% | 620ms |
| Static Linters (Ruff + Bandit) | Static Tool | 91.2% | 24.5% | 2.1% | 0.0% | 45ms |

*Key Takeaway:* A fine-tuned 7B model trained via RLVR achieved a **higher live precision** ($78.4\%$) and dramatically lower False-Positive Rate ($6.5\%$) than GPT-4o and Claude 3.5 Sonnet, while running in $420\text{ms}$ locally or on free CPU/GPU tiers.

### How to Use It Today

1. **GitHub Action (Zero-Hosting):**
   ```yaml
   - uses: aion-ai/aion@v1
     with:
       github_token: ${{ secrets.GITHUB_TOKEN }}
   ```
2. **Local CLI (Pre-Commit Review):**
   ```bash
   pip install aion-code-reviewer
   aion review --staged
   ```
3. **VS Code Extension:** Install `Aion Code Reviewer` from the VS Code Marketplace for inline squiggles and 1-click QuickFix code replacements.
4. **"Reviewed by Aion" README Badge:** Free for public open-source repos:
   ```markdown
   [![Reviewed by Aion](https://aion.openenv.org/api/badge/{owner}/{repo})](https://github.com/aion-ai/aion)
   ```

### 100% Free Forever for Open Source

Aion is licensed under Apache-2.0. We guarantee that Aion's full review pipeline, GitHub App, and badge service are **permanently free for all public open-source repositories**. Model weights, GGUF quantizations, and training datasets are available on Hugging Face Hub.

We'd love your feedback, bug reports, and contributions! Try it out and let us know what you think.

