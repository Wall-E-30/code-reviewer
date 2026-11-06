"""
rl/env.py

Gymnasium Reinforcement Learning Environment for Automated Code Review (RL-01).
Models pull request code review as a standard Markov Decision Process (MDP):
- State/Observation: Unified diff, file content, path, language, and active repository conventions.
- Action: Post an inline review comment with line anchor, category, explanation, and suggestion,
          or terminate review.
- Reward: Verifiable scalar feedback computed from ground-truth hits, false positives, clean-diff
          compliance, and code replacement validity.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import gymnasium as gym
from gymnasium import spaces

from bench.schema import BenchmarkCase, FindingCategory, FindingSeverity, GroundTruthFinding
from rl.memory import RepoConventionMemory
from rl.reward import VerifiableRewardCalculator

logger = logging.getLogger(__name__)


def create_default_case() -> BenchmarkCase:
    """Generate a default BenchmarkCase for standalone environment initialization."""
    original_code = "def process(items):\n    total = 0\n    for i in items:\n        total += i\n    return total\n"
    modified_code = "def process(items):\n    eval(items)\n    return sum(items)\n"
    diff = (
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1,5 +1,4 @@\n"
        " def process(items):\n"
        "-    total = 0\n"
        "-    for i in items:\n"
        "-        total += i\n"
        "-    return total\n"
        "+    eval(items)\n"
        "+    return sum(items)\n"
    )

    finding = GroundTruthFinding(
        finding_id="eval-vuln-01",
        line_start=2,
        line_end=2,
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.CRITICAL,
        description="Insecure dynamic code execution via eval",
        file_path="app.py",
        fix_suggestion="    # Removed unsafe eval\n",
        rule_id="sec-eval",
    )

    return BenchmarkCase(
        case_id="default-case-01",
        repository="aion/sandbox",
        language="python",
        file_path="app.py",
        original_code=original_code,
        modified_code=modified_code,
        diff=diff,
        split="dev",
        is_clean_diff=False,
        ground_truth=[finding],
    )


def export_openenv_spec() -> Dict[str, Any]:
    """
    Export the OpenEnv specification manifest for ReviewEnv.
    Enables zero-friction integration with OpenEnv-compliant training frameworks.
    """
    return {
        "env_id": "AionReviewEnv-v0",
        "version": "1.0.0",
        "description": "Standard Gymnasium environment for autonomous RL-driven code review policies",
        "observation_space": {
            "type": "Dict",
            "keys": {
                "diff": {"type": "Text", "description": "Unified git diff of pull request"},
                "file_content": {"type": "Text", "description": "Full file content of modified file"},
                "file_path": {"type": "Text", "description": "Relative path of file in repository"},
                "language": {"type": "Text", "description": "Programming language (python, typescript, etc.)"},
                "active_conventions": {
                    "type": "Sequence[Text]",
                    "description": "Active repository conventions and preferences",
                },
            },
        },
        "action_space": {
            "type": "Dict",
            "actions": {
                "post_comment": {
                    "line_number": "int: 1-based line number in modified file",
                    "category": "string: 'bug' | 'security' | 'performance' | 'style' | 'nitpick'",
                    "comment": "string: clear description of defect",
                    "suggestion": "string or null: 1-click replacement code",
                },
                "terminate": {
                    "description": "End the review episode",
                },
            },
        },
        "reward_range": [-10.0, 10.0],
        "framework": "gymnasium",
    }


class ReviewEnv(gym.Env):
    """
    Gymnasium reinforcement learning environment for code review agents.
    """

    metadata = {"render_modes": ["human", "ansi"]}

    def __init__(
        self,
        cases: Optional[List[BenchmarkCase]] = None,
        max_steps: int = 10,
        reward_calculator: Optional[VerifiableRewardCalculator] = None,
        convention_memory: Optional[RepoConventionMemory] = None,
    ) -> None:
        super().__init__()
        self.cases = cases or [create_default_case()]
        self.max_steps = max_steps
        self.reward_calculator = reward_calculator or VerifiableRewardCalculator()
        self.convention_memory = convention_memory or RepoConventionMemory()

        self.current_case_idx = 0
        self.current_case: BenchmarkCase = self.cases[0]
        self.current_step = 0
        self.posted_comments: List[Dict[str, Any]] = []
        self.is_terminated = False

        # Define Observation Space
        self.observation_space = spaces.Dict({
            "diff": spaces.Text(max_length=100000),
            "file_content": spaces.Text(max_length=100000),
            "file_path": spaces.Text(max_length=500),
            "language": spaces.Text(max_length=50),
            "active_conventions": spaces.Sequence(spaces.Text(max_length=500)),
        })

        # Define Action Space
        self.action_space = spaces.Dict({
            "action_type": spaces.Text(min_length=1, max_length=20),
            "line_number": spaces.Discrete(100000),
            "category": spaces.Text(min_length=1, max_length=20),
            "comment": spaces.Text(min_length=1, max_length=1000),
            "suggestion": spaces.Text(min_length=0, max_length=1000),
        })

    def _get_obs(self) -> Dict[str, Any]:
        """Construct the observation dictionary from current benchmark case."""
        conventions = [r.rule_text for r in self.convention_memory.state.custom_rules]
        return {
            "diff": self.current_case.diff,
            "file_content": self.current_case.modified_code or self.current_case.original_code,
            "file_path": self.current_case.file_path,
            "language": self.current_case.language,
            "active_conventions": conventions,
        }

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Reset the environment for a new code review episode.
        """
        super().reset(seed=seed)

        self.current_step = 0
        self.posted_comments = []
        self.is_terminated = False

        opts = options or {}
        if "case" in opts and isinstance(opts["case"], BenchmarkCase):
            self.current_case = opts["case"]
        elif "diff" in opts:
            self.current_case = BenchmarkCase(
                case_id=opts.get("case_id", "custom-case"),
                repository=opts.get("repository", "custom/repo"),
                language=opts.get("language", "python"),
                file_path=opts.get("file_path", "app.py"),
                original_code=opts.get("original_code", ""),
                modified_code=opts.get("modified_code", ""),
                diff=opts["diff"],
                split="dev",
                is_clean_diff=opts.get("is_clean_diff", False),
                ground_truth=opts.get("ground_truth", []),
            )
        else:
            if seed is not None:
                self.current_case_idx = seed % len(self.cases)
            else:
                self.current_case_idx = (self.current_case_idx) % len(self.cases)
            self.current_case = self.cases[self.current_case_idx]

        obs = self._get_obs()
        info = {
            "case_id": self.current_case.case_id,
            "repository": self.current_case.repository,
            "is_clean_diff": self.current_case.is_clean_diff,
            "ground_truth_count": len(self.current_case.ground_truth),
        }

        return obs, info

    def step(
        self, action: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]:
        """
        Execute one code review action step.

        Parameters:
            action: Dictionary with "action_type": "post_comment" | "terminate".

        Returns:
            Tuple of (observation, reward, terminated, truncated, info).
        """
        if self.is_terminated:
            logger.warning("Step called on terminated environment. Returning terminal state.")
            return self._get_obs(), 0.0, True, False, {"already_terminated": True}

        self.current_step += 1
        action_type = str(action.get("action_type", "")).strip().lower()

        reward = 0.0
        terminated = False
        truncated = False
        info: Dict[str, Any] = {"step": self.current_step}

        if action_type == "post_comment":
            comment = {
                "file_path": action.get("file_path") or self.current_case.file_path,
                "line_number": int(action.get("line_number", 1)),
                "category": str(action.get("category", "bug")),
                "comment": str(action.get("comment", "")),
                "suggestion": action.get("suggestion"),
            }
            self.posted_comments.append(comment)
            info["action"] = "post_comment"
            info["comments_count"] = len(self.posted_comments)

            # Check if step limit reached
            if self.current_step >= self.max_steps:
                truncated = True
                self.is_terminated = True
                final_reward, breakdown = self.reward_calculator.compute_reward(
                    comments=self.posted_comments,
                    ground_truth=self.current_case.ground_truth,
                    is_clean_diff=self.current_case.is_clean_diff,
                    file_content=self.current_case.modified_code,
                )
                reward = final_reward
                info.update(breakdown)

        elif action_type == "terminate":
            terminated = True
            self.is_terminated = True
            info["action"] = "terminate"

            final_reward, breakdown = self.reward_calculator.compute_reward(
                comments=self.posted_comments,
                ground_truth=self.current_case.ground_truth,
                is_clean_diff=self.current_case.is_clean_diff,
                file_content=self.current_case.modified_code,
            )
            reward = final_reward
            info.update(breakdown)

        else:
            logger.warning("Unknown action_type: %s", action_type)
            info["error"] = f"Unknown action_type: {action_type}"

        return self._get_obs(), reward, terminated, truncated, info

    def render(self, mode: str = "ansi") -> Optional[str]:
        """Render the current environment state."""
        summary = (
            f"ReviewEnv [Step {self.current_step}/{self.max_steps}] Case: {self.current_case.case_id}\n"
            f"Posted Comments: {len(self.posted_comments)}\n"
            f"Clean Diff: {self.current_case.is_clean_diff}\n"
        )
        if mode == "human":
            print(summary)
            return None
        return summary
