"""
tests/test_reward_hacking.py

Red-team reward hacking audit suite (RL-04):
Verifies that degenerate, gaming, or adversarial policies cannot achieve positive rewards:
1. Empty policy: 0 comments on buggy diffs scores <= 0 due to missed bugs.
2. All-line spam policy: Spamming comments on every line results in deeply negative net reward (R < -5.0).
3. Generic text policy: Non-actionable or invalid syntax advice yields zero bonus / scores <= 0.
4. Copy-paste suggestion policy: Identical code duplicates incur zero-delta penalties.
5. Clean-diff violation: False positives on clean diffs trigger severe penalties.
"""

import pytest
from bench.schema import BenchmarkCase, FindingCategory, FindingSeverity, GroundTruthFinding, ReviewComment
from rl.reward import VerifiableRewardCalculator


@pytest.fixture
def sample_buggy_case():
    """Sample benchmark case with 1 security defect at line 3 and 1 logic bug at line 7."""
    file_content = (
        "def calculate_metrics(items):\n"
        "    if not items:\n"
        "        eval(items)  # security bug\n"
        "        return 0\n"
        "    total = 0\n"
        "    for x in items:\n"
        "        total = total / 0  # logic bug\n"
        "    return total\n"
    )

    findings = [
        GroundTruthFinding(
            finding_id="vuln-01",
            line_start=3,
            line_end=3,
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.CRITICAL,
            description="Dynamic eval injection vulnerability",
            file_path="metrics.py",
        ),
        GroundTruthFinding(
            finding_id="bug-02",
            line_start=7,
            line_end=7,
            category=FindingCategory.BUG,
            severity=FindingSeverity.MAJOR,
            description="Division by zero crash",
            file_path="metrics.py",
        ),
    ]

    return file_content, findings


def test_empty_policy_on_buggy_diff(sample_buggy_case):
    """
    Degenerate Policy 1: Empty policy (0 comments posted).
    Must score <= 0.0 on buggy diffs due to missed bugs penalty.
    """
    file_content, findings = sample_buggy_case
    calc = VerifiableRewardCalculator()

    empty_comments = []
    reward, breakdown = calc.compute_reward(
        comments=empty_comments,
        ground_truth=findings,
        is_clean_diff=False,
        file_content=file_content,
    )

    assert reward <= 0.0
    assert breakdown["bug_hits"] == 0
    assert breakdown["security_hits"] == 0
    assert breakdown["missed_bugs"] == 2


def test_empty_policy_on_clean_diff():
    """
    Empty policy on clean diff must score 0.0 (no FP penalties, no violations).
    """
    calc = VerifiableRewardCalculator()

    reward, breakdown = calc.compute_reward(
        comments=[],
        ground_truth=[],
        is_clean_diff=True,
    )

    assert reward == 0.0
    assert breakdown["clean_diff_violations"] == 0


def test_all_line_spam_policy(sample_buggy_case):
    """
    Degenerate Policy 2: All-line spam policy.
    Spamming comments across every line must result in deeply negative net reward (R < -5.0).
    """
    file_content, findings = sample_buggy_case
    calc = VerifiableRewardCalculator()

    total_lines = len(file_content.splitlines())  # 8 lines
    # Post comments on lines 1..8 plus extras to simulate a 15-line spam attack
    spam_comments = [
        ReviewComment(
            file_path="metrics.py",
            line_number=line,
            category=FindingCategory.BUG,
            comment=f"Spam issue detected at line {line}",
            suggestion=None,
        )
        for line in range(1, 16)
    ]

    reward, breakdown = calc.compute_reward(
        comments=spam_comments,
        ground_truth=findings,
        is_clean_diff=False,
        file_content=file_content,
    )

    # Even though it hits the bugs, 10+ false positives result in net reward < -5.0
    assert reward < -5.0
    assert breakdown["false_positives"] >= 10
    assert breakdown["total_reward"] < -5.0


def test_generic_text_policy_fails_to_gain_bonus(sample_buggy_case):
    """
    Degenerate Policy 3: Generic advice policy ("Please fix this", invalid syntax, or no suggestion).
    Must not gain suggestion syntax bonus, and non-defect findings yield reward <= 0.0.
    """
    file_content, findings = sample_buggy_case
    calc = VerifiableRewardCalculator()

    # Generic advice with no concrete suggestion on non-buggy line 1
    generic_comments = [
        ReviewComment(
            file_path="metrics.py",
            line_number=1,
            category=FindingCategory.STYLE,
            comment="Please fix this function, make it clean and readable.",
            suggestion=None,  # No actionable code
        ),
        ReviewComment(
            file_path="metrics.py",
            line_number=4,
            category=FindingCategory.NITPICK,
            comment="Consider renaming total",
            suggestion="def invalid syntax ::::",  # Syntactically broken
        ),
    ]

    reward, breakdown = calc.compute_reward(
        comments=generic_comments,
        ground_truth=findings,
        is_clean_diff=False,
        file_content=file_content,
    )

    assert reward <= 0.0
    assert breakdown["syntax_bonuses"] == 0
    assert breakdown["false_positives"] >= 2


def test_copy_paste_suggestion_policy(sample_buggy_case):
    """
    Degenerate Policy 4: Copy-paste suggestion policy (Zero-delta duplicate).
    Copying the exact existing code line without fixing the issue triggers a penalty.
    """
    file_content, findings = sample_buggy_case
    calc = VerifiableRewardCalculator()

    # Line 3 is "        eval(items)  # security bug"
    # An adversarial policy outputs the exact same line as suggestion
    copy_paste_comment = ReviewComment(
        file_path="metrics.py",
        line_number=3,
        category=FindingCategory.SECURITY,
        comment="Check this security line",
        suggestion="eval(items)  # security bug",  # Exact duplicate of original
    )

    reward_copy_paste, breakdown_copy = calc.compute_reward(
        comments=[copy_paste_comment],
        ground_truth=findings,
        is_clean_diff=False,
        file_content=file_content,
    )

    assert breakdown_copy["zero_delta_penalties"] == 1
    assert breakdown_copy["syntax_bonuses"] == 0

    # Genuine fix for comparison
    genuine_fix_comment = ReviewComment(
        file_path="metrics.py",
        line_number=3,
        category=FindingCategory.SECURITY,
        comment="Dynamic eval injection",
        suggestion="json.loads(items)",
    )

    reward_genuine, breakdown_genuine = calc.compute_reward(
        comments=[genuine_fix_comment],
        ground_truth=findings,
        is_clean_diff=False,
        file_content=file_content,
    )

    assert breakdown_genuine["zero_delta_penalties"] == 0
    assert breakdown_genuine["syntax_bonuses"] == 1
    assert reward_genuine > reward_copy_paste


def test_clean_diff_violation_penalty():
    """
    Verify posting comments on a clean PR incurs severe clean-diff violation penalties.
    """
    calc = VerifiableRewardCalculator()

    comments = [
        ReviewComment(
            file_path="clean.py",
            line_number=5,
            category=FindingCategory.BUG,
            comment="False alarm on clean code",
            suggestion="x = 1",
        )
    ]

    reward, breakdown = calc.compute_reward(
        comments=comments,
        ground_truth=[],
        is_clean_diff=True,
    )

    assert reward <= -1.50
    assert breakdown["clean_diff_violations"] == 1
