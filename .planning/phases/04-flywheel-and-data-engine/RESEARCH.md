# Phase 04: Fast Flywheel & Verifiable Data Engine — Research & Technical Specification

**Phase:** `04-flywheel-and-data-engine`  
**Milestone:** v1.0 — Path to the No. 1 Code Reviewer (Zero-Budget, RL-Driven)  
**Date:** 2026-11-06  
**Requirements Covered:** `FLY-01`, `FLY-02`, `RL-01`, `RL-02`, `RL-03`, `RL-04`, `DATA-01`, `DATA-02`  

---

## 1. Executive Summary & Strategic Rationale

Phase 4 solves the two foundational bottlenecks of automated code review:
1. **The Slow Learning Flywheel Problem:** Training an LLM with Reinforcement Learning (Phase 5) takes time, free GPU scheduling, and iteration. Developers should not have to wait for GPU training to feel that Aion "learns" from their codebase. We unblock learning **immediately** by deploying per-repository convention memory (`FLY-01`) and an online contextual bandit (`FLY-02`) that tunes category posting confidence thresholds directly from maintainer feedback captured in Phase 3.
2. **The Verifiable RL Training Engine:** Upgrading the prototype AST environment into a true Gymnasium MDP (`ReviewEnv`, `RL-01`), backed by objective verifiable rewards (`RL-02`), an ephemeral container sandbox (`RL-03`) with automated escape tests, red-teamed against reward hacking (`RL-04`), and synthesizing $\ge 10,000$ verified training episodes (`DATA-01`) with strict cryptographic isolation from Aion-Bench (`DATA-02`).

---

## 2. Technical Architecture & Component Design

```
                     Pull Request Review Feedback
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │    Fast Flywheel Learning Engine      │
               │  - Convention Memory (FLY-01)        │
               │  - Online Contextual Bandit (FLY-02) │
               └──────────────────┬───────────────────┘
                                  │ Adaptively tunes thresholds & prompts
                                  ▼
                    ┌────────────────────────────┐
                    │   Action Review Pipeline   │
                    └────────────────────────────┘

                     RL Training Environment Core
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────┐        ┌──────────────────┐      ┌─────────────────┐
│ ReviewEnv MDP │        │ Verifiable Reward│      │ Ephemeral Box   │
│ Gymnasium API │        │ Multi-Tier Hits/ │      │ Rootless Sandbox│
│ (RL-01)       │        │ Penalties (RL-02)│      │ & Escape Tests  │
└───────────────┘        └──────────────────┘      │ (RL-03)         │
                                                   └─────────────────┘
                                  ▲
                                  │ Red-Team Validation (RL-04)
        ┌─────────────────────────┴─────────────────────────┐
        ▼                                                   ▼
┌─────────────────────────────────┐        ┌─────────────────────────────────┐
│   10k+ Verified Data Engine     │        │ Cryptographic Leakage Guard     │
│   Injections, Negatives, Replays│        │ Zero overlap with Aion-Bench    │
│   (DATA-01)                     │        │ manifest.json (DATA-02)         │
└─────────────────────────────────┘        └─────────────────────────────────┘
```

---

## 3. Deep-Dive Specifications

### 3.1 Per-Repository Convention Memory (`FLY-01`)
Maintainers frequently express specific team preferences that diverge from generic style guides.
- **Storage:** Persisted locally per repository in `.aion/conventions.json` or committed in repository configuration.
- **Tracked Patterns:**
  - Dismissed categories or rules (e.g., if a team dismisses `style/docstring` 3 times, auto-suppress that category).
  - Explicit maintainer rules parsed from `CONTRIBUTING.md` or `.editorconfig`.
  - Negative regexes and ignored line patterns (e.g. generated files, protobufs, migrations).
- **Prompt Injection:**
  ```python
  def build_convention_context(memory: RepoMemory) -> str:
      return (
          f"REPOSITORY CONVENTIONS:\n"
          f"- Suppressed categories: {memory.suppressed_categories}\n"
          f"- Preferred patterns: {memory.preferred_rules}\n"
      )
  ```

### 3.2 Online Contextual Bandit (`FLY-02`)
Instead of static confidence thresholds, Aion adaptively optimizes posting thresholds per category $c \in \{\text{bug}, \text{security}, \text{performance}, \text{style}\}$ using an online multi-armed bandit (LinUCB / Thompson Sampling):
- **Action:** Confidence threshold $\theta_c \in [0.5, 0.95]$.
- **Feedback Signals from Phase 3 Reaction Polling:**
  - Resolved comment: $+1.0$
  - Thumbs up (`+1` / `rocket`): $+0.5$
  - Subsequent commit modifying line: $+1.0$
  - Dismissed comment: $-1.0$
  - Thumbs down (`-1` / `confused`): $-1.5$
- **Dynamic Adaptation:** If maintainers dismiss security false alarms on internal scripts, the bandit quickly elevates the threshold for that category without touching logic bug thresholds.

### 3.3 Gymnasium `ReviewEnv` (`RL-01`)
A standard Gymnasium reinforcement learning environment:
- **Observation Space:** Dict containing:
  - `diff`: Unified diff string.
  - `file_content`: Full context of modified files.
  - `language`: `python` or `typescript`.
  - `active_conventions`: List of repository conventions.
- **Action Space:**
  - `post_comment(file, line, category, comment, suggestion)`
  - `terminate_review()`
- **Lifecycle:**
  - `reset(seed=None, options=None) -> (Observation, Dict)`
  - `step(Action) -> (Observation, float, bool, bool, Dict)`

### 3.4 Objective Verifiable Reward Function (`RL-02`)
Rewards are mathematically defined to eliminate subjective gaming:
$$R = R_{\text{bug\_hit}} + R_{\text{security\_hit}} - R_{\text{fp}} - R_{\text{clean\_violation}} - R_{\text{nitpick}} + R_{\text{patch\_pass}}$$

| Event | Reward Delta | Verification Method |
|---|:---:|---|
| Ground-truth bug hit (line $\pm 3$) | $+1.00$ | Exact line anchor match with category alignment |
| Critical security vulnerability hit | $+1.50$ | Exact vulnerability match |
| False positive (comment on non-bug line) | $-0.75$ | Unmatched candidate comment |
| Clean-diff violation | $-1.50$ | Comment posted on a verified clean diff |
| Subjective nitpick / unrequested style | $-0.25$ | Style/nitpick comment without defect |
| Patch compiles and passes tests | $+0.50$ | Ephemeral container test execution |

### 3.5 Ephemeral Containerized Sandbox (`RL-03`)
In Phase 1, host execution was banned (`SEC-01`). In Phase 4, patch validation requires dynamic test execution. We build an ephemeral container runner:
- Docker / Podman container: rootless, `--network none`, `--memory 512m`, `--cpus 1.0`, `--read-only`, ephemeral `/tmp` tmpfs, 10-second timeout.
- Automated escape test suite (`tests/test_sandbox_escape.py`):
  - Blocks network egress (sockets, outbound connections).
  - Blocks filesystem write outside `/tmp`.
  - Enforces CPU timeout on infinite loops.
  - Enforces memory limit on memory exhaustion attacks.

### 3.6 Reward Hacking Red-Team Audit (`RL-04`)
Degenerate policies are tested against `ReviewEnv` in `tests/test_reward_hacking.py`:
1. **Empty Policy (0 comments):** Scores $\le 0.0$ on buggy diffs (recall penalty).
2. **All-Line Spam Policy:** Massive FP penalties, resulting in deeply negative net reward ($R < -5.0$).
3. **Generic Advice Policy ("Make this clean"):** Discarded by suggestion validation, scoring zero or negative.
4. **Duplicate Suggestion Policy (Copy existing code):** Zero-delta suggestion detected, penalized.

### 3.7 Verifiable Data Engine & Leakage Guard (`DATA-01`, `DATA-02`)
- **Scale:** Generates $\ge 10,000$ verified episodes combining:
  - 5,000 synthetic AST bug mutations (Python & TypeScript) with failing test reproductions.
  - 3,000 clean-diff true negatives.
  - 2,000 mined real PR review replays with corrective commits.
- **Strict Leakage Guard:**
  - Computes SHA-256 hashes of every training case payload.
  - Asserts $0.0\%$ collision with `bench/splits/manifest.json` (`gold.json` and `test_locked.json`).
  - Strict repository-level blacklisting: Any repository present in Aion-Bench test splits is permanently excluded from training generation.

---

## 4. Phase 4 Plan Breakdown

| Plan | Title | Requirements | Key Deliverables |
|---|---|:---:|---|
| **04-01** | **Fast Flywheel: Repo Memory & Online Contextual Bandit** | `FLY-01`, `FLY-02` | `rl/memory.py`, `rl/bandit.py`, integration with `action/`, unit tests. |
| **04-02** | **Gymnasium ReviewEnv, Verifiable Reward & Sandboxed Execution** | `RL-01`, `RL-02`, `RL-03`, `RL-04` | `rl/env.py`, `rl/reward.py`, `rl/sandbox/`, red-team reward hacking tests, sandbox escape tests. |
| **04-03** | **Verifiable Data Engine: 10k+ Episodes & Leakage Guard** | `DATA-01`, `DATA-02` | `rl/data_engine/synthesizer.py`, `rl/data_engine/isolation.py`, $\ge 10,000$ verified episodes, leakage tests. |

