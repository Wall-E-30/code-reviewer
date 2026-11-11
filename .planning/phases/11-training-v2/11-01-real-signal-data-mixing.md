---
phase: 11-training-v2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - rl/training_v2/__init__.py
  - rl/training_v2/data_mixer.py
  - data/training_v2/manifest.json
  - tests/test_data_mixing_v2.py
autonomous: true
requirements:
  - TRAIN2-01
must_haves:
  truths:
    - Real mined review data, pilot feedback, and hard negatives are merged into a unified training dataset.
    - Synthetic data is strictly capped at <= 50% of the training mixture.
    - Repositories in bench_real (val.json, test_locked.json) are strictly excluded via contamination checks.
    - Cryptographic SHA-256 data hashes are computed and logged in data/training_v2/manifest.json.
  artifacts:
    - rl/training_v2/data_mixer.py
    - data/training_v2/manifest.json
    - tests/test_data_mixing_v2.py
---

<objective>
Implement the Real Signal Data Mixing Pipeline (`TRAIN2-01`).
Combine real mined reviews (excluding bench_real repos), opt-in pilot feedback, and hard negatives, with synthetic data capped at <= 50%, logging SHA-256 slice hashes in a cryptographic manifest.
</objective>

<tasks>

<task type="tracer">
<name>Build Data Mixer and Split Generation</name>
<files>rl/training_v2/__init__.py, rl/training_v2/data_mixer.py</files>
<action>
1. Create `rl/training_v2/__init__.py`.
2. Create `rl/training_v2/data_mixer.py`:
   - Enforce contamination exclusion: verify every candidate repo against `bench_real` splits (`val.json`, `test_locked.json`) using `ContaminationChecker`.
   - Ingest 4 data streams:
     a) Real mined reviews from historical PR candidates.
     b) Opt-in pilot feedback (maintainer reactions, positive/negative review ratings).
     c) Hard negatives (clean diffs and benign edits without review comments).
     d) Synthetic examples (capped strictly at <= 50% of the combined total).
   - Balance datasets into `train_v2.json` and `val_v2.json`.
   - Calculate cryptographic SHA-256 hashes per slice and write `data/training_v2/manifest.json`.
</action>
<verify>
python -c "from rl.training_v2.data_mixer import DataMixer; dm = DataMixer(); stats = dm.build_mixture(); assert stats['synthetic_ratio'] <= 0.50; print('Data mixer verified')"
</verify>
</task>

<task>
<name>Unit Test Data Mixing and Contamination Guard</name>
<files>tests/test_data_mixing_v2.py</files>
<action>
Create `tests/test_data_mixing_v2.py` verifying:
1. Synthetic data ratio is strictly <= 50%.
2. No repository from `bench_real/splits/` appears in training data.
3. Cryptographic SHA-256 manifest is generated and matches file contents.
4. Hard negatives and pilot feedback records are correctly labeled.
</action>
<verify>
pytest tests/test_data_mixing_v2.py -v
</verify>
</task>

</tasks>

