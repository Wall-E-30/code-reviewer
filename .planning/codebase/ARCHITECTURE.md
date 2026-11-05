<!-- refreshed: 2026-11-04 -->
# Architecture

**Analysis Date:** 2026-11-04

## System Overview

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                       Client Presentation Tier                            │
├─────────────────────────────────────┬─────────────────────────────────────┤
│        React 19 SPA (Vite)          │      Gradio Web UI (Standalone)     │
│       `frontend/src/App.jsx`        │            `inference.py`           │
│  (Live Optimizer, Bento Dashboard,  │   (Interactive exploratory testing, │
│     Hackathon Benchmark Panel)      │       task evaluation runner)       │
└──────────────────┬──────────────────┴──────────────────┬──────────────────┘
                   │ HTTP REST (JSON)                    │ Direct In-Process
                   ▼                                     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    API Gateway & Orchestration Layer                      │
│                            `server/app.py`                                │
│       - FastAPI ASGI Service (`/optimize`, `/optimize_full`, `/step`)     │
│       - Session-Isolated Environment Router (`environments` registry)     │
│       - Unified Diff Computation & Static Asset Server (`/assets`)        │
└──────────────────┬─────────────────────────────────────┬──────────────────┘
                   │                                     │
                   ▼                                     ▼
┌─────────────────────────────────────┐ ┌───────────────────────────────────┐
│       Inference & Policy Layer      │ │      RL Environment & Sandbox     │
│           `inference.py`            │ │             `env.py`              │
├─────────────────────────────────────┤ ├───────────────────────────────────┤
│ • Local Autoregressive RL Model     │ │ • `CodeReviewEnv` (Gym-like API)  │
│   (Fine-tuned GPT-2 via PyTorch)    │ │ • AST Syntax & Correctness Grader │
│ • Remote Hugging Face Router API    │ │ • Differential Execution Sandbox  │
│   (OpenAI client: Qwen2.5-72B)      │ │ • Dynamic Linter Engine           │
│ • Offline Deterministic Mock AI     │ │ • Automated Backtracking Recovery │
│ • AST Robustness & Code Normalizer  │ │ • AST Security & RCE Barrier      │
└──────────────────┬──────────────────┘ └──────────────────┬────────────────┘
                   │                                       │
                   ▼                                       ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                   Domain Models & Shared Utilities                        │
│            `models.py`                              `utils.py`            │
│  (Pydantic schemas: Action,           (18-Language Syntax Detection,      │
│   Observation, Reward, Response)       Deep Syntax Repair, Indent Normal) │
└───────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **FastAPI REST Application** | Exposes HTTP endpoints (`/reset`, `/step`, `/optimize`, `/optimize_full`, `/run_benchmark`, `/state`, `/diff`), logs requests, serves production SPA assets | `server/app.py` |
| **Session Environment Registry** | Tracks and isolates per-user/agent `CodeReviewEnv` instances keyed by `session_id` | `server/app.py` |
| **Gymnasium RL Environment** | Coordinates code editing steps, tracks episode horizons, triggers regression backtracking, enforces security sandboxing | `env.py` |
| **AST Quality Grader** | Evaluates code AST for indentation, unused imports, nested loops $O(N^2)$, SQL injection, and insecure execution sinks | `env.py` |
| **Differential Execution Sandbox** | Synthesizes test arguments, executes user code in isolated subprocesses, verifies functional invariance | `env.py` |
| **Dynamic Linter Engine** | Generates real-time diagnostic reports for Python (AST-based) and 17 secondary languages (regex-based) | `env.py` |
| **Inference Orchestrator** | Dispatches optimization tasks to local GPT-2, remote Hugging Face endpoints, or deterministic mock fallbacks | `inference.py` |
| **Universal Robustness Layer** | Normalizes indentation, repairs unquoted print literals, adds missing `if __name__` guards | `inference.py` |
| **Gradio Interactive Dashboard** | Standalone web UI for manual code optimization and hackathon task benchmarking | `inference.py` |
| **Domain Models & Schemas** | Defines Pydantic validation contracts for `Action`, `Observation`, `Reward`, and `OptimizeResponse` | `models.py` |
| **Multi-Language Normalizer** | Auto-detects 18 programming languages and repairs common syntax and brace errors | `utils.py` |
| **SFT & Trajectory Collector** | Harvests optimal trajectory traces from `CodeReviewEnv` and generates behavioral cloning datasets | `train.py` |
| **Autoregressive RL Trainer** | Fine-tunes GPT-2 via Supervised Fine-Tuning (SFT) and REINFORCE / Actor-Critic with baselines | `train_rl.py` / `train_autoregressive_rl.py` |
| **Comprehensive Test Suite** | 18-point verification testing environment resets, AST grading, indentation fixes, and API pipelines | `test_suite.py` |
| **React Single Page App** | Provides the Midnight Glass Bento Grid user interface, Live Optimizer, and Benchmark trajectory viewer | `frontend/src/App.jsx` |
| **Frontend Design System** | Midnight Glass design tokens, glassmorphism CSS classes, pulse animations, and responsive layout | `frontend/src/AionStyles.css` |

## Pattern Overview

**Overall:** Reinforcement Learning Evaluation Loop wrapped in a Microservice & SPA Architecture.

**Key Characteristics:**
- **Gymnasium-like MDP Interface:** `CodeReviewEnv` exposes standard `reset(task_id)` and `step(action)` methods returning `(Observation, reward, done, info)` tuples conforming to OpenEnv requirements.
- **AST-Based Objective Grading:** Rather than relying on non-deterministic LLM grading, code quality is evaluated mathematically via Python's built-in `ast` module, awarding rewards between `0.01` and `0.99`.
- **Automated Regression Backtracking:** If a proposed edit introduces syntax errors or reduces the scalar reward, `CodeReviewEnv` automatically reverts the working buffer to `best_code` and logs a `[Regression Warning]`.
- **Eager Multi-Pass Chaining:** Optimization requests can execute a 3-stage pipeline (Style Cleanup ➔ Efficiency Boost ➔ Security Audit), verifying intermediate states and gracefully recovering if any single stage fails.
- **Universal Robustness Filter:** Pre-processing and post-processing interceptors clean markdown code fences, repair unquoted function calls, and re-indent blocks before AST parsing.

## Layers

**Presentation Layer:**
- Purpose: Render code editing, review feedback, metrics, and benchmark logs.
- Location: `frontend/src/` (and optional Gradio interface in `inference.py`).
- Contains: React components (`frontend/src/App.jsx`), styling (`frontend/src/AionStyles.css`, `frontend/src/index.css`), Vite configs (`frontend/vite.config.js`).
- Depends on: Backend HTTP REST endpoints.
- Used by: End users, hackathon evaluators, browser clients.

**API Transport & Gateway Layer:**
- Purpose: Handle incoming HTTP requests, session management, static asset delivery, and CORS routing.
- Location: `server/app.py`.
- Contains: FastAPI router, middleware, session lookup helper, request models.
- Depends on: `env.py`, `models.py`, `inference.py`.
- Used by: Frontend SPA, OpenEnv benchmark evaluation clients, external curl/API clients.

**Domain Models & Data Contracts Layer:**
- Purpose: Define strongly-typed schemas for agent actions, environment observations, and API payloads.
- Location: `models.py`.
- Contains: `Action`, `Observation`, `Reward`, `OptimizeResponse`, `ResetRequest`, `OptimizeRequest`.
- Depends on: `pydantic`.
- Used by: `server/app.py`, `env.py`, `inference.py`, `test_suite.py`.

**Inference & Intelligence Layer:**
- Purpose: Generate code refactorings using fine-tuned neural models, external LLMs, or deterministic heuristics.
- Location: `inference.py`.
- Contains: Local GPT-2 inference pipeline, OpenAI-compatible HF Router client, `MockOpenAI` fallback engine, `evaluate_and_optimize()`, `run_full_optimization()`.
- Depends on: `env.py`, `models.py`, `utils.py`, `torch`, `transformers`, `openai`.
- Used by: `server/app.py`, Gradio UI, automated test runners.

**Environment & Quality Evaluation Layer:**
- Purpose: Host the RL MDP sandbox, parse AST trees, detect vulnerabilities, run differential unit tests, and compute rewards.
- Location: `env.py`.
- Contains: `CodeReviewEnv`, task benchmarks (`TASKS`), AST checkers for imports/loops/SQL injection, subprocess execution sandbox.
- Depends on: `models.py`, `ast`, `subprocess`, `tempfile`.
- Used by: `server/app.py`, `inference.py`, `train.py`, `train_rl.py`.

**Utilities & Code Repair Layer:**
- Purpose: Multi-language syntax identification, deep syntax repair, and indentation normalization.
- Location: `utils.py`.
- Contains: `detect_language()`, `fix_syntax_errors()`, `deep_syntax_repair()`, `normalize_indentation()`.
- Depends on: `re`, `ast`.
- Used by: `inference.py`, `env.py`, `test_suite.py`.

**Policy Training Layer:**
- Purpose: Generate trajectories and fine-tune language models with behavioral cloning and policy gradient RL.
- Location: `train.py`, `train_rl.py`, `train_autoregressive_rl.py`.
- Contains: SFT dataset generators, REINFORCE training loop, Actor-Critic `ValueNetwork`.
- Depends on: `env.py`, `models.py`, `torch`, `transformers`.
- Used by: Offline model training jobs.

## Data Flow

### Primary Request Path (Live Code Optimization)

1. **User Submission**: The developer submits code and an optimization goal (`style-cleanup`, `efficiency-boost`, or `security-audit`) from `frontend/src/App.jsx:108` via `fetch('/optimize')`.
2. **API Ingestion**: `server/app.py:238` receives `OptimizeRequest`, generates a unique `request_id`, and dispatches to `evaluate_and_optimize()`.
3. **Language Detection & Syntax Pre-Fix**: `inference.py:670` calls `detect_language()` and `fix_syntax_errors()` in `utils.py`.
4. **Environment Initialization & Differential Test Generation**: `inference.py:674` instantiates `CodeReviewEnv()` and calls `load_custom_code()`. In `env.py:223`, safe code is parsed and a temporary subprocess executes a generator script to create test cases with expected return values and stdout.
5. **Initial Grading**: `env._calculate_reward()` evaluates initial AST metrics and stores `initial_score` (`env.py:798`).
6. **Agent Generation**:
   - If local GPT-2 model is present, prompt `Task: {task}\nCode:\n{code}\nOptimized:\n` is tokenized and generated via PyTorch (`inference.py:680`).
   - If remote API is active, formatted prompt is sent to `Qwen/Qwen2.5-72B-Instruct` via Hugging Face Router (`inference.py:736`).
   - If offline, `MockOpenAI` applies deterministic AST transformations (`inference.py:144`).
7. **Robust Post-Processing**: The generated code passes through `robust_repair_code()` in `inference.py:36` to repair indentation and ensure `if __name__ == '__main__':` guards exist.
8. **Evaluation Step & Regression Guard**: `env.step(agent_action)` in `env.py:103` validates Python AST compilation. If reward drops, it reverts to `best_code`.
9. **AST Metric Estimation**: `estimate_ast_improvements()` in `inference.py:556` compares AST node counts, loop structures, and calculates estimated speedup percentage and memory reduction.
10. **Diff Generation & Response**: `server/app.py:282` runs `difflib.Differ` to produce structured line-by-line diff metadata (`added`, `removed`, `unchanged`), returning `OptimizeResponse` to the frontend.

### Secondary Flow 1 (Multi-Pass Chained Optimization)

1. User clicks **"Full Review (All Passes)"** in `frontend/src/App.jsx:233`.
2. Frontend sends POST request to `/optimize_full` (`server/app.py:215`).
3. `run_full_optimization()` in `inference.py:779` chains passes:
   - Pass 1: `style-cleanup` removes unused imports and normalizes indentation.
   - Pass 2: `efficiency-boost` refactors nested loops into set/dict lookups.
   - Pass 3: `security-audit` parameterizes SQL queries and replaces dangerous sinks.
4. Each step verifies that intermediate outputs do not start with `"Error:"`, preserving the latest valid code state across failures.
5. Final optimized code, combined score, and unified diff are returned.

### Secondary Flow 2 (RL Benchmark Trajectory Evaluation)

1. User selects benchmark task and clicks **"Run Benchmark Sequence"** in `frontend/src/App.jsx:88`.
2. Frontend sends POST request to `/run_benchmark` (`server/app.py:110`).
3. Server resets the environment using task ID (`style-cleanup`, `efficiency-boost`, or `security-audit`).
4. Step loop runs up to 5 iterations:
   - Model generates proposed code for current task.
   - `env.step()` computes step reward and updates linter warnings.
   - Step record (`step`, `code`, `reward`, `linter`, `action`) is appended.
   - Loop exits early if `done` is true or `reward >= 0.98`.
5. Benchmark payload containing full trajectory history and final code is returned to the UI.

### Secondary Flow 3 (OpenEnv Agent Step Loop)

1. Automated benchmark agent calls POST `/reset` with `ResetRequest` (`server/app.py:83`).
2. `CodeReviewEnv.reset()` resets task code buffer and returns initial `Observation`.
3. Agent repeatedly calls POST `/step` with `Action(action_type="apply_fix", content=..., session_id=...)` (`server/app.py:92`).
4. Server retrieves session-isolated environment, executes step, and returns structured `Observation` and `Reward` models.

**State Management:**
- Stateless client: React UI stores local form state and rendered output.
- Server session cache: `server/app.py:52` stores `environments = {}` dictionary keyed by client `session_id` (defaults to `"default"`).
- Environment state: `CodeReviewEnv` maintains `self.code`, `self.best_code`, `self.original_code`, `self.best_reward`, and `self.step_count`.

## Key Abstractions

**`CodeReviewEnv` (Gymnasium Environment):**
- Purpose: Represents the Markov Decision Process (MDP) for code editing.
- File: `env.py:62`
- Pattern: Adapter / Environment pattern implementing `reset()` and `step()`.

**`Action` & `Observation` & `Reward`:**
- Purpose: Canonical schema contracts for agent-environment interaction.
- File: `models.py:4-30`
- Pattern: Data Transfer Object (DTO) pattern using Pydantic `BaseModel`.

**AST Visitor & Inspector:**
- Purpose: Traverses Python AST using `ast.walk` to inspect node types (`ast.JoinedStr`, `ast.For`, `ast.Call`, `ast.ImportFrom`, `ast.Compare`).
- File: `env.py:182`, `env.py:451-634`, `env.py:808-1033`
- Pattern: Visitor pattern for static analysis.

**Universal Robustness & Repair Layer:**
- Purpose: Intercepts raw LLM code outputs, cleans markdown wrappers, fixes missing quotes in builtins, and formats indentation before parsing.
- File: `inference.py:15-86`, `utils.py:373-455`
- Pattern: Chain of Responsibility / Filter pipeline.

## Entry Points

**API Server Entry Point:**
- Location: `server/app.py:341` (`main()`) or command `uvicorn server.app:app --host 0.0.0.0 --port 7860`
- Triggers: Container startup, Render deploy, local backend startup.
- Responsibilities: Initializes FastAPI, mounts static SPA build, registers routes, listens on `$PORT`.

**Frontend SPA Entry Point:**
- Location: `frontend/src/main.jsx:1`
- Triggers: Browser loading `index.html`.
- Responsibilities: Mounts root React DOM tree and renders `<App />`.

**Gradio Interactive Entry Point:**
- Location: `inference.py:1140` (`if __name__ == "__main__":`)
- Triggers: Direct CLI execution `python inference.py`.
- Responsibilities: Runs automated baseline evaluations and launches Gradio server on port 7860 (unless `AION_NO_UI=1`).

**RL Training Pipeline Entry Points:**
- Location: `train.py:99`, `train_rl.py:249`, `train_autoregressive_rl.py:58`
- Triggers: Direct CLI commands `python train.py --collect --sft` or `python train_rl.py`.
- Responsibilities: Executes offline trajectory gathering and SFT / REINFORCE training.

**Verification Test Suite Entry Point:**
- Location: `test_suite.py:600`
- Triggers: Direct execution `python test_suite.py` or `pytest test_suite.py`.
- Responsibilities: Executes 18 automated unit and integration tests across all modules.

## Architectural Constraints

- **Threading & Execution Model:** FastAPI runs on an asynchronous event loop (`asyncio`), but AST parsing and synchronous helper routines run on the main thread. Differential testing launches worker subprocesses with 5.0-second timeouts.
- **Global State & Session Concurrency:** Environment instances are stored in memory in `server/app.py:environments`. Sessions are routed via `session_id`. If multiple clients omit `session_id`, they share the `"default"` environment buffer.
- **In-Memory Cache Lifecycle:** Environments are stored in memory and are not persisted to a database; restarting the server clears all active environments.
- **Security Isolation Boundaries:** Arbitrary code execution during differential testing is restricted to safe Python code inspected by `_is_code_safe_to_execute()` in `env.py:163`. Insecure imports (`subprocess`, `socket`, `pty`, `requests`) and magic attributes (`__globals__`, `__subclasses__`) are blocked.
- **Model Hardware Fallback:** If PyTorch or local GPT-2 weights are unavailable, the system smoothly falls back to remote HF Router API or offline deterministic rules without crashing.

## Anti-Patterns

### Unkeyed Concurrent Session Usage
**What happens:** Multiple agent threads or browser tabs making requests without specifying `session_id` share the `"default"` environment instance.
**Why it's wrong:** Concurrent actions overwrite `self.code` and step counters, resulting in race conditions and corrupted benchmarks.
**Do this instead:** Always pass a unique `session_id` (e.g. UUID) in `ResetRequest` and `Action` objects (`models.py:12`).

### Intermediate Error String Propagation
**What happens:** When an optimization pass fails and returns an error message (e.g. `"Error: API Timeout"`), passing that string to subsequent passes treats error text as Python code.
**Why it's wrong:** Syntax parsing crashes and corrupts the code buffer.
**Do this instead:** Validate `current_code` before chaining passes as implemented in `inference.py:788-806`, preserving the previous valid code state.

### Direct Subprocess Execution Without Sandbox
**What happens:** Running user-submitted code in `exec()` or `subprocess.run()` without inspecting the AST.
**Why it's wrong:** Malicious payloads can escape or access filesystem and network resources.
**Do this instead:** Enforce `_is_code_safe_to_execute()` check prior to running test generators as in `env.py:222`.

## Error Handling

**Strategy:** Multi-tier defense with automatic fallback and state recovery.

**Patterns:**
- **AST Parse Exception Catching:** All AST operations (`ast.parse`) are wrapped in `try/except SyntaxError` blocks returning structured diagnostics (`env.py:123`, `inference.py:201`).
- **Regression Recovery (Backtracking):** If a modification breaks syntax or reduces reward score, `CodeReviewEnv.step()` rolls back `self.code = self.best_code` (`env.py:133`, `env.py:144`).
- **Offline Mock Fallback:** When Hugging Face API keys are absent or network requests fail, `inference.py:140` seamlessly engages `MockOpenAI` to provide local rule-based optimizations.
- **Global FastAPI Exception Handler:** `server/app.py:327` captures unhandled server exceptions, logs stack traces, and returns HTTP 500 JSON responses.

## Cross-Cutting Concerns

**Logging:** Structured console logging via Python standard `logging` configured in `server/app.py:15` (`AionEngine` logger).
**Validation:** Pydantic v2 schemas (`models.py`) validate all incoming JSON requests and enforce scalar reward range constraints (`0.0 < value < 1.0`).
**Security & Sandboxing:** AST AST inspection (`env.py:163`) filters dangerous modules (`subprocess`, `socket`, `requests`, `builtins`) and dangerous functions (`eval`, `exec`, `open`) prior to differential testing.
**CORS & Networking:** Permissive CORS middleware (`server/app.py:35`) allows cross-origin requests from development servers (`http://localhost:5173`) and web clients.

---

*Architecture analysis: 2026-11-04*
