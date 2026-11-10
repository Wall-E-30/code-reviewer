# Legacy Prototype Archive: Aion Prototype RL & Grader (HARD-04)

**Status:** Deprecated as of Milestone v1.1 (Replaced by `rl/env.py` - `ReviewEnv`)  
**Security Classification:** Archive Only — Do Not Use in Production  

---

## 1. Why Was This Deprecated?

The files archived in this directory (`env.py`, `train_rl.py`, `train_autoregressive_rl.py`) represent the early v0.1 prototype of the Aion Code Reviewer.

### The Reward Hacking Vulnerability (RL-04, HARD-04)
In the early prototype, reward calculation was driven by a naive AST node count difference:
$$\text{Reward}_{\text{prototype}} \propto \text{NodeCount}(\text{initial}) - \text{NodeCount}(\text{current})$$

This formulation suffered from severe reward hacking:
1. **Node Padding:** An agent could insert empty expressions, dead conditional branches (`if True: pass`), or redundant docstrings to manipulate the AST node balance.
2. **Synthetic Speedup Heuristic:** The prototype displayed polynomial speedup estimates ($O(N^2) \to O(N)$) based purely on regex/AST heuristics rather than actual benchmarked executions.
3. **No Verifiable Ground Truth:** The environment lacked negative controls on clean diffs, allowing models to spam comments on bug-free code without penalty.

---

## 2. The Modern Architecture: `ReviewEnv` (`rl/env.py`)

Milestone v1.0 and v1.1 replaced this prototype with **`ReviewEnv`**:
- **OpenEnv & Gymnasium Compatible:** Adheres to standard Gymnasium `step(action)` and `reset(task)` interfaces.
- **Verifiable Rewards:** Rewards are tied strictly to:
  - Ground-truth bug detections ($+2.0$)
  - Actionable GitHub suggestion blocks ($+1.0$)
  - False-positive clean-diff penalties ($-1.50$)
  - AST / linter pre-filtering (Ruff, AST security analysis)
  - Isolated rootless container execution (`rl/sandbox/container.py`)
- **Anti-Hacking Red Teaming (`tests/test_reward_hacking.py`):** Explicitly verifies that degenerative policies (empty outputs, all-line spam, generic text) receive zero or negative reward.

---

## 3. Migration Guide

| Legacy Component | Modern Replacement |
|---|---|
| `legacy/env.py` (`CodeReviewEnv`) | `rl/env.py` (`ReviewEnv`) |
| `legacy/train_rl.py` (Q-Learning) | `rl/training/grpo.py` (Group-Relative Policy Optimization) |
| `legacy/train_autoregressive_rl.py` | `rl/training/sft.py` (ChatML SFT Warm-Start) |
| Synthetic speedup/memory metrics | Directly measured execution / AST verified diagnostics |
