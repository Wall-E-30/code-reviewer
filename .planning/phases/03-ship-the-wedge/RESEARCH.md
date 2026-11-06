# Phase 03: Ship the Wedge (GitHub Action & High-Precision Review Pipeline) — Research & Technical Specification

**Phase:** `03-ship-the-wedge`  
**Milestone:** v1.0 — Path to the No. 1 Code Reviewer (Zero-Budget, RL-Driven)  
**Date:** 2026-11-05  
**Requirements Covered:** `GH-01`, `GH-02`, `GH-03`, `GH-04`, `GH-05`  

---

## 1. Executive Summary & Objective

Phase 3 transitions Aion from a standalone prototype into a **developer-native distribution wedge: a zero-hosting GitHub Action**. Developers do not review code in separate web apps; they review code inside GitHub Pull Requests.

To win developer adoption, Aion enforces a radical philosophy: **Precision Over Volume**. AI reviewers that leave 25 comments full of stylistic nitpicks are uninstalled within a week. Aion posts at most **3 to 5 high-confidence, actionable comments per PR**, complete with valid GitHub suggestion blocks (````suggestion ...````), backed by static linters, and verified by a multi-stage confidence gate.

Furthermore, Phase 3 establishes the **flywheel foundation from day one**: publishing a strict, plain-language data policy (`DATA_POLICY.md`) and deploying an automated telemetry logger that tracks candidate comments, posting decisions, and subsequent maintainer reactions (resolved, dismissed, reactions) via subsequent-run polling.

---

## 2. Technical Constraints & Design Principles

1. **Zero-Hosting Architecture:** Runs directly inside GitHub's free runner minutes (`ubuntu-latest`). No centralized servers or hosting costs required.
2. **Bring-Your-Own-Key (BYOK) & Multi-Provider Support:** Supports user-supplied keys for Groq (ultra-fast free tier), OpenRouter, OpenAI, Hugging Face, or local Ollama instances without external tracking.
3. **Hard Ceiling on Volume ($\le 5$ Comments):** Strict limiter enforcing a maximum of 5 inline comments per PR, prioritizing critical bugs, security vulnerabilities, and logic flaws over nitpicks.
4. **Actionable Suggestions Required:** Every inline comment MUST include a concrete, syntactically valid GitHub suggestion block so maintainers can apply the fix with a single click.
5. **No Webhook Server Needed for Telemetry:** Because a GitHub Action cannot receive incoming webhooks, maintainer reactions are polled during subsequent runs in the repository.

---

## 3. Architecture & Data Flow

```
Pull Request Opened / Synchronized
               │
               ▼
   GitHub Action Runner (`action.yml`)
               │
               ▼
        `action/main.py`
               │
      ┌────────┴────────┐
      ▼                 ▼
Poll Previous Runs    Parse Current Diff
(Maintainer Reactions) (Added / Modified Lines)
      │                 │
      ▼                 ▼
Telemetry Logger      Static Linters (Pre-Filter)
(Resolved / Ignored)   (Ruff / Bandit / AST)
                        │
                        ▼
                 Context Builder
                 (Scope & Function Signatures)
                        │
                        ▼
                 LLM Inference Engine
                 (Groq / OpenRouter / Ollama / Mock)
                        │
                        ▼
                 Precision Verifier Gate
                 - Deduplicate against linters
                 - Verify suggestion syntax
                 - Discard style nitpicks
                 - Rank by confidence
                 - Cap at <= 5 comments
                        │
                        ▼
                 GitHub API Client
                 POST /repos/.../pulls/.../reviews
                 - Top-level Markdown summary
                 - Inline comments with suggestion blocks
                        │
                        ▼
                 Telemetry Ledger Output
```

---

## 4. Component Specifications

### 4.1 GitHub Action Interface (`action.yml`, `GH-01`)
```yaml
name: 'Aion Code Reviewer'
description: 'High-precision, verifiable AI code reviewer for GitHub Pull Requests'
inputs:
  github-token:
    description: 'GitHub token for reading PRs and posting review comments'
    required: true
    default: ${{ github.token }}
  api-key:
    description: 'API key for model inference (Groq, OpenRouter, OpenAI, Hugging Face)'
    required: false
  provider:
    description: 'Inference provider (groq, openrouter, openai, ollama, huggingface, mock)'
    required: false
    default: 'mock'
  model:
    description: 'Model identifier'
    required: false
    default: 'qwen-2.5-coder-32b'
  max-comments:
    description: 'Maximum inline comments per review'
    required: false
    default: '5'
  min-confidence:
    description: 'Confidence threshold (0.0 to 1.0) for posting comments'
    required: false
    default: '0.7'
  enable-telemetry:
    description: 'Enable anonymized candidate comment and reaction logging'
    required: false
    default: 'true'
```

### 4.2 Multi-Provider Inference Client (`action/providers.py`, `GH-04`)
- Unified interface `BaseReviewProvider`:
  - `generate_review(diff: str, context: str, file_path: str, language: str) -> List[ReviewComment]`
- Pluggable provider implementations:
  1. `GroqProvider`: Uses Groq API (`llama-3.3-70b-versatile`, `qwen-2.5-coder-32b-instruct`) with high throughput.
  2. `OpenRouterProvider`: Connects to OpenRouter free tiers.
  3. `OllamaProvider`: Connects to self-hosted Ollama on `http://localhost:11434/v1`.
  4. `OpenAIProvider`: Direct OpenAI API.
  5. `MockReviewProvider`: Fast, deterministic offline provider for CI testing and hermetic evaluation.

### 4.3 Hybrid Review Pipeline & Precision Verifier (`action/verifier.py`, `GH-03`)
- **Stage 1: Pre-Filtering with Linters:** Runs `ruff check` and `bandit` on modified Python files. Known linter issues are flagged immediately without LLM token waste.
- **Stage 2: LLM Candidate Generation:** Generates candidate review comments containing line numbers, explanations, and suggested replacements.
- **Stage 3: Verification & Precision Gate:**
  - Suggestion validation: Verifies that applying the suggestion yields valid syntax.
  - Nitpick suppression: Discards comments focusing purely on trivial whitespace, variable naming taste, or comments without concrete defects.
  - Confidence ranking: Assigns scores ($0.0 - 1.0$); discards anything below `min_confidence` (default 0.7).
  - Ceiling enforcement: Selects the top $K \le 5$ highest-impact comments.

### 4.4 High-Precision PR Comment Formatter (`action/formatter.py`, `GH-02`)
Every inline comment is rendered as:
````markdown
### 🛡️ Aion Finding: Potential Logic Bug (`invert_comparison`)
**Confidence:** 92% | **Severity:** Critical

The comparison operator on this loop condition was inverted, causing the loop to terminate prematurely when `count <= max_retries`.

```suggestion
    while count < max_retries:
```

*Reported by [Aion Code Reviewer](https://github.com/Wall-E-30/code-reviewer) • [Data & Privacy Policy](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/DATA_POLICY.md)*
````

### 4.5 Data Policy & Reaction Polling Telemetry (`action/telemetry.py`, `GH-05`)
1. **Plain-Language Data Policy (`DATA_POLICY.md`):**
   - Explicit guarantee: User repository source code is never stored, sold, or retained.
   - Telemetry data is restricted to:
     - Cryptographic SHA-256 hash of repository name and PR number.
     - Candidate comment category and confidence score.
     - Whether the comment was posted or suppressed by the verifier gate.
     - Maintainer outcome: resolved, dismissed, reacted to, or commit amended.
2. **Subsequent-Run Reaction Polling:**
   - On each PR workflow execution:
     - Query previously posted Aion comments on the active PR (`GET /repos/{owner}/{repo}/pulls/{number}/comments`).
     - Check if comment has reactions (`+1`, `-1`, `confused`, `rocket`).
     - Check if comment thread was marked resolved by the PR author.
     - Check if new commits in the PR touched the referenced line span (indicates human fix applied).
   - Writes telemetry records to `.aion/telemetry.jsonl` or GitHub Workflow Step Summary.

---

## 5. Plan Decomposition for Phase 3

| Plan | Title | Requirements | Key Deliverables |
|---|---|:---:|---|
| **03-01** | **Hybrid Pipeline, Multi-Provider Engine & Precision Verifier** | `GH-03`, `GH-04` | `action/diff_parser.py`, `action/providers.py`, `action/linters.py`, `action/verifier.py`, unit test suite. |
| **03-02** | **GitHub Action Packaging, API Client & PR Review Posting** | `GH-01`, `GH-02` | `action.yml`, `action/main.py`, `action/github_client.py`, `action/formatter.py`, inline suggestion formatting. |
| **03-03** | **Data Policy, Reaction Polling Telemetry & Benchmark Audit** | `GH-05` | `DATA_POLICY.md`, `action/telemetry.py`, reaction polling, Aion-Bench validation ($\ge 50\%$ precision, $\le 5$ comments/PR). |

