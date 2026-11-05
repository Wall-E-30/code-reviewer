# Aion: Strategic Blueprint — Path to the No. 1 Code Reviewer (Zero-Budget, RL-Driven)

**Date:** 2026-11-05  
**Context:** Research and strategy synthesis for Aion's project lifecycle.

---

## 1. Honest Baseline Evaluation

Aion is currently an ambitious hackathon-grade prototype built around a compelling premise: **code review as a Markov Decision Process (MDP) with a verifiable environment**.

### Current Assets
- A working Gymnasium-style environment (`env.py`) with `reset`/`step`, automated backtracking, and differential execution testing.
- Full-stack interface: FastAPI backend, React 19 SPA (Midnight Glass Bento Grid), Gradio exploratory UI, Docker configuration, Render and HF Space deployment profiles.
- Deterministic offline fallback engine (`MockOpenAI`) ensuring continuous operation without external API dependencies.
- Thoroughly audited debt and vulnerability manifest in `CONCERNS.md` and `bugs.md`.

### The Core Blockers to Market Leadership
1. **Host-Side Execution (Critical RCE)**: The AST-blacklist in `env.py` fails as a secure sandbox, allowing unauthorized filesystem reads and arbitrary host operations during differential testing.
2. **Toy Reward Signals**: The original three fixed tasks (`style-cleanup`, `efficiency-boost`, `security-audit`) rely on hand-written AST heuristics that reward gaming (e.g. adding `if __name__ == '__main__':` or trivial comprehensions) rather than meaningful code review.
3. **Full-File Rewrites vs. Actionable PR Review**: Real engineers need inline diff comments with high signal-to-noise ratio, not rewritten full files.
4. **Language Scope**: While 18 languages are identified via regex, only Python is genuinely analyzed via AST.
5. **Fabricated Metrics**: Speedup and memory reduction numbers are polynomial estimates over AST node differences, eroding user trust.
6. **Distribution Friction**: Developers work in GitHub pull requests, not standalone web interfaces.
7. **Lack of Objective Evaluation**: No standardized benchmark exists to measure whether model or prompt revisions actually improve review quality.

---

## 2. Competitive Strategy for a Zero-Budget Team

We win against well-funded competitors (CodeRabbit, Greptile, Qodo, Copilot code review, Cursor Bugbot) by executing on axes that money cannot easily replicate:

1. **Precision Over Volume**: Developers disable AI reviewers due to noisy, nitpicky comments. Aion targets high precision: posting at most 3–5 high-confidence, actionable comments per PR.
2. **Verifiable Correctness**: Findings are backed by concrete evidence—a reproducing test failure, an execution trace, or an automated patch that passes the repository test suite.
3. **Repo-Specific Learning (The RL Flywheel)**: The system learns from maintainer feedback (accepted, dismissed, resolved comments), adapting to each codebase's specific conventions and patterns.
4. **Open & Free for Open Source**: Zero friction for public open-source repositories with fully transparent benchmarks and leaderboards.

---

## 3. The 4-Tier Verifiable RL Reward Model

| Tier | Signal Type | Verifiable? | Source | Utilization |
|---|---|:---:|---|---|
| **Tier A** | Injected-Bug Detection (RLVR) | **Yes** (Ground Truth Known) | Public repos with passing test suites + automated mutations | Core RL training environment (`ReviewEnv`) |
| **Tier B** | Mined Review History | **Mostly** (Commit Corroboration) | GH Archive, public PR histories, CodeReviewer dataset | SFT warm-start data & reward model pre-training |
| **Tier C** | Patch Validity & Test Invariance | **Yes** (Automated Test Pass) | SWE-bench style tasks, synthetic bug-fix pairs | Reward shaping for code fix suggestions |
| **Tier D** | Live Maintainer Feedback | **Noisy but Real** | GitHub App user interactions (reactions, resolves, dismissals) | Contextual bandit tuning & preference alignment (DPO) |

---

## 4. Architectural Target: Zero-Budget Stack

- **Code Hosting & CI**: GitHub Actions (free for public repositories).
- **Static Analysis & Parsing**: `tree-sitter` (multi-language AST), `ruff`, `bandit`, `semgrep`, `eslint`.
- **Inference Engines**: Free API tiers (Groq, Hugging Face Router, OpenRouter free models, Gemini), local Ollama/llama.cpp runtime, and Bring-Your-Own-Key (BYOK) mode.
- **RL Training**: Kaggle / Google Colab free GPU hours, Unsloth / TRL for QLoRA and GRPO on 1.5B–7B open code models.
- **Sandboxing**: Ephemeral rootless Docker containers or bubblewrap/nsjail with network disabled and strict resource limits.
- **Distribution**: GitHub Action (native CI step) + GitHub App (webhook-driven PR comments).

