# Phase 7 Research: Community, Growth & Open-Source Moat

**Phase:** `07-community-and-growth`  
**Milestone:** v1.0 — Path to the No. 1 Code Reviewer (Zero-Budget, RL-Driven)  
**Requirements:** `GROWTH-01`, `GROWTH-02`, `GROWTH-03`  
**Date:** 2026-11-07  

---

## 1. Domain & Ecosystem Analysis

Phase 7 is the capstone phase of Milestone v1.0. With platform security (Phase 1), Aion-Bench (Phase 2), GitHub Action distribution (Phase 3), the RL learning flywheel & data engine (Phase 4), trained GRPO/RLVR models (Phase 5), and GitHub App scaling with CLI/editor distribution (Phase 6) completed, Phase 7 establishes Aion's long-term open-source moat and sustainability.

Commercial AI code reviewers (CodeRabbit, Qodo/Codium, GitHub Copilot code review) rely on venture funding and paywalls. Aion differentiates by adopting an open-weight, RL-first foundation that is **guaranteed free forever for open-source repositories**, backed by transparent, reproducible benchmarks (`Aion-Bench`), and powered by compute grant pipelines.

### Key Pillars for Phase 7:
1. **Free for Open Source Guarantee & Dynamic SVG Badge (`GROWTH-01`):**
   - High-throughput dynamic SVG badge endpoint (`GET /api/badge/{owner}/{repo}` and `GET /api/badge`) compatible with GitHub READMEs and Shields.io.
   - Transparent public repository quality API (`GET /api/repos/{owner}/{repo}/quality`) reporting live precision, convention adherence, review velocity, and top detected issue categories.
   - Irrevocable Open Source Commitment manifesto (`docs/OPEN_SOURCE_COMMITMENT.md`).
2. **Public Aion-Bench Leaderboard (`GROWTH-02`):**
   - Rigorous submission schema (`LeaderboardSubmission`) with replication recipe, split specification, and tamper-resistant checksum.
   - Ingestion and validation engine (`bench/leaderboard.py`) enforcing metric sanity bounds and automated ranking.
   - Pre-populated with reproducible baselines (Aion Qwen2.5-Coder GRPO, GPT-4o, Claude 3.5 Sonnet, DeepSeek-Coder, Llama-3.1, Ruff+Bandit).
   - API (`GET /api/leaderboard`, `POST /api/leaderboard/submit`) and responsive web view with sortable columns, open-weight vs commercial filtering, and interactive metric definitions.
3. **Launch Strategy & Compute Grant Acceleration (`GROWTH-03`):**
   - Show HN launch copy (`docs/launch/SHOW_HN.md`) emphasizing developer pain points (hallucinations, nitpicks), RLVR methodology, and zero-budget reproducibility.
   - GitHub Marketplace and Action distribution packaging (`docs/launch/MARKETPLACE.md`, `action.yml`).
   - Four ready-to-submit compute grant applications:
     - Hugging Face ZeroGPU / Community Grant (`docs/grants/HUGGINGFACE_ZEROGPU.md`)
     - Google Cloud for Startups / TPU Research Cloud (`docs/grants/GOOGLE_FOR_STARTUPS.md`)
     - AWS Activate Founders / Open Source Cloud Credits (`docs/grants/AWS_ACTIVATE.md`)
     - Microsoft for Startups Founders Hub (`docs/grants/AZURE_FOR_STARTUPS.md`)
   - Open-source moat strategy and community contribution framework (`docs/OPEN_SOURCE_MOAT.md`, updated `CONTRIBUTING.md`).

---

## 2. Technical Design Specifications

### A. Dynamic SVG Badge Generator (`server/badge.py`)
- **SVG Generation:** Clean, vector-crisp SVG template adhering to Flat design standards (similar to Shields.io):
  - Left label: `Reviewed by Aion` (charcoal background `#555`).
  - Right value: Dynamic status or precision percentage (e.g., `verified`, `78% precision`, `passing`).
  - Color palette:
    - $\ge 70\%$ precision: `#2ea44f` (GitHub green)
    - $50\% - 69\%$ precision: `#dfb317` (amber yellow)
    - $< 50\%$ precision: `#cb2431` (warning red)
    - No data: `#9f9f9f` (neutral gray)
- **HTTP Caching:** `Cache-Control: max-age=300, s-maxage=3600, must-revalidate` ensuring badges are cached by GitHub Camo proxy while updating promptly.

### B. Public Leaderboard Engine (`bench/leaderboard.py`)
- **Schema & Validation:**
  - `model_id`: unique slug (e.g., `aion-qwen2.5-coder-7b-grpo`).
  - `display_name`: human-readable title.
  - `organization`: author/lab.
  - `license`: open source vs proprietary.
  - `model_type`: `"open-weights" | "commercial-api" | "static-tool" | "hybrid"`.
  - `metrics`: `BenchmarkMetrics` (precision, recall, false_positive_rate, nitpick_rate, avg_latency_ms).
  - `replication_recipe`: URL to checkpoint, prompt template, or reproduction script.
  - `submission_date`: ISO 8601 timestamp.
  - `verified`: Boolean indicating evaluation was replicated or verified by Aion maintainers.
- **Persistence:** `data/leaderboard.json` with auto-save and initial default records.

### C. Web Leaderboard & Quality Dashboard UI
- Single-page responsive view or standalone interactive page displaying:
  - Leaderboard table with rank, model name, provider type badge, Precision (%), Recall (%), Clean-Diff FPR (%), Nitpick Rate (%), Latency (ms), and links.
  - Interactive submission form / modal with validation.
  - Repository Quality Card viewer allowing developers to enter any GitHub repo to see badge preview, precision score, and convention summary.

---

## 3. Plan Wave Breakdown

1. **Plan 07-01 (Wave 1: `GROWTH-01`):**
   - Implement `server/badge.py`: dynamic SVG badge generator with precision status coloring.
   - Implement repo quality endpoint `GET /api/repos/{owner}/{repo}/quality` in `server/app.py` and mount `GET /api/badge/{owner}/{repo}` and `GET /api/badge`.
   - Create `docs/OPEN_SOURCE_COMMITMENT.md` guaranteeing zero-cost access for open-source projects.
   - Build unit test suite `tests/test_badge_and_quality.py`.

2. **Plan 07-02 (Wave 2: `GROWTH-02`):**
   - Implement `bench/leaderboard.py`: Pydantic models, validation rules, baseline seed dataset, and persistence manager.
   - Mount API endpoints in `server/app.py`: `GET /api/leaderboard`, `POST /api/leaderboard/submit`.
   - Implement interactive Leaderboard & Repository Quality HTML component in `frontend/` or standalone HTML dashboard.
   - Build unit test suite `tests/test_leaderboard.py`.

3. **Plan 07-03 (Wave 3: `GROWTH-03`):**
   - Author Show HN submission dossier (`docs/launch/SHOW_HN.md`).
   - Create GitHub Marketplace distribution guide and asset checklist (`docs/launch/MARKETPLACE.md`).
   - Author four full compute grant application dossiers in `docs/grants/` (Hugging Face ZeroGPU, Google for Startups, AWS Activate, Microsoft for Startups).
   - Document the long-term open-source moat strategy (`docs/OPEN_SOURCE_MOAT.md`) and update `CONTRIBUTING.md`.
   - Build verification test `tests/test_launch_and_grants.py` ensuring all required sections, grant metrics, and submission schemas are complete.

