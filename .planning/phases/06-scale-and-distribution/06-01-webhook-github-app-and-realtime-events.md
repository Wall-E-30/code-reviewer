---
phase: 06-scale-and-distribution
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/github_app.py
  - server/app.py
  - tests/test_github_app.py
autonomous: true
requirements:
  - APP-01
must_haves:
  truths:
    - Webhook endpoint validates GitHub HMAC-SHA256 signatures using X-Hub-Signature-256 header and rejects unauthorized requests with HTTP 401.
    - GitHub App JWT generation and installation access token exchange allow the server to authenticate as a GitHub App without user PAT tokens.
    - pull_request events (opened, synchronize) automatically trigger review pipeline execution, posting at most 5 inline comments with suggestion blocks.
    - reaction and pull_request_review_comment events capture maintainer feedback in real-time, instantly routing reward signals to CategoryBandit and RepoConventionMemory without waiting for subsequent Action runs.
  artifacts:
    - server/github_app.py
    - server/app.py
    - tests/test_github_app.py
  key_links:
    - server/github_app.py routes real-time reactions to rl/bandit.py and rl/memory.py.
    - server/github_app.py reuses action review pipeline components (action/diff_parser.py, action/verifier.py, action/github_client.py).
---

<objective>
Build and deploy the webhook-driven GitHub App server module (`APP-01`).
Implement HMAC-SHA256 signature verification, GitHub App authentication (JWT & installation tokens), and real-time event dispatch for `pull_request` (automated review posting) and `reaction` / `review_comment` (real-time bandit and convention memory updates).

Purpose: Replace polling and manual CI Action scheduling with a real-time, webhook-driven GitHub App deployable on free tiers (Render, HF Spaces, Railway) that provides instantaneous reviews and live feedback capture.
Output: `server/github_app.py`, webhook routes mounted on `server/app.py`, and `tests/test_github_app.py`.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/06-scale-and-distribution/RESEARCH.md
@server/app.py
@action/github_client.py
@action/verifier.py
@rl/bandit.py
@rl/memory.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Webhook Signature Verifier and GitHub App Authenticator</name>
  <files>server/github_app.py</files>
  <action>
1. In `server/github_app.py`:
   - Implement `verify_webhook_signature(payload_bytes: bytes, signature_header: Optional[str], secret: str) -> bool`:
     - Computes HMAC-SHA256 of `payload_bytes` with `secret`.
     - Uses constant-time `hmac.compare_digest` to prevent timing attacks.
     - Returns False if signature header is missing, malformed, or doesn't match.
   - Implement `GitHubAppAuth`:
     - Accepts `app_id: str`, `private_key: str`, `client_id: Optional[str]`.
     - `create_app_jwt(expiration_minutes: int = 10) -> str`: Generates signed RS256 JWT for GitHub App authentication (or mock JWT in test mode).
     - `get_installation_token(installation_id: int) -> str`: Requests short-lived installation access token from GitHub API (`POST /app/installations/{id}/access_tokens`).
  </action>
  <verify>
python -c "from server.github_app import verify_webhook_signature; import hmac, hashlib; sec = 'test_secret'; body = b'hello world'; sig = 'sha256=' + hmac.new(sec.encode(), body, hashlib.sha256).hexdigest(); assert verify_webhook_signature(body, sig, sec) is True; assert verify_webhook_signature(body, 'sha256=bad', sec) is False; print('Signature verifier tracer verified')"
  </verify>
</task>

<task>
  <name>Implement Webhook Event Handler and Real-Time Feedback Router</name>
  <files>server/github_app.py, server/app.py</files>
  <action>
1. In `server/github_app.py`:
   - Implement `GitHubAppHandler`:
     - Constructor accepting optional `GitHubAppAuth`, `CategoryBandit`, `RepoConventionMemory`, and `PrecisionVerifier`.
     - `handle_pull_request_event(payload: Dict[str, Any]) -> Dict[str, Any]`:
       - Extracts repo full name, PR number, head SHA, base SHA, action (`opened`, `synchronize`).
       - If action is relevant: initiates review pipeline (diff extraction, linting, provider completion, verifier filtering, posting comments via GitHub client).
       - Returns review dispatch status dict.
     - `handle_reaction_event(payload: Dict[str, Any]) -> Dict[str, Any]`:
       - Handles reaction (`created`, `deleted`).
       - Extracts reaction content (`+1`, `-1`, `rocket`, `confused`, `heart`).
       - Maps emoji to reward score (+1.0 for positive, -1.5 for negative).
       - Routes feedback immediately to `CategoryBandit.update(category, reward)` and persists state.
     - `handle_review_comment_event(payload: Dict[str, Any]) -> Dict[str, Any]`:
       - Captures maintainer replies and resolutions, feeding signals into convention memory and bandit.
     - `dispatch_event(event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]`:
       - Routes GitHub event based on `X-GitHub-Event` header.
2. In `server/app.py`:
   - Mount webhook endpoint: `POST /api/github/webhook`.
   - Validates `X-Hub-Signature-256` header.
   - Dispatches payload to `GitHubAppHandler`.
  </action>
  <verify>
python -c "from server.github_app import GitHubAppHandler; from rl.bandit import CategoryBandit; b = CategoryBandit(); h = GitHubAppHandler(bandit=b); res = h.dispatch_event('reaction', {'action': 'created', 'reaction': {'content': '+1'}, 'comment': {'body': 'Category: security'}}); assert res['status'] == 'processed'; print('Event handler verified')"
  </verify>
</task>

<task>
  <name>Build GitHub App Webhook Test Suite</name>
  <files>tests/test_github_app.py</files>
  <action>
1. In `tests/test_github_app.py`, write comprehensive test cases:
   - `test_signature_verification_valid_and_invalid()`: Validates correct and tampered HMAC signatures.
   - `test_missing_signature_header_rejected()`: Confirms missing header returns False.
   - `test_pull_request_opened_dispatch()`: Simulates `pull_request` event and verifies review initiation.
   - `test_positive_reaction_updates_bandit()`: Verifies `+1` reaction on security comment increases bandit willingness.
   - `test_negative_reaction_elevates_threshold()`: Verifies `-1` reaction elevates bandit threshold.
   - `test_fastapi_webhook_endpoint_success()`: Uses FastAPI `TestClient` to test `POST /api/github/webhook` with signed payload.
   - `test_fastapi_webhook_endpoint_unauthorized()`: Verifies invalid signature returns 401 Unauthorized.
  </action>
  <verify>
python -m pytest tests/test_github_app.py -v
  </verify>
</task>

</tasks>

