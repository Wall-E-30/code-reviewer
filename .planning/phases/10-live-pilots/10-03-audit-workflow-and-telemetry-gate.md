---
phase: 10-live-pilots
plan: 03
type: execute
wave: 2
depends_on:
  - 10-01
  - 10-02
files_modified:
  - scripts/sample_pilot_comments.py
  - scripts/pilot_audit_report.py
  - server/precision_gate.py
  - tests/test_pilot_audit_workflow.py
autonomous: true
requirements:
  - PILOT-04
must_haves:
  truths:
    - scripts/sample_pilot_comments.py samples posted comments weekly into a JSON/spreadsheet format for human labelling.
    - scripts/pilot_audit_report.py computes audited live precision with 95% bootstrap confidence intervals, acceptance rate, applied suggestion rate, mute rate, and cost per PR.
    - server/precision_gate.py reads only real telemetry and strictly refuses to report "passed" on simulated or unverified data.
  artifacts:
    - scripts/sample_pilot_comments.py
    - scripts/pilot_audit_report.py
    - server/precision_gate.py
    - tests/test_pilot_audit_workflow.py
---

<objective>
Build the pilot comment audit workflow and harden the precision gate against simulated data (`PILOT-04`).
Sample live comments for weekly human labeling, compute audited metrics with bootstrap confidence intervals, and ensure `precision_gate.py` rejects simulated telemetry.
</objective>

<tasks>

<task type="tracer">
  <name>Build Comment Sampling Script and Audit Report Generator</name>
  <files>scripts/sample_pilot_comments.py, scripts/pilot_audit_report.py</files>
  <action>
1. Implement `scripts/sample_pilot_comments.py`:
   - Extracts posted review comments across pilot repositories for a given week.
   - Samples up to $N$ comments (default: 50) using stratified sampling across categories.
   - Outputs JSON and CSV formats suitable for human auditing.
2. Implement `scripts/pilot_audit_report.py`:
   - Ingests audited sample labels (accurate vs false-positive, applied suggestions).
   - Computes:
     - Audited live precision with 95% bootstrap confidence intervals (1,000 resamples).
     - Maintainer acceptance rate (positive reactions + applied suggestions).
     - Applied suggestion rate.
     - Repository mute rate.
     - Estimated inference cost per PR.
   - Generates structured Markdown and JSON audit reports.
  </action>
  <verify>
python -c "from scripts.sample_pilot_comments import sample_pilot_comments; print('Sampling script ready')"
  </verify>
</task>

<task>
  <name>Harden Precision Gate Against Simulated Telemetry</name>
  <files>server/precision_gate.py, tests/test_pilot_audit_workflow.py</files>
  <action>
1. Update `server/precision_gate.py`:
   - `RepoReviewRecord` tracks `is_real: bool = False` or `provenance: str = "simulated"`.
   - In `assert_precision_gate()` and `compute_rolling_precision()`:
     - Check if records are flagged `is_real=False` or `provenance == "simulated"`.
     - Refuse to emit "PASS" or "passed" status if any telemetry is simulated or if real telemetry has not satisfied the full criteria.
     - Return explicit status `"PENDING_PILOT_DATA"` with a descriptive message explaining that 30-day live pilot data is accumulating.
2. Add `tests/test_pilot_audit_workflow.py`:
   - Test weekly comment sampling output.
   - Test audit report generation with bootstrap CIs and metrics.
   - Test `precision_gate.py` refuses to report passed on simulated data.
  </action>
  <verify>
python -m pytest tests/test_pilot_audit_workflow.py -v
  </verify>
</task>

</tasks>

