---
phase: 08-truth-and-hardening
plan: 02
type: execute
wave: 2
depends_on:
  - 08-01
files_modified:
  - action/redactor.py
  - action/action_review.py
  - cli/main.py
  - server/github_app.py
  - docs/DATA_POLICY.md
  - tests/test_secret_redaction_and_reactions.py
autonomous: true
requirements:
  - HARD-03
  - HARD-03b
must_haves:
  truths:
    - action/redactor.py redacts API keys (AWS, GitHub, OpenAI, Anthropic, private keys, bearer tokens) from diffs before LLM calls.
    - CI logs and stdout never leak unredacted secrets or private tokens.
    - Diffs sent to LLMs enforce minimal context limits (<= 50 surrounding lines per hunk).
    - GitHub reaction queries use documented REST endpoints, and App event handling verifies against recorded real payload fixtures.
  artifacts:
    - action/redactor.py
    - action/action_review.py
    - cli/main.py
    - server/github_app.py
    - docs/DATA_POLICY.md
    - tests/test_secret_redaction_and_reactions.py
---

<objective>
Implement Diff Secret Redaction, Minimal Diff Context Window (`HARD-03b`), and Verified GitHub Reaction Polling & App Events (`HARD-03`).
Protect user codebases from leaking private tokens to LLMs and log streams, while establishing realistic telemetry capture using documented GitHub APIs.
</objective>

<tasks>

<task type="tracer">
  <name>Build Secret Redaction Engine and Minimal Context Extractor</name>
  <files>action/redactor.py, tests/test_secret_redaction_and_reactions.py</files>
  <action>
1. In `action/redactor.py`:
   - Implement regex patterns for AWS keys (`AKIA[0-9A-Z]{16}`), GitHub tokens (`ghp_[a-zA-Z0-9]{36}`), OpenAI keys (`sk-[a-zA-Z0-9]{32,}`), Anthropic keys, private keys (`-----BEGIN [A-Z ]*PRIVATE KEY-----`), and high-entropy bearer tokens.
   - `redact_secrets_from_diff(diff_str: str) -> Tuple[str, List[str]]`: replaces secrets with `[REDACTED_SECRET:<type>]`.
   - `extract_minimal_diff_context(diff_str: str, max_surrounding_lines: int = 25) -> str`: strips extraneous context lines, preserving modified lines and minimal scope context.
2. Hook `redact_secrets_from_diff` into `action/action_review.py` and `cli/main.py` before LLM inference.
  </action>
  <verify>
python -c "from action.redactor import redact_secrets_from_diff; d, r = redact_secrets_from_diff('sk-1234567890abcdef1234567890abcdef'); assert '[REDACTED_SECRET' in d; print('Redactor tracer verified')"
  </verify>
</task>

<task>
  <name>Implement Verified GitHub Reaction Polling and Recorded App Fixtures</name>
  <files>server/github_app.py, action/github_client.py, docs/DATA_POLICY.md</files>
  <action>
1. In `server/github_app.py` and `action/github_client.py`:
   - Implement reaction polling against official GitHub REST endpoint (`GET /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions`).
   - Support `+1`, `-1`, `confused`, `eyes`, `laugh`, `heart`, `rocket`, `hooray`.
   - Action polling logic: on subsequent workflow runs on the same PR, query reactions for comments posted in previous runs.
   - Add real recorded GitHub API webhook fixtures (`tests/fixtures/github_events/`) for pull_request, review_comment, and reaction events.
2. In `docs/DATA_POLICY.md`:
   - Update data policy to explicitly document secret redaction, minimal context window, and zero logging of raw tokens or diffs.
  </action>
  <verify>
pytest tests/test_secret_redaction_and_reactions.py -v
  </verify>
</task>

</tasks>
