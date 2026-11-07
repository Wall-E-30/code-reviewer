# GitHub Marketplace Listing Metadata: Aion Code Reviewer

**Product Name:** Aion Code Reviewer  
**Short Tagline:** High-precision, AST-verified AI code review trained with RLVR. Free for open source.  
**Categories:** `Code review`, `Code quality`, `Security`  
**Pricing Plan:** Free ($0.00 / month forever for public open-source repositories)  
**Icon / Logo:** `frontend/public/favicon.ico` / `assets/aion-logo.svg`  
**Repository:** https://github.com/aion-ai/aion  
**Documentation:** https://aion.openenv.org/docs  

---

## 1. Description & Marketing Copy

### The AI Code Reviewer That Knows When to Stay Quiet

Most AI code review bots flood pull requests with hallucinated bugs and pedantic style nitpicks. Aion is built differently: trained via **Reinforcement Learning from Verifiable Rewards (RLVR)** on an OpenEnv Gymnasium environment with strict negative controls on clean diffs.

Aion guarantees:
- 🎯 **High-Precision Signal:** Only alerts you to verifiable bugs, security vulnerabilities (SQL injection, unsafe sinks), and convention violations.
- 🚫 **Zero Clean-Diff Spam:** Trained to remain completely silent on clean code, maintaining a clean-diff False-Positive Rate strictly below $10\%$.
- 💡 **1-Click GitHub Suggestions:** Every valid finding comes with a concrete, syntactically verified code replacement block (`suggestion ...`).
- 🧠 **Per-Repo Convention Memory:** Remembers your team's custom style preferences and maintainer dismissals in `.aion/conventions.json`.
- ⚡ **Lightning Fast:** Powered by fine-tuned 7B open code models running in under $500\text{ms}$.

---

## 2. Installation & Quick Start

### Option A: GitHub Action Workflow

Create `.github/workflows/aion-review.yml`:

```yaml
name: Aion Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Aion Code Reviewer
        uses: aion-ai/aion@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          min_confidence: "0.70"
          max_comments: "5"
```

### Option B: Webhook-Driven GitHub App

1. Install the **Aion Code Reviewer** GitHub App directly from GitHub Marketplace.
2. Select target repositories.
3. Aion will automatically post inline review comments with suggestion blocks on new pull requests.

---

## 3. GitHub Permissions & Scopes Justification

| Permission | Access Level | Reason |
|---|:---:|---|
| **Pull Requests** | `Read & write` | Read PR unified diffs and post line-anchored review comments with suggestions. |
| **Contents** | `Read-only` | Read modified repository source files and `.aion/conventions.json`. |
| **Issues** | `Read-only` | Read PR comment reactions (`+1`, `-1`) to tune contextual bandit confidence thresholds. |
| **Metadata** | `Read-only` | Access basic repository identifiers. |

---

## 4. Open-Source Commitment

Aion is 100% free forever for all public open-source repositories. Show your commitment to code quality by embedding our dynamic README badge:

```markdown
[![Reviewed by Aion](https://aion.openenv.org/api/badge/{owner}/{repo})](https://github.com/aion-ai/aion)
```

