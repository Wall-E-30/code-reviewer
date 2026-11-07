---
phase: 05-model-training
plan: 02
type: execute
wave: 2
depends_on: []
files_modified:
  - rl/training/verifier_model.py
  - action/verifier.py
  - tests/test_verifier_model.py
autonomous: true
requirements:
  - TRAIN-02
must_haves:
  truths:
    - Actionability verifier extracts balanced positive and negative comment pairs from verified episodes.
    - Discriminator model predicts actionability score P(actionable) for any proposed review comment given diff context.
    - Temperature scaling calibration ensures well-calibrated probabilities with low Expected Calibration Error (ECE < 0.05).
    - Precision verifier in action/verifier.py integrates learned actionability scores to filter low-confidence comments before posting to pull requests.
  artifacts:
    - rl/training/verifier_model.py
    - action/verifier.py
    - tests/test_verifier_model.py
  key_links:
    - rl/training/verifier_model.py provides actionability scoring to action/verifier.py.
    - Learned actionability model serves as an additional verifiable reward term in Plan 05-03 GRPO loop.
---

<objective>
Train, calibrate, and deploy the Actionability Verifier Model (`TRAIN-02`).
Construct a discriminator that estimates the probability $P(\text{actionable} \mid \text{diff}, \text{comment}) \in [0, 1]$, calibrate logits using temperature scaling to prevent overconfidence, and integrate the verifier into the live PR review pipeline to eliminate nitpicks and false positives.

Purpose: Provide an objective filter that prevents annoying, subjective, or unhelpful comments from ever reaching developers, boosting maintainer trust and acceptance rates.
Output: `rl/training/verifier_model.py`, enhanced `action/verifier.py`, and `tests/test_verifier_model.py`.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-model-training/RESEARCH.md
@action/verifier.py
@rl/reward.py
@data/episodes/training_manifest.json
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Actionability Dataset Extraction and Feature Encoder</name>
  <files>rl/training/verifier_model.py</files>
  <action>
1. In `rl/training/verifier_model.py`, implement `ActionabilityDatasetBuilder`:
   - `extract_pairs_from_episodes(episodes_path: str, max_pairs: int = 2000) -> List[Dict[str, Any]]`:
     - Positive instances ($y = 1$): Real bug hits, accepted PR replays, valid suggestions solving ground-truth defects.
     - Negative instances ($y = 0$): False alarms on non-buggy code, comments emitted on clean diffs, subjective nitpicks ("consider renaming"), syntax-invalid suggestions, zero-delta duplicates.
     - Returns balanced dataset with feature dicts containing: `diff_hunk`, `line_number`, `category`, `comment_text`, `suggestion`, `label`.
2. Implement `ActionabilityFeatureExtractor`:
   - Encodes text pairs into dense/sparse representation:
     - Text similarity between suggestion and modified line.
     - Presence of actionable keywords vs subjective nitpick markers.
     - Syntactic validity score of suggestion.
     - Category one-hot encoding (bug, security, performance, style).
     - Diff locality indicator.
  </action>
  <verify>
python -c "from rl.training.verifier_model import ActionabilityDatasetBuilder, ActionabilityFeatureExtractor; b = ActionabilityDatasetBuilder(); pairs = b.extract_pairs_from_episodes('data/episodes/episodes_stream.jsonl', max_pairs=10); assert len(pairs) > 0; print('Actionability extractor tracer verified')"
  </verify>
</task>

<task>
  <name>Implement Actionability Verifier Classifier and Temperature Calibration</name>
  <files>rl/training/verifier_model.py</files>
  <action>
1. In `rl/training/verifier_model.py`, implement `ActionabilityVerifierModel`:
   - Architecture:
     - Neural classification head or calibrated gradient-boosted/logistic discriminator operating over encoded review features.
     - `fit(train_data: List[Dict[str, Any]], val_data: List[Dict[str, Any]])`:
       - Trains model to minimize binary cross-entropy loss.
       - Fits optimal temperature $T > 0$ via `TemperatureCalibrator` on validation split to minimize Expected Calibration Error (ECE).
     - `predict_proba(diff_hunk: str, comment: str, suggestion: Optional[str] = None, category: str = "bug") -> float`:
       - Returns calibrated probability $P(\text{actionable}) \in [0.0, 1.0]$.
     - `compute_ece(y_true: List[int], y_prob: List[float], n_bins: int = 10) -> float`:
       - Computes empirical Expected Calibration Error, verifying $\text{ECE} < 0.05$.
     - `save(path: str)` / `load(path: str)`: Persists model weights and temperature scaling parameter.
  </action>
  <verify>
python -c "from rl.training.verifier_model import ActionabilityVerifierModel; m = ActionabilityVerifierModel(); mock_data = [{'diff_hunk': '@@ -1 +1 @@', 'comment_text': 'Fix SQL injection', 'suggestion': 'clean()', 'category': 'security', 'label': 1}, {'diff_hunk': '', 'comment_text': 'Nit: whitespace', 'suggestion': None, 'category': 'style', 'label': 0}]; m.fit(mock_data, mock_data); p = m.predict_proba('@@', 'Fix bug', 'x = 1', 'bug'); assert 0.0 <= p <= 1.0; print('Verifier model and calibration verified')"
  </verify>
</task>

<task>
  <name>Integrate Actionability Verifier into PrecisionVerifier and Build Tests</name>
  <files>action/verifier.py, tests/test_verifier_model.py</files>
  <action>
1. In `action/verifier.py`:
   - Update `PrecisionVerifier`:
     - Accept optional `verifier_model: Optional[ActionabilityVerifierModel] = None`.
     - In `filter_candidates()`:
       - If `verifier_model` is present, evaluate $P(\text{actionable})$ for each candidate.
       - Discard candidate if $P(\text{actionable}) < \tau_{\text{actionable}}$ (default: 0.65).
       - Weight candidate ranking combining severity, bandit confidence, and learned actionability score.
2. In `tests/test_verifier_model.py`, build test cases:
   - `test_actionability_pair_extraction()`: Validates positive and negative pair distribution.
   - `test_temperature_scaling_calibration()`: Validates that uncalibrated vs calibrated probabilities achieve low ECE ($<0.05$).
   - `test_nitpick_and_clean_rejection()`: Proves subjective nitpicks and comments on clean diffs receive low actionability ($<0.30$).
   - `test_bug_hit_high_actionability()`: Proves real security and logic bug fixes with valid suggestions receive high actionability ($>0.75$).
   - `test_precision_verifier_integration()`: Verifies end-to-end filtering with `PrecisionVerifier`.
  </action>
  <verify>
python -m pytest tests/test_verifier_model.py -v
  </verify>
</task>

</tasks>

