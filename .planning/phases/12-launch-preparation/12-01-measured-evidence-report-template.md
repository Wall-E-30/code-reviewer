---
phase: 12-launch-preparation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/launch/EVIDENCE_REPORT_TEMPLATE.md
  - tests/test_evidence_report.py
autonomous: true
requirements:
  - LAUNCH-01
must_haves:
  truths:
    - Evidence report contains measured numbers and source tags only ([REAL-OFFLINE], [LIVE-PILOT]).
    - All uncollected production metrics have explicit [PENDING-PILOT-PRODUCTION] or [PENDING] placeholders with zero synthetic inventions.
    - Offline benchmark comparisons directly reference measured results from bench_real/data/BASELINE_EVAL_VAL.json.
    - Training v2 ablation metrics match data/training_v2/ablation_results.json.
  artifacts:
    - docs/launch/EVIDENCE_REPORT_TEMPLATE.md
    - tests/test_evidence_report.py
---

<objective>
Draft the Measured Evidence Report Template (`LAUNCH-01`).
Create `docs/launch/EVIDENCE_REPORT_TEMPLATE.md` containing strictly measured numbers and rigorous source tags (`[REAL-OFFLINE]`, `[LIVE-PILOT]`), with explicit placeholders for pending production metrics, following Non-Negotiable Rule #2 ("Never fake data").
</objective>

<tasks>

<task type="tracer">
<name>Author Measured Evidence Report Template</name>
<files>docs/launch/EVIDENCE_REPORT_TEMPLATE.md</files>
<action>
Create `docs/launch/EVIDENCE_REPORT_TEMPLATE.md` with:
1. Executive Summary & Provenance Disclosures.
2. Verified Bench_Real Offline Metrics table with 95% bootstrap CIs ([REAL-OFFLINE]) comparing:
   - Untrained Base Model
   - Plain-Prompt Hosted Model
   - Linters Alone (Ruff/Bandit/AST)
   - Current Aion Pipeline
   - Aion with Trained Model (RLVR / GRPO)
3. Training v2 Ablations table ([REAL-OFFLINE]) referencing `data/training_v2/ablation_results.json` (SFT baseline, verifier filter, GRPO, full stack).
4. Pilot Telemetry & Acceptance Metrics ([LIVE-PILOT] / [PENDING-PILOT-PRODUCTION]):
   - Audited live precision and 95% CIs.
   - Suggestion application rate and dismiss reason distribution.
   - Repo mute rate and pending 30-day multi-repo retention.
5. Explicit disclaimers for uncollected production data:
   - Mark pending items with `[PENDING-PILOT-PRODUCTION]`.
   - Never fabricate unverified percentages or user quotes.
</action>
<verify>
python -c "assert 'docs/launch/EVIDENCE_REPORT_TEMPLATE.md'; print('Evidence report template authored')"
</verify>
</task>

<task>
<name>Verify Evidence Report Template Compliance</name>
<files>tests/test_evidence_report.py</files>
<action>
Create `tests/test_evidence_report.py` verifying:
1. File exists and contains mandatory sections and headers.
2. Every quantitative claim has an explicit tag (`[REAL-OFFLINE]`, `[LIVE-PILOT]`, or `[PENDING-PILOT-PRODUCTION]`).
3. No untagged claims or ungrounded synthetic performance claims appear in the template.
4. Baseline numbers match `bench_real/data/BASELINE_EVAL_VAL.json` and ablation results match `data/training_v2/ablation_results.json`.
</action>
<verify>
pytest tests/test_evidence_report.py -v
</verify>
</task>

</tasks>
