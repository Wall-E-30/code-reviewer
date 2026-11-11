---
phase: 10-live-pilots
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - action.yml
  - action/main.py
  - server/github_app.py
  - docs/pilots/ONBOARDING_GUIDE.md
  - scripts/install_pilot.py
  - tests/test_pilot_modes_and_safeguards.py
autonomous: true
requirements:
  - PILOT-01
  - PILOT-02
must_haves:
  truths:
    - Shadow review mode in Action and App executes full review pipeline silently without posting PR comments.
    - Shadow reviews log what would have been posted to a telemetry/shadow file.
    - docs/pilots/ONBOARDING_GUIDE.md provides a 1-page installation and configuration guide for maintainers.
    - scripts/install_pilot.py automates GitHub Action workflow creation for pilot repositories.
  artifacts:
    - docs/pilots/ONBOARDING_GUIDE.md
    - scripts/install_pilot.py
    - tests/test_pilot_modes_and_safeguards.py
---

<objective>
Implement Shadow Review Mode in GitHub Action and GitHub App, and provide maintainer onboarding tooling (`PILOT-01`, `PILOT-02`).
Enable silent operation so maintainers can observe Aion's analysis without PR noise, accompanied by a clean 1-page guide and automated installation script.
</objective>

<tasks>

<task type="tracer">
  <name>Implement Shadow Review Mode in Action and App</name>
  <files>action.yml, action/main.py, server/github_app.py</files>
  <action>
1. Update `action.yml` to accept `mode` input (default: `visible`, optional: `shadow`).
2. Update `action/main.py`:
   - Parse `INPUT_MODE` or `--mode` flag (`shadow` vs `visible`).
   - If `mode == "shadow"`, run full analysis (linters, provider, secret redactor, verifier, bandit), log candidates to `.aion/shadow_reviews.jsonl` or telemetry, and bypass `gh_client.post_review()`.
   - Return review status `shadow_logged`.
3. Update `server/github_app.py`:
   - Support `mode="shadow"` in PR review event routing or repository config.
   - In shadow mode, suppress GitHub review submission API calls and log generated comments.
  </action>
  <verify>
python -c "from action.main import parse_action_inputs; print('Action inputs parsed successfully')"
  </verify>
</task>

<task>
  <name>Create Onboarding Guide and Pilot Install Script</name>
  <files>docs/pilots/ONBOARDING_GUIDE.md, scripts/install_pilot.py, tests/test_pilot_modes_and_safeguards.py</files>
  <action>
1. Author `docs/pilots/ONBOARDING_GUIDE.md`:
   - 1-page guide explaining:
     - Shadow mode (silent background evaluation, zero comment clutter)
     - Visible mode (high-precision comments, feedback links, $\le 5$ comments/PR ceiling)
     - Security and data policy (read-only PR permissions, secrets redacted, no code stored)
     - How to mute (`@aion mute`) or disable
2. Implement `scripts/install_pilot.py`:
   - CLI script generating `.github/workflows/aion-review.yml` for target pilot repos.
   - Supports `--mode shadow` or `--mode visible`, `--provider mock|groq|openrouter|ollama`.
3. Add initial tests in `tests/test_pilot_modes_and_safeguards.py` verifying shadow mode execution in Action and App.
  </action>
  <verify>
python -m pytest tests/test_pilot_modes_and_safeguards.py -v
  </verify>
</task>

</tasks>
