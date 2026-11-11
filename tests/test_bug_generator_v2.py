"""
tests/test_bug_generator_v2.py

Verification suite for Plan 11-02 (TRAIN2-02: Test-Verified LLM Bug Generator):
- Executable test/reproduction failure verification
- Verification rejects mutations that fail to break the test
- Disjoint generator sources/seeds between training and evaluation splits
- Category coverage across real bug classes
"""

import pytest
from rl.training_v2.bug_generator import (
    TestVerifiedBugGenerator,
    BugCategory,
    GeneratedBug,
    execute_test_on_code,
)


@pytest.fixture
def generator():
    return TestVerifiedBugGenerator(base_seed=42)


def test_test_verification_invariant(generator):
    """Every generated bug must satisfy: clean passes test, buggy fails test."""
    train_bugs = generator.generate_batch(count=4, split="train")
    assert len(train_bugs) == 4

    for bug in train_bugs:
        assert bug.verified is True
        # 1. Clean code must PASS test
        clean_ok, clean_err = execute_test_on_code(bug.clean_code, bug.test_code)
        assert clean_ok is True, f"Clean code failed test: {clean_err}"

        # 2. Buggy code must FAIL test
        buggy_ok, buggy_err = execute_test_on_code(bug.buggy_code, bug.test_code)
        assert buggy_ok is False, f"Buggy code unexpectedly passed test for {bug.bug_id}"
        assert buggy_err is not None


def test_invalid_mutation_rejected_by_verifier(generator):
    """Verifier must reject mutations if the buggy code does not cause test failure."""
    clean = "def add(a, b): return a + b\n"
    # Buggy mutation that doesn't affect the specific test assertion
    buggy = "def add(a, b):\n    # Just a comment change\n    return a + b\n"
    test = "assert add(2, 3) == 5\n"

    # Because buggy code still passes, verification must return False
    verified = generator.verify_bug_candidate(clean, buggy, test)
    assert verified is False


def test_source_isolation_between_train_and_eval(generator):
    """Evaluation bugs must originate from distinct templates and sources than training bugs."""
    train_bugs = generator.generate_batch(count=4, split="train")
    eval_bugs = generator.generate_batch(count=3, split="eval")

    train_bug_codes = {b.buggy_code.strip() for b in train_bugs}
    eval_bug_codes = {b.buggy_code.strip() for b in eval_bugs}

    # Disjoint code representations
    intersection = train_bug_codes.intersection(eval_bug_codes)
    assert len(intersection) == 0, f"Leakage detected between train and eval bugs: {intersection}"

    # Verify split tagging
    assert all(b.split == "train" for b in train_bugs)
    assert all(b.split == "eval" for b in eval_bugs)


def test_generated_bug_diff_and_fix_validity(generator):
    """Generated diffs must be valid unified diffs with non-empty suggestions."""
    bug = generator.generate_verified_bug(clean_code="", split="train")
    assert bug is not None
    assert "--- a/sample.py" in bug.diff
    assert "+++ b/sample.py" in bug.diff
    assert len(bug.suggested_fix) > 0
    assert bug.line_number > 0
    assert bug.category in [c for c in BugCategory]

