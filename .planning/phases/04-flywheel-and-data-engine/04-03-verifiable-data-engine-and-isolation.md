---
phase: 04-flywheel-and-data-engine
plan: 03
type: execute
wave: 3
depends_on:
  - 04-01
  - 04-02
files_modified:
  - rl/data_engine/__init__.py
  - rl/data_engine/synthesizer.py
  - rl/data_engine/isolation.py
  - data/episodes/training_manifest.json
  - tests/test_data_engine_isolation.py
autonomous: true
requirements:
  - DATA-01
  - DATA-02
must_haves:
  truths:
    - Data engine generates at least 10,000 verified training episodes spanning synthetic bug injections, clean-diff negatives, and real PR review replays.
    - Leakage guard cryptographically verifies zero SHA-256 hash collision between generated training episodes and Aion-Bench locked test/gold sets.
    - Repository-level isolation permanently excludes all repositories represented in Aion-Bench test splits from the training data engine.
    - All 10,000+ episodes are indexed in data/episodes/training_manifest.json ready for Phase 5 SFT warm-start and GRPO training.
  artifacts:
    - rl/data_engine/synthesizer.py
    - rl/data_engine/isolation.py
    - data/episodes/training_manifest.json
    - tests/test_data_engine_isolation.py
  key_links:
    - rl/data_engine/synthesizer.py generates the training corpus consumed by Phase 5 GRPO.
    - rl/data_engine/isolation.py enforces strict separation from bench/splits/manifest.json.
---

<objective>
Build the scalable verifiable data generation engine that produces $\ge 10,000$ verified training episodes, enforced with strict cryptographic SHA-256 hashing and repository-level isolation to prevent data leakage into Aion-Bench.

Purpose: Provide the massive, verified training dataset required for Phase 5 policy optimization without contaminating benchmark evaluation.
Output: `rl/data_engine/`, `data/episodes/training_manifest.json`, and isolation test suite.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/04-flywheel-and-data-engine/RESEARCH.md
@bench/splits/manifest.json
@bench/schema.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Cryptographic Leakage Guard in rl/data_engine/isolation.py</name>
  <files>rl/data_engine/__init__.py, rl/data_engine/isolation.py</files>
  <action>
1. Create `rl/data_engine/__init__.py`.
2. In `rl/data_engine/isolation.py`, implement `LeakageGuard`:
   - Loads `bench/splits/manifest.json` containing SHA-256 digests of all test cases in `test_locked.json` and `gold.json`.
   - Compiles list of protected repositories present in Aion-Bench test splits.
   - Methods:
     - `compute_episode_hash(episode: Dict[str, Any]) -> str`: Computes normalized SHA-256 digest of original code, modified code, and diff.
     - `is_leaked(episode: Dict[str, Any]) -> bool`:
       - Checks if episode hash matches any hash in `manifest.json`.
       - Checks if episode repository matches any protected benchmark repository.
       - Returns `True` if any contamination is detected.
     - `verify_corpus_isolation(episodes: List[Dict[str, Any]]) -> Dict[str, Any]`:
       - Asserts zero collisions across entire training corpus.
       - Returns isolation audit report.
  </action>
  <verify>
python -c "from rl.data_engine.isolation import LeakageGuard; g = LeakageGuard(); assert hasattr(g, 'is_leaked'); print('Leakage guard verified')"
  </verify>
</task>

<task>
  <name>Build Scalable Episode Synthesizer and Generate 10k+ Episodes</name>
  <files>rl/data_engine/synthesizer.py, data/episodes/training_manifest.json</files>
  <action>
1. In `rl/data_engine/synthesizer.py`:
   - Implement `EpisodeSynthesizer`:
     - Generates verified training episodes using parameterized mutations:
       a. Injected bugs (5,000+ episodes): AST transformations in Python and TypeScript with exact ground-truth anchors.
       b. Clean-diff negatives (3,000+ episodes): Valid refactorings, typing, and whitespace changes with `is_clean_diff=True`.
       c. Real PR replays (2,000+ episodes): Curated and parameterized human review examples with corrective commits.
     - Filters every candidate episode through `LeakageGuard` before inclusion.
     - Saves episodes to compressed streaming JSONL (`data/episodes/episodes_stream.jsonl`) or chunked manifests.
     - Generates `data/episodes/training_manifest.json` indexing:
       - Total episode count ($\ge 10,000$).
       - Language breakdown (Python $\ge 40\%$, TypeScript $\ge 40\%$).
       - Case type distribution (injected, clean negative, real review).
       - Zero-leakage cryptographic certificate.
2. Run synthesizer to generate the full $\ge 10,000$ episode index:
   - `python -m rl.data_engine.synthesizer --target 10000 --output data/episodes/training_manifest.json`.
  </action>
  <verify>
python -c "import json; m = json.load(open('data/episodes/training_manifest.json')); assert m['total_episodes'] >= 10000; assert m['leakage_collisions'] == 0; print(f'10k+ Dataset verified: {m[\"total_episodes\"]} episodes, 0 collisions')"
  </verify>
</task>

<task>
  <name>Implement Data Engine Isolation and Distribution Tests</name>
  <files>tests/test_data_engine_isolation.py</files>
  <action>
1. In `tests/test_data_engine_isolation.py`:
   - Test 1: Assert 0 SHA-256 hash collisions between generated training episodes and `bench/splits/manifest.json`.
   - Test 2: Assert zero repository-level overlap with benchmark test/gold splits.
   - Test 3: Verify total episode count in `training_manifest.json` is $\ge 10,000$.
   - Test 4: Verify language balance ($\ge 40\%$ Python and $\ge 40\%$ TypeScript/JavaScript).
   - Test 5: Verify clean-diff representation ($\ge 25\%$ of episodes are clean negatives to prevent over-commenting).
  </action>
  <verify>
python -m pytest tests/test_data_engine_isolation.py -v
  </verify>
</task>

</tasks>

