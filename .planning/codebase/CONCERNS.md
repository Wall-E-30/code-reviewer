# Codebase Concerns & Technical Debt

**Analysis Date:** 2026-11-04

---

## Executive Summary

The **Aion Code Reviewer** system is an AI-assisted and reinforcement-learning-guided code optimization engine designed for automated multi-pass refactoring (style cleanup, algorithmic efficiency, and security hardening). It features a Python backend (`env.py`, `inference.py`, `server/app.py`), training scripts (`train.py`, `train_rl.py`, `train_autoregressive_rl.py`), a React frontend (`frontend/src/App.jsx`), and dual serving interfaces (FastAPI and Gradio).

While the core concept demonstrates strong potential and several initial bugs have been cataloged in `bugs.md` and `bugs_report.md`, deep analysis reveals critical technical debt, security vulnerabilities, architectural fragility, and deployment hurdles:
1. **Critical Security Vulnerabilities**: Remote Code Execution (RCE) via an insecure AST-blacklisted sandbox in `env.py`, directory traversal risks in static file routing (`server/app.py`), and overly permissive CORS configurations.
2. **Broken Runtimes & Dependency Inconsistencies**: Missing dependencies in `pyproject.toml` (missing `fastapi`, `uvicorn`, and `utils.py`), top-level `gradio` import breaking headless testing in `test_suite.py`, and missing model weights in `models/rl_model`.
3. **Reward Hacking & Heuristic Gaming**: Scoring heuristics in `env.py` can be easily tricked (e.g., single loops or arbitrary list comprehensions scoring 0.99 without optimization; mandatory `if __name__ == '__main__':` bonus penalizing libraries).
4. **Performance & Concurrency Bottlenecks**: Blocking synchronous OpenAI API calls inside `async def` endpoints, unconstrained in-memory session dictionaries leading to memory leaks, and synthetic/fabricated performance metrics.
5. **Testing & Training Gaps**: No automated test coverage for API endpoints or the frontend, broken standalone test execution due to missing optional modules, and training scripts with disconnected model save paths and obsolete stubs.

---

## 1. Critical Issues & Active Bugs

### 1.1 Unrunnable Test Suite in Lean / Headless Environments
* **File References**: `test_suite.py` (lines 11–18), `inference.py` (line 7)
* **Severity**: High
* **Description**: `test_suite.py` directly imports helper functions from `inference.py`. However, `inference.py` unconditionally imports `gradio as gr` at the top level. When running in a standard virtual environment or headless CI without Gradio installed, running `python test_suite.py` crashes immediately with `ModuleNotFoundError: No module named 'gradio'`.
* **Impact**: Core testing infrastructure cannot execute in minimal containers or CI/CD pipelines without installing heavy UI packages.
* **Concrete Fix**:
  1. Move utility functions (`clean_json_string`, `robust_repair_code`, `evaluate_and_optimize`) out of `inference.py` and into `utils.py` or a dedicated `engine/` module.
  2. Guard `import gradio as gr` inside `inference.py` within a conditional check or dynamic import (`if __name__ == '__main__':` or inside `build_ui()`).

### 1.2 Multi-Line Python Signature Corruption in Syntax Fixer
* **File Reference**: `utils.py` (lines 180–189 in `_fix_python_syntax`)
* **Severity**: High
* **Description**: The syntax fixer attempts to ensure colons are present on block openers by matching `re.match(r'^(def|if|elif|for|while|class|try|except|finally|with)\b', lstripped)`. If the line does not contain `:`, it appends `:` to the end of the line. For multi-line function declarations such as:
  ```python
  def calculate_aggregate_metrics(
      data_list,
      threshold=0.5
  ):
  ```
  The first line `def calculate_aggregate_metrics(` has no colon, so `_fix_python_syntax` appends a colon, converting it to `def calculate_aggregate_metrics(:`. This creates a severe syntax error that prevents Python from parsing the code.
* **Impact**: Valid multi-line functions submitted for review are corrupted before evaluation or optimization.
* **Concrete Fix**:
  Parse tokens or maintain a parenthesis balance counter across lines before appending colons, or verify against `ast.parse` before altering syntax.

### 1.3 `Reward` Model Strict Bounds Violation on Edge Scores
* **File Reference**: `models.py` (line 28), `env.py` (line 1033), `server/app.py` (lines 98–102)
* **Severity**: Medium
* **Description**: In `models.py`, `Reward` is declared with `value: float = Field(..., gt=0.0, lt=1.0)`. This requires values to be *strictly greater than 0.0* and *strictly less than 1.0*. In `env.py`, scores can be `0.01` or `0.99`. While clamped in `server/app.py` line 98 (`max(0.01, min(0.99, float(reward)))`), if an unhandled evaluation produces `0.0` or `1.0` (or `models.py` validation is checked on raw environment scores), Pydantic raises a fatal `ValidationError`.
* **Impact**: Client requests fail with HTTP 500 when scores hit standard minimum (0.0) or maximum (1.0) limits.
* **Concrete Fix**:
  Update `models.py` to allow inclusive bounds:
  ```python
  value: float = Field(..., ge=0.0, le=1.0, description="Quality score of the current code state")
  ```

---

## 2. Security & Vulnerabilities

### 2.1 Remote Code Execution (RCE) via Flawed AST Sandbox in `env.py`
* **File Reference**: `env.py` (lines 163–211 in `_is_code_safe_to_execute`, lines 222–318 in `load_custom_code`, lines 664–796 in `_verify_correctness`)
* **Severity**: Critical
* **Description**:
  When custom code is loaded via `/optimize` or `load_custom_code`, the environment executes the code using `subprocess.run([sys.executable, f_path])` containing `exec(code_str, globals_dict)` to generate differential test cases and verify correctness.
  The only safety barrier is `_is_code_safe_to_execute()`, which uses an AST blacklist:
  - `os` is **not** included in `dangerous_modules` (only `subprocess`, `socket`, `pty`, `ctypes`, etc.). While calls to `system` and `popen` are blocked, calls to `os.remove()`, `os.rmdir()`, `os.walk()`, `os.listdir()`, and `os.environ` are not blocked!
  - `pathlib.Path` is completely permitted, allowing unhindered file read/write operations (e.g., `Path('.env').read_text()`).
  - Python dynamic attribute access, string concatenation, and reflection (e.g., iterating subclasses) can bypass naive AST checks.
* **Impact**: Any user or external actor submitting code to the public API can execute arbitrary code on the server, read environment variables/secrets, modify or delete repository files, and compromise host infrastructure.
* **Concrete Fix**:
  1. Do not use AST string/module blacklists as a security boundary.
  2. Isolate code execution in an ephemeral, unprivileged sandbox (e.g., gVisor, Docker container with `read_only` root filesystem, network disabled `--network none`, non-root user, memory and CPU limits, and seccomp/apparmor profiles).
  3. Never run `exec()` directly on the host process or unconfined host subshell.

### 2.2 Potential Path Traversal in Catch-All Static File Serving
* **File Reference**: `server/app.py` (lines 314–318)
* **Severity**: High
* **Description**: The catch-all route handles static front-end assets:
  ```python
  @app.get("/{full_path:path}")
  async def catch_all(full_path: str):
      if os.path.exists(os.path.join(frontend_path, full_path)):
          return FileResponse(os.path.join(frontend_path, full_path))
      return FileResponse(os.path.join(frontend_path, "index.html"))
  ```
  `os.path.join(frontend_path, full_path)` does not verify that the resolved canonical path (`os.path.realpath`) resides within `frontend_path`. If an incoming request provides traversal payloads (`..%2F` or `..\`), it may access files outside `frontend/dist`.
* **Impact**: Information disclosure of backend source code, configuration files, and system files.
* **Concrete Fix**:
  Validate path canonicalization before serving:
  ```python
  resolved = os.path.realpath(os.path.join(frontend_path, full_path))
  if resolved.startswith(os.path.realpath(frontend_path)) and os.path.isfile(resolved):
      return FileResponse(resolved)
  return FileResponse(os.path.join(frontend_path, "index.html"))
  ```

### 2.3 Invalid & Insecure CORS Configuration
* **File Reference**: `server/app.py` (lines 35–41)
* **Severity**: Medium
* **Description**:
  The CORS middleware is configured with:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  According to W3C Fetch and browser security specifications, combining `allow_origins=["*"]` with `allow_credentials=True` is disallowed. Browsers will block credentialed cross-origin requests. Furthermore, wildcard origins without restriction open the API to cross-origin abuse.
* **Impact**: Browser warnings/rejections on credentialed requests and unintended exposure to cross-site request forgery.
* **Concrete Fix**:
  Configure specific allowed origins via environment variable:
  ```python
  allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:7860").split(",")
  app.add_middleware(
      CORSMiddleware,
      allow_origins=allowed_origins,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

### 2.4 Unfiltered Exception Disclosure to API Consumers
* **File Reference**: `server/app.py` (lines 327–339)
* **Severity**: Medium
* **Description**:
  The global exception handler directly echoes raw internal exception messages back in the HTTP 500 response:
  ```python
  return JSONResponse(
      status_code=500,
      content={
          "error": "Internal Server Error",
          "message": str(exc),
          ...
      }
  )
  ```
* **Impact**: Leaks internal filesystem paths, module names, database connection errors, or third-party service tokens to external clients.
* **Concrete Fix**:
  Log the detailed exception internally with `logger.error(...)`, but return a sanitized generic error message to the client unless in a local debug mode.

---

## 3. Performance Bottlenecks & Resource Constraints

### 3.1 Event Loop Starvation from Synchronous OpenAI Calls in Async Handlers
* **File References**: `inference.py` (lines 526–529, 736–739), `server/app.py` (lines 221, 255)
* **Severity**: High
* **Description**:
  Endpoints in `server/app.py` are declared as `async def optimize_endpoint` and call `await evaluate_and_optimize()`. However, inside `evaluate_and_optimize()` in `inference.py`, the network call to the LLM uses the synchronous client:
  ```python
  response = client.chat.completions.create(model=MODEL_NAME, messages=[...])
  ```
  Because this network call is blocking (can take 2 to 10 seconds per inference step, up to 5 steps = 10–50 seconds), running synchronous I/O directly inside the asyncio thread completely freezes the FastAPI event loop for all concurrent users.
* **Impact**: Total loss of concurrency. While one optimization request runs, health checks, other client requests, and UI updates stall.
* **Concrete Fix**:
  Use `AsyncOpenAI`:
  ```python
  from openai import AsyncOpenAI
  async_client = AsyncOpenAI(...)
  response = await async_client.chat.completions.create(...)
  ```
  Or run synchronous calls in a worker thread pool using `asyncio.to_thread(client.chat.completions.create, ...)`.

### 3.2 Unbounded In-Memory Session Storage (Memory Leak)
* **File Reference**: `server/app.py` (lines 52–58)
* **Severity**: High
* **Description**:
  `server/app.py` stores environments in a module-level dictionary:
  ```python
  environments = {}
  def get_env(session_id: str = "default") -> CodeReviewEnv:
      session_id = session_id or "default"
      if session_id not in environments:
          environments[session_id] = CodeReviewEnv()
      return environments[session_id]
  ```
  Sessions are never cleaned up, expired, or purged. Every unique `session_id` allocates and retains a `CodeReviewEnv` instance along with its state history and cached ASTs indefinitely.
* **Impact**: Under sustained production traffic or crawler scanning, the server process experiences continuous memory growth leading to Out-Of-Memory (OOM) termination.
* **Concrete Fix**:
  Implement an LRU cache or time-to-live (TTL) eviction mechanism (e.g., using `cachetools.TTLCache(maxsize=1000, ttl=3600)`), or move session state to Redis.

### 3.3 Temporary File Accumulation on Subprocess Timeouts
* **File Reference**: `env.py` (lines 303–311, 785–793)
* **Severity**: Medium
* **Description**:
  Differential test cases write temporary Python scripts using `tempfile.NamedTemporaryFile(suffix=".py", delete=False)`. If the subprocess execution times out or encounters a fatal crash before `os.unlink(f_path)` executes, or if the process exits abruptly, orphaned files persist in the system temp directory.
* **Impact**: Over time, thousands of stale temporary files clutter the disk.
* **Concrete Fix**:
  Use a `try...finally` block strictly wrapping file creation and deletion:
  ```python
  f_path = None
  try:
      with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
          f.write(script_content)
          f_path = f.name
      res = subprocess.run([sys.executable, f_path], timeout=5.0)
  finally:
      if f_path and os.path.exists(f_path):
          try:
              os.unlink(f_path)
          except OSError:
              pass
  ```

### 3.4 Fabricated Synthetic Performance Metrics
* **File Reference**: `inference.py` (lines 556–664 in `estimate_ast_improvements`)
* **Severity**: Low / Cosmetic
* **Description**:
  The metrics displayed in the UI ("Est. Speedup" and "Memory Saved") are calculated using arbitrary mathematical polynomials based on AST node counts and line differences (e.g., `perf_gain = round((score_diff * 90.0) + (node_diff * 1.5) + (orig_nodes / 5.0), 1)`). They do not measure runtime execution time or actual memory profiling.
* **Impact**: Misleading information presented to developers who expect real profiling benchmarks.
* **Concrete Fix**:
  Clearly label metrics in the UI as "Estimated Heuristic Index" rather than empirical performance figures, or integrate true benchmark execution with Python's `timeit` and `tracemalloc`.

---

## 4. Technical Debt & Fragility

### 4.1 Packaging Configuration Missing Dependencies and Files
* **File References**: `pyproject.toml` (lines 11–18, 23–25), `requirements.txt` (lines 1–7)
* **Severity**: High
* **Description**:
  There is significant drift between `pyproject.toml` and `requirements.txt`:
  1. `pyproject.toml` declares `"openenv-core"`, which is not in `requirements.txt`.
  2. `pyproject.toml` **omits** `fastapi` and `uvicorn`, yet defines `[project.scripts] server = "server.app:main"`. Installing the project as a package (`pip install .`) fails to run the server script because FastAPI is missing.
  3. `pyproject.toml` defines `py-modules = ["env", "models", "inference"]`, **completely omitting `utils.py`**. Any packaged installation will crash on `import utils` with `ModuleNotFoundError`.
* **Impact**: Broken package builds, wheel distributions, and deployment failures when installing from `pyproject.toml`.
* **Concrete Fix**:
  Update `pyproject.toml`:
  ```toml
  dependencies = [
      "openenv-core",
      "openai>=1.0",
      "pydantic>=2.0",
      "fastapi>=0.110.0",
      "uvicorn>=0.29.0",
      "gradio>=4.0.0",
      "torch>=2.0.0",
      "transformers>=4.40.0"
  ]

  [tool.setuptools]
  packages = ["server"]
  py-modules = ["env", "models", "inference", "utils"]
  ```

### 4.2 Duplicate Serving Entrypoints & Port Collision
* **File References**: `server/app.py` (lines 342–345), `inference.py` (lines 1154–1156)
* **Severity**: Medium
* **Description**:
  Both `server/app.py` and `inference.py` run independent HTTP servers defaulting to the exact same port `7860`:
  - `server/app.py`: `uvicorn.run(app, host="0.0.0.0", port=port)` where `port = int(os.getenv("PORT", 7860))`
  - `inference.py`: `demo.launch(server_name="0.0.0.0", server_port=7860)`
  If a developer or deployment runner executes both, the second process crashes with `OSError: [Errno 98/10048] Address already in use`.
* **Impact**: Developer confusion and orchestration conflicts.
* **Concrete Fix**:
  Unify the architecture: Mount the Gradio application inside FastAPI using `gradio.mount_gradio_app(app, demo, path="/gradio")` on a single port, or assign different default ports (e.g., FastAPI on 8000, Gradio on 7860).

### 4.3 Fragile & Easily Gamed Reward Mechanics in `env.py`
* **File Reference**: `env.py` (lines 806–1033)
* **Severity**: High
* **Description**:
  The reward grading system exhibits multiple brittle heuristics:
  1. **Mandatory Main Entrypoint Guard (+0.09)**: Lines 1020–1032 give a hardcoded +0.09 bonus only if `if __name__ == '__main__':` is present. Code submitted without this boilerplate cannot achieve a score above 0.90, penalizing standard library functions or microservice modules.
  2. **Efficiency Trivial Bypass**: Lines 877–883 award an automatic 0.99 score if `len(all_loops) == 1` or if any comprehension exists (`uses_comp`), even if the underlying algorithm is still $O(N^2)$ (e.g., `[x for x in a if x in [y for y in b]]`).
  3. **Indentation Brittleness**: Lines 829–837 enforce `stmt.col_offset != node.col_offset + 4`. This fails on PEP-8-compliant code featuring multi-line conditions, wrapped parameter lists, or docstrings.
  4. **Mock Benchmark Hardcoding**: In `server/app.py` (lines 158–193), benchmark fallback actions check if `find_duplicates` is in code and blindly inject hardcoded solution strings.
* **Impact**: The RL agent learns to exploit syntax heuristics rather than improving algorithmic quality; real-world user code is incorrectly penalized or awarded false high scores.
* **Concrete Fix**:
  Refactor the grader to reward measurable improvements (complexity reductions, standard linter diagnostics via Flake8/Ruff, and automated test pass rates) rather than rigid AST node checks.

### 4.4 Monolithic Script Architecture
* **File References**: `env.py` (1,163 lines), `inference.py` (1,157 lines), `server/app.py` (348 lines), `frontend/src/App.jsx` (352 lines)
* **Severity**: Medium
* **Description**:
  The codebase places massive amounts of disparate logic into single monolithic files:
  - `env.py`: Gym environment, 12-language regex parsers, AST linters, subprocess test execution, dynamic test synthesis.
  - `inference.py`: Model loader, prompt templates, mock OpenAI logic, Gradio UI layout, CSS styles, AST diff metrics.
  - `frontend/src/App.jsx`: State, styles, syntax highlighter, tabs, API callers, toasts.
* **Impact**: High cognitive load, difficulty maintaining code, severe risk of merge conflicts and regression bugs.
* **Concrete Fix**:
  Split into clean modules:
  - `aion/core/env.py`, `aion/core/grader.py`, `aion/core/linter.py`
  - `aion/llm/client.py`, `aion/llm/prompt.py`
  - `aion/ui/gradio_app.py`
  - Frontend components: `components/InputArea.jsx`, `components/OutputArea.jsx`, `components/BenchmarkTab.jsx`.

---

## 5. Test Coverage & Reliability Gaps

### 5.1 Zero Integration Tests for FastAPI API Layer
* **File References**: `server/app.py`, `test_suite.py`
* **Severity**: High
* **Description**:
  `test_suite.py` tests internal Python helper functions and environment step methods, but contains **zero tests for the FastAPI HTTP endpoints**:
  - `/health` and `/ready`
  - `/reset`
  - `/step`
  - `/optimize` and `/optimize_full`
  - `/diff`
  - `/run_benchmark`
* **Impact**: Breaking API regressions (such as Pydantic schema mismatches or unhandled exceptions) can easily reach production unnoticed.
* **Concrete Fix**:
  Add `pytest` tests using FastAPI's `TestClient`:
  ```python
  from fastapi.testclient import TestClient
  from server.app import app

  client = TestClient(app)
  def test_health():
      response = client.get("/health")
      assert response.status_code == 200
  ```

### 5.2 Missing Test Suite for Training Pipelines
* **File References**: `train.py`, `train_rl.py`, `train_autoregressive_rl.py`
* **Severity**: Medium
* **Description**:
  None of the training scripts have accompanying test cases or verification routines:
  - Trajectory collection in `train.py` is not verified.
  - Loss convergence and weight updates in `train_rl.py` and `train_autoregressive_rl.py` are untested.
  - `train_rl.py` contains obsolete stubs (`QNetwork`, `extract_features`, `ACTION_MUTATORS`) that are dead code.
* **Impact**: Training code can rot, break silently, or produce corrupted model weights.
* **Concrete Fix**:
  Write smoke tests executing 1 step of SFT and 1 step of RL with dummy weights to ensure gradient propagation and checkpoint saving remain functional.

### 5.3 Zero Frontend Automated Tests
* **File References**: `frontend/src/App.jsx`, `frontend/package.json`
* **Severity**: Medium
* **Description**:
  The React frontend contains no test dependencies (no Vitest, Jest, or React Testing Library) and zero component or end-to-end tests.
* **Impact**: Frontend regressions (e.g., API payload schema changes, syntax highlighter crashes on unsupported syntax) must be caught manually.
* **Concrete Fix**:
  Install Vitest and React Testing Library; add tests for input handling, API error handling, and tab switching.

---

## 6. Scaling Limits & Operational Risks

### 6.1 Missing Model Checkpoints on Fresh Deployment
* **File References**: `inference.py` (lines 89–105), `.gitignore`
* **Severity**: High
* **Description**:
  `models/rl_model` was removed from git tracking (commit `097558a`). On a fresh clone, `models/rl_model` does not exist. `inference.py` catches the missing folder and sets `HAS_RL_MODEL = False`.
  However, without the RL model or a valid `HF_TOKEN`, the entire system drops to `MockOpenAI` and rule-based regex string replacement.
* **Impact**: Deployments in new environments behave as a mock demo rather than an actual AI-driven RL engine unless external keys and models are manually provisioned.
* **Concrete Fix**:
  Add an automated model download hook (e.g., pulling model weights from Hugging Face Hub on startup if local weights are not present) or document exact setup steps in `README.md`.

### 6.2 Model Save Path Disconnect in Training Scripts
* **File References**: `train_rl.py` (line 43), `train_autoregressive_rl.py` (line 161), `inference.py` (line 89)
* **Severity**: Medium
* **Description**:
  - `train_rl.py` saves model weights to `models/rl_model`.
  - `train_autoregressive_rl.py` saves weights to `models/autoregressive_rl_model`.
  - `inference.py` exclusively attempts to load from `models/rl_model`.
  Running `train_autoregressive_rl.py` will not update or affect the model used by `inference.py`.
* **Impact**: Developers training the actor-critic model will find their changes never loaded in inference.
* **Concrete Fix**:
  Standardize the model directory constant across all scripts to a shared configuration in `models.py` or `config.py`.

### 6.3 State Desynchronization Across Multi-Worker Deployments
* **File Reference**: `server/app.py` (lines 52–58)
* **Severity**: Medium
* **Description**:
  Because `environments` is an in-memory dictionary inside the Python process, running Uvicorn with multiple workers (`--workers 4`) will cause request routing to land on different workers. A client calling `/reset` on worker A and `/step` on worker B will encounter a missing or desynchronized session state.
* **Impact**: Prevents horizontal scaling of the API backend beyond a single worker thread.
* **Concrete Fix**:
  Either make environment steps stateless (passing full code and task ID on every step) or store session state in an external cache like Redis.

---

## 7. Dependencies at Risk

| Dependency | Location | Current State | Risk | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `fastapi` | `requirements.txt` | `>=0.110.0` (Missing from `pyproject.toml`) | Package install fails to include server runtime | Add to `pyproject.toml` dependencies |
| `uvicorn` | `requirements.txt` | `>=0.29.0` (Missing from `pyproject.toml`) | CLI entrypoint `server` fails to start | Add to `pyproject.toml` dependencies |
| `gradio` | `pyproject.toml`, `requirements.txt` | `>=4.0.0` (Hard dependency in `inference.py`) | Prevents lean server and headless testing | Make optional or isolate inside `ui` submodule |
| `openenv-core` | `pyproject.toml` | Unpinned (Missing from `requirements.txt`) | Schema drift between container and OpenEnv test runner | Pin exact version in both files |
| `torch` & `transformers` | `pyproject.toml`, `requirements.txt` | Unpinned `>=2.0.0`, `>=4.40.0` | Very large image footprint (~3GB+); potential breaking changes | Pin exact versions; consider CPU-only wheels in Dockerfile |

---

## 8. Prioritized Remediation Roadmap

| Priority | Issue | Affected File(s) | Impact | Recommended Action |
| :---: | :--- | :--- | :--- | :--- |
| **P0** | Insecure AST Subprocess Sandbox (RCE) | `env.py` | Arbitrary host code execution | Replace AST blacklist with containerized/gVisor sandboxing |
| **P0** | Unrunnable Test Suite due to `gradio` | `inference.py`, `test_suite.py` | CI/CD and tests fail | Decouple utility functions; make Gradio import conditional |
| **P0** | Missing Dependencies in `pyproject.toml` | `pyproject.toml` | `pip install .` fails to run server | Add `fastapi`, `uvicorn`, `utils.py` to `pyproject.toml` |
| **P1** | Path Traversal Risk in Static Routing | `server/app.py` | Arbitrary file disclosure | Enforce `os.path.realpath` boundary checks |
| **P1** | Insecure/Invalid CORS Policy | `server/app.py` | Browser request rejection, CSRF | Replace `*` with configurable origins when credentials allowed |
| **P1** | Event Loop Blocking on Synchronous I/O | `inference.py`, `server/app.py` | API concurrency freezes | Switch to `AsyncOpenAI` or `asyncio.to_thread` |
| **P1** | Unbounded Memory Growth (`environments`) | `server/app.py` | OOM crashes on long uptime | Implement TTL/LRU eviction for session store |
| **P2** | Multi-Line Signature Syntax Corruptor | `utils.py` | Valid code corrupted | Use AST/paren-matching before colon insertion |
| **P2** | Reward Schema Boundary Failure | `models.py` | HTTP 500 on 0.0 or 1.0 reward | Change `gt=0.0, lt=1.0` to `ge=0.0, le=1.0` |
| **P2** | Temporary File Accumulation | `env.py` | Disk leak in temp directory | Wrap script creation and deletion in `try...finally` |
| **P2** | Inconsistent Training Model Paths | `train_rl.py`, `train_autoregressive_rl.py` | Models saved to wrong dir | Standardize path constant across all files |
| **P3** | Port Collision (`7860` for both servers) | `server/app.py`, `inference.py` | Port conflict errors | Mount Gradio inside FastAPI or use distinct ports |
| **P3** | Missing Automated API / UI Tests | `test_suite.py`, `frontend/` | Regressions undetected | Add `pytest` TestClient and Vitest suites |
| **P3** | Monolithic File Layout | `env.py`, `inference.py` | High technical debt | Refactor into modular package directory structure |

---
*Generated by GSD Codebase Mapper on 2026-11-04.*
