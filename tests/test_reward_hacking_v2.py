"""
tests/test_reward_hacking_v2.py

Red-team reward hacking audit suite v2 (TRAIN2-03):
Verifies that advanced degenerate and gaming policies cannot achieve positive rewards under RewardVersion v2.0.0:
1. Linter copycat policy: Copying or verbatim repeating raw linter messages incurs copycat penalty.
2. Hedged generic comment policy: Vacuous non-actionable platitudes incur generic penalties.
3. Linter proximity spam policy: Clustering comments near linter lines without suggestions incurs proximity penalties.
4. Reward versioning metadata: Confirms breakdown tracking and version compatibility.
"""

import pytest
from bench.schema import FindingCategory, FindingSeverity, GroundTruthFinding, ReviewComment
from rl.reward import RewardVersion, VerifiableRewardCalculator


@pytest.fixture
def calculator_v2():
    return VerifiableRewardCalculator(version=RewardVersion.V2_0_0)


@pytest.fixture
def sample_findings():
    return [
        GroundTruthFinding(
            finding_id="sec-01",
            line_start=10,
            line_end=10,
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.CRITICAL,
            description="SQL injection via raw string formatting",
            file_path="app.py",
        )
    ]


def test_linter_copycat_policy(calculator_v2, sample_findings):
    """
    Degenerate Policy 6: Linter Copycat.
    Repeating raw linter diagnostics verbatim must be detected and penalized.
    """
    raw_linter_msgs = [
        "F401 'os' imported but unused",
        "W0611: Unused import sys in line 2",
    ]

    # Policy parrots the linter message verbatim
    copycat_comments = [
        ReviewComment(
            file_path="app.py",
            line_number=2,
            category=FindingCategory.STYLE,
            comment="F401 'os' imported but unused",
            suggestion=None,
        )
    ]

    reward, breakdown = calculator_v2.compute_reward(
        comments=copycat_comments,
        ground_truth=sample_findings,
        is_clean_diff=False,
        linter_messages=raw_linter_msgs,
    )

    assert breakdown["linter_copycat_penalties"] >= 1
    assert breakdown["reward_version"] == "2.0.0"
    assert reward <= 0.0


def test_hedged_generic_comment_policy(calculator_v2, sample_findings):
    """
    Degenerate Policy 7: Hedged Generic Platitudes.
    Vague, vacuous comments without actionable code references must be penalized.
    """
    generic_comments = [
        ReviewComment(
            file_path="app.py",
            line_number=10,
            category=FindingCategory.BUG,
            comment="Consider checking for edge cases in this implementation.",
            suggestion=None,
        ),
        ReviewComment(
            file_path="app.py",
            line_number=15,
            category=FindingCategory.BUG,
            comment="Ensure proper error handling is implemented here.",
            suggestion=None,
        ),
    ]

    reward, breakdown = calculator_v2.compute_reward(
        comments=generic_comments,
        ground_truth=sample_findings,
        is_clean_diff=False,
    )

    assert breakdown["hedged_generic_penalties"] >= 2
    assert reward <= 0.0


def test_linter_proximity_spam_policy(calculator_v2, sample_findings):
    """
    Degenerate Policy 8: Linter Proximity Spamming.
    Blindly commenting within 1 line of linter locations without fix suggestions must be penalized.
    """
    linter_lines = [5, 20]

    # Comments posted directly at lines 5 and 21 without actionable code replacement suggestions
    proximity_comments = [
        ReviewComment(
            file_path="app.py",
            line_number=5,
            category=FindingCategory.BUG,
            comment="Potential issue identified near here.",
            suggestion=None,
        ),
        ReviewComment(
            file_path="app.py",
            line_number=21,
            category=FindingCategory.BUG,
            comment="Something might be wrong around this block.",
            suggestion=None,
        ),
    ]

    reward, breakdown = calculator_v2.compute_reward(
        comments=proximity_comments,
        ground_truth=sample_findings,
        is_clean_diff=False,
        linter_lines=linter_lines,
    )

    assert breakdown["linter_proximity_penalties"] >= 2
    assert reward <= 0.0


def test_reward_version_backward_compatibility(sample_findings):
    """V1_0_0 calculator should not apply v2 specific degenerate penalties."""
    calc_v1 = VerifiableRewardCalculator(version=RewardVersion.V1_0_0)
    comments = [
        ReviewComment(
            file_path="app.py",
            line_number=10,
            category=FindingCategory.BUG,
            comment="Consider checking for edge cases in this implementation.",
            suggestion=None,
        )
    ]
    _, breakdown = calc_v1.compute_reward(
        comments=comments,
        ground_truth=sample_findings,
        is_clean_diff=False,
    )

    assert breakdown["reward_version"] == "1.0.0"
    assert breakdown["hedged_generic_penalties"] == 0
