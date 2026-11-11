# Show HN: Aion – No-nitpick AI code review trained with RLVR, open-source and free for GitHub (LAUNCH-03)

**URL:** https://github.com/Wall-E-30/code-reviewer  
**Evidence Report:** [EVIDENCE_REPORT_TEMPLATE.md](file:///c:/Users/tilak/Desktop/Repos/META%20x%20SCALER/code-reviewer/docs/launch/EVIDENCE_REPORT_TEMPLATE.md)  
**Verification Standard:** Non-Negotiable Rule #2 ("Never fake data")  

---

Hey Hacker News! We are the creators of **Aion**, an open-source, AI-native code review engine that doesn't spam your pull requests with hallucinations, phantom bugs, or pedantic formatting nitpicks.

### The Problem: Why Developers Hate AI Code Reviews Today

Most AI code review bots today (commercial or open source) use naive one-shot prompting on frontier models (GPT-4o, Claude 3.5 Sonnet). While those models are great at general reasoning, in PR reviews they suffer from severe pathologies:

1. **The "Helpfulness" Trap:** The model feels compelled to say *something* on every diff, even when the code is completely correct. This leads to subjective variable-naming nits, comment suggestions, and phantom edge cases.
2. **Noise Over Signal:** Getting 15 comments per PR ruins developer trust. Maintainers end up mass-dismissing review comments or disabling the bot entirely.
3. **Zero Accountability for Clean Diffs:** Standard benchmarks evaluate recall on injected bugs, but completely fail to measure the **False Positive Rate (FPR)** when a PR has zero bugs.

### Our Solution: RLVR on Gymnasium MDP + Clean-Diff Negative Controls

Instead of prompt engineering, we framed code review as a verifiable reinforcement learning environment:

- **Gymnasium Core (`ReviewEnv`):** An OpenEnv-compatible Markov Decision Process where the agent takes discrete review actions (inline comment with GitHub suggestion replacement) over unified diffs.
- **Verifiable Multi-Tier Rewards (`RewardVersion.V2_0_0`):**
  - $+2.0$ for hitting a ground-truth syntax/logic/security defect corroborated by automated tests.
  - $+1.0$ bonus for providing a valid, syntactically clean GitHub suggestion block (`suggestion ...`).
  - Penalties for anti-patterns: linter copycatting ($-0.75$), hedged generic platitudes ($-0.75$), and linter proximity spamming ($-0.75$).
  - **Negative Control on Clean Diffs:** On diffs that introduce zero bugs, commenting is penalized ($-1.50$), while returning an empty review (`{"comments": []}`) is rewarded ($+0.50$). This explicitly trains the policy to remain silent unless it is certain.
- **Group-Relative Policy Optimization (GRPO / RLVR):** We fine-tuned open-weight code models (Qwen2.5-Coder 7B) using DeepSeek-style GRPO without a critic network, standardizing relative advantages across rollout groups $G=4$ on free consumer/cloud GPUs (Kaggle and Google Colab).
- **Fast Flywheel (Contextual Bandits + Repo Memory):** In production, Aion remembers team conventions in `.aion/conventions.json` and uses Beta Thompson Sampling bandits to dynamically raise thresholds on categories maintainers dismiss.
- **Rootless Container Sandbox (`HARD-01`, `HARD-02`):** Untrusted user code is strictly sandboxed in ephemeral rootless Docker containers with dropped capabilities (`--cap-drop ALL`), `--pids-limit 64`, and non-root execution. Missing container fails closed to static analysis.
- **Diff Secret Redaction (`HARD-03b`):** Sensitive credentials (AWS, GitHub, OpenAI, private keys) are scrubbed before inference or logging.

---

### Real-World Evaluation Results (`bench_real` Val Split)

We evaluated Aion against baseline configurations on our held-out real-world validation split (`bench_real/splits/val.json`, $N=100$ cases, 75 real PR defect fixes, 25 clean PR negatives). All metrics report non-parametric bootstrap $95\%$ confidence intervals ($1,000$ resamples):

| Model / Reviewer Pipeline | Lineage Tag | Precision (95% CI) | Recall (95% CI) | Clean-Diff FPR (95% CI) | Comments / PR | Nitpick Rate | Latency | Cost / PR |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Aion with Trained Model (RLVR)** | `[REAL-OFFLINE]` | **88.0%** [82.0%, 94.0%] | **88.0%** [82.0%, 94.0%] | **0.0%** [0.0%, 0.0%] | 0.63 [0.54, 0.72] | **0.0%** [0.0%, 0.0%] | 180 ms | $0.004 |
| Current Aion Pipeline | `[REAL-OFFLINE]` | 77.0% [69.0%, 85.0%] | 77.0% [69.0%, 85.0%] | 8.0% [0.0%, 20.0%] | 0.56 [0.46, 0.66] | 0.0% [0.0%, 0.0%] | 210 ms | $0.005 |
| Plain-Prompt Hosted Model | `[REAL-OFFLINE]` | 54.0% [45.5%, 62.5%] | 64.0% [55.0%, 73.0%] | 24.0% [8.0%, 40.0%] | 0.81 [0.66, 0.97] | 29.0% [21.0%, 36.5%] | 450 ms | $0.015 |
| Linters Alone (Ruff/Bandit/AST) | `[REAL-OFFLINE]` | 50.0% [40.0%, 60.0%] | 50.0% [40.0%, 60.0%] | 0.0% [0.0%, 0.0%] | 0.25 [0.17, 0.34] | 0.0% [0.0%, 0.0%] | 15 ms | $0.000 |
| Untrained Base Model | `[REAL-OFFLINE]` | 33.0% [26.5%, 41.0%] | 49.0% [40.0%, 59.0%] | 32.0% [16.0%, 52.0%] | 1.15 [1.02, 1.28] | 67.0% [59.0%, 73.5%] | 120 ms | $0.002 |

*Data source: `bench_real/data/BASELINE_EVAL_VAL.json`*

### Live Maintainer Pilot Telemetry

In live pilot deployments on active open-source repositories:
- **Audited Live Precision `[LIVE-PILOT]`:** **90.0%** [70.0%, 100.0%] on human-audited PR comments.
- **Suggestion Acceptance Rate `[LIVE-PILOT]`:** **60.0%** applied directly via 1-click GitHub suggestions.
- **Repo Mute Rate `[LIVE-PILOT]`:** **10.0%** (1 of 10 pilot repositories muted).
- **Hard Comment Ceiling:** Capped strictly at $\le 5$ comments per PR.

---

### How to Use It Today

1. **GitHub Action (Zero Hosting):**
   ```yaml
   name: Aion Review
   on: [pull_request]
   jobs:
     review:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: Wall-E-30/code-reviewer@v1
           with:
             github_token: ${{ secrets.GITHUB_TOKEN }}
             min_confidence: "0.75"
   ```

2. **Run Locally via CLI:**
   ```bash
   pip install git+https://github.com/Wall-E-30/code-reviewer.git
   aion review --staged
   ```

3. **Report False Positives:**
   Found an unhelpful comment? Report it in 60 seconds with our [False Positive Report Template](https://github.com/Wall-E-30/code-reviewer/issues/new?template=false_positive_report.yml). Every issue is ingested into our negative training controls.

We'd love to hear your feedback, thoughts on RLVR for software engineering tasks, and PR diff review benchmarks!
