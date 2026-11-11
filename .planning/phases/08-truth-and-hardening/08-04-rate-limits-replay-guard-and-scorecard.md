---
phase: 08-truth-and-hardening
plan: 04
type: execute
wave: 4
depends_on:
  - 08-01
  - 08-02
  - 08-03
files_modified:
  - server/app.py
  - server/rate_limiter.py
  - docs/SCORECARD.md
  - docs/MASTER_DOCUMENT.md
  - tests/test_rate_limits_and_scorecard.py
autonomous: true
requirements:
  - HARD-06
  - SCORECARD
must_haves:
  truths:
    - FastAPI server enforces 2MB request body ceiling, returning 413 for oversized payloads.
    - Sliding window rate limiter enforces per-IP (60 req/min) and per-repo (120 req/min) limits, returning 429 Too Many Requests.
    - Webhook endpoint checks X-GitHub-Delivery against a 1-hour TTL cache to block replay attacks.
    - Outbound HTTP calls have explicit <= 10.0s timeouts.
    - docs/SCORECARD.md contains an honest two-column scorecard ('Built' vs 'Validated on Real Data') with explicit source tags ([SYNTHETIC], [SIMULATED], [REAL-OFFLINE], [LIVE-PILOT]).
  artifacts:
    - server/rate_limiter.py
    - server/app.py
    - docs/SCORECARD.md
    - tests/test_rate_limits_and_scorecard.py
---

<objective>
Implement API Hardening, Rate Limiting, Webhook Replay Guard (`HARD-06`), and the Honest Milestone Scorecard (`SCORECARD`).
Shield server endpoints from exhaustion and replay attacks, and produce an unvarnished audit scorecard with explicit data lineage tags.
</objective>

<tasks>

<task type="tracer">
  <name>Implement Rate Limiter, Payload Size Guard, and Replay Protection</name>
  <files>server/rate_limiter.py, server/app.py</files>
  <action>
1. In `server/rate_limiter.py`:
   - Implement `RateLimiter` with sliding-window request counting per IP (default: 60/min) and per repo (default: 120/min).
   - Implement `WebhookDeliveryCache` tracking `X-GitHub-Delivery` UUIDs with 1-hour TTL.
2. In `server/app.py`:
   - Add middleware checking `Content-Length`: returns `413 Request Entity Too Large` if $> 2\text{MB}$.
   - Add rate limiter middleware checking client IP and repo ID.
   - In `/api/github/webhook`: check delivery ID cache and reject/idempotently acknowledge replays.
   - Enforce `timeout=10.0` on all outbound HTTP calls.
  </action>
  <verify>
python -c "from server.rate_limiter import RateLimiter, WebhookDeliveryCache; rl = RateLimiter(); assert rl.allow_request('127.0.0.1'); print('Rate limiter tracer verified')"
  </verify>
</task>

<task>
  <name>Author Honest Milestone Scorecard with Source Tagging</name>
  <files>docs/SCORECARD.md, docs/MASTER_DOCUMENT.md</files>
  <action>
1. Create `docs/SCORECARD.md`:
   - Add two-column audit table: "Built (Code Exists & Tests Pass)" vs "Validated on Real Data (In-the-Wild Evidence)".
   - Tag every metric explicitly:
     - `[SYNTHETIC]` — Injected bugs, programmatic AST mutations
     - `[SIMULATED]` — Unit test mocks, synthetic PR events
     - `[REAL-OFFLINE]` — Mined GitHub historical PRs
     - `[LIVE-PILOT]` — Real-time telemetry from active partner repos.
   - Clearly delineate what is proven vs what is pending pilot validation in Milestone v1.1.
2. Cross-reference `docs/SCORECARD.md` in `docs/MASTER_DOCUMENT.md`.
  </action>
  <verify>
pytest tests/test_rate_limits_and_scorecard.py -v
  </verify>
</task>

</tasks>

