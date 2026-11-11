---
phase: 11-training-v2
plan: 03
type: execute
wave: 3
depends_on:
  - 11-01
  - 11-02
files_modified:
  - rl/reward.py
  - tests/test_reward_hacking_v2.py
autonomous: true
requirements:
  - TRAIN2-03
must_haves:
  truths:
    - Reward system formalizes RewardVersion (v2.0.0) tracking formula changes, penalty weights, and verification rules.
    - Degenerate policy detection penalizes: (a) linter hit proximity clustering, (b) linter copycat verbatim repetition, and (c) hedged generic comments.
    - Anti-reward-hacking red team test suite verifies that all three degenerate policy classes receive zero or negative reward.
  artifacts:
    - rl/reward.py
    - tests/test_reward_hacking_v2.py
---

<objective>
Implement Expanded Reward Hacking Audits & Versioning (`TRAIN2-03`).
Update the verifiable reward engine to RewardVersion v2.0.0, penalizing linter proximity hacking, linter copycats, and generic hedging comments, verified by red-team tests.
</objective>

<tasks>

<task type="tracer">
<name>Update VerifiableRewardCalculator with RewardVersion v2.0.0</name>
<files>rl/reward.py</files>
<action>
1. In `rl/reward.py`:
   - Introduce `RewardVersion` enum (`V1_0_0 = "1.0.0"`, `V2_0_0 = "2.0.0"`).
   - In `VerifiableRewardCalculator`:
     - Add `reward_version: RewardVersion = RewardVersion.V2_0_0`.
     - Implement `_detect_linter_copycat(comment_text, linter_messages)`: penalizes direct copy-paste or high token overlap with raw linter diagnostics.
     - Implement `_detect_hedged_generic_comment(comment_text)`: penalizes vacuous, non-actionable platitudes ("Consider verifying edge cases", "Ensure proper error handling").
     - Implement `_detect_linter_proximity_spam(comments, linter_findings)`: penalizes clustering comments near linter lines without providing valid fix suggestions.
     - Incorporate penalty deductions into total reward under `v2.0.0`.
</action>
<verify>
python -c "from rl.reward import VerifiableRewardCalculator, RewardVersion; calc = VerifiableRewardCalculator(version=RewardVersion.V2_0_0); assert calc.version == RewardVersion.V2_0_0; print('Reward v2 verified')"
</verify>
</task>

<task>
<name>Author Red-Team Test Suite for Reward Hacking v2</name>
<files>tests/test_reward_hacking_v2.py</files>
<action>
Create `tests/test_reward_hacking_v2.py` verifying:
1. Linter copycat policy receives negative penalty reward.
2. Hedged generic comment policy receives negative penalty reward.
3. Linter proximity cluster without fix suggestions receives penalty reward.
4. Reward metadata includes version and breakdown details.
</action>
<verify>
pytest tests/test_reward_hacking_v2.py -v
</verify>
</task>

</tasks>

