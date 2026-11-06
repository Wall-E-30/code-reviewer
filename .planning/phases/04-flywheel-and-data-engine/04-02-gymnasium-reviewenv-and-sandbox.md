---
phase: 04-flywheel-and-data-engine
plan: 02
type: execute
wave: 2
depends_on:
  - 04-01
files_modified:
  - rl/env.py
  - rl/reward.py
  - rl/sandbox/__init__.py
  - rl/sandbox/container.py
  - tests/test_review_env.py
  - tests/test_reward_hacking.py
  - tests/test_sandbox_escape.py
autonomous: true
requirements:
  - RL-01
  - RL-02
  - RL-03
  - RL-04
must_haves:
  truths:
    - ReviewEnv exposes standard Gymnasium reset and step interfaces with PR diff observations, structured review actions, and OpenEnv exportability.
    - Verifiable reward function scores ground-truth bug hits positively while penalizing false positives, clean-diff violations, subjective nitpicks, and invalid patches.
    - Reward-hacking red team tests prove that degenerate policies (empty output, spamming every line, generic advice, zero-delta suggestions) cannot achieve positive rewards.
    - Ephemeral container sandbox enforces network isolation, read-only root filesystems, resource limits, and passes an automated escape test suite in CI.
  artifacts:
    - rl/env.py
    - rl/reward.py
    - rl/sandbox/container.py
    - tests/test_review_env.py
    - tests/test_reward_hacking.py
    - tests/test_sandbox_escape.py
  key_links:
    - rl/env.py provides the reinforcement learning environment for Phase 5 GRPO training.
    - rl/reward.py computes verifiable scalar feedback without subjective LLM-as-a-judge grading.
    - rl/sandbox/container.py runs test patch verification safely inside isolated containers.
---

<objective>
Build the core Gymnasium reinforcement learning environment (`ReviewEnv`), an objective multi-tier verifiable reward function, an ephemeral container sandbox with automated escape tests, and red-team tests proving resistance to reward hacking.

Purpose: Replace prototype AST heuristic scoring with a true Gymnasium MDP and verifiable reward engine ready for RL policy optimization.
Output: `rl/env.py`, `rl/reward.py`, `rl/sandbox/`, and verification test suites.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/04-flywheel-and-data-engine/RESEARCH.md
@bench/schema.py
@bench/evaluator/matcher.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Gymnasium ReviewEnv in rl/env.py</name>
  <files>rl/env.py, tests/test_review_env.py</files>
  <action>
1. In `rl/env.py`, implement `ReviewEnv`:
   - Follows standard Gymnasium interface:
     - `reset(seed=None, options=None) -> (Observation, Dict)`:
       - Loads a `BenchmarkCase` or PR diff.
       - Returns `observation: Dict` with keys: `diff`, `file_content`, `file_path`, `language`, `active_conventions`.
     - `step(action: Dict) -> (Observation, float, bool, bool, Dict)`:
       - Handles actions:
         - `post_comment`: `{"action_type": "post_comment", "line_number": int, "category": str, "comment": str, "suggestion": Optional[str]}`.
         - `terminate`: `{"action_type": "terminate"}` ending the episode.
       - Returns `(observation, reward, terminated, truncated, info)`.
       - Enforces max steps per review (default 10).
   - Export OpenEnv specification helper `export_openenv_spec()`.
2. In `tests/test_review_env.py`:
   - Unit tests covering `reset`, valid steps, action processing, step limits, and termination.
  </action>
  <verify>
python -c "from rl.env import ReviewEnv; env = ReviewEnv(); obs, info = env.reset(); assert 'diff' in obs; obs, r, term, trunc, info = env.step({'action_type': 'terminate'}); assert term is True; print('ReviewEnv verified')"
  </verify>
</task>

<task>
  <name>Implement Verifiable Reward Function and Reward Hacking Audit</name>
  <files>rl/reward.py, tests/test_reward_hacking.py</files>
  <action>
1. In `rl/reward.py`, implement `VerifiableRewardCalculator`:
   - Inputs: List of posted comments, ground-truth findings, and `is_clean_diff` flag.
   - Reward formula:
     - Bug hit (matched to ground truth within line window): $+1.00$
     - Security vulnerability hit: $+1.50$
     - False positive (comment on non-buggy code): $-0.75$
     - Clean-diff violation (posting any comment on clean PR): $-1.50$
     - Nitpick deduction (style comment on substantive defect): $-0.25$
     - Suggestion syntax validity / test pass bonus: $+0.50$
     - Zero-delta suggestion penalty (copy of existing code): $-0.50$
   - Methods: `compute_reward(comments, ground_truth, is_clean_diff) -> Tuple[float, Dict[str, Any]]`.
2. In `tests/test_reward_hacking.py`:
   - Red-team tests against degenerate policies:
     - Empty policy: Scores $\le 0$ on buggy diffs due to missed bugs.
     - All-line spam policy: Commenting on every line results in deeply negative net reward ($R < -5.0$).
     - Generic text policy ("Please fix this"): Fails syntax/specificity check, yielding zero or negative reward.
     - Copy-paste suggestion policy: Penalized for zero code delta.
  </action>
  <verify>
python -m pytest tests/test_reward_hacking.py -v
  </verify>
</task>

<task>
  <name>Implement Ephemeral Container Sandbox and Automated Escape Tests</name>
  <files>rl/sandbox/__init__.py, rl/sandbox/container.py, tests/test_sandbox_escape.py</files>
  <action>
1. Create `rl/sandbox/__init__.py`.
2. In `rl/sandbox/container.py`, implement `SandboxRunner`:
   - Executes code / patches inside an ephemeral, isolated container boundary:
     - Resource constraints: `--memory 512m`, `--cpus 1.0`, 10-second timeout.
     - Security flags: `--network none`, `--read-only`, rootless execution, isolated ephemeral `/tmp` volume.
     - Graceful fallback: If Docker/Podman is not installed in the current environment, employs subprocess execution inside a restricted, isolated temp directory with non-zero timeout and restricted environment variables.
   - Methods: `run_patch_verification(original_code: str, patch: str, test_command: str) -> PatchResult`.
3. In `tests/test_sandbox_escape.py`:
   - Test network isolation (attempting outbound socket raises or fails).
   - Test filesystem confinement (attempting to write outside `/tmp` fails).
   - Test CPU timeout enforcement (infinite while loop terminated in $\le 10$ seconds).
   - Test memory limit enforcement (allocating 1GB triggers memory error or OOM termination).
  </action>
  <verify>
python -m pytest tests/test_sandbox_escape.py -v
  </verify>
</task>

</tasks>

