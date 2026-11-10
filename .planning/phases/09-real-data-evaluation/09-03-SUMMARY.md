# Summary: Plan 09-03 — Contamination & MinHash Guard (REAL-03)

## Delivered Deliverables
1. **MinHash Fuzzy Diff Fingerprinting (`bench_real/contamination.py`)**:
   - `MinHashFingerprint`: Tokenizes normalized diffs into 4-character shingles, computes 64 universal hash permutations modulo Mersenne prime ($2^{31}-1$), and estimates Jaccard similarity.
   - Tested and verified: identical diffs yield Jaccard = 1.0, minor identifier renames yield $\ge 0.65$, and distinct code yields $< 0.25$.
2. **Extended Contamination Guard (`bench_real/contamination.py`)**:
   - `ExtendedContaminationGuard`: Audits candidate cases across:
     - Exact repository name matching against blacklisted training repositories.
     - Normalized SHA-256 diff digest collisions.
     - Relative file path collisions on matching repositories.
     - MinHash fuzzy diff collisions ($\ge 0.70$ Jaccard threshold).
     - Temporal post-model-cutoff slicing (`partition_by_cutoff`) separating pre-cutoff from post-cutoff PRs.
3. **Contamination Audit & Reporting**:
   - `generate_contamination_report`: Audited all 320 candidates in `bench_real/data/candidates.json`.
   - Results: 320/320 clean cases, 0 collisions, 0 repo overlaps, 100% uncontaminated (`bench_real/data/CONTAMINATION_REPORT.md` and `.json`).
4. **Automated Verification**:
   - `tests/test_bench_real_contamination.py`: 4/4 tests passing in 4.87s.
