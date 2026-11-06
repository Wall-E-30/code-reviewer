"""
tests/test_review_env.py

Unit tests for Gymnasium ReviewEnv (RL-01):
- Environment reset and observation schema
- Action processing (post_comment and terminate)
- Truncation on step ceiling
- Reward computation on termination
- OpenEnv specification export
"""

import pytest
from bench.schema import BenchmarkCase, FindingCategory, FindingSeverity, GroundTruthFinding
from rl.env import ReviewEnv, create_default_case, export_openenv_spec
from rl.memory import RepoConventionMemory


def test_review_env_reset():
    """Verify reset returns expected observation and info dictionary."""
    env = ReviewEnv()
    obs, info = env.reset()

    # Observation keys
    assert "diff" in obs
    assert "file_content" in obs
    assert "file_path" in obs
    assert "language" in obs
    assert "active_conventions" in obs

    # Types
    assert isinstance(obs["diff"], str)
    assert isinstance(obs["file_content"], str)
    assert isinstance(obs["active_conventions"], list)

    # Info dictionary
    assert "case_id" in info
    assert "repository" in info
    assert "is_clean_diff" in info


def test_review_env_post_comment():
    """Verify posting a comment updates environment state."""
    env = ReviewEnv()
    env.reset()

    action = {
        "action_type": "post_comment",
        "line_number": 2,
        "category": "security",
        "comment": "Avoid dynamic eval",
        "suggestion": "sum(items)",
    }

    obs, reward, terminated, truncated, info = env.step(action)

    assert not terminated
    assert not truncated
    assert env.current_step == 1
    assert len(env.posted_comments) == 1
    assert info["action"] == "post_comment"
    assert info["comments_count"] == 1


def test_review_env_terminate_and_reward():
    """Verify terminating returns terminal flag and verifiable reward."""
    env = ReviewEnv()
    env.reset()

    # Post an accurate finding matching default case ground truth (line 2, security)
    env.step({
        "action_type": "post_comment",
        "line_number": 2,
        "category": "security",
        "comment": "Unsafe eval sink",
        "suggestion": "    # safe code",
    })

    obs, reward, terminated, truncated, info = env.step({"action_type": "terminate"})

    assert terminated is True
    assert truncated is False
    assert reward > 0.0  # Security hit (+1.50) + syntax bonus (+0.50)
    assert info["security_hits"] >= 1
    assert "total_reward" in info


def test_review_env_truncation():
    """Verify environment truncates when max_steps is reached."""
    env = ReviewEnv(max_steps=3)
    env.reset()

    env.step({"action_type": "post_comment", "line_number": 1, "comment": "Note 1"})
    env.step({"action_type": "post_comment", "line_number": 1, "comment": "Note 2"})
    obs, reward, terminated, truncated, info = env.step({
        "action_type": "post_comment", "line_number": 1, "comment": "Note 3"
    })

    assert truncated is True
    assert terminated is False
    assert env.current_step == 3
    assert "total_reward" in info


def test_review_env_custom_options():
    """Verify reset accepts custom options with BenchmarkCase."""
    case = BenchmarkCase(
        case_id="custom-clean-case",
        repository="org/repo",
        language="python",
        file_path="clean.py",
        original_code="x = 1\n",
        modified_code="x = 2\n",
        diff="@@ -1 +1 @@\n-x = 1\n+x = 2\n",
        split="dev",
        is_clean_diff=True,
    )

    env = ReviewEnv()
    obs, info = env.reset(options={"case": case})

    assert info["case_id"] == "custom-clean-case"
    assert info["is_clean_diff"] is True
    assert "x = 2" in obs["diff"]


def test_review_env_with_active_conventions():
    """Verify active conventions are reflected in observation."""
    mem = RepoConventionMemory()
    mem.add_convention("Enforce PascalCase for class names", category="naming")
    mem.add_convention("Do not commit debug print statements", category="quality")

    env = ReviewEnv(convention_memory=mem)
    obs, _ = env.reset()

    assert len(obs["active_conventions"]) == 2
    assert "Enforce PascalCase for class names" in obs["active_conventions"]


def test_export_openenv_spec():
    """Verify OpenEnv specification schema."""
    spec = export_openenv_spec()
    assert spec["env_id"] == "AionReviewEnv-v0"
    assert "observation_space" in spec
    assert "action_space" in spec
    assert "post_comment" in spec["action_space"]["actions"]
    assert "terminate" in spec["action_space"]["actions"]
    assert spec["reward_range"] == [-10.0, 10.0]
