---
phase: 12-launch-preparation
plan: 04
type: execute
wave: 4
depends_on:
  - 12-01-measured-evidence-report-template.md
  - 12-02-false-positive-issue-template.md
  - 12-03-publication-assets-and-submission-flow.md
files_modified:
  - scripts/launch_gate_check.py
  - tests/test_launch_gate_check.py
autonomous: true
requirements:
  - LAUNCH-04
must_haves:
  truths:
    - scripts/launch_gate_check.py reads real artifacts and enforces strict pass/fail gates.
    - Script fails closed (exit code 1) on missing data, synthetic ratio > 50%, unverified metrics, or failing security checks.
    - Script outputs structured human-readable CLI summary and machine-readable JSON output (--json).
    - Checks bench_real evaluations, pilot audit data, training v2 data mixture, reward versioning, and sandbox security.
  artifacts:
    - scripts/launch_gate_check.py
    - tests/test_launch_gate_check.py
---

<objective>
Build the Automated Launch Gate Check Script (`LAUNCH-04`).
Implement `scripts/launch_gate_check.py` to evaluate all milestone artifacts, benchmark measurements, training manifests, and security baselines, failing closed if any release criterion is unmet.
</objective>

<tasks>

<task type="tracer">
<name>Implement Launch Gate Check Engine</name>
<files>scripts/launch_gate_check.py</files>
<action>
Create `scripts/launch_gate_check.py`:
1. Gate 1: Bench Real Evaluation (`bench_real/data/BASELINE_EVAL_VAL.json`):
   - Precision >= 0.75 for trained policy.
   - Clean diff FPR <= 0.10.
   - 95% bootstrap CIs present and finite.
2. Gate 2: Training v2 Data Integrity (`data/training_v2/manifest.json`):
   - Manifest exists with SHA-256 slice digests.
   - Synthetic data ratio <= 0.50 (50%).
   - Contamination verification: zero overlap with `bench_real` splits.
3. Gate 3: Verifiable Reward & Versioning (`rl/reward.py`):
   - Reward version == `RewardVersion.V2_0_0`.
   - Anti-reward-hacking checks active (linter copycat, hedged generic, proximity spam).
4. Gate 4: Sandbox & Secret Hardening:
   - `docs/SANDBOX_THREAT_MODEL.md` exists and covers non-root, cap-drop, and pids limits.
   - Secret redaction regexes tested and active.
5. Gate 5: Telemetry & Precision Gate Policy:
   - `server/precision_gate.py` refuses simulated data.
   - Live pilot sampling script and audit report script exist.
6. Gate 6: Launch Assets & Evidence Documentation:
   - `docs/launch/EVIDENCE_REPORT_TEMPLATE.md`, `MODEL_CARD.md`, `DATASET_CARD.md`, `SHOW_HN.md`, `MARKETPLACE.md`, and `.github/ISSUE_TEMPLATE/false_positive_report.yml` all present and valid.
7. Support CLI options:
   - `--json`: emit JSON report.
   - `--strict`: exit 1 on any warning or pending item.
   - Return exit code 0 if all required gates pass, 1 if any gate fails.
</action>
<verify>
python scripts/launch_gate_check.py --help
</verify>
</task>

<task>
<name>Unit Test Launch Gate Verification</name>
<files>tests/test_launch_gate_check.py</files>
<action>
Create `tests/test_launch_gate_check.py` verifying:
1. Script passes on the repository's valid milestone state.
2. Script fails closed if `bench_real` results are missing or show precision < 0.75.
3. Script fails closed if synthetic ratio in training mixture exceeds 50%.
4. Script fails closed if required launch artifacts are missing.
5. JSON output mode produces valid parsable report.
</action>
<verify>
pytest tests/test_launch_gate_check.py -v
</verify>
</task>

</tasks>
