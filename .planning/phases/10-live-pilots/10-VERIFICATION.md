# Phase 10 Verification Report: Live Pilots & Maintainer Tooling

**Milestone:** v1.1 "Prove It on Real Code"
**Phase:** 10 — Live Pilots (agent builds tooling; humans recruit)
**Status:** COMPLETE (All Phase 10 plans verified, tests passing)

---

## 1. Executive Summary

Phase 10 delivers the complete pilot infrastructure and maintainer safeguards required to transition Aion from offline benchmark evaluation to live open-source repository trials, while strictly isolating human actions and enforcing absolute data honesty.

All automated tooling has been built, tested, and hardened:
1. **Shadow Mode (`PILOT-01`, `PILOT-02`)**: Zero-noise silent evaluation in both GitHub Action and GitHub App. Analyzes PRs, scrubs secrets, runs static linters and the calibrated precision verifier, and logs candidate reviews to `.aion/shadow_reviews.jsonl` without posting any PR comments. Accompanied by a 1-page onboarding guide (`docs/pilots/ONBOARDING_GUIDE.md`) and 1-command installer script (`scripts/install_pilot.py`).
2. **Visible Mode Safeguards (`PILOT-03`)**: High-precision visible reviews with structured feedback footers containing one-click dismiss reasons (`wrong`, `nitpick`, `already_known`, `out_of_scope`). Maintainers can silence Aion instantly at the repo level via `@aion mute` or `/aion mute` (and unmute via `@aion unmute`). An emergency global kill switch (`AION_KILL_SWITCH`) halts all review operations immediately, and visible comments are strictly capped at $\le 5$ per PR.
3. **Audit Workflow & Hardened Precision Gate (`PILOT-04`)**: Stratified sampling script (`scripts/sample_pilot_comments.py`) exporting weekly candidate comments to JSON and CSV for human auditing. Audited report generator (`scripts/pilot_audit_report.py`) computing audited live precision with 95% non-parametric bootstrap confidence intervals (1,000 resamples), maintainer acceptance rate, applied suggestion rate, repo mute rate, and inference cost per PR. `server/precision_gate.py` has been hardened to track data provenance (`is_real`, `provenance`) and strictly rejects simulated telemetry with `ValueError(status: PENDING_PILOT_DATA)`.
4. **Maintainer Qualitative Protocol & Human Tracking (`PILOT-05`)**: 20-minute structured interview protocol (`docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md`) covering noise perception, false positive frustration, suggestion block usability, and NPS. Outreach templates, candidate repo lists, and interview tracking are strictly cataloged in `HUMAN_TODO.md` with zero data fabrication.

---

## 2. Requirement Coverage & Verification Evidence

| Requirement | Implementation Details | Verification Test / Evidence | Status |
| :--- | :--- | :--- | :---: |
| **`PILOT-01`** | Added `--mode shadow` and `INPUT_MODE` to `action.yml` and `action/main.py`. Added shadow review logging in `server/github_app.py`. Silently executes pipeline, logs to `.aion/shadow_reviews.jsonl`, bypasses `post_review()`. | `tests/test_pilot_modes_and_safeguards.py::test_action_shadow_mode_logs_without_posting`<br>`tests/test_pilot_modes_and_safeguards.py::test_github_app_shadow_mode` | **PASS** |
| **`PILOT-02`** | Authored `docs/pilots/ONBOARDING_GUIDE.md` (1-page guide on modes, safeguards, permissions). Created `scripts/install_pilot.py` generating `.github/workflows/aion-review.yml`. | `tests/test_pilot_modes_and_safeguards.py::test_install_pilot_workflow`<br>`docs/pilots/ONBOARDING_GUIDE.md` validated | **PASS** |
| **`PILOT-03`** | Feedback footers with 1-click dismiss reasons (`wrong`, `nitpick`, `already_known`, `out_of_scope`) in `action/formatter.py`. Repository mute lifecycle in `rl/memory.py` (`RepoConventionMemory`) and webhook handlers. Global kill switch (`AION_KILL_SWITCH`). Strict $\le 5$ comments ceiling. | `tests/test_pilot_modes_and_safeguards.py::test_formatter_feedback_footer_contains_all_reasons`<br>`tests/test_pilot_modes_and_safeguards.py::test_repo_convention_memory_mute_lifecycle`<br>`tests/test_pilot_modes_and_safeguards.py::test_action_kill_switch_aborts`<br>`tests/test_pilot_modes_and_safeguards.py::test_action_muted_repo_aborts`<br>`tests/test_pilot_modes_and_safeguards.py::test_github_app_issue_comment_mute_and_unmute`<br>`tests/test_pilot_modes_and_safeguards.py::test_github_app_feedback_dismiss_tags`<br>`tests/test_pilot_modes_and_safeguards.py::test_github_app_strict_comment_cap` | **PASS** |
| **`PILOT-04`** | Built `scripts/sample_pilot_comments.py` (stratified sampling across categories into JSON/CSV). Built `scripts/pilot_audit_report.py` (95% bootstrap CIs with 1,000 resamples, acceptance rate, applied suggestion rate, mute rate, cost per PR). Updated `server/precision_gate.py` to enforce data provenance (`is_real`, `provenance`) and reject simulated telemetry. | `tests/test_pilot_audit_workflow.py::test_stratified_comment_sampling`<br>`tests/test_pilot_audit_workflow.py::test_sampling_export_lifecycle`<br>`tests/test_pilot_audit_workflow.py::test_bootstrap_precision_ci_properties`<br>`tests/test_pilot_audit_workflow.py::test_audit_report_generation`<br>`tests/test_pilot_audit_workflow.py::test_precision_gate_rejects_simulated_telemetry`<br>`tests/test_pilot_audit_workflow.py::test_precision_gate_passes_on_live_telemetry` | **PASS** |
| **`PILOT-05`** | Authored `docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md` (20-min qualitative protocol). Updated `HUMAN_TODO.md` with candidate target repositories, outreach templates, maintainer permission checklists, and interview trackers. | `docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md` created<br>`HUMAN_TODO.md` updated | **PASS** |

---

## 3. Dedicated Phase 10 Test Suite Results

```text
============================= test session starts =============================
tests/test_pilot_modes_and_safeguards.py::test_formatter_feedback_footer_contains_all_reasons PASSED
tests/test_pilot_modes_and_safeguards.py::test_repo_convention_memory_mute_lifecycle PASSED
tests/test_pilot_modes_and_safeguards.py::test_action_shadow_mode_logs_without_posting PASSED
tests/test_pilot_modes_and_safeguards.py::test_action_kill_switch_aborts PASSED
tests/test_pilot_modes_and_safeguards.py::test_action_muted_repo_aborts PASSED
tests/test_pilot_modes_and_safeguards.py::test_github_app_shadow_mode PASSED
tests/test_pilot_modes_and_safeguards.py::test_github_app_kill_switch PASSED
tests/test_pilot_modes_and_safeguards.py::test_github_app_muted_repo PASSED
tests/test_pilot_modes_and_safeguards.py::test_github_app_issue_comment_mute_and_unmute PASSED
tests/test_pilot_modes_and_safeguards.py::test_github_app_feedback_dismiss_tags PASSED
tests/test_pilot_modes_and_safeguards.py::test_github_app_strict_comment_cap PASSED
tests/test_pilot_modes_and_safeguards.py::test_install_pilot_workflow PASSED
tests/test_pilot_audit_workflow.py::test_stratified_comment_sampling PASSED
tests/test_pilot_audit_workflow.py::test_sampling_export_lifecycle PASSED
tests/test_pilot_audit_workflow.py::test_bootstrap_precision_ci_properties PASSED
tests/test_pilot_audit_workflow.py::test_audit_report_generation PASSED
tests/test_pilot_audit_workflow.py::test_precision_gate_rejects_simulated_telemetry PASSED
tests/test_pilot_audit_workflow.py::test_precision_gate_passes_on_live_telemetry PASSED
============================= 18 passed in 1.65s ==============================
```

---

## 4. Scientific Honesty & Data Integrity Tagging

Every metric and dataset in Phase 10 has been rigorously labeled according to Rule #1:
- `bench/`: `[SYNTHETIC-IN-DISTRIBUTION]`
- `bench_real/`: `[REAL-OFFLINE-CANDIDATES]`
- `scripts/pilot_audit_report.py`: `[AUDITED-PILOT]` (95% bootstrap CIs)
- `server/precision_gate.py`: `[LIVE-TELEMETRY-GATE]` (`status: PENDING_PILOT_DATA` when awaiting live pilot telemetry)
- Pilot maintainer recruitment, outreach, and interviews: Strictly recorded in `HUMAN_TODO.md` (`[HUMAN-ACTION-REQUIRED]`). Zero synthetic feedback.

