# Phase 8 Plan 04: Rate Limiting, Replay Guard & Scorecard Summary (HARD-06, SCORECARD)

**Execution Date:** 2026-11-10  
**Phase:** 08-truth-and-hardening  
**Wave:** 4  
**Status:** Completed ✅  

---

## 1. Accomplishments

### 1.1 API Hardening & Payload Size Ceiling (`HARD-06`)
- Implemented `MAX_PAYLOAD_BYTES = 2 * 1024 * 1024` ($2\text{MB}$) body limit check in `server/app.py` middleware.
- Oversized requests are immediately rejected with `413 Request Entity Too Large`.

### 1.2 Sliding-Window Rate Limiting (`HARD-06`)
- Created `server/rate_limiter.py` with thread-safe `RateLimiter`:
  - Per-IP rate limiting: 60 req/min ceiling; returns `429 Too Many Requests` with `Retry-After: 60` and `X-RateLimit-Limit: 60`, `X-RateLimit-Remaining`.
  - Excluded `/health` and `/ready` probes from rate limits.
  - Per-repo rate limiting: 120 req/min ceiling across webhook deliveries.

### 1.3 Webhook Replay Guard (`HARD-06`)
- Created `WebhookDeliveryCache` tracking `X-GitHub-Delivery` UUIDs in a 1-hour TTL cache (`TTLCache(maxsize=10000, ttl=3600)`).
- Webhook endpoint `/api/github/webhook` checks incoming delivery IDs; duplicate deliveries are idempotently acknowledged and ignored without double-processing.

### 1.4 Outbound HTTP Timeouts (`HARD-06`)
- Enforced strict $\le 10.0\text{s}$ timeout ceilings across all outbound HTTP clients:
  - `GitHubClient` (`action/github_client.py`): Default timeout reduced from $30.0\text{s}$ to $10.0\text{s}$.
  - `OpenAICompatibleProvider` (`action/providers.py`): Default timeout reduced from $30.0\text{s}$ to $10.0\text{s}$.

### 1.5 Honest Milestone Scorecard & Lineage Tagging (`SCORECARD`)
- Created `docs/SCORECARD.md`:
  - Formalized two-column comparison: "Built (Code Exists & Tests Pass)" vs "Validated on Real Data (In-the-Wild Evidence)".
  - Defined and applied 4 metric taxonomy tags: `[SYNTHETIC]`, `[SIMULATED]`, `[REAL-OFFLINE]`, and `[LIVE-PILOT]`.
  - Delineated what is proven in automated CI vs what is pending pilot validation in Milestone v1.1.
- Updated `MASTER_DOCUMENT.md` Section 12 with data lineage tags and cross-references to `docs/SCORECARD.md`.

---

## 2. Verification Results

All 7 tests in `tests/test_rate_limits_and_scorecard.py` passed:
```
tests/test_rate_limits_and_scorecard.py::test_payload_size_ceiling_413 PASSED
tests/test_rate_limits_and_scorecard.py::test_payload_under_limit_allowed PASSED
tests/test_rate_limits_and_scorecard.py::test_per_ip_rate_limiting_429 PASSED
tests/test_rate_limits_and_scorecard.py::test_webhook_replay_guard PASSED
tests/test_rate_limits_and_scorecard.py::test_per_repo_rate_limiting PASSED
tests/test_rate_limits_and_scorecard.py::test_outbound_http_timeout_ceilings PASSED
tests/test_rate_limits_and_scorecard.py::test_honest_scorecard_integrity PASSED
============================== 7 passed in 2.43s ==============================
```

---

## 3. Files Created / Modified
- `server/rate_limiter.py`
- `server/app.py`
- `action/github_client.py`
- `action/providers.py`
- `docs/SCORECARD.md`
- `MASTER_DOCUMENT.md`
- `tests/test_rate_limits_and_scorecard.py`
