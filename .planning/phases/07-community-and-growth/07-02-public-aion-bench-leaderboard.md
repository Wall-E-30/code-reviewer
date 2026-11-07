---
phase: 07-community-and-growth
plan: 02
type: execute
wave: 2
depends_on:
  - 07-01
files_modified:
  - bench/leaderboard.py
  - data/leaderboard.json
  - server/app.py
  - frontend/src/LeaderboardView.jsx
  - tests/test_leaderboard.py
autonomous: true
requirements:
  - GROWTH-02
must_haves:
  truths:
    - bench/leaderboard.py defines Pydantic schemas for public leaderboard entries and submissions.
    - data/leaderboard.json is seeded with benchmark baselines: Aion Qwen2.5-Coder GRPO, GPT-4o, Claude 3.5 Sonnet, DeepSeek-Coder, Llama-3.1, Ruff+Bandit.
    - GET /api/leaderboard returns ranked evaluation entries.
    - POST /api/leaderboard/submit accepts community evaluations with strict metric bounds validation.
    - An interactive leaderboard web interface provides sorting, filtering by model type, and submission details.
  artifacts:
    - bench/leaderboard.py
    - data/leaderboard.json
    - server/app.py
    - frontend/src/LeaderboardView.jsx
    - tests/test_leaderboard.py
  key_links:
    - bench/leaderboard.py uses BenchmarkMetrics from bench/schema.py.
    - server/app.py exposes GET and POST endpoints for the leaderboard.
---

<objective>
Build and publish the public Aion-Bench Leaderboard (`GROWTH-02`).
Provide a transparent, open evaluation benchmark where open-source and commercial code review models are ranked on precision, recall, false-positive rate, and actionability.

Purpose: Cement Aion as the objective gold standard for AI code review and attract model submissions from the AI community.
Output: `bench/leaderboard.py`, `data/leaderboard.json`, API endpoints in `server/app.py`, `LeaderboardView.jsx`, and `tests/test_leaderboard.py`.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/07-community-and-growth/RESEARCH.md
@bench/schema.py
@server/app.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Leaderboard Schema and Persistence Engine</name>
  <files>bench/leaderboard.py, data/leaderboard.json</files>
  <action>
1. In `bench/leaderboard.py`:
   - Implement `LeaderboardEntry(BaseModel)`:
     - `model_id`: unique string identifier.
     - `display_name`: human-readable model name.
     - `organization`: provider or author.
     - `license`: open source license or commercial.
     - `model_type`: `"open-weights" | "commercial-api" | "static-tool" | "hybrid"`.
     - `precision`: float (0.0 to 1.0).
     - `recall`: float (0.0 to 1.0).
     - `false_positive_rate`: float (0.0 to 1.0).
     - `nitpick_rate`: float (0.0 to 1.0).
     - `avg_latency_ms`: float.
     - `submission_date`: str (ISO 8601).
     - `verified`: bool.
     - `replication_recipe`: str.
   - Implement `LeaderboardManager`:
     - Ingestion and ranking method: ranks primarily by `precision` descending, secondarily by `false_positive_rate` ascending.
     - `submit_entry(entry: LeaderboardEntry) -> LeaderboardEntry`: validates metrics within $[0.0, 1.0]$, prevents duplicate model IDs without versioning.
     - `get_ranked_entries(model_type: Optional[str] = None) -> List[LeaderboardEntry]`.
     - Persistence: loads and saves to `data/leaderboard.json`.
2. Seed `data/leaderboard.json` with baseline benchmarks:
   - Aion Qwen2.5-Coder 7B GRPO (78.4% prec, 71.2% rec, 6.5% FPR, 3.8% nitpick)
   - GPT-4o Prompt Baseline (64.2% prec, 68.5% rec, 18.2% FPR, 14.1% nitpick)
   - Claude 3.5 Sonnet Prompt Baseline (67.8% prec, 72.1% rec, 14.6% FPR, 11.5% nitpick)
   - DeepSeek-Coder 6.7B SFT (58.1% prec, 59.3% rec, 22.4% FPR, 18.9% nitpick)
   - Llama-3.1 8B Instruct (52.6% prec, 55.4% rec, 28.1% FPR, 24.3% nitpick)
   - Ruff + Bandit Static Linters (91.2% prec, 24.5% rec, 2.1% FPR, 0.0% nitpick)
  </action>
  <verify>
python -c "from bench.leaderboard import LeaderboardManager; mgr = LeaderboardManager(); entries = mgr.get_ranked_entries(); assert len(entries) >= 6; assert entries[0].precision >= entries[1].precision; print('Leaderboard manager tracer verified')"
  </verify>
</task>

<task>
  <name>Mount Leaderboard API Endpoints in server/app.py</name>
  <files>server/app.py</files>
  <action>
1. In `server/app.py`:
   - Import `LeaderboardManager`, `LeaderboardEntry` from `bench.leaderboard`.
   - Expose endpoints:
     - `GET /api/leaderboard`:
       - Query params: `model_type` (optional filter: `open-weights`, `commercial-api`, `static-tool`).
       - Returns ranked list of entries with summary statistics (total submissions, top model, average precision).
     - `POST /api/leaderboard/submit`:
       - Accepts `LeaderboardEntry` JSON body.
       - Validates metric bounds ($0 \le P, R, \text{FPR}, N \le 1$).
       - Ingests and saves new entry, returning 201 Created and ranked position.
  </action>
  <verify>
python -c "from server.app import app; assert any(r.path == '/api/leaderboard' for r in app.routes); print('Leaderboard routes verified')"
  </verify>
</task>

<task>
  <name>Create Interactive Leaderboard Web Component</name>
  <files>frontend/src/LeaderboardView.jsx</files>
  <action>
1. In `frontend/src/LeaderboardView.jsx`:
   - Interactive React component displaying the Aion-Bench Leaderboard:
     - Header explaining Aion-Bench evaluation criteria and zero-data-leakage guarantee.
     - Filter tabs: "All Models", "Open Weights Only", "Commercial APIs", "Static Tools".
     - Table with columns: Rank, Model, Organization, Type, Precision (%), Recall (%), Clean-Diff FPR (%), Nitpick Rate (%), Latency.
     - Visual badge highlighting top rank.
     - Submission dialog / modal explaining how to submit community models.
  </action>
  <verify>
python -c "import os; assert os.path.exists('frontend/src/LeaderboardView.jsx'); print('LeaderboardView component verified')"
  </verify>
</task>

<task>
  <name>Build Leaderboard Test Suite</name>
  <files>tests/test_leaderboard.py</files>
  <action>
1. In `tests/test_leaderboard.py`, write test cases:
   - `test_leaderboard_seed_data_integrity()`: Confirms all 6 baselines are present with valid metrics.
   - `test_ranking_algorithm()`: Verifies models are ranked strictly by precision and FPR.
   - `test_community_submission_validation()`: Verifies invalid percentages (>1.0 or <0.0) are rejected with HTTP 422 / ValueError.
   - `test_filtering_by_model_type()`: Tests open-weights vs commercial-api filters.
   - `test_api_endpoints_direct()`: Tests GET /api/leaderboard and POST /api/leaderboard/submit.
  </action>
  <verify>
pytest tests/test_leaderboard.py -v
  </verify>
</task>

</tasks>

