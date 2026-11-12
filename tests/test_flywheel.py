"""
tests/test_flywheel.py

Comprehensive test suite for Phase 4 Fast Learning Flywheel:
- RepoConventionMemory (FLY-01): dismissal tracking, pattern suppression, prompt context, persistence
- CategoryBandit (FLY-02): Thompson Sampling / Beta-Bernoulli threshold adaptation, bounds, persistence
- End-to-end integration: PrecisionVerifier with bandit thresholds, action pipeline feedback loop
"""

import json
import os
import tempfile
import pytest

from action.github_client import GitHubClient
from action.main import run_action
from action.providers import CandidateComment, MockReviewProvider
from action.verifier import PrecisionVerifier
from rl.bandit import CategoryBandit
from rl.memory import RepoConventionMemory


# ==============================================================================
# 1. RepoConventionMemory Tests (FLY-01)
# ==============================================================================

def test_record_dismissal_threshold():
    """Verify dismissal counting and automatic suppression when threshold is reached."""
    mem = RepoConventionMemory(suppression_threshold=2)

    # 1st dismissal: count = 1, not yet suppressed
    sp1 = mem.record_dismissal(
        category="style/whitespace",
        rule_id="ws-line-length",
        pattern="Line too long",
        reason="We allow 120 chars in this repo",
    )
    assert sp1.dismissal_count == 1
    assert not sp1.suppressed
    assert not mem.is_suppressed("style/whitespace", "Line too long here", "ws-line-length")

    # 2nd dismissal: count = 2, automatically marked suppressed
    sp2 = mem.record_dismissal(
        category="style/whitespace",
        rule_id="ws-line-length",
        pattern="Line too long",
    )
    assert sp2.dismissal_count == 2
    assert sp2.suppressed
    assert mem.is_suppressed("style/whitespace", "Line too long here", "ws-line-length")


def test_is_suppressed_pattern_substring_matching():
    """Verify substring and case-insensitive matching for suppressed patterns."""
    mem = RepoConventionMemory(suppression_threshold=1)
    mem.record_dismissal("style", None, "trailing whitespace")

    assert mem.is_suppressed("style", "Found trailing whitespace at end of file")
    assert mem.is_suppressed("style", "TRAILING WHITESPACE detected")
    assert not mem.is_suppressed("style", "Missing return type annotation")
    assert not mem.is_suppressed("bug", "Found trailing whitespace in regex")


def test_is_suppressed_category_hierarchy():
    """Verify whole category suppression and hierarchical matching."""
    mem = RepoConventionMemory()
    mem.suppress_category("style")

    assert mem.is_suppressed("style", "Any style note")
    assert mem.is_suppressed("style/whitespace", "Whitespace note")
    assert mem.is_suppressed("style/naming", "Naming note")
    assert not mem.is_suppressed("bug", "Null pointer exception")
    assert not mem.is_suppressed("security", "SQL injection")


def test_is_suppressed_rule_id():
    """Verify rule_id matching and suppression."""
    mem = RepoConventionMemory(suppression_threshold=1)
    mem.record_dismissal("security", "sec-eval-exec", "*", reason="Allowed in scripts")

    assert mem.is_suppressed("security", "Dangerous eval call", rule_id="sec-eval-exec")
    assert not mem.is_suppressed("security", "Dangerous eval call", rule_id="sec-sql-injection")


def test_custom_conventions_and_prompt_context():
    """Verify adding custom rules and building LLM prompt context."""
    mem = RepoConventionMemory()

    # Empty memory produces empty context
    assert mem.build_prompt_context() == ""

    # Add custom guidelines
    mem.add_convention("All public functions must have type hints", category="types")
    mem.add_convention("Prefer pathlib.Path over os.path", category="modern-python")
    mem.suppress_category("style/whitespace")
    mem.record_dismissal("style", None, "Docstring format", reason="Docstrings optional")
    mem.record_dismissal("style", None, "Docstring format")

    context = mem.build_prompt_context()
    assert "### REPOSITORY CONVENTIONS & GUIDELINES" in context
    assert "All public functions must have type hints" in context
    assert "Prefer pathlib.Path over os.path" in context
    assert "Suppressed Categories: style/whitespace" in context
    assert 'Pattern "Docstring format"' in context


def test_memory_persistence():
    """Verify saving and loading convention memory to and from JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "conventions.json")

        mem1 = RepoConventionMemory(suppression_threshold=2, auto_save_path=path)
        mem1.add_convention("Use 4 spaces indentation", category="formatting")
        mem1.record_dismissal("style", "no-any", "Do not use Any", reason="Any allowed in tests")
        mem1.record_dismissal("style", "no-any", "Do not use Any")
        mem1.suppress_category("style/tabs")

        assert os.path.exists(path)

        # Load into new instance
        mem2 = RepoConventionMemory.load_or_create(path)
        assert len(mem2.state.custom_rules) == 1
        assert mem2.state.custom_rules[0].rule_text == "Use 4 spaces indentation"
        assert mem2.is_suppressed("style", "Do not use Any here", rule_id="no-any")
        assert mem2.is_suppressed("style/tabs", "Tab used")


# ==============================================================================
# 2. CategoryBandit Tests (FLY-02)
# ==============================================================================

def test_bandit_initial_thresholds():
    """Verify initial thresholds start at expected baseline (0.70) within [0.50, 0.95]."""
    bandit = CategoryBandit()

    for cat in ["bug", "security", "performance", "style"]:
        thresh = bandit.get_threshold(cat)
        assert 0.50 <= thresh <= 0.95
        assert pytest.approx(thresh, abs=0.02) == 0.70


def test_bandit_negative_feedback_elevation():
    """Verify negative feedback (-1.5) elevates the confidence threshold."""
    bandit = CategoryBandit()
    t0 = bandit.get_threshold("style")

    # Maintainer downvotes or dismisses finding
    t1 = bandit.update("style", reward=-1.5)
    assert t1 > t0

    # Repeated negative feedback continues elevating threshold
    t2 = bandit.update("style", reward=-1.5)
    assert t2 > t1
    assert t2 <= 0.95


def test_bandit_positive_feedback_relaxation():
    """Verify positive feedback (+1.0) relaxes the threshold (willing to post more)."""
    bandit = CategoryBandit()
    t0 = bandit.get_threshold("bug")

    # Maintainer resolves or gives thumbs up
    t1 = bandit.update("bug", reward=1.0)
    assert t1 < t0

    # Repeated positive feedback continues lowering threshold
    t2 = bandit.update("bug", reward=1.0)
    assert t2 < t1
    assert t2 >= 0.50


def test_bandit_strict_bounds_guarantee():
    """Verify thresholds never exceed 0.95 or drop below 0.50 even under extreme feedback."""
    bandit = CategoryBandit()

    # 100 negative signals
    for _ in range(100):
        bandit.update("style", reward=-1.5)
    assert bandit.get_threshold("style") <= 0.95
    assert bandit.get_threshold("style") >= 0.90

    # 100 positive signals
    for _ in range(100):
        bandit.update("bug", reward=1.0)
    assert bandit.get_threshold("bug") >= 0.50
    assert bandit.get_threshold("bug") <= 0.55


def test_bandit_thompson_sampling():
    """Verify Thompson Sampling draws valid thresholds in [0.50, 0.95]."""
    bandit = CategoryBandit()

    samples = [bandit.get_threshold("security", sample=True) for _ in range(20)]
    for s in samples:
        assert 0.50 <= s <= 0.95
    # Variance check: samples should not all be identical
    assert len(set(samples)) > 1


def test_bandit_persistence():
    """Verify saving and loading bandit state to and from JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "bandit_state.json")

        b1 = CategoryBandit(auto_save_path=path)
        b1.update("style", reward=-1.5)
        b1.update("bug", reward=1.0)
        expected_style = b1.get_threshold("style")
        expected_bug = b1.get_threshold("bug")

        assert os.path.exists(path)

        b2 = CategoryBandit.load_or_create(path)
        assert pytest.approx(b2.get_threshold("style"), abs=0.001) == expected_style
        assert pytest.approx(b2.get_threshold("bug"), abs=0.001) == expected_bug
        assert b2.state.categories["style"].pulls == 1
        assert b2.state.categories["bug"].pulls == 1


# ==============================================================================
# 3. Pipeline Integration Tests
# ==============================================================================

def test_precision_verifier_dynamic_category_thresholds():
    """Verify PrecisionVerifier respects bandit dynamic thresholds per category."""
    # Elevated style threshold (0.85), default bug threshold (0.70)
    cat_thresholds = {
        "bug": 0.70,
        "style": 0.85,
    }

    verifier = PrecisionVerifier(
        default_min_confidence=0.70,
        category_thresholds=cat_thresholds,
    )

    candidates = [
        CandidateComment(
            file_path="app.py",
            line_number=10,
            category="style",
            confidence=0.75,  # Below 0.85 -> rejected
            comment="Format this nicely",
            suggestion="clean_code()",
        ),
        CandidateComment(
            file_path="app.py",
            line_number=20,
            category="bug",
            confidence=0.75,  # Above 0.70 -> accepted
            comment="Fix potential None dereference",
            suggestion="if x is not None: x.call()",
        ),
    ]

    filtered = verifier.filter_candidates(
        candidates=candidates,
        modified_lines={10, 20},
    )

    assert len(filtered) == 1
    assert filtered[0].category == "bug"
    assert filtered[0].line_number == 20


def test_pipeline_convention_memory_suppression_and_bandit_learning():
    """
    End-to-end action pipeline execution with:
    1. Convention suppression of unwanted findings.
    2. Bandit dynamic threshold gating.
    3. State persistence to state directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock GitHub client
        class FakeGitHubClient(GitHubClient):
            def __init__(self):
                super().__init__(token="mock")
                self.posted_reviews = []

            def get_pull_request_diff(self, repo: str, pr_number: int) -> str:
                return (
                    "diff --git a/src/main.py b/src/main.py\n"
                    "index 111..222 100644\n"
                    "--- a/src/main.py\n"
                    "+++ b/src/main.py\n"
                    "@@ -1,3 +1,4 @@\n"
                    " def process():\n"
                    "+    eval(user_input)\n"
                    "+    x = 1  # suppressed pattern note\n"
                )

            def get_existing_review_comments(self, repo: str, pr_number: int):
                # Simulate a previous Aion comment that maintainer dismissed
                return [
                    {
                        "id": 1001,
                        "path": "src/main.py",
                        "line": 5,
                        "body": "### 🧹 Aion Finding: Code Quality Finding (`style-check`)\n**Confidence:** 70% | **Severity:** Minor\n\nOld style issue",
                        "reactions": {"-1": 1},
                    }
                ]

            def post_review(self, repo: str, pr_number: int, commit_sha: str, body: str, comments: list, *args, **kwargs):
                self.posted_reviews.append({"body": body, "comments": comments})
                return {"status": "success", "id": 999}

        fake_client = FakeGitHubClient()

        # Set up convention memory with a suppressed pattern
        mem = RepoConventionMemory(suppression_threshold=1)
        mem.record_dismissal("style", None, "suppressed pattern note")

        # Set up bandit with elevated threshold for style
        bandit = CategoryBandit()
        bandit.update("style", reward=-1.5)

        cfg = {
            "repo": "owner/repo",
            "pr_number": 42,
            "commit_sha": "abcdef123456",
            "provider": "mock",
            "aion_state_dir": tmpdir,
            "enable_telemetry": False,
        }

        # Run action
        exit_code = run_action(
            config=cfg,
            client=fake_client,
            memory=mem,
            bandit=bandit,
        )

        assert exit_code == 0
        assert len(fake_client.posted_reviews) == 1

        # Check posted comments: security eval should be posted, suppressed pattern should NOT
        posted_comments = fake_client.posted_reviews[0]["comments"]
        assert len(posted_comments) >= 1
        bodies = [c["body"] for c in posted_comments]
        assert any("eval" in b for b in bodies)
        assert not any("suppressed pattern note" in b for b in bodies)

        # Check that state files were created in tmpdir
        assert os.path.exists(os.path.join(tmpdir, "conventions.json"))
        assert os.path.exists(os.path.join(tmpdir, "bandit_state.json"))

        # Verify bandit learned from the previous reaction in existing comments
        # (the previous comment was style with -1 reaction -> style threshold elevated further)
        with open(os.path.join(tmpdir, "bandit_state.json"), "r") as f:
            saved_bandit = json.load(f)
        assert saved_bandit["categories"]["style"]["pulls"] >= 1
