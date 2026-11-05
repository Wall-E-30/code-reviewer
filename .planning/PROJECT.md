# Project: Aion Code Reviewer
**Autonomous AI-Driven Code Reviewer & Verifiable RL Sandbox**

---

## 1. Vision & Executive Summary
**Aion** is transforming automated software engineering from static, noisy linting into a dynamic, goal-oriented **Reinforcement Learning (RL) feedback loop**. 

By evaluating code quality through verifiable environments (real reproduction tests, AST parsers, and maintainer feedback) rather than uncalibrated LLM opinions, Aion delivers high-precision, evidence-backed code review comments directly inside pull requests. The system continually adapts to individual repositories, learning project conventions and user preferences over time.

---

## 2. Strategic Objectives & Core Tenets
1. **Precision-First Reviewing**: Post $\le 5$ high-confidence, actionable comments per PR. Eliminate low-value nitpicks and false positives.
2. **Verifiable Correctness**: Back comments with reproducible evidence (failing unit test, execution trace, or validated patch).
3. **True Reinforcement Learning (RLVR & GRPO)**: Replace prototype heuristic grading with verifiable injected-bug environments, real PR history datasets, and maintainer interaction signals.
4. **Early Learning Flywheel**: Deploy per-repo convention memory and online contextual bandits immediately after the GitHub Action ships, without waiting for slow, unpredictable GPU model training.
5. **Native Developer Distribution**: Deliver review comments natively via a GitHub Action and webhook-driven GitHub App.
6. **Zero-Budget Scalability**: Run on free-tier APIs, open-weight models (1.5B–7B LoRA fine-tuning), and community compute resources (Kaggle/Colab/HF).
7. **Explicit Scope**: Focus deeply on Python and TypeScript/JavaScript as Tier-1 supported languages; all other 16 languages are explicitly marked experimental.
8. **Licensing**: Licensed under the open Apache-2.0 license.

---

## 3. Technology Architecture

### Core Stack
- **Backend**: Python 3.11, FastAPI (`server/app.py`), Uvicorn ASGI server.
- **Frontend**: React 19, Vite, Midnight Glass Bento Grid design system (`frontend/src/App.jsx`, `AionStyles.css`).
- **Parsing & Static Analysis**: Python AST, `tree-sitter` (multi-language), `ruff`, `bandit`, `semgrep`, `eslint`.
- **Inference & Orchestration**: OpenAI SDK (HF Router endpoint with fallback to free providers), local Ollama/llama.cpp, deterministic `MockOpenAI`.
- **RL & Training**: Gymnasium-compatible `CodeReviewEnv` / `ReviewEnv`, PyTorch, Transformers, TRL (GRPO), Unsloth.
- **Packaging & DevOps**: Multi-stage Docker build (`node:22-slim` + `python:3.11-slim`), Render Blueprint, OpenEnv manifest (`openenv.yaml`).

### Key Repository Assets
- `env.py`: Gymnasium RL environment and AST grading logic.
- `inference.py`: Model inference coordinator, robust syntax repair, and Gradio laboratory UI.
- `models.py`: Pydantic data schemas (`Action`, `Observation`, `Reward`, `OptimizeResponse`).
- `server/app.py`: FastAPI REST API and session environment manager.
- `utils.py`: Indentation normalizer, language detection, and syntax repairs.
- `test_suite.py`: 18-point verification test suite.
- `MASTER_DOCUMENT.md`: Complete A-to-Z technical architecture manual.
- `.planning/codebase/`: 7-document comprehensive architectural map.

---

## 4. Current State & Immediate Priorities
The codebase has been thoroughly mapped. All initial logic bugs are resolved, but critical production debt must be addressed before commencing RL training:
- **Security**: Explicitly disable host-side execution of untrusted code in differential testing; rely strictly on safe static analysis for public services.
- **Concurrency**: Replace blocking synchronous OpenAI calls with `AsyncOpenAI` or `asyncio.to_thread` to stop FastAPI event loop starvation.
- **Sanitization**: Fix path traversal vulnerabilities in the static catch-all file route and restrict CORS.
- **Testing & CI**: Decouple Gradio imports so `test_suite.py` runs headless in clean environments, and add GitHub Actions CI.
- **Metrics**: Remove polynomial AST speedup/memory estimates and display verifiable metrics.

---

## 5. Non-Negotiable Engineering Rules
1. **Measure First, Optimize Later**: No model training without the locked Aion-Bench evaluation suite.
2. **Precision Over Volume**: Better to post 1 verified bug than 10 questionable suggestions.
3. **No Hallucinated Claims**: All metrics displayed in UI or reports must be directly measured.
4. **Zero Untrusted Host Execution**: Treat all user and repository code as untrusted; isolate completely.
5. **Transparent Open Source**: Core engine and benchmarks remain open source and free for public repositories.
