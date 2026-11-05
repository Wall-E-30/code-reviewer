# Testing Patterns

**Analysis Date:** 2026-11-04

## Overview & Test Philosophy

The **Aion Code Reviewer** system employs a custom, deterministic verification philosophy centered on Abstract Syntax Tree (AST) validation, reinforcement learning reward boundary checks, syntax repair safety, and sandboxed dynamic execution. 

Testing in this repository is currently centralized into a single primary test file: `test_suite.py`. This standalone script contains 18 comprehensive verification tests that validate the grading environment (`env.py`), code repair utilities (`utils.py`, `inference.py`), and offline optimization pipelines.

---

## 1. Test Framework & Runners

### 1.1 Custom Standalone Runner (`test_suite.py`)

The codebase uses a native, standalone Python test harness rather than relying strictly on external test runners like `pytest` or `unittest.main()`.
- **Entrypoint**: `test_suite.py:569-627` defines `main()`, which registers all 18 test functions, executes them in a sequential loop, and tallies passes and failures.
- **Exit Code**: Returns `0` on 100% success or `1` if any test fails, enabling integration into automated build scripts or CI pipelines.
- **Execution**: Can be triggered directly via:
  ```bash
  python test_suite.py
  ```
  Or via `pytest` (compatible due to standard `test_*` function naming):
  ```bash
  pytest test_suite.py -v
  ```

#### Runner Implementation from Code:
```python
# From test_suite.py:599-623: Custom execution loop
for test in tests:
    try:
        test()
        print("PASS: %s" % test.__name__)
        passed += 1
    except AssertionError as e:
        print("FAIL: %s: %s" % (test.__name__, str(e)))
        failed += 1
    except Exception as e:
        print("ERROR: %s: %s" % (test.__name__, str(e)))
        import traceback
        traceback.print_exc()
        failed += 1

print("="*60)
print("Results: %d passed, %d failed" % (passed, failed))
print("="*60)
return 0 if failed == 0 else 1
```

### 1.2 Frontend Testing Infrastructure

The frontend Single-Page Application (`frontend/package.json`) currently has **no automated testing framework** configured:
- No test script defined under `scripts` (only `"dev"`, `"build"`, `"lint"`, `"preview"`).
- No testing libraries installed (e.g., `vitest`, `jest`, `@testing-library/react`).
- Quality assurance for the UI currently relies exclusively on static analysis via ESLint (`frontend/eslint.config.js`).

---

## 2. Test Suite Organization & Inventory

`test_suite.py` organizes 18 distinct tests across six functional categories:

| Category | Test Function Name | Tested Area | File References |
| :--- | :--- | :--- | :--- |
| **Code Normalization & Repair** | `test_deep_syntax_repair` | Unquoted string prints (`print(Hello World)`) | `utils.py:373`, `inference.py:12` |
| | `test_normalize_indentation` | Nested defs, inner imports, top-level lines | `utils.py:416` |
| | `test_robust_repair_code` | Empty input fallback, `if __name__` attachment | `inference.py:36` |
| | `test_clean_json_string` | Embedded JSON extraction & markdown unwrapping | `inference.py:15` |
| | `test_robust_parser_and_extra_languages` | Unescaped quotes, text fallbacks, multi-language detection | `inference.py:401`, `utils.py:11` |
| **Data Schema Validation** | `test_env_observation_model` | Pydantic fields, types, and schema compliance | `models.py:14`, `env.py:639` |
| | `test_env_reward_bounds` | Reward boundaries `[0.01, 0.99]`, syntax error floor | `models.py:24`, `env.py:1033` |
| **Task Grading Logic** | `test_env_style_cleanup` | Unused import removal and 4-space indentation | `env.py:812` |
| | `test_env_efficiency_boost` | Nested loop refactoring to O(N) `set()` | `env.py:839` |
| | `test_env_efficiency_boost_comprehensions` | Set comprehensions, annotated assigns, loop penalties | `env.py:842-863` |
| | `test_env_security_audit` | SQL parameterization vs string formatting | `env.py:905-1019` |
| | `test_security_audit_direct_and_alias_detection` | `from os import system`, aliases (`subprocess as sub`), `shell=True` | `env.py:924-1008` |
| | `test_new_ast_linter_checks` | Bare excepts, mutable defaults, nested ifs, deprecated modules (`md5`, `pickle`) | `env.py:478-550` |
| **Safety & Security Sandboxing** | `test_load_custom_code_rce_blocking` | Blocking execution of `os.system`, `eval()`, `__subclasses__` | `env.py:163-211` |
| **Differential Execution Testing** | `test_custom_code_differential_testing` | Dynamic test case validation on uploaded algorithms | `env.py:222-320`, `env.py:759` |
| **Inference & Policy Optimization** | `test_evaluate_and_optimize` | Single-task step optimization using `MockOpenAI` | `inference.py:700` |
| | `test_run_full_optimization` | Multi-pass pipeline chaining & error recovery | `inference.py:779` |
| **Environment Control** | `test_env_backtracking_and_string_bypass` | `backtrack=False` persistence & JS comment string bypass prevention | `env.py:68, 334` |

---

## 3. Test Structure & Assertion Patterns

### 3.1 Standard Test Structure

Tests follow a clean AAA (Arrange, Act, Assert) structure:
1. **Arrange**: Initialize the environment or define target code snippets.
2. **Act**: Invoke the environment method (`reset`, `step`, `load_custom_code`) or parser utility.
3. **Assert**: Verify expected values using plain Python `assert` with clear failure messages.
4. **Log**: Print a success message (`PASS: <test_name>`) upon completion.

#### Concrete Example: AST Security Alias Verification
```python
# From test_suite.py:217-254
def test_security_audit_direct_and_alias_detection():
    """Test that direct imports and aliases for security audit sinks are correctly detected as vulnerable."""
    env = CodeReviewEnv()
    env.reset(task_id='security-audit')
    
    # 1. Test "from os import system" vulnerable code
    vulnerable_os_direct = '''from os import system
def run_command(cmd):
    system(cmd)
'''
    env.load_custom_code(vulnerable_os_direct, 'security-audit')
    assert env._calculate_reward() == 0.10, "Failed to detect vulnerable direct import 'from os import system'"

    # 2. Test "import os as my_os" vulnerable code
    vulnerable_os_alias = '''import os as my_os
def run_command(cmd):
    my_os.system(cmd)
'''
    env.load_custom_code(vulnerable_os_alias, 'security-audit')
    assert env._calculate_reward() == 0.10, "Failed to detect vulnerable os alias 'my_os.system'"
```

### 3.2 Regression & Boundary Assertions

Boundary tests verify that numeric rewards conform to OpenEnv's strict range restrictions:
```python
# From test_suite.py:276-299
def test_env_reward_bounds():
    """Test that rewards are always in (0, 1) range."""
    env = CodeReviewEnv()
    for task_id in ['style-cleanup', 'efficiency-boost', 'security-audit']:
        env.reset(task_id=task_id)
        # Test with valid code
        for code, task in [("def foo(): pass", task_id), ("def bar(): return 1", task_id)]:
            env.load_custom_code(code, task)
            reward = env._calculate_reward()
            assert 0.01 <= reward <= 0.99, f"Reward {reward} out of bounds for task {task}"
        
        # Test with invalid syntax
        env.load_custom_code("def invalid(", task_id)
        reward = env._calculate_reward()
        assert reward == 0.01, f"Invalid syntax should score 0.01, got {reward}"
```

---

## 4. Mocking & Isolation Strategy

### 4.1 In-Memory LLM Mock Client (`MockOpenAI`)

To execute integration tests without network access or valid API credentials (`HF_TOKEN`), `inference.py:126-350` implements an in-memory client conforming to the OpenAI SDK interface:
- **`MockMessage` & `MockChoice`**: Mirrors OpenAI completion choice structures.
- **`MockResponse`**: Wraps serialized JSON actions `{"action_type": "apply_fix", "content": "..."}`.
- **`MockOpenAI.create()`**: Parses the incoming prompt (`LANGUAGE: ...`, `TASK: ...`, `USER CODE: ...`), determines the optimization goal, and returns a rule-optimized code solution.

```python
# From inference.py:139-146
class MockOpenAI:
    def __init__(self):
        self.chat = self
        self.completions = self
    
    def create(self, **kwargs):
        messages = kwargs.get("messages", [{}])
        task_prompt = str(messages[-1].get("content", ""))
        # ... extracts code and returns MockResponse ...
```

In `test_suite.py:302-326`, `test_evaluate_and_optimize` utilizes this mock client to test offline end-to-end optimization:
```python
# From test_suite.py:317-324
from inference import MockOpenAI
mock_client = MockOpenAI()
res = mock_client.create(messages=[{"content": "LANGUAGE: python\nTASK: style-cleanup\nUSER CODE:\nimport sys, math\nx = math.sqrt(4)\nprint(x)\nReturn the COMPLETE"}])
res_data = json.loads(res.choices[0].message.content)
fixed_res = res_data["content"]
assert "import math" in fixed_res
assert "import sys" not in fixed_res
```

### 4.2 SQLite Database Mocking

In `env.py:726-750`, functional correctness testing for the `security-audit` task intercepts `sqlite3.connect` using `unittest.mock.patch` to execute queries against a temporary `:memory:` database:
```python
# From env.py:728-748
import sqlite3
import unittest.mock as mock

mock_conn = sqlite3.connect(":memory:")
mock_conn.execute("CREATE TABLE users (id TEXT, name TEXT)")
mock_conn.execute("INSERT INTO users VALUES ('admin', 'Administrator')")
mock_conn.commit()

with mock.patch("sqlite3.connect", return_value=mock_conn):
    exec(code_str, globals_dict)
    res = globals_dict['get_user_data']("admin")
```

### 4.3 Subprocess Isolation & Sandboxing

Code execution safety is tested vigorously in `test_load_custom_code_rce_blocking` (`test_suite.py:470-516`):
- Dangerous constructs (`import os; os.system(...)`, `eval(...)`, `[].__class__.__base__.__subclasses__()`, `import requests`, `getattr(x, '__builtins__')`) must be caught by static AST inspection (`_is_code_safe_to_execute`).
- Verified behavior: Custom code containing these constructs must have `len(env.test_cases) == 0`, emit a `"Security Warning"` in the linter report, and avoid executing untrusted code in the subprocess runner.

---

## 5. Differential Testing Mechanism

One of the most advanced test features implemented in `env.py` and validated in `test_suite.py:428-469` is **Dynamic Differential Testing**:
1. When custom Python code is loaded via `env.load_custom_code(code, task_type)`:
   - The code is inspected via AST for top-level functions (`FunctionDef`).
   - Standard scenario inputs are automatically generated (e.g., single arguments `[1, 2, 3]`, pair arguments `([1, 2], [2, 3])`).
   - The original function is executed inside a temporary subprocess with `redirect_stdout` to record expected return values and outputs.
2. When the agent steps with an action (`apply_fix`):
   - The environment runs the proposed fix against the captured test cases inside a subprocess.
   - If functional behavior changes or breaks, `_verify_correctness()` returns `False` and the score is clamped to `0.01`.

```python
# From test_suite.py:445-465: Testing differential detection of regressions
hacked_code = (
    "def sum_pairs(lst):\n"
    "    return []\n"
)
action_hack = Action(action_type="apply_fix", content=hacked_code)
obs, reward, done, info = env.step(action_hack)
assert reward == 0.01  # Functional regression penalized

correct_code = (
    "def sum_pairs(lst):\n"
    "    res = []\n"
    "    for x in lst:\n"
    "        for y in lst:\n"
    "            res.append(x + y)\n"
    "    return res\n"
)
action_correct = Action(action_type="apply_fix", content=correct_code)
obs2, reward2, done2, info2 = env.step(action_correct)
assert reward2 > 0.01  # Correct behavior rewarded
```

---

## 6. Fixtures & Test Data

The codebase utilizes three sources of test fixtures and benchmark data:
1. **In-Line String Fixtures**: Code samples embedded directly into test functions in `test_suite.py` (e.g., SQL queries, nested loops, style violations).
2. **Task Baseline Definitions (`TASKS` dict in `env.py:15-60`)**:
   - `style-cleanup`: Unused `import sys` and indentation mismatch in `style.py`.
   - `efficiency-boost`: O(N^2) nested loop in `logic.py`.
   - `security-audit`: SQL string formatting in `security.py`.
3. **Reference Data Files (`data/`)**:
   - `data/logic.py`: 8-line sample containing O(N^2) duplicate search.
   - `data/security.py`: 9-line sample with vulnerable `cursor.execute(f"SELECT...")`.
   - `data/style.py`: 6-line sample with style errors.
   - `data/sft_trajectories.json`: 3 pre-collected optimal trajectory episodes for behavioral cloning.

---

## 7. How to Run Tests

### 7.1 Running the Full Python Test Suite

To run all 18 unit and integration tests:
```powershell
python test_suite.py
```

Expected output format:
```text
============================================================
Running Aion Code Reviewer Test Suite
============================================================
PASS: test_load_custom_code_rce_blocking
PASS: test_custom_code_differential_testing
PASS: test_deep_syntax_repair
PASS: test_normalize_indentation
PASS: test_robust_repair_code
PASS: test_clean_json_string
PASS: test_env_observation_model
PASS: test_env_reward_bounds
PASS: test_env_style_cleanup
PASS: test_env_efficiency_boost
PASS: test_env_efficiency_boost_comprehensions
PASS: test_env_security_audit
PASS: test_security_audit_direct_and_alias_detection
PASS: test_evaluate_and_optimize
PASS: test_run_full_optimization
PASS: test_env_backtracking_and_string_bypass
PASS: test_robust_parser_and_extra_languages
PASS: test_new_ast_linter_checks
============================================================
Results: 18 passed, 0 failed
============================================================
```

### 7.2 Running via Pytest

Pytest can discover and run `test_suite.py`:
```powershell
pytest test_suite.py -v
```

### 7.3 Known Execution Hurdles & Solutions

1. **Top-Level `gradio` Dependency Barrier**:
   - **Problem**: `test_suite.py` imports functions from `inference.py`, which unconditionally imports `gradio as gr` at line 7. In minimal virtual environments where `gradio` is omitted, `test_suite.py` fails on import.
   - **Solution**: Install all packages in `requirements.txt` (`pip install -r requirements.txt`) before running tests, or run within an environment where Gradio is installed.
2. **Missing Frontend Test Runner**:
   - Running `npm test` inside `frontend/` fails because no test script is defined. Unit tests for React components (`App.jsx`, `StatBox`, `Toast`) require installing Vitest and React Testing Library.

---

## 8. Test Coverage Gaps & Quality Recommendations

While `test_suite.py` thoroughly verifies the AST grading logic and code repairs in `env.py` and `utils.py`, several critical coverage gaps remain:

1. **Zero Automated API Endpoint Tests**:
   - `server/app.py` has no automated integration tests using FastAPI's `TestClient` (from `httpx` / `starlette.testclient`).
   - The `/step`, `/reset`, `/optimize`, `/optimize_full`, and `/run_benchmark` endpoints are not verified in continuous integration.
   - **Recommendation**: Create `tests/test_api.py` using `pytest` and `fastapi.testclient.TestClient`.
2. **Zero Automated Frontend Tests**:
   - UI interaction flows (code pasting, tab switching, toast display, benchmark triggers) are only tested manually.
   - **Recommendation**: Add `vitest` and `@testing-library/react` to `frontend/package.json` with component tests in `frontend/src/__tests__/App.test.jsx`.
3. **Training Script Verification**:
   - Training scripts (`train.py`, `train_rl.py`, `train_autoregressive_rl.py`) have no smoke tests to verify tensor shapes or forward/backward pass execution without downloading full models.
   - **Recommendation**: Add a fast smoke test (`test_train_dry_run()`) verifying one training iteration with a dummy 2-layer model.
