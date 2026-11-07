---
phase: 07-community-and-growth
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/badge.py
  - server/app.py
  - docs/OPEN_SOURCE_COMMITMENT.md
  - tests/test_badge_and_quality.py
autonomous: true
requirements:
  - GROWTH-01
must_haves:
  truths:
    - GET /api/badge/{owner}/{repo} and GET /api/badge returns dynamically rendered SVG badges compatible with GitHub READMEs and Shields.io.
    - Badges dynamically reflect live repo precision (green for >= 70%, yellow for 50-69%, red for <50%, gray for no data).
    - GET /api/repos/{owner}/{repo}/quality returns repository precision, review volume, convention adherence, and badge embed URLs.
    - docs/OPEN_SOURCE_COMMITMENT.md guarantees perpetual zero-cost access for public open-source repositories under OSI-approved licenses.
  artifacts:
    - server/badge.py
    - server/app.py
    - docs/OPEN_SOURCE_COMMITMENT.md
    - tests/test_badge_and_quality.py
  key_links:
    - server/badge.py reads repo precision data from server/precision_gate.py or telemetry records.
    - server/app.py exposes GET /api/badge and GET /api/repos/{owner}/{repo}/quality.
---

<objective>
Implement the "Free for Open Source" guarantee, dynamic SVG badge generator, and repository quality dashboard API (`GROWTH-01`).
Enable open-source maintainers to showcase their code quality with a live "Reviewed by Aion" README badge and inspect rolling precision metrics.

Purpose: Provide open-source repositories with free, verifiable code quality credentials that drive viral GitHub distribution.
Output: `server/badge.py`, updated `server/app.py`, `docs/OPEN_SOURCE_COMMITMENT.md`, and `tests/test_badge_and_quality.py`.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/07-community-and-growth/RESEARCH.md
@server/app.py
@server/precision_gate.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Dynamic SVG Badge Generator</name>
  <files>server/badge.py</files>
  <action>
1. In `server/badge.py`:
   - Implement `generate_svg_badge(left_text: str, right_text: str, color_hex: str) -> str`:
     - Creates crisp, scalable SVG badge using standard flat template (Shields.io style).
     - Renders left label (e.g. "Reviewed by Aion") on charcoal background (`#555`).
     - Renders right label (e.g. "passing", "78% precision", "verified") on colored pill background.
   - Implement `get_badge_for_precision(precision: Optional[float], label: str = "Reviewed by Aion") -> str`:
     - If `precision is None`: returns gray badge (`#9f9f9f`, text: "unverified" or "no data").
     - If `precision >= 0.70`: returns green badge (`#2ea44f`, text: f"{int(precision * 100)}% precision" or "passing").
     - If `0.50 <= precision < 0.70`: returns yellow badge (`#dfb317`, text: f"{int(precision * 100)}% precision").
     - If `precision < 0.50`: returns red badge (`#cb2431`, text: f"{int(precision * 100)}% precision").
  </action>
  <verify>
python -c "from server.badge import generate_svg_badge, get_badge_for_precision; svg = get_badge_for_precision(0.85); assert '<svg' in svg and '#2ea44f' in svg; print('SVG badge generator tracer verified')"
  </verify>
</task>

<task>
  <name>Mount Badge and Repository Quality Endpoints in server/app.py</name>
  <files>server/app.py</files>
  <action>
1. In `server/app.py`:
   - Import `generate_svg_badge`, `get_badge_for_precision` from `server.badge`.
   - Import `MultiRepoTelemetryAggregator` from `server.precision_gate`.
   - Add routes:
     - `GET /api/badge/{owner}/{repo}` and `GET /api/badge`:
       - Query params: `repo` (optional fallback), `metric` (`precision` | `status`, default `precision`).
       - Returns `Response(content=svg_bytes, media_type="image/svg+xml")`.
       - Adds caching headers: `Cache-Control: public, max-age=300, s-maxage=3600`.
     - `GET /api/repos/{owner}/{repo}/quality`:
       - Returns JSON with repository precision, total reviews, accepted reviews, active days, badge markdown & HTML snippets, and status (`PASS`/`MONITORING`).
  </action>
  <verify>
python -c "from server.app import app; assert any(r.path == '/api/badge/{owner}/{repo}' for r in app.routes); print('Badge routes mounted successfully')"
  </verify>
</task>

<task>
  <name>Document Open-Source Commitment Manifesto</name>
  <files>docs/OPEN_SOURCE_COMMITMENT.md</files>
  <action>
1. In `docs/OPEN_SOURCE_COMMITMENT.md`:
   - Declare irrevocable guarantee: Aion core review engine is permanently free for public open-source repositories under OSI-approved licenses.
   - Outline zero telemetry retention of private code, data privacy guarantees, and README badge integration guide.
   - Detail how open-source maintainers can install and display the "Reviewed by Aion" badge.
  </action>
  <verify>
python -c "import os; assert os.path.exists('docs/OPEN_SOURCE_COMMITMENT.md'); print('Open Source Commitment doc verified')"
  </verify>
</task>

<task>
  <name>Build Badge and Quality Test Suite</name>
  <files>tests/test_badge_and_quality.py</files>
  <action>
1. In `tests/test_badge_and_quality.py`, write test cases:
   - `test_generate_svg_badge_structure()`: Verifies valid SVG tags, dimensions, text escaping, and colors.
   - `test_badge_color_and_text_thresholds()`: Verifies green (>=70%), yellow (50-69%), red (<50%), and gray (no data).
   - `test_badge_endpoint_direct()`: Tests badge generation with live repo records.
   - `test_repo_quality_endpoint()`: Tests JSON metrics return and markdown embed snippet generation.
   - `test_open_source_commitment_document()`: Tests presence and key guarantees of commitment manifesto.
  </action>
  <verify>
pytest tests/test_badge_and_quality.py -v
  </verify>
</task>

</tasks>

