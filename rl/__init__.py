"""
rl/__init__.py

Reinforcement Learning & Adaptive Flywheel module for Aion Code Reviewer.
Provides:
- RepoConventionMemory (FLY-01): Per-repository convention memory and pattern suppression
- CategoryBandit (FLY-02): Online contextual bandit tuning category confidence thresholds
- ReviewEnv (RL-01): Gymnasium MDP environment for code review
- VerifiableRewardCalculator (RL-02, RL-04): Objective verifiable reward engine
- SandboxRunner, PatchResult (RL-03): Ephemeral containerized test sandbox
"""

from __future__ import annotations

from rl.bandit import CategoryBandit
from rl.env import ReviewEnv, export_openenv_spec
from rl.memory import CustomRule, RepoConventionMemory, RepoMemoryState, SuppressedPattern
from rl.reward import VerifiableRewardCalculator
from rl.sandbox.container import PatchResult, SandboxRunner

__all__ = [
    "CategoryBandit",
    "CustomRule",
    "PatchResult",
    "RepoConventionMemory",
    "RepoMemoryState",
    "ReviewEnv",
    "SandboxRunner",
    "SuppressedPattern",
    "VerifiableRewardCalculator",
    "export_openenv_spec",
]
