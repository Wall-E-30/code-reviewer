---
phase: 03-ship-the-wedge
plan: 03
type: execute
wave: 3
depends_on:
  - 03-01
  - 03-02
files_modified:
  - DATA_POLICY.md
  - action/telemetry.py
  - action/reactions.py
  - bench/baselines/run_action_eval.py
  - tests/test_telemetry.py
autonomous: true
requirements:
  - GH-05
must_haves:
  truths:
    - DATA_POLICY.md publishes an unambiguous, plain-language privacy policy guaranteeing zero source code retention.
    - Telemetry engine logs candidate comments, confidence ratings, and verifier decisions using anonymized repository hashes.
    - Reaction polling inspects earlier Aion review comments on subsequent PR runs to detect resolved status, reactions, and commit fixes.
    - Full action review pipeline evaluates against Aion-Bench (gold.json), achieving >= 50% precision with an average of <= 5 comments per PR.
  artifacts:
    - DATA_POLICY.md
    - action/telemetry.py
    - action/reactions.py
    - bench/baselines/run_action_eval.py
    - tests/test_telemetry.py
  key_links:
    - DATA_POLICY.md governs all telemetry collection and is linked in PR review comments.
    - action/reactions.py feeds maintainer outcomes into action/telemetry.py without needing a hosted webhook server.
    - bench/baselines/run_action_eval.py benchmarks the complete GitHub Action review pipeline against Aion-Bench gold.json.
---

<objective>
Establish the feedback flywheel and user trust: publish the plain-language privacy data policy (`DATA_POLICY.md`), build the anonymized review telemetry engine with subsequent-run reaction polling, and evaluate the full GitHub Action review pipeline against Aion-Bench to verify $\ge 50\%$ precision with $\le 5$ comments per PR.

Purpose: Guarantee data privacy, capture the earliest training and bandit feedback from day one, and verify review precision before distribution.
Output: `DATA_POLICY.md`, telemetry engine, reaction polling module, and Aion-Bench evaluation report.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/03-ship-the-wedge/RESEARCH.md
@.planning/phases/03-ship-the-wedge/03-01-hybrid-pipeline-and-providers.md
@.planning/phases/03-ship-the-wedge/03-02-github-action-packaging-and-posting.md
</execution_context>

<tasks>

<task type="tracer">
  <name>Publish Plain-Language Data Policy in DATA_POLICY.md</name>
  <files>DATA_POLICY.md</files>
  <action>
1. Author `DATA_POLICY.md` in the repository root:
   - Clear, transparent, plain-English privacy declaration.
   - Core commitments:
     a. **Zero Source Code Storage:** Aion never stores, caches, transmits, or trains on user repository source code or commit diffs.
     b. **Zero Private IP Retention:** In BYOK mode, API calls go directly from user CI to the chosen LLM provider.
     c. **Anonymized Telemetry Only:** Telemetry logs only SHA-256 salted hashes of repository names and PR numbers.
     d. **What We Measure:** Proposed finding categories, confidence scores, whether comments were posted or suppressed by the verifier, and maintainer reactions (resolved, dismissed, thumbs up/down).
     e. **Complete Opt-Out:** Users can disable telemetry at any time by setting `enable-telemetry: 'false'` in their action workflow.
  </action>
  <verify>
python -c "assert os.path.exists('DATA_POLICY.md'); content = open('DATA_POLICY.md', encoding='utf-8').read(); assert 'Zero Source Code' in content and 'Opt-Out' in content; print('Data policy verified')"
  </verify>
</task>

<task>
  <name>Build Telemetry Logger and Reaction Polling in action/telemetry.py and action/reactions.py</name>
  <files>action/telemetry.py, action/reactions.py, tests/test_telemetry.py</files>
  <action>
1. In `action/telemetry.py`:
   - Define `TelemetryEvent` schema:
     - `timestamp: str`, `repo_hash: str`, `pr_hash: str`, `provider: str`, `model: str`
     - `candidates_generated: int`, `comments_posted: int`, `comments_suppressed: int`
     - `finding_categories: List[str]`, `confidences: List[float]`
   - Implement `TelemetryLogger`:
     - Method `log_event(event: TelemetryEvent, output_path: Optional[str] = None)`:
       - Appends record to `.aion/telemetry.jsonl` if telemetry is enabled.
       - Emits formatted telemetry metrics to GitHub Step Summary (`GITHUB_STEP_SUMMARY`).
       - Bypasses writing if `enable_telemetry` is false.
2. In `action/reactions.py`:
   - Implement `poll_previous_reactions(github_client: GitHubClient, repo: str, pr_number: int) -> ReactionSummary`:
     - Queries previously posted Aion comments on the PR via `github_client.get_existing_review_comments(repo, pr_number)`.
     - Analyzes reactions (`+1`, `-1`, `confused`, `heart`, `rocket`) and reply comments.
     - Checks if referenced line was subsequently modified by newer commits in the PR.
     - Produces `ReactionSummary` (`total_tracked`, `resolved_count`, `dismissed_count`, `positive_reactions`, `negative_reactions`).
3. In `tests/test_telemetry.py`:
   - Unit tests for hashing anonymity, event logging, opt-out handling, and reaction polling logic.
  </action>
  <verify>
python -m pytest tests/test_telemetry.py -v
  </verify>
</task>

<task>
  <name>Evaluate Action Review Pipeline on Aion-Bench and Verify Precision Gate</name>
  <files>bench/baselines/run_action_eval.py</files>
  <action>
1. In `bench/baselines/run_action_eval.py`:
   - Integrates the full `action/` review pipeline (linter pre-filtering + precision verifier) with the `bench.runner` evaluation harness.
   - Evaluates on `bench/splits/gold.json` (120 calibration cases) and `bench/splits/dev.json`.
   - Measures:
     - Precision: Must achieve $\ge 50\%$ precision on gold benchmark.
     - Average comments per PR: Must strictly respect $\le 5$ comments per PR.
     - False-Positive Rate on clean diffs: Verifies verifier suppression of clean diff noise.
   - Outputs evaluation summary report to console and `bench/results/action_pipeline_benchmark.json`.
  </action>
  <verify>
python bench/baselines/run_action_eval.py
  </verify>
</task>

</tasks>

