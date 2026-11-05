# Phase 1: Stabilize & Make Trustworthy (Platform & Security Hardening) — Research

**Phase:** `01-stabilize-platform`  
**Date:** 2026-11-05  
**Focus:** Platform stability, sandbox hardening, asynchronous concurrency, packaging, testing, and honesty.

---

## 1. Security & Sandboxing Findings

### 1.1 Differential Execution RCE in `env.py`
- **Location:** `env.py` (lines 163–211 in `_is_code_safe_to_execute`, lines 222–318 in `load_custom_code`, lines 664–796 in `_verify_correctness`).
- **Mechanism:** When custom code is loaded via `/optimize` or `load_custom_code`, `env.py` generates a test runner script and invokes `subprocess.run([sys.executable, f_path])` running `exec(code_str)` directly on the host machine.
- **Vulnerability:** The AST filter blocks only specific dangerous modules (like `subprocess`, `socket`, `pty`), but permits `pathlib.Path`, `os.remove`, `os.listdir`, and environment reflection. Any user can execute arbitrary code on the server host.
- **Phase 1 Decision (`SEC-01`):** Completely disable host-side `subprocess.run` execution of untrusted user code. Rely strictly on static analysis: Python AST parsing, syntax validation, and dynamic AST linting. Defer full ephemeral container execution to Phase 4 (`RL-03`).

### 1.2 Path Traversal in Static File Serving
- **Location:** `server/app.py` (lines 314–318 in `catch_all`).
- **Code:**
  ```python
  @app.get("/{full_path:path}")
  async def catch_all(full_path: str):
      if os.path.exists(os.path.join(frontend_path, full_path)):
          return FileResponse(os.path.join(frontend_path, full_path))
      return FileResponse(os.path.join(frontend_path, "index.html"))
  ```
- **Vulnerability:** `os.path.join(frontend_path, full_path)` without verification permits directory traversal via `..%2F` or encoded slashes, potentially leaking backend source code or configuration files.
- **Fix:** Validate that the resolved canonical path (`os.path.realpath`) is strictly prefixed by the canonical frontend root:
  ```python
  canonical_root = os.path.realpath(frontend_path)
  resolved_path = os.path.realpath(os.path.join(frontend_path, full_path))
  if resolved_path.startswith(canonical_root) and os.path.isfile(resolved_path):
      return FileResponse(resolved_path)
  return FileResponse(os.path.join(canonical_root, "index.html"))
  ```

### 1.3 CORS Hardening & Exception Disclosure
- **Location:** `server/app.py` (lines 35–41 and lines 327–339).
- **CORS Fix:** Combine explicit `ALLOWED_ORIGINS` loaded from environment variables (defaulting to `http://localhost:5173,http://localhost:7860`), replacing invalid `allow_origins=["*"]` + `allow_credentials=True`.
- **Exception Sanitization:** Log detailed tracebacks server-side with `logger.error(...)`, but return sanitized messages (`{"error": "Internal Server Error", "request_id": request_id}`) to public API consumers.

---

## 2. Concurrency & Performance Findings

### 2.1 Event Loop Starvation
- **Location:** `inference.py` (lines 526–529, 736–739) called from `server/app.py`.
- **Problem:** Synchronous network calls `client.chat.completions.create(...)` run directly inside `async def` endpoints, completely freezing the Uvicorn event loop for several seconds per inference step.
- **Fix:** Offload synchronous inference calls to worker threads via `asyncio.to_thread(func, *args)` or migrate to `AsyncOpenAI(api_key=..., base_url=...)` and `await client.chat.completions.create(...)`.

### 2.2 Unbounded Session Dictionary Memory Leak
- **Location:** `server/app.py` (line 52: `environments = {}`).
- **Problem:** Every new `session_id` instantiates a `CodeReviewEnv` that persists indefinitely in memory.
- **Fix:** Use `cachetools.TTLCache(maxsize=1000, ttl=3600)` with a 1-hour expiration policy to automatically evict stale session instances.

---

## 3. Syntax Auto-Repair & Packaging Findings

### 3.1 Multi-Line Function Signature Corruption
- **Location:** `utils.py` (lines 180–189 in `_fix_python_syntax`).
- **Bug:** Checks `if not line.endswith(':'): line += ':'` on any line starting with `def|class|if|for`. For multi-line signatures like:
  ```python
  def calculate_score(
      items,
      weights
  ):
  ```
  It forcefully transforms line 1 into `def calculate_score(:`, corrupting valid code.
- **Fix:** Count unclosed parentheses across lines, and only append `:` if the complete multi-line header statement has closed all parentheses and brackets.

### 3.2 Headless Test Suite Execution
- **Location:** `inference.py` (line 7: `import gradio as gr`) and `test_suite.py` (lines 11–18).
- **Problem:** `test_suite.py` imports `inference.py`, which unconditionally imports Gradio at the top level. In lean CI or headless containers without Gradio installed, tests immediately abort with `ModuleNotFoundError: No module named 'gradio'`.
- **Fix:** Make `gradio` import lazy (inside `build_ui()` or guarded by `if __name__ == '__main__':`).

---

## 4. UI Metric Honesty & Scope Clarity

### 4.1 Fabricated Metric Removal
- **Location:** `inference.py` (`estimate_ast_improvements`) and `frontend/src/App.jsx`.
- **Problem:** Speedup and memory reduction numbers are polynomial functions over AST node count deltas, destroying trust.
- **Fix:** Relabel metrics in the UI as "Structural Complexity Index" (or AST node reduction), and measure real runtime with `timeit` where execution is enabled.

### 4.2 Language Scope Clarification
- **Location:** `frontend/src/App.jsx` language selector.
- **Update:** Group languages into:
  - **Supported (Tier-1):** Python, TypeScript, JavaScript
  - **Experimental:** Java, C++, C, Go, Rust, Ruby, Kotlin, Swift, C#, PHP, HTML, CSS, SQL, Bash.

