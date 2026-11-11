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
| **TRAIN-01**| SFT Warm-Start Pipeline | P0 | Phase 5 | Complete ✅ | Supervised fine-tuning of open code models (1.5B–7B, e.g. Qwen2.5-Coder) on mined reviews and verified bug injections using QLoRA/Unsloth. |
| **TRAIN-02**| Actionability Verifier Model | P1 | Phase 5 | Complete ✅ | Train and calibrate a discriminator model to predict whether a proposed review comment will be acted upon. |
| **TRAIN-03**| GRPO / RLVR Training Loop | P0 | Phase 5 | Complete ✅ | Implement Group-Relative Policy Optimization on free GPU compute (Kaggle/Colab), with bootstrap-validated precision gains and FPR $<10\%$ on clean diffs. |
| **TRAIN-04**| Model Quantization & Release | P1 | Phase 5 | Complete ✅ | Export quantized checkpoints (GGUF/AWQ) for public Hugging Face release and local Ollama inference. |
| **APP-01** | Webhook-Driven GitHub App | P1 | Phase 6 | Complete ✅ | Expand from Action polling to a webhook-driven GitHub App hosted on free tiers for real-time review dispatch and instant feedback capture. |
| **APP-02** | 100+ Repos Precision Gate | P0 | Phase 6 | Complete ✅ | Maintain $\ge 70\%$ live precision over 30 consecutive days across 100+ active open-source repositories. |
| **APP-03** | CLI & Editor Surface | P1 | Phase 6 | Complete ✅ | Release `aion review --staged` CLI and VS Code extension reusing the core review engine. |
| **GROWTH-01**| Free for Open Source & Badge | P1 | Phase 7 | Complete ✅ | Guarantee core review engine is free forever for public open-source repos with "Reviewed by Aion" badge and quality dashboard. |
| **GROWTH-02**| Public Aion-Bench Leaderboard | P1 | Phase 7 | Complete ✅ | Host public evaluation benchmark leaderboard accepting community model and external reviewer submissions. |
| **GROWTH-03**| Launch & Grant Acceleration | P2 | Phase 7 | Complete ✅ | Public launch on Show HN, GitHub Marketplace, dev communities, and apply for AI startup/OSS cloud compute grants. |

---

## 2. Milestone v1.1: Prove It on Real Code

| ID | Title | Priority | Target Phase | Status | Description |
|---|---|:---:|:---:|:---:|---|
| **HARD-01** | Remove Untrusted Subprocess Fallback | P0 | Phase 8 | Complete ✅ | Eliminate in-process subprocess fallback for untrusted code. Keep monkey-patch harness only for unit tests in test module. Container missing means refuse execution and fall back to static analysis only. |
| **HARD-02** | Comprehensive Sandbox Threat Model & Tests | P0 | Phase 8 | Complete ✅ | Add symlink reads, /proc writes, fork bomb, disk quota, DNS exfiltration, token leakage, and mount escape tests. Add `--pids-limit`, `--cap-drop ALL`, `--security-opt no-new-privileges`, disk quota, non-root user. Publish `docs/SANDBOX_THREAT_MODEL.md`. |
| **HARD-03** | Verified Reaction Polling & App Events | P0 | Phase 8 | Complete ✅ | Check official GitHub API for reactions, threads, edits, deletions, commits. Implement Action polling (next run) and App documented events with real payload fixtures. Update docs. |
| **HARD-03b**| Diff Secret Redaction & Minimal Context | P0 | Phase 8 | Complete ✅ | Redact secrets from diffs before LLM calls. Never log diffs or tokens in CI output. Send minimal necessary context. Add tests and update data policy. |
| **HARD-04** | Deprecate Legacy AST Grader & Clean Metrics | P0 | Phase 8 | Complete ✅ | Move `env.py`, old trainers, `/optimize` to `legacy/` with README explaining reward hacking. Point `/reset`, `/step`, `openenv.yaml` to `ReviewEnv`. Remove unmeasured speedup/memory numbers from UI and API. |
| **HARD-05** | Document & Code Consistency Reconciliation | P1 | Phase 8 | Complete ✅ | Unify benchmark CLI command name, describe matcher exactly as implemented (greedy vs Hungarian), describe bandit exactly as per-category Beta Thompson sampling without misnaming it contextual. |
| **HARD-06** | Request Limits, Rate Limits & Replay Guard | P0 | Phase 8 | Complete ✅ | Implement request size limits, per-IP and per-repo rate limits, webhook replay protection (delivery ID cache), and timeouts on all outbound calls with tests. |
| **SCORECARD**| Milestone Scorecard Honest Source Tagging | P0 | Phase 8 | Complete ✅ | Rewrite milestone scorecard in docs with "Built" and "Validated on real data" columns. Tag every metric (synthetic, real, simulated, live). |
| **REAL-01** | `bench_real/` Schema & Collectors | P0 | Phase 9 | Complete ✅ | Create Pydantic schema and GitHub collectors for real bug fixes, reverted PRs, CVE fixes, and clean merged PRs (300+ cases). |
| **REAL-02** | Annotation Tooling & Agreement Metrics | P0 | Phase 9 | Complete ✅ | Build annotation tool, export two independent label files per case, script computing Cohen's kappa and disagreement list. Route human work to `HUMAN_TODO.md`. |
| **REAL-03** | Extended Contamination & MinHash Guard | P0 | Phase 9 | Complete ✅ | Check repos, file paths, and MinHash fuzzy diff hashes across SFT, GRPO, verifier data and bench_real with post-cutoff slice. Contamination report generator & tests. |
| **REAL-04** | Real-Data Benchmark Evaluation Runner | P0 | Phase 9 | Complete ✅ | One-command evaluation runner producing baseline table with bootstrap 95% CIs. Validation split only until decisions frozen. |
| **REAL-05** | Verifier Calibration on Real Validation Split | P0 | Phase 9 | Complete ✅ | Re-fit and verify verifier calibration on real validation split; generate reliability curves and ECE. |
| **PILOT-01** | Shadow Review Mode | P0 | Phase 10 | Complete ✅ | Implement shadow review mode in Action and App (silent review, no comments on PR). |
| **PILOT-02** | Shadow Mode Onboarding & Install Script | P1 | Phase 10 | Complete ✅ | Provide one-page onboarding guide and installation script for pilot repositories. |
| **PILOT-03** | Visible Mode with Safeguards | P0 | Phase 10 | Complete ✅ | Visible mode with feedback link, one-click "not useful" reasons, repo mute, 5 comments/PR hard cap, and kill switch. |
| **PILOT-04** | Pilot Audit Workflow & Real Telemetry Gate | P0 | Phase 10 | Complete ✅ | Weekly sampling script, audited live precision report with CIs, acceptance rate, mute rate. Ensure `precision_gate.py` rejects simulated telemetry. |
| **PILOT-05** | Maintainer Interview Guide & Recruitment | P1 | Phase 10 | Complete ✅ | Draft interview guide. Put recruiting, outreach, and interviews into `HUMAN_TODO.md`. |
| **TRAIN2-01**| Real Signal Data Mixing | P0 | Phase 11 | Planned 📋 | Mix real mined reviews, pilot feedback, and hard negatives; cap synthetic data at 50%; log data hashes. |
| **TRAIN2-02**| Test-Verified LLM Bug Generator | P0 | Phase 11 | Planned 📋 | Synthetic bugs with test/reproduction failure verification; evaluation bugs from different source than training bugs. |
| **TRAIN2-03**| Expanded Reward Hacking & Versioning | P0 | Phase 11 | Planned 📋 | Red-team degenerate policies (linter hit proximity, linter copycat, hedged generic comments). Track reward versions. |
| **TRAIN2-04**| Ablation Configurations & Notebooks | P1 | Phase 11 | Planned 📋 | Prepare configs and Kaggle/Colab notebooks for SFT, verifier filter, GRPO, and full stack ablations. |
| **LAUNCH-01**| Measured Evidence Report Template | P0 | Phase 12 | Planned 📋 | Evidence report template with measured numbers and source tags only; placeholders for pending data. |
| **LAUNCH-02**| False-Positive Issue Template | P1 | Phase 12 | Planned 📋 | Structured issue template for reporting false-positive review comments. |
| **LAUNCH-03**| Publication Assets & Submission Flow | P1 | Phase 12 | Planned 📋 | Model/dataset cards, marketplace copy, and reproducible leaderboard submission flow. |
| **LAUNCH-04**| Automated Launch Gate Check Script | P0 | Phase 12 | Planned 📋 | `scripts/launch_gate_check.py` reading real results and enforcing strict pass/fail per gate; fails closed on missing data. |

---

## 3. Requirement Coverage Invariant
Every requirement listed above is assigned to exactly one implementation phase in `.planning/ROADMAP.md`. No orphan requirements are permitted.
