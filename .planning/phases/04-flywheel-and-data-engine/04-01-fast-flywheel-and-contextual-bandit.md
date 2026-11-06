---
phase: 04-flywheel-and-data-engine
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - rl/__init__.py
  - rl/memory.py
  - rl/bandit.py
  - action/main.py
  - tests/test_flywheel.py
autonomous: true
requirements:
  - FLY-01
  - FLY-02
must_haves:
  truths:
    - Repo convention memory tracks dismissed comment patterns and custom style rules, suppressing repetitive complaints and injecting conventions into review context.
    - Online contextual bandit adaptively adjusts category posting confidence thresholds based on maintainer reaction signals (resolved, dismissed, upvotes, downvotes).
    - Review pipeline integrates convention suppression and bandit thresholds before comments are posted to GitHub.
    - Feedback from previous runs dynamically updates bandit weights and convention memory without requiring GPU model training.
  artifacts:
    - rl/memory.py
    - rl/bandit.py
    - tests/test_flywheel.py
  key_links:
    - rl/memory.py injects conventions and suppresses unwanted categories in action/main.py.
    - rl/bandit.py tunes category confidence cutoffs for action/verifier.py using reaction signals.
---

<objective>
Deploy the fast learning flywheel immediately after Phase 3 without waiting for GPU training: build per-repository convention memory to suppress repeat complaints, and implement an online contextual bandit that adaptively tunes category confidence thresholds from maintainer feedback.

Purpose: Deliver adaptive, repo-specific learning from day one so maintainers see Aion learn their team conventions instantly.
Output: `rl/memory.py`, `rl/bandit.py`, action pipeline integration, and test suite.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/04-flywheel-and-data-engine/RESEARCH.md
@action/main.py
@action/verifier.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Per-Repository Convention Memory in rl/memory.py</name>
  <files>rl/__init__.py, rl/memory.py</files>
  <action>
1. Create `rl/__init__.py`.
2. In `rl/memory.py`, implement `RepoConventionMemory`:
   - Data structures: `SuppressedPattern`, `CustomRule`, `RepoMemoryState`.
   - Methods:
     - `record_dismissal(category: str, rule_id: Optional[str], pattern: str, reason: str = "")`:
       - Increments dismissal counter for the pattern/category.
       - If dismissals exceed threshold (default 2), automatically marks pattern as suppressed.
     - `add_convention(rule_text: str, category: str = "general")`:
       - Explicitly registers team style conventions (e.g. from `CONTRIBUTING.md` or `.editorconfig`).
     - `is_suppressed(category: str, comment_text: str, rule_id: Optional[str] = None) -> bool`:
       - Checks whether a proposed review comment matches any suppressed pattern or category.
     - `build_prompt_context() -> str`:
       - Returns concise Markdown block summarizing team preferences and suppressed rules to inject into LLM review prompts.
     - `save(path: str)` / `load(path: str)`: Persists state to `.aion/conventions.json`.
  </action>
  <verify>
python -c "from rl.memory import RepoConventionMemory; m = RepoConventionMemory(); m.record_dismissal('style/whitespace', None, 'Line too long'); m.record_dismissal('style/whitespace', None, 'Line too long'); assert m.is_suppressed('style/whitespace', 'Line too long is bad'); print('Convention memory verified')"
  </verify>
</task>

<task>
  <name>Implement Online Contextual Bandit in rl/bandit.py</name>
  <files>rl/bandit.py</files>
  <action>
1. In `rl/bandit.py`, implement `CategoryBandit`:
   - Maintains adaptive confidence thresholds $\theta_c \in [0.50, 0.95]$ per finding category (`bug`, `security`, `performance`, `style`).
   - Implements Thompson Sampling / LinUCB updates:
     - Maintain $(\alpha_c, \beta_c)$ parameters for Beta-Bernoulli bandit or running mean reward per category.
     - When maintainer resolves comment or reacts with `+1`/`rocket`: `reward = +1.0` (decreases threshold / increases posting willingness).
     - When maintainer dismisses comment or reacts with `-1`/`confused`: `reward = -1.5` (elevates threshold / demands higher model certainty).
     - Bounded range: Thresholds never drop below 0.50 or rise above 0.95.
   - Methods:
     - `get_threshold(category: str) -> float`: Returns current threshold for category.
     - `update(category: str, reward: float)`: Updates bandit parameters based on feedback.
     - `save(path: str)` / `load(path: str)`: Persists state to `.aion/bandit_state.json`.
  </action>
  <verify>
python -c "from rl.bandit import CategoryBandit; b = CategoryBandit(); t0 = b.get_threshold('style'); b.update('style', reward=-1.5); assert b.get_threshold('style') >= t0; print('Bandit threshold adaptation verified')"
  </verify>
</task>

<task>
  <name>Integrate Flywheel with GitHub Action Pipeline and Build Tests</name>
  <files>action/main.py, tests/test_flywheel.py</files>
  <action>
1. Update `action/main.py`:
   - Initialize `RepoConventionMemory` and `CategoryBandit` from `.aion/` directory.
   - Inject `memory.build_prompt_context()` into review generation prompts.
   - Filter candidate comments through `memory.is_suppressed(...)` prior to posting.
   - Pass bandit's dynamic category thresholds to `PrecisionVerifier`.
   - Update bandit and memory from `poll_previous_reactions(...)` outcomes.
   - Save updated memory and bandit state to `.aion/`.
2. In `tests/test_flywheel.py`:
   - Unit tests covering dismissal tracking, suppression checks, prompt context building, bandit threshold elevation on negative feedback, threshold relaxation on positive feedback, and end-to-end pipeline integration.
  </action>
  <verify>
python -m pytest tests/test_flywheel.py -v
  </verify>
</task>

</tasks>

