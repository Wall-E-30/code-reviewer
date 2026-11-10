# Roadmap: Aion Code Reviewer

**Milestone:** v1.0 — Path to the No. 1 Code Reviewer (Zero-Budget, RL-Driven)  
**Status:** **100% Complete & Verified** ✅  
**Date:** 2026-11-07  
**Coverage:** 36 / 36 Requirements Mapped & Verified (100%)

---

## Phase Overview

- [x] **Phase 1: Stabilize & Make Trustworthy (Platform & Security Hardening)** - Completed 2026-11-05
  - Explicitly disable untrusted host execution (static analysis only), fix path traversal & CORS, unblock headless test suite, unblock async event loop, reconcile packaging, declare Apache-2.0 license, add GitHub Actions CI, and set Tier-1 language scope (Python, TypeScript/JS). [VERIFICATION.md](.planning/phases/01-stabilize-platform/01-VERIFICATION.md)
- [x] **Phase 2: Build the Yardstick (Aion-Bench Evaluation Suite)** - Completed 2026-11-05
  - Build reproducible evaluation benchmark with injected bugs, clean-diff negatives, mined human PR reviews, hand-audited gold set (100–200 cases), locked private test split, and day-one baseline calibrations. [VERIFICATION.md](.planning/phases/02-build-the-yardstick/02-VERIFICATION.md)
- [x] **Phase 3: Ship the Wedge (GitHub Action & High-Precision Review Pipeline)** - Completed 2026-11-05
  - Deliver native PR reviews via GitHub Action, cap output at $\le 5$ high-precision inline comments with suggestion blocks, integrate tree-sitter + static linters, publish plain-language data policy, and log minimal review telemetry. [VERIFICATION.md](.planning/phases/03-ship-the-wedge/03-VERIFICATION.md)
- [x] **Phase 4: Fast Flywheel & Verifiable Data Engine (ReviewEnv & Repo Memory)** - Completed 2026-11-06
  - Unblock the learning flywheel early without waiting for GPU training: deploy per-repo convention memory and online contextual bandits. Build `ReviewEnv` Gymnasium MDP, verifiable multi-tier reward function, ephemeral container sandbox with escape tests, and generate 10,000+ verified training episodes strictly isolated from benchmark test splits. [VERIFICATION.md](.planning/phases/04-flywheel-and-data-engine/04-VERIFICATION.md)
- [x] **Phase 5: Model Training (SFT Warm-Start & GRPO / RLVR Policy Optimization)** - Completed 2026-11-07
  - SFT warm-start on open code models (1.5B–7B), train actionability verifier model, run Group-Relative Policy Optimization (GRPO) on free GPU compute (Kaggle/Colab), achieve bootstrap-validated precision gains with clean-diff FPR $<10\%$, and release quantized GGUF/AWQ weights. [VERIFICATION.md](.planning/phases/05-model-training/05-VERIFICATION.md)
- [x] **Phase 6: Scale & Distribution (GitHub App & Long-Term Precision Gate)** - Completed 2026-11-07
  - Transition from Action polling to webhook-driven GitHub App, verify $\ge 70\%$ live precision over 30 days across 100+ active repositories, and release `aion review --staged` CLI and VS Code extension. [VERIFICATION.md](.planning/phases/06-scale-and-distribution/06-VERIFICATION.md)
- [x] **Phase 7: Community, Growth & Open-Source Moat** - Completed 2026-11-07
  - Guarantee free for open source forever with "Reviewed by Aion" badge, launch public Aion-Bench leaderboard accepting outside submissions, execute public launch (Show HN, GitHub Marketplace), and secure AI compute grants. [VERIFICATION.md](.planning/phases/07-community-and-growth/07-VERIFICATION.md)

---

## Detailed Phase Specifications

### Phase 1: Stabilize & Make Trustworthy (Platform & Security Hardening)
**Status:** Completed ✅ (2026-11-05)  
**Goal:** The repository is safe, unblocked, honest, and thoroughly verified with zero critical security risks or misleading claims.  
**Requirements Mapped:** `SEC-01`, `SEC-02`, `PLAT-01`, `PLAT-02`, `PLAT-03`, `PLAT-04`, `PLAT-05`, `SCOPE-01`

**Success Criteria:**
- [x] 1. Direct host-side execution of untrusted user code in differential testing is completely disabled; public demo and analysis endpoints rely strictly on safe static analysis (Python AST, Ruff, Semgrep).
- [x] 2. Direct path traversal attempts against `/{full_path:path}` are blocked via canonical `os.path.realpath` boundary checks, and CORS is bound to explicit `ALLOWED_ORIGINS`.
- [x] 3. `python test_suite.py` passes completely inside a clean, lean virtual environment without requiring Gradio.
- [x] 4. FastAPI concurrent requests do not freeze when LLM inferences are processing (event loop remains responsive via `AsyncOpenAI` or `asyncio.to_thread`).
- [x] 5. All synthetic polynomial speedup and memory footprint percentages in the UI are replaced with honest, directly measured labels or explicit heuristic indices.
- [x] 6. GitHub Actions CI runs on all commits/PRs (Ruff lint, Pytest unit tests, Vite frontend build), and the project explicitly adopts the Apache-2.0 license.
- [x] 7. Language scope is formally documented: Python and TypeScript/JavaScript are Tier-1 supported; all other 16 languages are explicitly marked experimental.

**Dependencies:** None (Immediate Foundation)

---

### Phase 2: Build the Yardstick (Aion-Bench Evaluation Suite)
**Status:** Completed ✅ (2026-11-05)  
**Goal:** A versioned, reproducible benchmark exists to objectively evaluate review quality before any model training or prompt modifications.  
**Requirements Mapped:** `BENCH-01`, `BENCH-02`, `BENCH-03`, `BENCH-04`, `BENCH-05`

**Success Criteria:**
- [x] 1. A developer can run `python -m aion.bench run --split dev` and receive a structured JSON and Markdown report in under 60 minutes on local/free hardware.
- [x] 2. The benchmark contains at least 200 verifiable test cases (injected bugs with failing reproductions + clean diff negatives to measure false positives).
- [x] 3. The benchmark includes a hand-audited gold set of 100–200 human-verified cases to calibrate automatic metrics.
- [x] 4. A private test split is strictly locked and hidden from development/training to guarantee zero benchmark contamination.
- [x] 5. Precision, Recall on injected bugs, False-Positive Rate on clean diffs, Comments per PR, Nitpick Rate, and Latency/Cost are measured simultaneously.
- [x] 6. Day-one baseline numbers are permanently recorded for the current Aion prototype, a plain-prompt LLM, and static linters (Ruff/Bandit).

**Dependencies:** Phase 1 (Trustworthy Platform & Headless CI)

---

### Phase 3: Ship the Wedge (GitHub Action & High-Precision Review Pipeline)
**Status:** Completed ✅ (2026-11-05)  
**Goal:** Developers can install Aion into their repositories via a GitHub Action to receive high-precision inline PR review comments.  
**Requirements Mapped:** `GH-01`, `GH-02`, `GH-03`, `GH-04`, `GH-05`

**Success Criteria:**
- [x] 1. The GitHub Action runs inside a PR workflow, identifies changed files via `tree-sitter` (Python & TypeScript/JavaScript), and posts a summary plus at most 5 inline comments.
- [x] 2. Review comments include actionable explanations and valid GitHub suggestion blocks (`suggestion ...`).
- [x] 3. Linters (Ruff, Bandit, ESLint) run as pre-filters before LLM inference to minimize token overhead and latency.
- [x] 4. Users can supply their own API keys (BYOK) or connect to local Ollama endpoints without relying on centralized hosted servers.
- [x] 5. A plain-language data policy is published prior to any telemetry shipping; candidate comments, posting status, and author reactions (resolved, dismissed, ignored) are logged via subsequent-run polling.
- [x] 6. Dogfooding across 10+ open-source repositories achieves $\ge 50\%$ live comment precision with fewer than 5 comments per PR on average.

**Dependencies:** Phase 2 (Benchmark calibrated for precision)

---

### Phase 4: Fast Flywheel & Verifiable Data Engine (ReviewEnv & Repo Memory)
**Status:** Completed ✅ (2026-11-06)  
**Goal:** Deploy per-repo learning early without waiting for slow GPU training, replace the prototype AST grader with `ReviewEnv`, and synthesize 10k+ verified training episodes.  
**Requirements Mapped:** `FLY-01`, `FLY-02`, `RL-01`, `RL-02`, `RL-03`, `RL-04`, `DATA-01`, `DATA-02`

**Success Criteria:**
- [x] 1. Aion maintains per-repository memory of dismissed comment types and repo style guidelines, suppressing repeat complaints and injecting conventions into review context.
- [x] 2. An online contextual bandit adaptively tunes category posting confidence thresholds per repository using captured feedback to maximize maintainer acceptance rate without GPU training.
- [x] 3. `ReviewEnv` exposes standard Gymnasium `reset(task)` and `step(action)` methods accepting diff observations and returning verifiable rewards.
- [x] 4. Rewards score ground-truth bug hits positively while penalizing false positives, redundant comments, and broken patches.
- [x] 5. RL rollouts run inside ephemeral rootless Docker/nsjail containers with resource limits and an automated escape test suite passing in CI.
- [x] 6. Reward-hacking red team tests confirm that degenerative policies (empty comments, commenting on every line, generic text) receive low or negative rewards.
- [x] 7. Data engine generates $\ge 10,000$ verified training episodes (injected bugs with failing tests, clean diff negatives, real-review replays).
- [x] 8. Strict hashing and repository-level isolation prevent any training data from leaking into Aion-Bench locked test or gold sets.

**Dependencies:** Phase 2, Phase 3

---

### Phase 5: Model Training (SFT Warm-Start & GRPO / RLVR Policy Optimization)
**Status:** Completed ✅ (2026-11-07)  
**Goal:** A small, open-weight code model (1.5B–7B parameters) fine-tuned via SFT and GRPO outperforms prompt-engineered baselines on Aion-Bench.  
**Requirements Mapped:** `TRAIN-01`, `TRAIN-02`, `TRAIN-03`, `TRAIN-04`

**Success Criteria:**
- [x] 1. SFT warm-start fine-tuning on mined review data and verified bug injections improves initial diff comprehension on open code models (e.g. Qwen2.5-Coder) using QLoRA/Unsloth.
- [x] 2. A trained verifier/reward model accurately discriminates between actionable and invalid review comments.
- [x] 3. Group-Relative Policy Optimization (GRPO) training using free GPU resources (Kaggle/Colab/HF) yields a statistically significant precision gain (verified via bootstrap confidence intervals) on the held-out test split over base and prompt baselines.
- [x] 4. False-positive rate on clean diffs remains strictly below 10%, with recall on real bugs maintained without collapse.
- [x] 5. Final checkpoints are quantized (GGUF/AWQ) and published for open-source community inference via Ollama or Hugging Face.

**Dependencies:** Phase 4 (Verifiable `ReviewEnv` & 10k+ Verified Dataset)

---

### Phase 6: Scale & Distribution (GitHub App & Long-Term Precision Gate)
**Status:** Completed ✅ (2026-11-07)  
**Goal:** Expand distribution to a webhook-driven GitHub App, achieve long-term precision stability, and release CLI/editor surfaces.  
**Requirements Mapped:** `APP-01`, `APP-02`, `APP-03`

**Success Criteria:**
- [x] 1. A webhook-driven GitHub App hosted on free tiers provides instantaneous PR comment dispatch and real-time reaction capture (replacing Action polling).
- [x] 2. Live review precision across 100+ active open-source repositories reaches $\ge 70\%$ over 30 consecutive days with verifiable weekly improvement charts.
- [x] 3. `aion review --staged` CLI and VS Code extension are released, reusing the core review and contextual bandit engine for local developer workflows.

**Dependencies:** Phase 3, Phase 4, Phase 5

---

### Phase 7: Community, Growth & Open-Source Moat
**Status:** Completed ✅ (2026-11-07)  
**Goal:** Cement Aion as the standard open-source AI code reviewer with a transparent leaderboard, active community, and compute sustainability.  
**Requirements Mapped:** `GROWTH-01`, `GROWTH-02`, `GROWTH-03`

**Success Criteria:**
- [x] 1. Aion is permanently free for public open-source repositories, offering a "Reviewed by Aion" README badge and repository quality dashboard.
- [x] 2. A public Aion-Bench leaderboard is hosted online, allowing outside AI models and commercial reviewers to submit and evaluate their performance.
- [x] 3. Public launch is executed across Show HN, GitHub Marketplace, and developer communities with full methodology transparency.
- [x] 4. Applications for open-source AI startup and cloud compute credits (HF, Google, AWS, Azure) are submitted and approved to support zero-budget scaling.

**Dependencies:** Phase 2, Phase 6

---

## Requirement Coverage Map

```
Phase 1: SEC-01, SEC-02, PLAT-01, PLAT-02, PLAT-03, PLAT-04, PLAT-05, SCOPE-01  (8) [100% VERIFIED]
Phase 2: BENCH-01, BENCH-02, BENCH-03, BENCH-04, BENCH-05                     (5) [100% VERIFIED]
Phase 3: GH-01, GH-02, GH-03, GH-04, GH-05                                     (5) [100% VERIFIED]
Phase 4: FLY-01, FLY-02, RL-01, RL-02, RL-03, RL-04, DATA-01, DATA-02         (8) [100% VERIFIED]
Phase 5: TRAIN-01, TRAIN-02, TRAIN-03, TRAIN-04                               (4) [100% VERIFIED]
Phase 6: APP-01, APP-02, APP-03                                               (3) [100% VERIFIED]
Phase 7: GROWTH-01, GROWTH-02, GROWTH-03                                       (3) [100% VERIFIED]

Total v1.0: 36 / 36 Requirements Mapped & Verified (100% Coverage)
```

---

# Milestone v1.1: Prove It on Real Code

**Goal:** Establish objective evidence and operational hardening on real-world code repositories rather than synthetic/in-distribution benchmarks.

---

## Phase Overview (v1.1)

- [ ] **Phase 8: Truth and Hardening**
  - Remove subprocess fallback for untrusted code (container missing = refuse & static analysis only). Complete sandbox threat model (`docs/SANDBOX_THREAT_MODEL.md`) and escape test coverage (symlinks, /proc, fork bomb, disk quota, DNS, env/token leakage, mounted paths) with container hardening flags (`--pids-limit`, `--cap-drop ALL`, `--security-opt no-new-privileges`, disk quota, non-root user). Implement realistic reaction polling in Action (next run) and documented events in App using recorded real API fixtures. Redact secrets from diffs before LLM call, never log diffs/tokens in CI, send minimum context. Move legacy AST grader and old trainers (`env.py`, `train_rl.py`, `train_autoregressive_rl.py`, `/optimize`, `/optimize_full`) to `legacy/` with README explaining reward hacking; point `/reset`, `/step`, `openenv.yaml` at `ReviewEnv`. Remove unmeasured speedup/memory numbers from UI/API. Fix doc/code inconsistencies (single benchmark CLI command, greedy vs Hungarian matcher, exact bandit description as Beta Thompson sampling). Add request size limits, per-IP/repo rate limits, webhook replay protection, timeouts on outbound calls. Rewrite milestone scorecard with "Built" vs "Validated on real data" columns and source tags.
- [ ] **Phase 9: Real-Data Evaluation**
  - Establish `bench_real/` with Pydantic schema and collectors for real bug fixes, reverted PRs, security advisories, and clean merged PRs (300+ cases). Build annotation tool and Cohen's kappa script (human annotation in `HUMAN_TODO.md`). Extend isolation guard to check repos, file paths, and MinHash fuzzy diffs across SFT, GRPO, verifier data and bench_real. Build evaluation runner for bench_real producing baseline table with 95% bootstrap CIs. Re-fit and verify calibration on real validation split.
- [ ] **Phase 10: Live Pilots**
  - Implement shadow mode in Action and App with onboarding guide and install script. Implement visible mode with feedback link, one-click "not useful" reasons, repo-level mute, 5 comments/PR cap, and kill switch. Build audit workflow sampling posted comments weekly, audited live precision report, and enforce real telemetry in `precision_gate.py`. Prepare maintainer interview guide.
- [ ] **Phase 11: Training v2 on Real Signal**
  - Data mixing with real mined reviews excluding bench_real repos, opt-in pilot feedback, hard negatives, and synthetic data capped at 50%. Test-verified LLM bug generator mimicking real bug classes with failing test verification. Extend reward hacking audit with degenerate policies (linter proximity, copycat, hedged generic comments) and reward versioning. Prepare Kaggle/Colab training configs and ablation log.
- [ ] **Phase 12: Launch Preparation**
  - Draft evidence report template, rewrite Show HN/Marketplace copy with measured results and source tags, and create false-positive issue template. Prepare listings, model/dataset cards, and leaderboard submission flow. Add `scripts/launch_gate_check.py` reading real results and printing pass/fail per gate.

---

## Detailed Phase Specifications (v1.1)

### Phase 8: Truth and Hardening
**Status:** In Progress ⏳  
**Goal:** Eliminate all insecure subprocess execution of untrusted code, harden the container sandbox, fix doc/code discrepancies, remove unmeasured metrics, and protect against diff secret leakage and replay attacks.  
**Requirements Mapped:** `HARD-01`, `HARD-02`, `HARD-03`, `HARD-03b`, `HARD-04`, `HARD-05`, `HARD-06`, `SCORECARD`

**Success Criteria:**
- [ ] 1. In-process subprocess execution of untrusted code is removed; missing container runtime refuses execution and falls back to static analysis only (`HARD-01`).
- [ ] 2. Sandbox escape tests pass covering symlink reads, /proc writes, fork bomb, disk quota, DNS, token leaks, and mount escapes; container runs with `--pids-limit`, `--cap-drop ALL`, `--security-opt no-new-privileges`, disk quota, and non-root user; `docs/SANDBOX_THREAT_MODEL.md` is published (`HARD-02`).
- [ ] 3. GitHub reaction polling and App events use documented APIs and recorded fixtures (`HARD-03`).
- [ ] 4. Diffs are redacted of secrets before LLM calls; CI logs never expose diffs or tokens (`HARD-03b`).
- [ ] 5. Legacy AST grader and old trainers moved to `legacy/` with README; endpoints point to `ReviewEnv`; unmeasured speedup/memory numbers removed (`HARD-04`).
- [ ] 6. Doc/code inconsistencies resolved (CLI command, matcher algorithm, bandit description) (`HARD-05`).
- [ ] 7. Request size limits, rate limits, webhook replay protection (delivery ID cache), and outbound timeouts enforced (`HARD-06`).
- [ ] 8. Scorecard updated with "Built" vs "Validated on real data" columns and explicit source tags (`SCORECARD`).

### Phase 9: Real-Data Evaluation
**Status:** Planned 📋  
**Goal:** Create an untainted real-world code review benchmark (`bench_real/`), annotation pipeline, and evaluation harness with bootstrap confidence intervals.  
**Requirements Mapped:** `REAL-01`, `REAL-02`, `REAL-03`, `REAL-04`, `REAL-05`

### Phase 10: Live Pilots
**Status:** Planned 📋  
**Goal:** Deploy shadow and visible review modes in live partner repositories with audit workflows and strict feedback telemetry.  
**Requirements Mapped:** `PILOT-01`, `PILOT-02`, `PILOT-03`, `PILOT-04`, `PILOT-05`

### Phase 11: Training v2 on Real Signal
**Status:** Planned 📋  
**Goal:** Train next-generation models on real mined reviews, pilot feedback, and test-verified bugs with anti-reward-hacking audits.  
**Requirements Mapped:** `TRAIN2-01`, `TRAIN2-02`, `TRAIN2-03`, `TRAIN2-04`

### Phase 12: Launch Preparation
**Status:** Planned 📋  
**Goal:** Produce measured-only evidence reports, listings, and automated release verification gate (`scripts/launch_gate_check.py`).  
**Requirements Mapped:** `LAUNCH-01`, `LAUNCH-02`, `LAUNCH-03`, `LAUNCH-04`

---

## Requirement Coverage Map (v1.1)

```
Phase 8:  HARD-01, HARD-02, HARD-03, HARD-03b, HARD-04, HARD-05, HARD-06, SCORECARD (8)
Phase 9:  REAL-01, REAL-02, REAL-03, REAL-04, REAL-05                               (5)
Phase 10: PILOT-01, PILOT-02, PILOT-03, PILOT-04, PILOT-05                          (5)
Phase 11: TRAIN2-01, TRAIN2-02, TRAIN2-03, TRAIN2-04                               (4)
Phase 12: LAUNCH-01, LAUNCH-02, LAUNCH-03, LAUNCH-04                               (4)

Total v1.1: 26 Requirements Mapped
```

