---
phase: 11-training-v2
plan: 02
type: execute
wave: 2
depends_on:
  - 11-01
files_modified:
  - rl/training_v2/bug_generator.py
  - tests/test_bug_generator_v2.py
autonomous: true
requirements:
  - TRAIN2-02
must_haves:
  truths:
    - Synthetic bugs are generated across standard real bug categories (null/None dereference, boundary error, resource leak, SQL injection, off-by-one).
    - Every generated bug MUST be verified by a test or executable reproduction assertion that passes on clean code and fails on buggy code.
    - Evaluation bugs and training bugs use separate seed/operator sources to guarantee zero test leakage.
  artifacts:
    - rl/training_v2/bug_generator.py
    - tests/test_bug_generator_v2.py
---

<objective>
Implement the Test-Verified LLM Bug Generator (`TRAIN2-02`).
Generate realistic synthetic bugs with guaranteed executable test/reproduction failure verification, maintaining disjoint sources for training vs evaluation bugs.
</objective>

<tasks>

<task type="tracer">
<name>Build Test-Verified Bug Generator</name>
<files>rl/training_v2/bug_generator.py</files>
<action>
1. Create `rl/training_v2/bug_generator.py`:
   - Define `BugCategory` enum (OFF_BY_ONE, NULL_DEREFERENCE, RESOURCE_LEAK, SQL_INJECTION, BOUNDARY_ERROR).
   - Implement `TestVerifiedBugGenerator`:
     - Mutation operators targeting AST structures (loop limits, None checks, file handles, query strings).
     - Execution / reproduction assertion verification: executes test assertion against clean code (must pass) and mutated code (must fail).
     - Source partitioning: `split="train"` vs `split="eval"` use distinct pseudo-random seeds and disjoint operator variations to guarantee evaluation bugs are from a distinct source.
</action>
<verify>
python -c "from rl.training_v2.bug_generator import TestVerifiedBugGenerator; gen = TestVerifiedBugGenerator(); res = gen.generate_verified_bug('def f(x):\n    if x is not None:\n        return x + 1\n    return 0\n'); assert res is not None; print('Bug generator verified')"
</verify>
</task>

<task>
<name>Unit Test Bug Generation and Test Verification</name>
<files>tests/test_bug_generator_v2.py</files>
<action>
Create `tests/test_bug_generator_v2.py` verifying:
1. Every generated bug case contains a reproduction assertion that succeeds on clean code and fails on buggy code.
2. Training bugs and evaluation bugs generated from separate sources/seeds do not overlap.
3. Unsupported or non-failing mutations are safely rejected.
</action>
<verify>
pytest tests/test_bug_generator_v2.py -v
</verify>
</task>

</tasks>

