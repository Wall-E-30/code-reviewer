# Phase 8 Research: Truth and Hardening

**Phase:** `08-truth-and-hardening`  
**Milestone:** v1.1 — Prove It on Real Code  
**Requirements:** `HARD-01`, `HARD-02`, `HARD-03`, `HARD-03b`, `HARD-04`, `HARD-05`, `HARD-06`, `SCORECARD`  
**Date:** 2026-11-10  

---

## 1. Executive Summary & Problem Analysis

Milestone v1.1 shifts Aion from synthetic/in-distribution evaluation to operational reality and provable guarantees on real-world code. Phase 8 ("Truth and Hardening") is the foundational integrity phase of this milestone. It enforces strict separation of concerns, closes security and sandbox threat vectors, eliminates misleading or unmeasured metrics, purges legacy prototype code that is susceptible to reward hacking, redacts secrets from pull request diffs, protects endpoints from replay and exhaustion attacks, and produces an honest scorecard with explicit source tagging.

---

## 2. Requirement Breakdown & Implementation Strategy

### A. Sandbox Hardening & Zero Untrusted Host Execution (`HARD-01`, `HARD-02`)
- **Status in Codebase:** In commit `1ba7016`, `rl/sandbox/container.py` was refactored to eliminate the insecure in-process subprocess fallback.
- **Security Invariant:** If Docker or Podman is not running or missing, Aion **strictly refuses host execution** of untrusted code and falls back to safe static analysis (Python AST syntax parsing).
- **Hardening Flags:** Container runs with `--pids-limit 64`, `--cap-drop ALL`, `--security-opt no-new-privileges`, `--memory 512m`, `--cpus 1.0`, `--network none`, read-only root (`/`), non-root user `1000:1000`, and a 64MB `tmpfs` for `/tmp`.
- **Threat Model & Tests:** `docs/SANDBOX_THREAT_MODEL.md` and `tests/test_sandbox_escape.py` (11 tests) cover symlinks, `/proc` writes, fork bombs, disk quotas, DNS exfiltration, token leaks, and filesystem escape.

### B. Verified Reaction Polling & App Events (`HARD-03`)
- **GitHub Reactions API:** Reactions to review comments (`+1`, `-1`, `laugh`, `confused`, `heart`, `hooray`, `rocket`, `eyes`) must be queried using official GitHub REST endpoints (`GET /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions`).
- **Action Polling:** In GitHub Action (which runs per-commit/PR event, not as a daemon), reaction feedback from *previous* review comments must be polled on the *next* workflow run.
- **App Webhook Fixtures:** Webhook processing in `server/github_app.py` must use recorded, real GitHub API event fixtures (`pull_request_review_comment`, `reaction`) rather than synthetic mock formats.

### C. Diff Secret Redaction & Minimal Context (`HARD-03b`)
- **Secret Redaction:** Before any diff content is passed to LLM inference or logged, it must pass through an automated secret redactor scanning for:
  - AWS access keys (`AKIA[0-9A-Z]{16}`)
  - GitHub personal access tokens (`ghp_[a-zA-Z0-9]{36}`)
  - Generic private keys (`-----BEGIN [A-Z ]*PRIVATE KEY-----`)
  - OpenAI / Anthropic API keys (`sk-[a-zA-Z0-9]{32,}`)
  - Slack tokens, generic bearer tokens, high-entropy secrets.
- **Log Hygiene:** CI logs and terminal output must never print unredacted diffs or tokens.
- **Minimal Context:** Send only modified line hunks and immediate enclosing function/class scopes (bounded to $\le 50$ lines of context).

### D. Deprecate Legacy AST Grader & Clean Metrics (`HARD-04`)
- **Legacy Purge:** The original prototype files (`env.py`, `train_rl.py`, `train_autoregressive_rl.py`) relied on an unconstrained AST node count heuristic that was vulnerable to reward hacking (e.g. padding code with dead AST nodes yielded artificial speedup).
- **Migration:**
  - Move `env.py`, `train_rl.py`, `train_autoregressive_rl.py` to `legacy/`.
  - Add `legacy/README.md` explaining the reward-hacking vulnerability and directing users to `ReviewEnv` (`rl/env.py`).
  - Deprecate `/optimize` and `/optimize_full` endpoints in `server/app.py` or re-route `/reset` and `/step` to `ReviewEnv`.
  - Remove all synthetic speedup percentages and memory reduction numbers from the UI (`frontend/src/`) and API responses.

### E. Document & Code Consistency Reconciliation (`HARD-05`)
- **Single Benchmark CLI:** Standardize on `python -m bench.runner` (and `aion bench run`).
- **Matcher Algorithm:** Ensure documentation accurately states the exact matcher algorithm used (greedy matching on line distance + category, rather than claiming Kuhn-Munkres/Hungarian unless Hungarian is implemented).
- **Bandit Description:** Accurately document the online threshold optimizer as per-category Beta-Bernoulli Thompson Sampling rather than general contextual multi-armed bandit.

### F. Request Limits, Rate Limits & Replay Guard (`HARD-06`)
- **Payload Size Limits:** Reject HTTP request bodies $> 2\text{MB}$ with `413 Payload Too Large`.
- **Rate Limiting:** Implement per-IP and per-repo rate limiting (e.g., 60 requests/minute per IP, 120 requests/minute per repo).
- **Webhook Replay Protection:** Store recent `X-GitHub-Delivery` UUIDs in a sliding-window TTL cache (`TTLCache(maxsize=10000, ttl=3600)`) and reject duplicate delivery IDs with `409 Conflict` or idempotent `200 OK`.
- **Outbound Timeouts:** Enforce explicit timeouts (e.g. $10\text{s}$) on all external HTTP requests (GitHub API, LLM inference).

### G. Milestone Scorecard Honest Source Tagging (`SCORECARD`)
- **Scorecard Overhaul:** Rewrite the Milestone Scorecard in documentation (`MASTER_DOCUMENT.md`, `ROADMAP.md`, `STATE.md`).
- **Two Columns:** "Built (Code Exists & Tests Pass)" vs "Validated on Real Data (In-the-Wild Evidence)".
- **Source Tags:** Tag every single reported metric:
  - `[SYNTHETIC]` — Injected bugs, programmatic AST mutations
  - `[SIMULATED]` — Unit test mocks, synthetic PR events
  - `[REAL-OFFLINE]` — Mined GitHub historical PRs
  - `[LIVE-PILOT]` — Real-time telemetry from active partner repos.

---

## 3. Plan Wave Breakdown for Phase 8

1. **Plan 08-01 (Wave 1: `HARD-01`, `HARD-02`):**
   - Formalize sandbox threat model and escape test suite verification.
   - Confirm container flags and zero-untrusted-host-execution guarantees.
2. **Plan 08-02 (Wave 2: `HARD-03`, `HARD-03b`):**
   - Diff secret redaction engine (`action/redactor.py`).
   - Verified reaction polling on next workflow run and recorded real API fixtures.
   - CI log sanitization and minimal diff context enforcement.
3. **Plan 08-03 (Wave 3: `HARD-04`, `HARD-05`):**
   - Move legacy `env.py`, `train_rl.py`, `train_autoregressive_rl.py` to `legacy/` with explanatory README.
   - Re-route `/reset`, `/step` to `ReviewEnv`; remove unmeasured speedup numbers from UI and API.
   - Reconcile CLI runner, matcher documentation (greedy matching), and bandit documentation (Beta Thompson sampling).
4. **Plan 08-04 (Wave 4: `HARD-06`, `SCORECARD`):**
   - Request size limiter middleware, rate limiter, webhook delivery ID replay cache, and outbound timeouts in `server/app.py`.
   - Update Milestone Scorecard with "Built" vs "Validated on real data" columns and source tags.
