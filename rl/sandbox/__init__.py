"""
rl/sandbox/__init__.py

Ephemeral container sandbox module for Aion Code Reviewer (RL-03).
Provides isolated patch execution and escape prevention.
"""

from __future__ import annotations

from rl.sandbox.container import PatchResult, SandboxRunner

__all__ = ["PatchResult", "SandboxRunner"]
