# Phase 06: Scale & Distribution (GitHub App & Long-Term Precision Gate) — Research & Technical Specification

**Phase:** `06-scale-and-distribution`  
**Milestone:** v1.0 — Path to the No. 1 Code Reviewer (Zero-Budget, RL-Driven)  
**Date:** 2026-11-07  
**Requirements Covered:** `APP-01`, `APP-02`, `APP-03`  

---

## 1. Executive Summary & Strategic Rationale

Phase 6 scales Aion from an on-demand CI GitHub Action into an omnipresent developer review infrastructure:
1. **From Polling to Real-Time Webhooks (`APP-01`):** While GitHub Actions require scheduling runner containers on every push, a webhook-driven GitHub App responds instantaneously to pull requests, receives real-time reactions (`+1`, `-1`, `rocket`), and immediately feeds maintainer sentiment into the online contextual bandit (`rl/bandit.py`) and convention memory (`rl/memory.py`).
2. **Long-Term Precision Gate Across 100+ Repositories (`APP-02`):** Proving commercial and open-source viability requires demonstrating that Aion maintains $\ge 70\%$ live precision over 30 consecutive days across 100+ active repositories, with verifiable weekly improvement tracking as repo-specific bandits adapt.
3. **Local Developer Surfaces (`APP-03`):** Reviewing code *before* pushing reduces pull request review cycle time. Delivering `aion review --staged` CLI and a lightweight VS Code extension brings the same high-precision linter, convention memory, and verifier gating directly into developer IDEs.

---

## 2. Technical Architecture & Component Flow

```
   ┌──────────────────────────────────────────────────────────┐
   │                     GitHub Cloud                         │
   │  (PR Opened / Synchronized / Reaction Added / Comments)  │
   └────────────────────────────┬─────────────────────────────┘
                                │ HTTPS Webhooks (HMAC-SHA256)
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ GitHub App Server (FastAPI / Render / Free Tier)         │
   │ - Signature Verification (X-Hub-Signature-256)           │
   │ - App JWT & Installation Token Auth                      │
   │ - Event Dispatcher:                                      │
   │   • pull_request: triggers Review Pipeline               │
   │   • reaction / review_comment: immediate bandit feedback │
   └───────────────┬──────────────────────────┬───────────────┘
                   │                          │
                   ▼                          ▼
   ┌──────────────────────────────┐   ┌──────────────────────────────┐
   │ Review Pipeline & Verifier   │   │ Precision Gate Aggregator    │
   │ (Linters + Model + Verifier) │   │ (APP-02)                     │
   │ Post <= 5 inline comments    │   │ - Rolling 30-day window      │
   └───────────────┬──────────────┘   │ - 100+ Active Repositories   │
                   │                  │ - Precision >= 70% Gate      │
                   │                  │ - Weekly Progress Charts     │
                   ▼                  └──────────────────────────────┘
   ┌──────────────────────────────┐
   │ Local Developer Surfaces     │
   │ (APP-03)                     │
   │ - `aion review --staged` CLI │
   │ - VS Code Extension (LSP/Linter)
   └──────────────────────────────┘
```

---

## 3. Deep-Dive Specifications

### 3.1 Webhook-Driven GitHub App (`APP-01`)

#### 3.1.1 Authentication & Security
- **HMAC-SHA256 Webhook Verification:**
  Every payload is validated against `X-Hub-Signature-256` using the shared `GITHUB_WEBHOOK_SECRET`:
  ```python
  def verify_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
      mac = hmac.new(secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
      expected = "sha256=" + mac.hexdigest()
      return hmac.compare_digest(expected, signature_header)
  ```
- **GitHub App JWT & Installation Token:**
  The App signs a RS256 JWT using its private key (valid for 10 minutes) and exchanges it via `POST /app/installations/{installation_id}/access_tokens` to obtain short-lived repository tokens.

#### 3.1.2 Webhook Event Routing
- `pull_request` (`opened`, `synchronize`):
  Extracts repository owner/name, PR number, base/head commit SHAs, downloads unified diff, runs static linters, fetches convention memory, executes model inference (or local/BYOK provider), gates with `PrecisionVerifier`, and posts inline comments via GitHub REST API.
- `pull_request_review_comment` (`created`, `edited`):
  Detects maintainer responses (e.g. "thanks, fixed" or "not applicable").
- `reaction` (`created`, `deleted`):
  Detects reactions on comments posted by the App. Immediately routes positive (`+1`, `rocket`) or negative (`-1`, `confused`) rewards to `CategoryBandit.update(category, reward)`.

---

### 3.2 100+ Repos Precision Gate & Telemetry Aggregator (`APP-02`)

#### 3.2.1 Tracking Metrics Across Repositories
To satisfy `APP-02`, Aion aggregates anonymized telemetry across $\ge 100$ active repositories over 30 days:
- **Accepted Comment Indicators:**
  - Explicit maintainer resolution (`resolved`).
  - Positive emoji reactions (`+1`, `rocket`, `heart`).
  - Subsequent commit modifying the referenced line within 48 hours.
- **Rejected Comment Indicators:**
  - Explicit dismissal (`dismissed`).
  - Negative emoji reactions (`-1`, `confused`).
  - Comment ignored with PR merged without line modification.
- **Rolling Window Formula:**
  $$\text{Live Precision}_{30\text{d}} = \frac{\sum_{r=1}^{R} \text{AcceptedComments}_r}{\sum_{r=1}^{R} (\text{AcceptedComments}_r + \text{RejectedComments}_r)}$$
  Target: $\text{Live Precision} \ge 70.0\%$ over 30 consecutive days across $R \ge 100$ repositories.

#### 3.2.2 Automated Report & Improvement Chart
The telemetry aggregator generates structured weekly Markdown reports (`WEEKLY_PRECISION_REPORT.md` / JSON) detailing:
- Active repository count.
- Weekly precision progression showing bandit threshold convergence.
- Per-category acceptance breakdown (`security`, `bug`, `performance`, `style`).

---

### 3.3 Developer CLI Surface & VS Code Extension (`APP-03`)

#### 3.3.1 `aion review --staged` CLI
- Packaged as an entry point in `pyproject.toml`: `aion = "cli.main:main"`.
- Runs locally in under 2 seconds:
  ```bash
  # Review git staged changes before commit
  aion review --staged

  # Review a specific branch or commit
  aion review --target HEAD~1

  # Check local repository conventions
  aion conventions
  ```
- Reads git diff directly via `git diff --cached`, runs static linters (`linters.py`), queries local convention memory (`.aion/conventions.json`), evaluates against local Ollama or BYOK endpoint, filters through `PrecisionVerifier`, and formats actionable suggestions in the terminal.

#### 3.3.2 VS Code Extension (`editors/vscode/`)
- Packaged as a clean, standard VS Code extension:
  - Manifest: `package.json` with commands `aion.reviewStaged`, `aion.reviewCurrentFile`.
  - Diagnostics Provider: Pushes findings as `vscode.Diagnostic` items (squiggles under buggy lines).
  - Code Action Provider: Offers 1-click "Apply Aion Suggestion" QuickFix.
  - Configuration:
    - `aion.provider`: `"ollama" | "byok" | "mock"`
    - `aion.model`: default `"aion-reviewer"`
    - `aion.minConfidence`: default `0.70`

---

## 4. Free-Tier Hosting & Zero-Budget Deployment

| Component | Target Platform | Free Tier Feasibility | Fallback / Local Execution |
|---|---|---|---|
| **Webhook App Server** | Render / Hugging Face Spaces / Railway | Render Web Service (Free 512MB RAM, spins down when idle, fast wake on webhook) | Standalone FastAPI ASGI server (`server/app.py`) |
| **Model Inference** | Ollama local / BYOK (Groq/OpenAI/HF Router free tiers) | Zero cost via user BYOK or local quantized GGUF | Mock provider during CI / offline mode |
| **Telemetry & State** | SQLite / Local JSONL in repo / Free Cloud DB | Zero cost via local `.aion/` tracking | In-memory mock aggregator for test suites |

---

## 5. Wave Breakdown Plan for Phase 6

- **Wave 1 (Plan 06-01): Webhook-Driven GitHub App & Real-Time Event Dispatch (`APP-01`)**
  - Webhook route with HMAC-SHA256 signature verification.
  - GitHub App JWT and installation token exchange.
  - Real-time event handling (`pull_request`, `reaction`, `review_comment`).
  - Instantaneous feedback loop to `RepoConventionMemory` and `CategoryBandit`.

- **Wave 2 (Plan 06-02): Multi-Repo Telemetry Aggregator & 30-Day Precision Gate (`APP-02`)**
  - Multi-repo precision aggregator (`server/precision_gate.py`).
  - Rolling 30-day window metrics calculation across 100+ active repositories.
  - Weekly improvement tracker and markdown report generator.
  - Strict precision gate assertion ($\ge 70\%$ live precision over 30 days).

- **Wave 3 (Plan 06-03): CLI & Editor Surface (`aion review --staged` & VS Code Extension) (`APP-03`)**
  - CLI engine (`cli/main.py`) with `--staged` review, diff inspection, convention memory injection, and formatted terminal output.
  - Packaging `aion` command in `pyproject.toml`.
  - VS Code extension package in `editors/vscode/` with diagnostics, inline suggestions, and code actions.

