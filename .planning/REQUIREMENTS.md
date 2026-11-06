# Requirements Specification: Aion Code Reviewer

**Milestone:** v1.0 — Path to the No. 1 Code Reviewer (Zero-Budget, RL-Driven)  
**Date:** 2026-11-05 (Updated with Comprehensive Architecture & Strategy Review)  
**Status:** Scoped and Approved

---

## 1. Requirements Matrix

| ID | Title | Priority | Target Phase | Status | Description |
|---|---|:---:|:---:|:---:|---|
| **SEC-01** | Disable Untrusted Host Execution | P0 | Phase 1 | Complete ✅ | Explicitly disable direct host-side execution of untrusted user code in differential testing; rely strictly on static analysis (AST, Ruff, Semgrep) for public services. |
| **SEC-02** | Path Traversal & CORS Hardening | P0 | Phase 1 | Complete ✅ | Restrict catch-all static asset serving to verified canonical paths (`os.path.realpath`), bind CORS to explicit `ALLOWED_ORIGINS`, and sanitize 500 error disclosures. |
| **PLAT-01** | Headless Test Suite & Decoupling | P0 | Phase 1 | Complete ✅ | Decouple top-level Gradio imports and move shared utility helpers out of `inference.py` so `test_suite.py` runs headless in clean CI environments. |
| **PLAT-02** | Async Event Loop Unblocking | P0 | Phase 1 | Complete ✅ | Wrap all LLM network calls with `AsyncOpenAI` or `asyncio.to_thread` to stop freezing the FastAPI event loop during multi-step inferences. |
| **PLAT-03** | Packaging & Session Cache TTL | P0 | Phase 1 | Complete ✅ | Reconcile `pyproject.toml` with `requirements.txt`, implement TTL eviction (`cachetools.TTLCache`) for session storage, and fix multi-line colon corruption in `_fix_python_syntax`. |
| **PLAT-04** | Honest Metrics Display | P1 | Phase 1 | Complete ✅ | Replace synthetic polynomial AST speedup/memory estimates with directly measured runtime (`timeit`/`tracemalloc`) or explicit heuristic labels. |
| **PLAT-05** | CI Pipeline & License Definition | P0 | Phase 1 | Complete ✅ | Establish GitHub Actions CI (Ruff, Pytest, frontend build) on every commit/PR and declare explicit Apache-2.0 project license. |
| **SCOPE-01**| Explicit Language Scope | P0 | Phase 1 | Complete ✅ | Explicitly define Python and TypeScript/JavaScript as Tier-1 supported languages; clearly label all other 16 languages as experimental. |
| **BENCH-01**| Benchmark Schema & CLI Runner | P0 | Phase 2 | Complete ✅ | Establish `bench/` directory structure, case schema (diff, ground-truth bugs, labels, metadata), and one-command runner CLI (`python -m aion.bench run`). |
| **BENCH-02**| Injected-Bug & Clean Generator | P0 | Phase 2 | Complete ✅ | Synthesize reproducible bug injections that break test suites, plus clean-diff negatives to measure false-positive rates. |
| **BENCH-03**| Mined Real-Review Dataset | P1 | Phase 2 | Complete ✅ | Ingest real human PR review comments corroborated by subsequent corrective commits from GH Archive and CodeReviewer. |
| **BENCH-04**| Gold Set & Locked Test Split | P0 | Phase 2 | Complete ✅ | Establish a 100–200 case hand-audited gold set for calibration, and lock a private test split hidden from training to prevent benchmark overfitting. |
| **BENCH-05**| Baseline Calibration & Metrics | P0 | Phase 2 | Complete ✅ | Measure and permanently document day-one baselines (Aion prototype, plain LLMs, Ruff/Bandit) across Precision, Recall, FPR, Comments per PR, Nitpicks, and Latency. |
| **GH-01** | GitHub Action Distribution | P0 | Phase 3 | Complete ✅ | Package review workflow into a zero-hosting GitHub Action that runs directly in user repository CI. |
| **GH-02** | High-Precision PR Comments | P0 | Phase 3 | Complete ✅ | Post $\le 5$ high-confidence inline comments with concise rationale and valid GitHub suggestion blocks (`suggestion ...`), plus a summary comment. |
| **GH-03** | Hybrid Review Pipeline | P0 | Phase 3 | Complete ✅ | Multi-stage review combining `tree-sitter` diff parsing, pre-filtering via static linters (Ruff/Bandit/ESLint), context retrieval, and verifier filtering. |
| **GH-04** | Multi-Provider & BYOK Mode | P1 | Phase 3 | Complete ✅ | Support Bring-Your-Own-Key, local Ollama/llama.cpp inference, and automated fallback across free API tiers. |
| **GH-05** | Telemetry & Data Policy | P0 | Phase 3 | Complete ✅ | Publish a plain-language data policy; log candidate comments, whether posted, and maintainer reactions (resolved, dismissed, ignored via subsequent-run polling). |
| **FLY-01** | Per-Repository Convention Memory | P0 | Phase 4 | Complete ✅ | Store dismissed comment patterns and repository style guides to suppress repetitive feedback and inject conventions into prompt context. |
| **FLY-02** | Online Contextual Bandit | P1 | Phase 4 | Complete ✅ | Adaptively tune category posting confidence thresholds per repository using captured feedback to maximize maintainer acceptance rate without GPU training. |
| **RL-01** | `ReviewEnv` Gymnasium Core | P0 | Phase 4 | Complete ✅ | Implement MDP with PR diff observations, tool actions, and OpenEnv-compatible step/reset interfaces. |
| **RL-02** | Objective Verifiable Reward | P0 | Phase 4 | Complete ✅ | Calculate rewards based on ground-truth bug hits, false-positive penalties, nitpick deductions, and test patch validity. |
| **RL-03** | Ephemeral Containerized Sandbox | P0 | Phase 4 | Complete ✅ | Host RL rollouts in rootless ephemeral Docker/nsjail containers with resource limits and automated CI escape tests. |
| **RL-04** | Reward Hacking Audit | P0 | Phase 4 | Complete ✅ | Red-team reward functions to guarantee empty outputs, all-line spam, and generic advice score zero. |
| **DATA-01**| 10k+ Verified Training Episodes | P0 | Phase 4 | Complete ✅ | Synthesize bug injections and historical PR replays filtered by test execution, producing $\ge 10,000$ verified episodes. |
| **DATA-02**| Split Isolation & Leakage Guard | P0 | Phase 4 | Complete ✅ | Enforce strict repository-level and case-level hashing ensuring zero overlap between training data and Aion-Bench locked test/gold sets. |
| **TRAIN-01**| SFT Warm-Start Pipeline | P0 | Phase 5 | Planned | Supervised fine-tuning of open code models (1.5B–7B, e.g. Qwen2.5-Coder) on mined reviews and verified bug injections using QLoRA/Unsloth. |
| **TRAIN-02**| Actionability Verifier Model | P1 | Phase 5 | Planned | Train and calibrate a discriminator model to predict whether a proposed review comment will be acted upon. |
| **TRAIN-03**| GRPO / RLVR Training Loop | P0 | Phase 5 | Planned | Implement Group-Relative Policy Optimization on free GPU compute (Kaggle/Colab), with bootstrap-validated precision gains and FPR $<10\%$ on clean diffs. |
| **TRAIN-04**| Model Quantization & Release | P1 | Phase 5 | Planned | Export quantized checkpoints (GGUF/AWQ) for public Hugging Face release and local Ollama inference. |
| **APP-01** | Webhook-Driven GitHub App | P1 | Phase 6 | Planned | Expand from Action polling to a webhook-driven GitHub App hosted on free tiers for real-time review dispatch and instant feedback capture. |
| **APP-02** | 100+ Repos Precision Gate | P0 | Phase 6 | Planned | Maintain $\ge 70\%$ live precision over 30 consecutive days across 100+ active open-source repositories. |
| **APP-03** | CLI & Editor Surface | P1 | Phase 6 | Planned | Release `aion review --staged` CLI and VS Code extension reusing the core review engine. |
| **GROWTH-01**| Free for Open Source & Badge | P1 | Phase 7 | Planned | Guarantee core review engine is free forever for public open-source repos with "Reviewed by Aion" badge and quality dashboard. |
| **GROWTH-02**| Public Aion-Bench Leaderboard | P1 | Phase 7 | Planned | Host public evaluation benchmark leaderboard accepting community model and external reviewer submissions. |
| **GROWTH-03**| Launch & Grant Acceleration | P2 | Phase 7 | Planned | Public launch on Show HN, GitHub Marketplace, dev communities, and apply for AI startup/OSS cloud compute grants. |

---

## 2. Requirement Coverage Invariant
Every requirement listed above is assigned to exactly one implementation phase in `.planning/ROADMAP.md`. No orphan requirements are permitted.
