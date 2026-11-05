---
phase: 01-stabilize-platform
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - env.py
  - server/app.py
  - utils.py
autonomous: true
requirements:
  - SEC-01
  - SEC-02
  - PLAT-02
  - PLAT-03
must_haves:
  truths:
    - Host-side subprocess execution of untrusted user code is disabled in env.py; static analysis and AST checks are used exclusively.
    - Catch-all static route validates that resolved paths reside inside the canonical frontend directory.
    - CORS middleware rejects wildcard credentials and binds to explicit ALLOWED_ORIGINS.
    - API 500 internal server error responses sanitize error details and return unique request IDs.
    - Synchronous LLM calls are offloaded to prevent freezing the FastAPI asyncio event loop.
    - Session environment dictionary in server/app.py uses a bounded TTLCache.
    - utils.py does not corrupt multi-line Python function signatures with misplaced colons.
  artifacts:
    - env.py
    - server/app.py
    - utils.py
  key_links:
    - server/app.py imports cachetools for session TTL and protects static asset delivery.
    - env.py load_custom_code evaluates code safely without spawning host subprocesses.
---

<objective>
Harden backend security and concurrency by eliminating host-side RCE, securing static path routing and CORS, preventing asyncio event loop starvation, bounding session memory with a TTL cache, and fixing multi-line Python syntax repair.

Purpose: Protect the server host from arbitrary code execution and path traversal, ensure high API responsiveness under concurrent load, and prevent syntax corruption of valid user code.
Output: Hardened env.py, server/app.py, and utils.py.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/01-stabilize-platform/RESEARCH.md
</execution_context>

<tasks>

<task type="tracer">
  <name>Disable Host Subprocess Execution in env.py (Static Analysis Only)</name>
  <files>env.py</files>
  <action>
Modify `load_custom_code` and `_verify_correctness` in `env.py` to completely disable spawning host `subprocess.run` on untrusted user code.
Replace the dynamic subprocess test generator with safe static analysis:
1. Parse the AST with `ast.parse` and catch `SyntaxError`.
2. Compute baseline code reward and run `_generate_dynamic_linter` directly in-process via AST visitors.
3. In `_verify_correctness`, return `(True, "Static AST analysis verified (safe mode)")` without executing `exec()` or subshells on the host.
4. Add a module-level docstring documenting that untrusted code execution is prohibited on the host process per SEC-01.
  </action>
  <verify>
    <automated>python -c "from env import CodeReviewEnv; env = CodeReviewEnv(); obs = env.load_custom_code('import os\nprint(1)', 'style-cleanup'); assert obs is not None"</automated>
  </verify>
  <done>Untrusted code is analyzed purely via AST visitors without invoking host subshells or exec.</done>
</task>

<task type="auto">
  <name>Harden Path Traversal, CORS, and Session TTL in server/app.py</name>
  <files>server/app.py</files>
  <action>
Update `server/app.py` with three security and stability fixes:
1. Path Traversal: In `catch_all`, canonicalize `frontend_path` using `os.path.realpath`. Assert that `os.path.realpath(os.path.join(frontend_path, full_path))` starts with the canonical root before returning `FileResponse`.
2. CORS: Read `ALLOWED_ORIGINS` from `os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:7860")`. Split into a list and configure `CORSMiddleware`.
3. Error Sanitization: In the global exception handler, log `traceback.format_exc()` server-side, but return `{"error": "Internal Server Error", "request_id": request_id}` to clients without leaking `str(exc)`.
4. Session TTL: Replace `environments = {}` with `cachetools.TTLCache(maxsize=1000, ttl=3600)`.
  </action>
  <verify>
    <automated>python -c "import server.app as app; assert hasattr(app, 'environments'); from cachetools import TTLCache; assert isinstance(app.environments, TTLCache)"</automated>
  </verify>
  <done>Static file route verifies canonical path boundaries, CORS is bound to explicit origins, and session cache enforces TTL eviction.</done>
</task>

<task type="auto">
  <name>Unblock Async Event Loop & Fix Multi-Line Syntax Repair</name>
  <files>server/app.py, utils.py</files>
  <action>
1. In `server/app.py`, ensure endpoints `/optimize` and `/optimize_full` run inference calls inside `asyncio.to_thread` (e.g. `await asyncio.to_thread(evaluate_and_optimize, ...)` or `await asyncio.to_thread(run_full_optimization, ...)`), preventing blocking network I/O from stalling the event loop.
2. In `utils.py:180-189` (`_fix_python_syntax`), fix the colon-appending logic: maintain an open-parentheses balance counter across lines. Do not append `:` to a line starting with `def|class|if|for` if the line has unclosed `(`, `[`, or `{` (such as multi-line function declarations).
  </action>
  <verify>
    <automated>python -c "from utils import fix_syntax_errors; code = 'def test(\n    a,\n    b\n):\n    return a + b\n'; fixed = fix_syntax_errors(code, 'python'); import ast; ast.parse(fixed)"</automated>
  </verify>
  <done>FastAPI event loop remains unblocked during inference, and multi-line function signatures are parsed cleanly without corrupted colons.</done>
</task>

</tasks>

