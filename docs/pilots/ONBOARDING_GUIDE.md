# Aion Pilot Onboarding Guide
**Version 1.1** | *Precision Code Review for Maintainers*

Welcome to the Aion pilot program. Aion is an automated code reviewer designed to achieve high precision ($\ge 85\%$) by filtering noise and enforcing a strict ceiling of $\le 5$ comments per PR.

---

## 1. Choose Your Review Mode

Aion supports two operating modes during the pilot phase:

| Mode | What It Does | Who It Is For |
| :--- | :--- | :--- |
| **Shadow Mode** (`mode: shadow`) | Runs the full linter, secret scrubber, and precision verifier pipeline **silently**. Analyzes pull requests and logs findings to `.aion/shadow_reviews.jsonl` without posting any comments to PRs. | Maintainers who want to evaluate Aion's accuracy, noise profile, and false-positive rates offline before enabling public PR comments. |
| **Visible Mode** (`mode: visible`) | Posts up to 5 verified findings per PR as inline GitHub review comments. Every comment includes structured explanation, diff suggestions, and a 1-click feedback footer. | Repositories ready for live feedback. |

---

## 2. Quickstart Installation (GitHub Action)

### Automated Setup
Run the automated installation script from the root of your repository:
```bash
# Install in silent Shadow Mode (Recommended for Week 1)
python scripts/install_pilot.py --mode shadow

# Or install in Visible Mode
python scripts/install_pilot.py --mode visible
```

### Manual Setup
Add `.github/workflows/aion-review.yml` to your repository:

```yaml
name: Aion Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Aion Reviewer
        uses: aion-org/code-reviewer@v1.1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          mode: shadow # Change to 'visible' when ready
          provider: groq # mock | groq | openrouter | ollama
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
```

---

## 3. Maintainer Controls & Safeguards

You maintain total control over Aion at all times:

### Repository Muting
- **Mute Reviewer**: Comment `@aion mute` or `/aion mute` anywhere in an issue or PR thread. Aion will immediately cease all review activity on the repository.
- **Unmute Reviewer**: Comment `@aion unmute` or `/aion unmute` to resume reviews.

### One-Click Dismissal & Feedback
Every comment in visible mode includes one-click feedback options. If a comment is unhelpful, reply with one of the following commands:
- `@aion wrong`: Factual error or misinterpretation.
- `@aion nitpick`: Trivial styling or preference issue that doesn't matter.
- `@aion already_known`: Known issue, tech debt, or intentional decision.
- `@aion out_of_scope`: Finding is outside the scope of this PR.

*Note: Dismissals automatically adjust the adaptive contextual bandit to raise precision thresholds for that finding category.*

### Emergency Kill Switch
To immediately shut off Aion across your organization without modifying code, set the repository or organization secret:
```bash
AION_KILL_SWITCH=true
```
When this variable is detected, Aion halts instantly without posting or updating reviews.

---

## 4. Security & Privacy Guarantees

1. **Minimal Permissions**: Requires only `contents: read` and `pull-requests: write`. No admin, secret, or deployment access is ever requested.
2. **Secret Redaction**: Diff text is scrubbed before processing. High-entropy API tokens (AWS, OpenAI, Anthropic, GitHub, Slack) are automatically replaced with `[REDACTED_SECRET]`.
3. **No Code Retention**: Diffs are ephemeral and evaluated in memory. Code is never logged to external servers or used for public model training.
4. **Strict Comment Ceiling**: Never exceeds 5 comments on any PR, protecting contributors from notification fatigue.
