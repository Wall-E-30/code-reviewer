# Aion Plain-Language Data & Privacy Policy (GH-05, HARD-03b)

**Effective Date:** 2026-11-10  
**Version:** 1.1.0  
**Status:** Active Security & Data Policy  

---

## 1. Core Data Principles

Aion was designed from the ground up for minimal data collection, zero private code retention, and automated credential protection.

1. **Zero Private Code Training:** Aion will never train models on private user code without explicit, written opt-in consent.
2. **Automated Diff Secret Redaction (`HARD-03b`):** Before any code diff or hunk is passed to language models or diagnostic engines, it is scanned and sanitized by an automated regex redactor. All API keys, cloud tokens, private keys, and bearer credentials are substituted with `[REDACTED_SECRET:<type>]`.
3. **Zero Raw Token/Diff Logging:** CI logs, terminal output, and backend server traces never print unredacted diffs, raw tokens, or secrets.
4. **Minimal Diff Context Window (`HARD-03b`):** Review requests send only the changed diff hunks bounded by at most 25–50 surrounding context lines. Full repository checkouts are never transferred to remote inference endpoints.
5. **Telemetry Confined to Quality Signals (`HARD-03`):** Telemetry is restricted to anonymized maintainer acceptance signals:
   - Comment posted count
   - Maintainer reaction (`+1`, `-1`, `confused`, `eyes`)
   - Thread resolution status (resolved, ignored, dismissed)
   - Rule category (bug, security, style, performance)

---

## 2. What Data Is Processed

| Data Type | Processed Locally | Sent to Inference | Logged in Telemetry | Retained on Disk |
|---|:---:|:---:|:---:|:---:|
| **Repository Code** | Yes (AST linters) | Redacted hunks only | No | No (Ephemeral only) |
| **Credentials & Secrets** | Filtered | **Never** (Redacted) | **Never** | **Never** |
| **Maintainer Reactions** | Yes | No | Yes (Counts only) | Rolling 30-day window |
| **PR Metadata** | Yes (Repo/PR #) | No | Yes (Anonymized) | Rolling 30-day window |

---

## 3. GitHub API Reaction Verification (`HARD-03`)

In accordance with official GitHub documentation:
- Reactions are fetched via `GET /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions`.
- Action workflows poll previous reactions on subsequent commit/PR runs without long-running background daemons.
- App webhooks verify `X-Hub-Signature-256` HMAC signatures before ingesting any review reaction payloads.

