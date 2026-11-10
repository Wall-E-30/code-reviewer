# Summary: Plan 09-01 — bench_real Schema & Real PR Collectors (REAL-01)

## Delivered Deliverables
1. **Pydantic Data Contracts (`bench_real/schema.py`)**:
   - `RealBenchmarkCase`: Full metadata schema tracking repository provenance, PR/commit URLs, base/head SHAs, permissive OSI licenses, languages, unified diffs, original/modified code, clean diff flags, and consensus actionability derivation.
   - `SourceType`: Enum capturing the 4 real-world PR sources:
     - `REVIEW_FLAGGED_BUG` (Source A)
     - `REVERTED_OR_FIXED_PR` (Source B)
     - `SECURITY_ADVISORY_CVE` (Source C)
     - `CLEAN_MERGED_PR` (Source D)
   - `AnnotatorVote` and `RealFinding`: Schemas for human labeling and spatial bug localization.
2. **Provenance Collectors (`bench_real/collectors/`)**:
   - `BaseCollector`: Enforces OSI-approved license checks, respect for GitHub API rate limits (exponential backoff on 429/403), hard timeout ceiling $\le 10$s, and strict blacklisting of any repository ever used in training or v1.0 test sets.
   - `ReviewedBugsCollector`: Mines PRs where human reviewers flagged issues that triggered code amendments before merge.
   - `RevertsAndFixesCollector`: Mines regression-causing PRs later reverted or followed by linked bug-fix commits.
   - `SecurityCVECollector`: Mines CVE security patches using pre-fix code as buggy input.
   - `CleanPRsCollector`: Mines pristine, unreverted PRs representing benign changes to benchmark false-positive rate.
   - `CandidateMiner`: Coordinates mining across 8 target repositories (`tornado`, `aiohttp`, `starlette`, `datasette`, `bottle`, `moment`, `dayjs`, `node-glob`), producing 320 candidate cases into `bench_real/data/candidates.json`.
3. **Automated Verification**:
   - `tests/test_bench_real_schema_and_collectors.py`: 4/4 tests passing in 0.68s.
   - Zero overlap with blacklisted repositories verified.

