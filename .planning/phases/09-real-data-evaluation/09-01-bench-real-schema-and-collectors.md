---
phase: 09-real-data-evaluation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - bench_real/__init__.py
  - bench_real/schema.py
  - bench_real/collectors/__init__.py
  - bench_real/collectors/base.py
  - bench_real/collectors/reviewed_bugs.py
  - bench_real/collectors/reverts_and_fixes.py
  - bench_real/collectors/security_cve.py
  - bench_real/collectors/clean_prs.py
  - bench_real/collectors/candidate_miner.py
  - tests/test_bench_real_schema_and_collectors.py
autonomous: true
requirements:
  - REAL-01
must_haves:
  truths:
    - bench_real/schema.py defines strict Pydantic schemas (RealBenchmarkCase, SourceType, AnnotatorVote, RealFinding).
    - Collectors respect GitHub API rate limits, check OSI licenses, and exclude any repository used in training episodes.
    - All 4 source types are implemented: (a) reviewer-flagged bugs amended later, (b) reverted PRs or bug-fix links, (c) security/CVE advisories with pre-fix diffs, and (d) clean merged PRs never reverted.
    - Candidate miner assembles 300+ candidate cases with deterministic offline fixture fallbacks.
  artifacts:
    - bench_real/schema.py
    - bench_real/collectors/candidate_miner.py
    - tests/test_bench_real_schema_and_collectors.py
---

<objective>
Implement the `bench_real/` benchmark data schema and the 4 real-world PR collectors (`REAL-01`).
Establish candidate pools targeting 300+ cases across 5+ public OSS repositories completely disjoint from training episodes, with rate-limiting and offline fixture fallback support.
</objective>

<tasks>

<task type="tracer">
  <name>Build bench_real Pydantic Schema and Base Collector</name>
  <files>bench_real/__init__.py, bench_real/schema.py, bench_real/collectors/__init__.py, bench_real/collectors/base.py</files>
  <action>
1. Create `bench_real/__init__.py` exporting core classes.
2. Create `bench_real/schema.py` defining:
   - `SourceType` (enum: REVIEW_FLAGGED_BUG, REVERTED_OR_FIXED_PR, SECURITY_ADVISORY_CVE, CLEAN_MERGED_PR)
   - `AnnotatorVote` (annotator_id, actionable, category, notes, timestamp)
   - `RealFinding` (file, line, end_line, category, description, fix_suggestion)
   - `RealBenchmarkCase` (case_id, repo_owner, repo_name, pr_number, pr_url, base_sha, head_sha, commit_url, license, language, diff, original_code, modified_code, source_type, ground_truth_findings, is_clean_diff, annotator_labels, metadata)
3. Create `bench_real/collectors/base.py` with:
   - BaseCollector handling HTTP rate limits (429/403 backoff), OSI license validation (MIT, Apache-2.0, BSD-2/3, ISC), and training repo exclusion.
  </action>
  <verify>
python -c "from bench_real.schema import RealBenchmarkCase, SourceType; print('Schema imported successfully')"
  </verify>
</task>

<task>
  <name>Implement Specific Collectors and Candidate Miner</name>
  <files>bench_real/collectors/reviewed_bugs.py, bench_real/collectors/reverts_and_fixes.py, bench_real/collectors/security_cve.py, bench_real/collectors/clean_prs.py, bench_real/collectors/candidate_miner.py</files>
  <action>
1. Implement `reviewed_bugs.py` (Source A: PR comments flagged bugs that triggered code amendments).
2. Implement `reverts_and_fixes.py` (Source B: Merged PRs that were later reverted or followed by linked bug-fix commits).
3. Implement `security_cve.py` (Source C: CVE security patches, using the pre-fix state as buggy input).
4. Implement `clean_prs.py` (Source D: Merged refactors/docs with zero subsequent reverts or fixes).
5. Implement `candidate_miner.py` orchestrating candidate generation from target repos (e.g., `pallets/flask`, `psf/requests`, `encode/httpx`, `tiangolo/fastapi`, `pydantic/pydantic`), producing $\ge 300$ candidate cases into `bench_real/data/candidates.json` with deterministic offline fixture generation.
  </action>
  <verify>
python -m pytest tests/test_bench_real_schema_and_collectors.py -v
  </verify>
</task>

</tasks>
