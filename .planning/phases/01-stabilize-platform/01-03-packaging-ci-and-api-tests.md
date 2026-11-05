---
phase: 01-stabilize-platform
plan: 03
type: execute
wave: 2
depends_on:
  - 01-01
  - 01-02
files_modified:
  - pyproject.toml
  - requirements.txt
  - LICENSE
  - .github/workflows/ci.yml
  - tests/test_api.py
autonomous: true
requirements:
  - PLAT-03
  - PLAT-05
must_haves:
  truths:
    - pyproject.toml and requirements.txt are aligned with dependencies including fastapi, uvicorn, and cachetools.
    - LICENSE file exists at project root containing the full Apache License Version 2.0 text.
    - .github/workflows/ci.yml runs Ruff linting, Pytest test suites, and Vite frontend builds on push and pull requests.
    - tests/test_api.py uses FastAPI TestClient to test /health, /reset, /step, /optimize, /optimize_full, and /diff endpoints.
  artifacts:
    - pyproject.toml
    - requirements.txt
    - LICENSE
    - .github/workflows/ci.yml
    - tests/test_api.py
  key_links:
    - tests/test_api.py verifies server/app.py routes without running external servers.
    - .github/workflows/ci.yml automates verification on GitHub infrastructure.
---

<objective>
Align packaging manifests, create the official Apache-2.0 LICENSE file, build a dedicated FastAPI API test suite using TestClient, and establish an automated GitHub Actions CI workflow.

Purpose: Provide standard open-source licensing, guarantee package installability across environments, and ensure automated regression testing in continuous integration.
Output: pyproject.toml, requirements.txt, LICENSE, .github/workflows/ci.yml, and tests/test_api.py.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/01-stabilize-platform/RESEARCH.md
</execution_context>

<tasks>

<task type="tracer">
  <name>Align Packaging & Create Apache-2.0 License</name>
  <files>pyproject.toml, requirements.txt, LICENSE</files>
  <action>
1. Update `pyproject.toml`:
   - Declare dependencies: `fastapi>=0.110.0`, `uvicorn>=0.29.0`, `pydantic>=2.0`, `openai>=1.0`, `cachetools>=5.3.0`, `torch>=2.0.0`, `transformers>=4.40.0`, `openenv-core`.
   - Update project license to `"Apache-2.0"`.
2. Update `requirements.txt` to include `cachetools>=5.3.0`.
3. Create `LICENSE` file containing the standard Apache License, Version 2.0 text with 2026 Aion contributors copyright.
  </action>
  <verify>
    <automated>python -c "import tomli if sys.version_info < (3, 11) else tomllib as tomllib; open('LICENSE'); print('License file confirmed')"</automated>
  </verify>
  <done>Packaging dependencies are reconciled across files, and Apache-2.0 LICENSE is present.</done>
</task>

<task type="auto">
  <name>Build Comprehensive API Test Suite in tests/test_api.py</name>
  <files>tests/test_api.py</files>
  <action>
Create `tests/test_api.py` using `fastapi.testclient.TestClient`:
1. Test `GET /health` returns status healthy and 200.
2. Test `POST /reset` with valid task ID returns Observation schema.
3. Test `POST /step` with valid action returns Observation and structured Reward model.
4. Test `POST /optimize` with Python code returns valid OptimizeResponse with non-empty diff and score.
5. Test `POST /optimize_full` completes chained passes and recovers gracefully from intermediate syntax flaws.
6. Test `POST /diff` returns line-by-line diff metadata.
7. Test Path Traversal: Request `GET /..%2F..%2Fpyproject.toml` or similar traversal payload and verify that internal files are NOT returned.
  </action>
  <verify>
    <automated>python -m pytest tests/test_api.py -v</automated>
  </verify>
  <done>All FastAPI API endpoints and security boundaries are validated with automated tests.</done>
</task>

<task type="auto">
  <name>Create GitHub Actions CI Workflow</name>
  <files>.github/workflows/ci.yml</files>
  <action>
Create `.github/workflows/ci.yml` defining continuous integration for pushes to `main` and all pull requests:
1. Job: `backend-tests`:
   - Runs on `ubuntu-latest`.
   - Sets up Python 3.11.
   - Installs dependencies from `requirements.txt`.
   - Runs Ruff linter (`ruff check .`).
   - Runs Pytest test suite (`pytest tests/ test_suite.py`).
2. Job: `frontend-build`:
   - Runs on `ubuntu-latest`.
   - Sets up Node.js 22.
   - Runs `npm ci` inside `frontend/`.
   - Runs `npm run build` inside `frontend/` to verify bundling without errors.
  </action>
  <verify>
    <automated>python -c "import os; assert os.path.exists('.github/workflows/ci.yml')"</automated>
  </verify>
  <done>GitHub Actions CI configuration is active for linting, testing, and frontend bundling.</done>
</task>

</tasks>

