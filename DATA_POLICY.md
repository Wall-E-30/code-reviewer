# Aion Code Reviewer — Data & Privacy Policy

**Effective Date:** November 5, 2026  
**Version:** 1.0  
**Scope:** Aion GitHub Action (`action.yml`) & Code Review Intelligence Engine  

---

## 1. Executive Summary

Aion is built on a fundamental principle: **Your source code is your property, and we treat it with absolute confidentiality.**

Most developer tools silently upload private repositories, index proprietary intellectual property, or use customer code to train commercial models. **Aion does neither.** Aion runs directly inside your own GitHub Actions execution runner (`ubuntu-latest`) using a zero-hosting architecture.

---

## 2. Core Privacy Guarantees

### 🛡️ 1. Zero Source Code Storage
Aion **never** stores, caches, persists, transmits, sells, or trains on your repository source code, commit history, or pull request diffs.
- Source code diffs are ingested exclusively in-memory during the ephemeral lifespan of your GitHub Action runner job.
- When the runner finishes executing, all in-memory code structures are permanently discarded.
- No central Aion servers or third-party databases retain any code snippets.

### 🔑 2. Zero Private IP Retention (Bring-Your-Own-Key)
When using Aion in Bring-Your-Own-Key (BYOK) mode (e.g., Groq, OpenRouter, OpenAI, Hugging Face, or local Ollama):
- Inference requests are dispatched directly from your GitHub runner to your configured model endpoint using your credentials.
- Your API keys are passed via GitHub Secrets and are never transmitted to, inspected by, or stored by Aion.
- When using self-hosted Ollama (`http://localhost:11434`), your code never leaves your private network.

### 🔒 3. Anonymized Telemetry Only
To iteratively improve precision, reduce false positives, and train reinforcement learning reward models, Aion records minimal, anonymized operational metadata.
- **Repository and PR identifiers are cryptographically hashed** using SHA-256 with a unique salt:
  - `repo_hash = sha256(salt + repository_name)`
  - `pr_hash = sha256(salt + pr_number)`
- Repository names, author usernames, branch names, and commit messages are **never** logged.

### 📊 4. What We Measure
Our telemetry schema records only:
1. **Model & Provider Configuration:** E.g., `provider: groq`, `model: qwen-2.5-coder-32b`.
2. **Review Metrics:** Count of candidate comments generated, count of comments posted, and count of comments suppressed by the precision verifier.
3. **Finding Taxonomies:** Categories (e.g., `bug`, `security`, `performance`) and confidence scores ($0.0 - 1.0$).
4. **Maintainer Outcomes (Subsequent Runs):** Aggregated counts of whether posted comments were marked resolved, reacted to (👍, 👎, 🚀), or amended in subsequent commits.

### 🚫 5. Complete Opt-Out
You have total control over telemetry collection. You can disable telemetry at any time by adding a single configuration flag to your `.github/workflows/review.yml` workflow:

```yaml
- name: Run Aion Code Reviewer
  uses: Wall-E-30/code-reviewer@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    enable-telemetry: 'false'
```

When `enable-telemetry: 'false'` is configured:
- No telemetry records are written to `.aion/telemetry.jsonl`.
- No telemetry metrics are recorded or exported.

---

## 3. Data Flow Diagram

```
GitHub Runner (Your Environment)
┌────────────────────────────────────────────────────────┐
│  PR Diff Ingested (In-Memory Only)                     │
│               │                                        │
│               ▼                                        │
│  Static Linters & BYOK Inference (Direct to Provider)   │
│               │                                        │
│               ▼                                        │
│  Precision Verifier Gate (Suppresses Low-Confidence)   │
│               │                                        │
│               ▼                                        │
│  Post Inline Suggestions directly to GitHub PR API     │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (If enable-telemetry: true)
          Salted SHA-256 Event Hash:
          {
            "repo_hash": "e3b0c442...",
            "pr_hash": "a1b2c3d4...",
            "comments_posted": 2,
            "categories": ["security", "bug"]
          }
```

---

## 4. Inquiries and Verification

Aion's code review pipeline and telemetry logging are fully open-source and auditable in this repository:
- Telemetry implementation: [`action/telemetry.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/action/telemetry.py)
- GitHub client: [`action/github_client.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/action/github_client.py)
- Precision verifier: [`action/verifier.py`](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/action/verifier.py)

If you have questions regarding this policy, please open a GitHub Discussion or Issue at [Wall-E-30/code-reviewer](https://github.com/Wall-E-30/code-reviewer).

