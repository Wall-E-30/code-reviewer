---
phase: 10-live-pilots
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - action/formatter.py
  - action/main.py
  - server/github_app.py
  - rl/memory.py
  - tests/test_pilot_modes_and_safeguards.py
autonomous: true
requirements:
  - PILOT-03
must_haves:
  truths:
    - Visible mode includes a feedback link and one-click "not useful" reasons (wrong, nitpick, already_known, out_of_scope) on every posted comment.
    - Maintainers can issue a repo-level mute command (@aion mute / /aion mute) to immediately silence all Aion reviews on the repository.
    - Global kill switch (AION_KILL_SWITCH environment variable or flag) immediately halts all review activity across all repositories.
    - Hard ceiling of <= 5 comments per PR is strictly enforced in all visible reviews.
  artifacts:
    - action/formatter.py
    - server/github_app.py
    - tests/test_pilot_modes_and_safeguards.py
---

<objective>
Implement visible mode safeguards, feedback links, one-click dismiss reasons, repo-level muting, and global kill switch (`PILOT-03`).
Ensure maintainers retain complete control with one-click dismiss reasons, immediate repository silencing commands, and an emergency kill switch.
</objective>

<tasks>

<task type="tracer">
  <name>Add Feedback Links and One-Click Dismiss Reasons to Formatter</name>
  <files>action/formatter.py</files>
  <action>
1. Update `action/formatter.py`:
   - Append structured feedback footer to inline comments and executive summaries.
   - Include quick-feedback dismiss tags:
     - `wrong`
     - `nitpick`
     - `already_known`
     - `out_of_scope`
   - Include direct feedback URL link and repository mute instructions (`@aion mute`).
  </action>
  <verify>
python -c "from action.formatter import format_inline_comment; print('Formatter ready')"
  </verify>
</task>

<task>
  <name>Implement Repo Mute Command and Global Kill Switch</name>
  <files>action/main.py, server/github_app.py, rl/memory.py, tests/test_pilot_modes_and_safeguards.py</files>
  <action>
1. Update `rl/memory.py` and `server/github_app.py`:
   - Add `is_muted(repo)` and `mute_repo(repo, reason)` methods.
   - Parse maintainer issue/PR comment bodies for `@aion mute`, `/aion mute`, `@aion unmute`, `/aion unmute`.
   - When a repository is muted, return `status: "muted"` and post zero review comments.
2. Implement global kill switch in `action/main.py` and `server/github_app.py`:
   - If `AION_KILL_SWITCH` environment variable is `"true"`, `"1"`, or `"yes"`, immediately abort review execution, log warning, and exit cleanly with zero comments posted.
3. Add tests in `tests/test_pilot_modes_and_safeguards.py` covering:
   - Feedback footer formatting with the 4 dismiss reasons.
   - `@aion mute` command recognition and review abort.
   - Global kill switch abort.
   - Strict $\le 5$ comments enforcement.
  </action>
  <verify>
python -m pytest tests/test_pilot_modes_and_safeguards.py -v
  </verify>
</task>

</tasks>

