---
phase: 09-real-data-evaluation
plan: 03
type: execute
wave: 2
depends_on:
  - 09-01
files_modified:
  - bench_real/contamination.py
  - rl/data_engine/isolation.py
  - tests/test_bench_real_contamination.py
autonomous: true
requirements:
  - REAL-03
must_haves:
  truths:
    - MinHash fuzzy diff hashing (k-shingles with permutation hashing) detects near-duplicate diff hunks with customizable Jaccard threshold.
    - Isolation guard checks repos, file paths, and fuzzy diffs across SFT episodes, GRPO training data, verifier pairs, and bench_real.
    - Post-model-cutoff date slicing partitions benchmark candidates into pre-cutoff and post-cutoff sets.
    - Contamination report generator produces detailed audit breakdown with zero false assumptions.
  artifacts:
    - bench_real/contamination.py
    - tests/test_bench_real_contamination.py
---

<objective>
Implement extended contamination and MinHash fuzzy diff isolation guard (`REAL-03`).
Ensure zero data leakage between training pipelines (SFT, GRPO, verifier) and `bench_real` across exact hashes, repository names, file paths, fuzzy diff similarity, and post-cutoff temporal slices.
</objective>

<tasks>

<task type="tracer">
  <name>Build MinHash Fuzzy Diff Engine and Extended Leakage Guard</name>
  <files>bench_real/contamination.py</files>
  <action>
1. Implement `MinHashFingerprint`:
   - Tokenizes normalized diffs into character or word $k$-shingles ($k=5$).
   - Computes $N=64$ or $128$ min-hash values using deterministic salted universal hash functions.
   - Calculates estimated Jaccard similarity between two fingerprints.
2. Implement `ExtendedContaminationGuard`:
   - Scans against SFT training episodes, GRPO episodes, and verifier datasets.
   - Rejects candidate cases if:
     a) Repository is blacklisted or matches any training repo.
     b) Exact SHA-256 diff hash collision occurs.
     c) MinHash Jaccard similarity exceeds threshold (e.g. $\ge 0.70$).
     d) Specific commit SHA or PR URL appears in training sources.
3. Add post-model-cutoff date slicing helper: filters PRs created after a specified cutoff timestamp (e.g. 2024-01-01 or 2024-06-01) to benchmark on unseen distribution.
  </action>
  <verify>
python -c "from bench_real.contamination import ExtendedContaminationGuard, MinHashFingerprint; print('MinHash engine ready')"
  </verify>
</task>

<task>
  <name>Build Contamination Report Generator and Test Suite</name>
  <files>bench_real/contamination.py, tests/test_bench_real_contamination.py</files>
  <action>
1. Implement `generate_contamination_report(bench_cases, training_sources)` in `bench_real/contamination.py`:
   - Generates structured summary with exact collision count, repo overlap count, fuzzy near-duplicate count, and post-cutoff breakdown.
   - Produces Markdown and JSON reports.
2. Add comprehensive test suite in `tests/test_bench_real_contamination.py`:
   - Verifies identical diffs have Jaccard = 1.0.
   - Verifies distinct diffs have low Jaccard ($< 0.20$).
   - Verifies near-duplicate diff detection ($\ge 0.70$).
   - Verifies repo overlap and file path filtering.
   - Verifies post-cutoff temporal partitioning.
  </action>
  <verify>
python -m pytest tests/test_bench_real_contamination.py -v
  </verify>
</task>

</tasks>

