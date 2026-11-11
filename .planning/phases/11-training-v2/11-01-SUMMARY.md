# Phase 11 Plan 01: Real Signal Data Mixing Summary (TRAIN2-01)

**Execution Date:** 2026-11-11  
**Phase:** 11-training-v2  
**Wave:** 1  
**Status:** Completed ✅  

---

## 1. Accomplishments

### 1.1 Real Signal Data Mixing Pipeline (`TRAIN2-01`)
- Implemented `rl/training_v2/data_mixer.py` merging four distinct data streams:
  1. Real mined pull request reviews from approved public open-source repos (`psf/requests`, `pallets/flask`, `tiangolo/fastapi`, `encode/httpx`, `urllib3/urllib3`).
  2. Opt-in pilot maintainer feedback records (maintainer accepted and dismissed actions with explicit dismissal reasons).
  3. Hard negative controls (clean diffs, comment refactors, benign edits).
  4. Synthetic bug data with strict mathematical bounding: $\text{synthetic} / \text{total} \le 0.50$.
- In the generated dataset, the synthetic ratio is strictly 38.46% (well below the 50% ceiling).

### 1.2 Evaluation Contamination Guard (`TRAIN2-01`)
- Embedded strict `bench_real` exclusion: all 5 reserved evaluation repositories (`bottlepy/bottle`, `aio-libs/aiohttp`, `tornadoweb/tornado`, `starlette/starlette`, `simonw/datasette`) and their diff SHA-256 hashes are strictly blocked from entering the training set.

### 1.3 Cryptographic Integrity Manifest (`TRAIN2-01`)
- Generated `data/training_v2/manifest.json` with cryptographic SHA-256 digests for `train_v2.json` and `val_v2.json`, item counts, and stream breakdown.

---

## 2. Verification Results

All 4 tests in `tests/test_data_mixing_v2.py` passed in 0.77s:
- `test_data_mixing_build_and_cap` PASSED
- `test_bench_real_contamination_exclusion` PASSED
- `test_manifest_sha256_cryptographic_verification` PASSED
- `test_hard_negatives_and_pilot_feedback_integrity` PASSED

---

## 3. Files Created / Modified
- `rl/training_v2/__init__.py`
- `rl/training_v2/data_mixer.py`
- `data/training_v2/manifest.json`
- `data/training_v2/train_v2.json`
- `data/training_v2/val_v2.json`
- `tests/test_data_mixing_v2.py`
