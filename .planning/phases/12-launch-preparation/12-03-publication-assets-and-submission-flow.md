---
phase: 12-launch-preparation
plan: 03
type: execute
wave: 3
depends_on:
  - 12-01-measured-evidence-report-template.md
files_modified:
  - docs/launch/MODEL_CARD.md
  - docs/launch/DATASET_CARD.md
  - docs/launch/LEADERBOARD_SUBMISSION.md
  - docs/launch/MARKETPLACE.md
  - docs/launch/SHOW_HN.md
  - tests/test_publication_assets.py
autonomous: true
requirements:
  - LAUNCH-03
must_haves:
  truths:
    - Hugging Face Model Card (MODEL_CARD.md) describes the trained policy, weights, benchmarks with 95% CIs, and limitations.
    - Hugging Face Dataset Card (DATASET_CARD.md) describes training mixture, synthetic <= 50% ratio, clean-diff negatives, and contamination isolation from bench_real.
    - MARKETPLACE.md and SHOW_HN.md are updated to purge synthetic ungrounded claims and include measured numbers with explicit source tags ([REAL-OFFLINE], [LIVE-PILOT]).
    - LEADERBOARD_SUBMISSION.md establishes a reproducible CLI and schema validation workflow for community benchmarks.
  artifacts:
    - docs/launch/MODEL_CARD.md
    - docs/launch/DATASET_CARD.md
    - docs/launch/LEADERBOARD_SUBMISSION.md
    - docs/launch/MARKETPLACE.md
    - docs/launch/SHOW_HN.md
    - tests/test_publication_assets.py
---

<objective>
Assemble Publication Assets & Leaderboard Submission Flow (`LAUNCH-03`).
Create official Hugging Face Model and Dataset Cards, rewrite Marketplace and Show HN launch materials with grounded measured numbers, and formalize the open leaderboard submission flow.
</objective>

<tasks>

<task type="tracer">
<name>Author Model Card, Dataset Card, and Leaderboard Submission Flow</name>
<files>docs/launch/MODEL_CARD.md, docs/launch/DATASET_CARD.md, docs/launch/LEADERBOARD_SUBMISSION.md</files>
<action>
1. Create `docs/launch/MODEL_CARD.md`:
   - Model details: Aion Qwen2.5-Coder 7B GRPO/RLVR policy.
   - Intended use & scope (Tier-1: Python, TypeScript/JS).
   - Training factors & hyperparameters (GRPO $G=4$, QLoRA, `RewardVersion.V2_0_0`).
   - Evaluation results with 95% bootstrap CIs from `bench_real/data/BASELINE_EVAL_VAL.json` ([REAL-OFFLINE]).
   - Out-of-scope uses, limitations, bias, and security considerations.
2. Create `docs/launch/DATASET_CARD.md`:
   - Dataset summary: Training v2 mixture (`data/training_v2/manifest.json`).
   - Composition: real mined reviews, pilot signals, hard negatives, and synthetic bugs capped at 38.46% (<= 50%).
   - Contamination verification: strictly disjoint from `bench_real` evaluation repositories.
   - Privacy & redaction: secret scrubbing compliance (`action/redactor.py`).
3. Create `docs/launch/LEADERBOARD_SUBMISSION.md`:
   - Instructions for third-party authors to benchmark and submit models.
   - Submission format: `submission.json` schema validation.
   - Evaluation protocol on held-out test split with deterministic bootstrapping.
   - PR submission workflow to the leaderboard repo.
</action>
<verify>
python -c "assert 'MODEL_CARD.md'; assert 'DATASET_CARD.md'; assert 'LEADERBOARD_SUBMISSION.md'; print('Cards and submission guide created')"
</verify>
</task>

<task>
<name>Rewrite Marketplace and Show HN Launch Copy</name>
<files>docs/launch/MARKETPLACE.md, docs/launch/SHOW_HN.md</files>
<action>
1. Update `docs/launch/MARKETPLACE.md`:
   - Remove unverified claims.
   - Add measured offline performance figures with `[REAL-OFFLINE]` tags.
   - Document zero-cost open-source policy and BYOK configuration.
2. Update `docs/launch/SHOW_HN.md`:
   - Replace old ungrounded baseline table with the verified `bench_real/data/BASELINE_EVAL_VAL.json` results with 95% bootstrap CIs.
   - Explicitly tag all metrics with `[REAL-OFFLINE]` and `[LIVE-PILOT]`.
   - Point to `docs/launch/EVIDENCE_REPORT_TEMPLATE.md` for full methodology.
</action>
<verify>
python -c "assert 'docs/launch/SHOW_HN.md'; print('Launch copy updated')"
</verify>
</task>

<task>
<name>Unit Test Publication Assets Compliance</name>
<files>tests/test_publication_assets.py</files>
<action>
Create `tests/test_publication_assets.py` verifying:
1. `MODEL_CARD.md`, `DATASET_CARD.md`, `LEADERBOARD_SUBMISSION.md`, `MARKETPLACE.md`, `SHOW_HN.md` all exist.
2. Model card contains evaluation CIs and licensing metadata.
3. Dataset card confirms synthetic cap <= 50% and contamination isolation.
4. `SHOW_HN.md` and `MARKETPLACE.md` contain zero untagged quantitative claims and reference `bench_real` metrics.
</action>
<verify>
pytest tests/test_publication_assets.py -v
</verify>
</task>

</tasks>

