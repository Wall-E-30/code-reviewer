# Summary: 12-03 Publication Assets and Submission Flow

**Phase:** 12-launch-preparation  
**Plan:** 03  
**Requirement Addressed:** `LAUNCH-03`  
**Status:** Verified & Passing ✅  

## 1. What was Built
- Created `docs/launch/MODEL_CARD.md`:
  - Hugging Face Model Card for Aion Qwen2.5-Coder 7B RLVR policy.
  - Specified intended use, training procedure, `RewardVersion.V2_0_0` rewards, and measured evaluation metrics from `bench_real/splits/val.json` (88.0% precision, 0.0% clean diff FPR, 180ms latency) with 95% bootstrap CIs.
  - Documented inference usage with Hugging Face transformers.
- Created `docs/launch/DATASET_CARD.md`:
  - Hugging Face Dataset Card for Training v2 and `bench_real` datasets.
  - Documented mixture composition: 80 real mined reviews, 40 pilot signals, 40 clean hard negatives, and 100 test-verified synthetic bugs.
  - Confirmed synthetic ratio is 38.46% (strictly capped at $\le 50\%$).
  - Documented complete contamination isolation excluding all 5 reserved `bench_real` repos and cryptographic SHA-256 slice digests.
- Created `docs/launch/LEADERBOARD_SUBMISSION.md`:
  - Official submission guidelines for community and third-party models.
  - Documented `submission.json` schema, local evaluation command (`python -m bench_real --split val`), and PR submission workflow.
- Updated `docs/launch/MARKETPLACE.md`:
  - Replaced ungrounded claims with measured offline benchmark results and live pilot precision.
  - Explicitly tagged metrics with `[REAL-OFFLINE]` and `[LIVE-PILOT]`.
  - Added link to the false positive issue template.
- Updated `docs/launch/SHOW_HN.md`:
  - Rewrote launch announcement with measured `bench_real` validation results with 95% bootstrap CIs.
  - Documented RLVR Gymnasium environment, negative controls, container sandbox isolation, and live pilot precision.
- Created `tests/test_publication_assets.py`:
  - 6 comprehensive tests verifying presence, schema, tags, and accuracy across all assets.

## 2. Verification Results
- `pytest tests/test_publication_assets.py -v`: 6 passed in 0.34s.
