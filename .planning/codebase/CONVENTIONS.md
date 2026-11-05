# Coding Conventions

**Analysis Date:** 2026-11-04

## Overview & Architecture Style

The **Aion Code Reviewer** codebase is a hybrid AI engineering and full-stack web project. It unites an AST-graded reinforcement learning environment with Large Language Model (LLM) inference and a reactive web UI. The codebase spans two primary language ecosystems:
1. **Python 3.10+**: Core RL environment (`env.py`), LLM orchestration & Gradio UI (`inference.py`), REST API (`server/app.py`), utility layers (`utils.py`), data schemas (`models.py`), training scripts (`train.py`, `train_rl.py`, `train_autoregressive_rl.py`), and test infrastructure (`test_suite.py`).
2. **JavaScript (ES2020+) & React 19**: Modern Single-Page Application (`frontend/src/App.jsx`) configured with Vite and ESLint.

Architecturally, the project favors a flat, script-centric root layout with distinct modular directories for web serving (`server/`), user interface (`frontend/`), and reference benchmark data (`data/`).

---

## 1. Naming Conventions

### 1.1 Python

The Python codebase follows standard PEP 8 naming conventions with domain-specific patterns for RL and AST handling:

| Entity Type | Convention | Examples | Source Locations |
| :--- | :--- | :--- | :--- |
| **Classes / Pydantic Models** | `PascalCase` | `CodeReviewEnv`, `Action`, `Observation`, `Reward`, `OptimizeResponse`, `MockOpenAI`, `QNetwork` | `models.py`, `env.py`, `inference.py`, `train_rl.py` |
| **Functions & Methods** | `snake_case` | `reset`, `step`, `_calculate_reward`, `_is_code_safe_to_execute`, `evaluate_and_optimize`, `run_full_optimization`, `detect_language`, `normalize_indentation` | `env.py`, `inference.py`, `utils.py` |
| **Private / Internal Methods** | `_leading_underscore` | `_get_observation`, `_build_diff`, `_verify_correctness`, `_calculate_reward_generic`, `_strip_comments`, `_fix_python_syntax` | `env.py`, `utils.py` |
| **Global Constants & Dictionaries** | `UPPER_SNAKE_CASE` | `TASKS`, `SUPPORTED_LANGUAGES`, `LANG_KEY_MAP`, `GRADIO_LANG_MAP`, `RL_MODEL_DIR`, `MODEL_NAME`, `API_BASE_URL` | `env.py:15`, `inference.py:89-123`, `utils.py:4-9` |
| **Variables & Parameters** | `snake_case` | `current_task_id`, `step_count`, `max_score_seen`, `proposed_code`, `session_id`, `linter_report` | `env.py`, `server/app.py`, `models.py` |
| **CLI / Entry Scripts** | `snake_case.py` | `test_suite.py`, `train_rl.py`, `train_autoregressive_rl.py` | Root directory |

#### Concrete Examples from Code:
```python
# From models.py: PascalCase model and snake_case fields
class OptimizeResponse(BaseModel):
    initial_score: float = Field(..., description="Quality score of the code before optimization")
    final_score: float = Field(..., description="Quality score of the code after optimization")
    fixed_code: str = Field(..., description="Optimized source code")
    perf_gain: str = Field(..., description="Estimated performance improvement percentage")
    mem_reduction: str = Field(..., description="Estimated memory savings")
    recommendation: str = Field(..., description="AI insight and summary of changes made")
```

```python
# From env.py: Internal AST helper naming
def _is_code_safe_to_execute(self, code: str) -> bool:
    dangerous_modules = {'subprocess', 'socket', 'pty', 'ctypes', ...}
    ...
```

### 1.2 JavaScript & React

The frontend located in `frontend/src/` adheres to modern React standards:

| Entity Type | Convention | Examples | Source Locations |
| :--- | :--- | :--- | :--- |
| **React Components** | `PascalCase` | `App`, `StatBox`, `Toast` | `frontend/src/App.jsx:20, 27, 57` |
| **State Variables & Hooks** | `camelCase` with `set*` | `[activeTab, setActiveTab]`, `[inputCode, setInputCode]`, `[isOptimizing, setIsOptimizing]` | `frontend/src/App.jsx:58-75` |
| **Event Handlers** | `handle*` | `handleCopy`, `handleRunBenchmark`, `handleOptimize` | `frontend/src/App.jsx:82, 88, 108` |
| **Utility Functions** | `camelCase` | `highlightPython`, `addToast` | `frontend/src/App.jsx:4, 77` |
| **Constants & Mappings** | `UPPER_SNAKE_CASE` | `SUPPORTED_LANGUAGES`, `LANG_KEYS`, `API_BASE` | `frontend/src/App.jsx:41, 47, 55` |
| **CSS Class Names** | `kebab-case` | `gradio-container`, `stat-box`, `code-box`, `badge`, `action-btn` | `frontend/src/AionStyles.css` |

#### Concrete Example from Code:
```jsx
// From frontend/src/App.jsx: Component, state, and handler conventions
const StatBox = ({ title, value, type = '' }) => (
  <div className={`stat-box ${type}`}>
    <h3>{title}</h3>
    <p>{value}</p>
  </div>
);

function App() {
  const [activeTab, setActiveTab] = useState('optimizer');
  const [taskType, setTaskType] = useState('efficiency-boost');
  const [isOptimizing, setIsOptimizing] = useState(false);

  const handleOptimize = async (full = false) => {
    setIsOptimizing(true);
    // ...
  };
  // ...
}
```

### 1.3 REST API Endpoints

In `server/app.py`, endpoint paths use a combination of simple lowercase and `snake_case`:
- System checks: `/health`, `/ready`, `/state`
- Environment lifecycle: `/reset`, `/step`
- Optimization actions: `/optimize`, `/optimize_full`, `/diff`, `/run_benchmark`
- Static & documentation endpoints: `/`, `/docs`, `/redoc`, `/openapi.json`

---

## 2. Imports & Dependency Management

### 2.1 Python Import Organization

Python source files generally organize imports into three logical tiers:
1. **Standard Library**: `os`, `sys`, `json`, `re`, `ast`, `difflib`, `asyncio`, `uuid`, `logging`, `tempfile`, `subprocess`, `base64`.
2. **Third-Party Frameworks**: `fastapi`, `uvicorn`, `pydantic`, `openai`, `torch`, `transformers`, `gradio`.
3. **Local Project Modules**: `env`, `models`, `utils`, `inference`.

```python
# From server/app.py: Layered imports and system path adjustment
import sys
import os
import uvicorn
import logging
import uuid
import difflib
import ast
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

# Ensure the system can find env.py and inference.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env import CodeReviewEnv
from models import Action, OptimizeResponse, Observation, Reward
```

### 2.2 Dynamic & Conditional Imports

To manage heavy ML dependencies (`torch`, `transformers`) and defer startup latencies:
- `server/app.py` defers imports of `inference.py` (`run_full_optimization`, `evaluate_and_optimize`, `HAS_RL_MODEL`) inside individual endpoint functions (`/run_benchmark`, `/optimize`, `/optimize_full`).
- `torch` is dynamically imported in `server/app.py:138` via `torch = __import__('torch')` if `HAS_RL_MODEL` is True.
- `train.py:84-85` wraps `import torch` and `from transformers import AutoModelForCausalLM` inside a `try...except ImportError` block to provide informative warning messages when ML packages are absent.

```python
# From train.py: Guarded optional import
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print("PyTorch and Transformers are available. Starting training script configuration...")
except ImportError:
    print("\n[Dependency Warning] PyTorch, Transformers, or TRL not found in the current environment.")
```

### 2.3 JavaScript / React Imports

The frontend strictly uses ES Modules with relative imports for local styles and components:
```javascript
// From frontend/src/main.jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
```
In `frontend/src/App.jsx`, React hooks are imported via named destructuring:
```javascript
import React, { useState, useEffect, useRef } from 'react';
import './AionStyles.css';
```

---

## 3. Error Handling & Defensive Coding

The codebase employs defense-in-depth patterns to ensure continuous operation across AI generation errors, syntax bugs, and network failures.

### 3.1 Syntax Validation & Automatic Regression Recovery

In `env.py`, the `step()` method performs pre-execution validation using `ast.parse()`. If proposed code contains syntax errors or degrades the quality score, the environment automatically reverts to the previous best known code:

```python
# From env.py: Pre-validation and automatic rollback
if self.language == "python":
    try:
        ast.parse(proposed_code)
    except SyntaxError as e:
        has_syntax_error = True
        syntax_err_msg = str(e)

if has_syntax_error:
    reward = 0.01
    if self.backtrack:
        self.code = self.best_code
        regression_warning = f"[Regression Warning] Action failed due to Syntax Error: {syntax_err_msg}. Reverted to the previous best-known state."
    else:
        self.code = proposed_code
        regression_warning = f"[Syntax Error] {syntax_err_msg}."
```

### 3.2 Robust AI Output Sanitization

LLM outputs are inherently unpredictable. `inference.py` and `utils.py` implement defensive parsing pipelines:
- **`clean_json_string()`**: Recursively balances braces to extract valid JSON even when surrounded by markdown code blocks or conversational text.
- **`deep_syntax_repair()`**: Employs AST-aware regex to repair common unquoted `print(Hello World)` calls without mangling valid variables or keywords.
- **`robust_repair_code()`**: Automatically attaches missing `if __name__ == "__main__":` entrypoint guards and corrects function body indentation.

```python
# From inference.py: Defensive JSON extraction
def clean_json_string(raw_string):
    """Aggressively extracts the largest valid JSON object from model output."""
    if not raw_string:
        return raw_string
    first_brace = raw_string.find('{')
    if first_brace == -1:
        return raw_string
    last_brace_indices = [i for i, ch in enumerate(raw_string) if ch == '}']
    for last_brace in reversed(last_brace_indices):
        if last_brace > first_brace:
            candidate = raw_string[first_brace : last_brace + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue
    match = re.search(r'\{.*\}', raw_string, re.DOTALL)
    if match:
        return match.group(0)
    return raw_string
```

### 3.3 Mock AI Fallback for Offline Resilience

When external API keys (`HF_TOKEN`) are missing or network calls fail, the inference engine falls back seamlessly to `MockOpenAI`:
```python
# From inference.py: Fallback client selection
if not HF_TOKEN or len(HF_TOKEN.strip()) < 10:
    client = MockOpenAI()
else:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
```
The `MockOpenAI` implementation in `inference.py:140-350` utilizes internal rule-based optimizers to simulate high-quality model responses across all three core tasks.

### 3.4 API Server Exception Handling

In `server/app.py`:
- Input validation errors return structured HTTP 400 status codes:
  ```python
  if not request.code or not request.code.strip():
      raise HTTPException(status_code=400, detail="Code cannot be empty")
  ```
- Catch-all global error handling formats exceptions into structured JSON responses:
  ```python
  @app.exception_handler(Exception)
  async def global_exception_handler(request: Request, exc: Exception):
      logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
      return JSONResponse(
          status_code=500,
          content={
              "error": "Internal Server Error",
              "message": str(exc),
              "initial_score": 0.01,
              "final_score": 0.01,
              "recommendation": "Engine encountered a critical error. Please try again."
          }
      )
  ```

### 3.5 Isolated Subprocess Execution with Cleanup

When dynamically evaluating user code in `env.py:303-312` and `env.py:785-794`, temporary scripts are executed via `subprocess.run` with strict timeouts (`timeout=5.0`), and temporary files are unlinked inside `try...finally` or immediate `try...except` blocks:
```python
# From env.py: Temporary file execution pattern
with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
    f.write(generator_script)
    f_path = f.name

res = subprocess.run([sys.executable, f_path], capture_output=True, text=True, timeout=5.0)
try:
    os.unlink(f_path)
except Exception:
    pass
```

---

## 4. Logging & Telemetry

### 4.1 Server-Level Logging

In `server/app.py`, standard Python logging is configured with timestamps, logger names, and log levels:
```python
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AionEngine")
```
An ASGI HTTP middleware automatically intercepts non-healthcheck requests and logs incoming HTTP method and path:
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.url.path not in ["/health", "/ready"]:
        logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    return response
```
Requests within critical endpoints are tracked with short UUID request traces:
```python
req_id = str(uuid.uuid4())[:8]
logger.info(f"[{req_id}] Initiating full optimization sequence")
```

### 4.2 Step & Episode Telemetry

In `inference.py:543-553`, RL step transitions emit standardized, machine-parsable logging strings with `flush=True`:
```python
print(f"[STEP] step={step_idx} action={agent_action.action_type} reward={reward} done={str(done).lower()} error=null", flush=True)
print(f"[END] success={str(success >= 0.7).lower()} steps={step_idx} rewards={','.join(str(r) for r in total_rewards)}", flush=True)
```

---

## 5. Comments & Documentation

### 5.1 Docstring Conventions

Top-level modules and key methods feature clear, descriptive docstrings:
- Module headers use triple double-quoted docstrings outlining scope (`test_suite.py`, `train.py`, `train_rl.py`).
- Classes and methods document operational contracts and OpenEnv requirements:
```python
# From env.py
class CodeReviewEnv:
    """
    Code Reviewer RL Environment conforming to Gymnasium-like interfaces.
    Coordinates code modifications, safety sandboxing, differential testing,
    AST-based grading, and regression recovery.
    """
```
- Pydantic models leverage `Field(..., description="...")` tags to auto-generate comprehensive OpenAPI schemas (`models.py`).

### 5.2 Section Dividers & Inline Annotations

Major structural sections across backend scripts use stylized comment banners:
```python
# --- BASELINE TASKS DEFINITIONS ---
# --- MOCK CLIENT FOR OFFLINE TESTING ---
# --- CORE API ENDPOINTS ---
# --- STATIC FILE SERVING ---
```
Inline comments highlight algorithmic reasoning, time complexity warnings, and edge case considerations:
```python
# Very slow O(N^2) approach
# Standardize strings to avoid string content bypasses
# Main entry point guard bonus (0.09)
```

---

## 6. Function & Module Design

### 6.1 Gymnasium Interface Alignment

The core environment class `CodeReviewEnv` in `env.py` mirrors the standard Reinforcement Learning interface:
- `reset(task_id: str) -> Observation`: Re-initializes state, resets step counters, returns the initial observation.
- `step(action: Action) -> Tuple[Observation, float, bool, dict]`: Advances state, evaluates AST rewards, handles rollbacks, returns `(obs, reward, done, info)`.
- `state() -> dict`: Returns serialized snapshot of current task ID, code, step count, and cumulative score.

### 6.2 AST Inspection Conventions

AST inspections in `env.py` and `utils.py` follow canonical `ast.walk(tree)` traversal patterns combined with `isinstance` checks against specific AST node types:
- `ast.Import`, `ast.ImportFrom` for module and alias tracking.
- `ast.Call`, `ast.Attribute`, `ast.Name` for sink and function invocation detection.
- `ast.For`, `ast.While`, `ast.ListComp`, `ast.SetComp` for nested loop detection.
- `ast.JoinedStr` (f-strings) and `ast.BinOp` (`%` formatting) for SQL injection vulnerability scanning.

```python
# From env.py: Canonical AST inspection
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        func_name = getattr(node.func, 'attr', getattr(node.func, 'id', ''))
        if func_name == 'execute' and len(node.args) > 0:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.JoinedStr):
                sql_vulnerable = True
```

### 6.3 Separation of Concerns & Hotspots

- **`models.py`**: Clean, decoupled Pydantic data schemas without business logic.
- **`utils.py`**: Pure utility functions (`detect_language`, `normalize_indentation`, `deep_syntax_repair`) with minimal external dependencies.
- **`env.py`**: Dedicated evaluation and grading engine.
- **Hotspot Alert**: `inference.py` carries multiple responsibilities: LLM client setup, mock fallback logic, Gradio UI generation (`gr.Blocks`), and regex repair re-exports. Future refactoring should decouple the Gradio UI from headless inference logic.

---

## 7. Language-Specific Conventions Summary

### Python Summary
- **Formatting**: 4 spaces, PEP 8 compliance checked dynamically by the grader (`stmt.col_offset != node.col_offset + 4`).
- **Typing**: Type annotations on models (`models.py`) and environment transitions (`env.py`); loose typing in helper scripts (`utils.py`, `inference.py`).
- **Standard Idiom**: Mandatory inclusion of `if __name__ == '__main__':` for executable modules, incentivized by the grader with a `+0.09` reward bonus.

### JavaScript / React Summary
- **Configuration**: ESLint 9 flat config (`eslint.config.js`) enforcing React Hooks rules and flagging unused variables (`varsIgnorePattern: '^[A-Z_]'`).
- **Component Pattern**: Arrow function components (`StatBox`, `Toast`) and standard function declaration for `App()`.
- **CSS Architecture**: Global CSS files (`AionStyles.css`, `App.css`, `index.css`) utilizing CSS custom properties, backdrop blur filters, and radial gradient backgrounds for the Midnight Glass theme.
