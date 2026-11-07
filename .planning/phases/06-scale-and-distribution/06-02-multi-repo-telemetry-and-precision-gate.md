---
phase: 06-scale-and-distribution
plan: 02
type: execute
wave: 2
depends_on: []
files_modified:
  - server/precision_gate.py
  - tests/test_precision_gate.py
autonomous: true
requirements:
  - APP-02
must_haves:
  truths:
    - Multi-repo telemetry aggregator collects anonymized review acceptance and rejection events across multiple repositories over rolling 30-day time windows.
    - Precision calculation measures accepted comments (resolved, upvoted, code applied) vs rejected comments (dismissed, downvoted, ignored).
    - Multi-repo precision gate asserts live precision >= 70% across at least 100 active repositories over 30 consecutive days.
    - Weekly progress tracker demonstrates monotonic or convergent precision improvements as contextual bandits adapt to repo preferences.
  artifacts:
    - server/precision_gate.py
    - tests/test_precision_gate.py
  key_links:
    - server/precision_gate.py consumes telemetry events emitted by action/telemetry.py and server/github_app.py.
    - server/precision_gate.py verifies requirement APP-02 before milestone completion.
---

<objective>
Implement the Multi-Repository Telemetry Aggregator and Long-Term Precision Gate (`APP-02`).
Aggregate live feedback signals across $\ge 100$ active repositories over rolling 30-day windows, enforce the strict $\ge 70\%$ live precision gate, and generate weekly progress reports illustrating convergence.

Purpose: Prove that Aion's automated reviews achieve and sustain high precision ($\ge 70\%$) at scale across 100+ diverse open-source codebases, ensuring maintainer trust and zero fatigue.
Output: `server/precision_gate.py` and `tests/test_precision_gate.py`.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/06-scale-and-distribution/RESEARCH.md
@action/telemetry.py
@rl/bandit.py
@rl/memory.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Multi-Repo Telemetry Record Schema and Ingestion Engine</name>
  <files>server/precision_gate.py</files>
  <action>
1. In `server/precision_gate.py`:
   - Implement `RepoReviewRecord` dataclass:
     - `repo_id: str`: Anonymized salted SHA-256 hash of repository.
     - `timestamp: datetime`: UTC timestamp of event.
     - `comments_posted: int`: Number of inline comments posted.
     - `comments_accepted: int`: Comments resolved, upvoted, or patch committed.
     - `comments_rejected: int`: Comments dismissed, downvoted, or PR merged without adoption.
     - `category: str`: `bug`, `security`, `performance`, `style`.
   - Implement `MultiRepoTelemetryAggregator`:
     - `record_event(record: RepoReviewRecord)`: Appends event to in-memory or persisted telemetry store.
     - `load_from_jsonl(jsonl_path: str)`: Ingests telemetry stream files.
     - `get_active_repo_count(window_days: int = 30) -> int`: Counts unique active repositories in time window.
  </action>
  <verify>
python -c "from server.precision_gate import MultiRepoTelemetryAggregator, RepoReviewRecord; from datetime import datetime, timezone; agg = MultiRepoTelemetryAggregator(); agg.record_event(RepoReviewRecord(repo_id='repo1', timestamp=datetime.now(timezone.utc), comments_posted=3, comments_accepted=2, comments_rejected=1, category='bug')); assert agg.get_active_repo_count(30) == 1; print('Aggregator tracer verified')"
  </verify>
</task>

<task>
  <name>Implement 30-Day Precision Calculator, Weekly Tracker, and Gate Assertion</name>
  <files>server/precision_gate.py</files>
  <action>
1. In `server/precision_gate.py`:
   - In `MultiRepoTelemetryAggregator`:
     - `compute_rolling_precision(window_days: int = 30) -> Dict[str, Any]`:
       - Filters records within past `window_days`.
       - Computes total accepted comments $A$ and rejected comments $R$.
       - Calculates live precision $P = A / (A + R)$ if $(A + R) > 0$ else $1.0$.
       - Calculates per-category precision breakdown.
       - Returns metrics dictionary: `{"active_repos": int, "total_comments": int, "accepted": int, "rejected": int, "live_precision": float}`.
     - `compute_weekly_progression(num_weeks: int = 4) -> List[Dict[str, Any]]`:
       - Breaks rolling window into 7-day buckets.
       - Computes weekly precision and accepted volumes, showing learning trajectory.
     - `generate_precision_report(output_markdown_path: Optional[str] = None) -> str`:
       - Formats structured Markdown report with summary table, weekly trend chart (ASCII/Markdown), and category breakdown.
     - `assert_precision_gate(window_days: int = 30, min_repos: int = 100, min_precision: float = 0.70) -> bool`:
       - Validates that active repos $\ge \text{min\_repos}$.
       - Validates that live precision $\ge \text{min\_precision}$.
       - Raises `AssertionError` if either requirement is violated.
  </action>
  <verify>
python -c "from server.precision_gate import MultiRepoTelemetryAggregator, RepoReviewRecord; from datetime import datetime, timezone, timedelta; agg = MultiRepoTelemetryAggregator(); now = datetime.now(timezone.utc); [agg.record_event(RepoReviewRecord(repo_id=f'r-{i}', timestamp=now - timedelta(days=i % 25), comments_posted=2, comments_accepted=2, comments_rejected=0, category='bug')) for i in range(105)]; assert agg.assert_precision_gate(30, 100, 0.70) is True; print('Precision gate verified')"
  </verify>
</task>

<task>
  <name>Build Multi-Repo Precision Gate Comprehensive Test Suite</name>
  <files>tests/test_precision_gate.py</files>
  <action>
1. In `tests/test_precision_gate.py`, write complete test cases:
   - `test_record_ingestion_and_active_repo_count()`: Verifies multi-repo counting across time horizons.
   - `test_rolling_precision_calculation()`: Validates accepted vs rejected ratio calculation.
   - `test_weekly_progression_trend()`: Verifies 4-week progression demonstrates improving precision as bandits adapt.
   - `test_precision_gate_passing_100_repos()`: Simulates 100+ active repositories with $>70\%$ acceptance, confirms gate passes.
   - `test_precision_gate_failing_insufficient_repos()`: Confirms gate raises AssertionError when repos $< 100$.
   - `test_precision_gate_failing_low_precision()`: Confirms gate raises AssertionError when precision $< 70\%$.
   - `test_markdown_report_generation()`: Verifies report formatting and output writing.
  </action>
  <verify>
python -m pytest tests/test_precision_gate.py -v
  </verify>
</task>

</tasks>

