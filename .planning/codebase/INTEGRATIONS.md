# External Integrations

**Analysis Date:** 2026-11-04

## Overview

Aion operates primarily as a self-contained code evaluation and optimization engine designed to interface with external LLM providers via OpenAI-compatible API routers, while supporting autonomous execution through built-in mock engines and local neural policies. Its external integrations span AI inference gateways, container platforms, cloud PaaS deployment descriptors, and task-definition standards (OpenEnv).

---

## External APIs & AI Model Providers

### Hugging Face Router API (OpenAI Client Compatible)
- **Integration Layer**: The application uses the standard `openai.OpenAI` SDK (`inference.py:8, 439`) to communicate with Hugging Face's serverless router.
- **Endpoint**:
  - `API_BASE_URL`: Defaults to `https://router.huggingface.co/v1` (configured in `inference.py:121`, `Dockerfile:24`, and `render.yaml:13`).
- **Target Model**:
  - `MODEL_NAME`: Defaults to `Qwen/Qwen2.5-72B-Instruct` (defined in `inference.py:122`, `docker-compose.yml:11`, `Dockerfile:25`, `render.yaml:15`).
- **Authentication**:
  - Authenticates via Bearer token using `HF_TOKEN` environment variable.
- **Failover / Mock AI Fallback**:
  - If `HF_TOKEN` is absent, set to `None`, or contains the placeholder string `"dummy_key_for_server_boot"`, the application logs a warning (`"--- WARNING: HF_TOKEN missing or invalid. Using Mock AI for demonstration. ---"`) and instantiates `MockOpenAI` (`inference.py:435-437`).
  - `MockOpenAI` (`inference.py:126-260`) performs AST-based and regex-based code transformations locally, ensuring 100% test coverage and functional demonstration capability in zero-network or sandboxed environments without requiring cloud API credentials.

### Local Autoregressive RL Model Integration
- **Checkpoint Path**: `models/rl_model` (checked in `inference.py:89-105`) and `models/autoregressive_rl_model` (trained in `train_autoregressive_rl.py:161-167`).
- **Architecture**: Hugging Face Transformers `GPT2LMHeadModel` and `GPT2Tokenizer`.
- **Behavior**:
  - If weights are detected in the `models/` directory, `inference.py` loads the model onto CPU/device and sets `HAS_RL_MODEL = True`.
  - When active, the `/run_benchmark` endpoint uses this model to generate iterative code edits directly; if absent, it gracefully falls back to deterministic rule-based repair functions (`server/app.py:137-193`).

---

## Databases & Data Storage

### In-Memory State & Session Management
- **Environment Isolation Cache**:
  - In `server/app.py:52-58`, the engine maintains an in-memory dictionary `environments = {}` mapping client session IDs to individual `CodeReviewEnv` instances.
  - Enables concurrent multi-session optimization and benchmark evaluations without shared state pollution.
  - Note: In-memory state is non-persistent across process restarts or multi-instance scaling.

### Embedded SQLite (`sqlite3`)
- **Usage**:
  - Used in `env.py:48-56` (baseline task definition for `security-audit`), `data/security.py`, and `train.py:39-47`.
  - Represents a local database (`users.db`) queried by evaluated code snippets to detect and audit SQL injection vulnerabilities (e.g. string concatenation or f-string interpolation vs. parameterized queries with `?`).
  - No external database engines (PostgreSQL, MySQL, etc.) are connected.

### File System Storage
- **Static Asset Distribution**: `frontend/dist/` contains production bundles served by FastAPI's `StaticFiles` mount at `/assets` (`server/app.py:305-325`).
- **Benchmark Trajectories**:
  - SFT behavioral cloning training datasets are written to `data/sft_trajectories.json` by `train.py:74-77`.
  - Benchmark task template definitions reside in `data/style.py`, `data/logic.py`, and `data/security.py`.
- **Model Checkpoints**: Checkpoints and weights are stored in `models/` (e.g., `models/autoregressive_rl_model.pt` and `models/autoregressive_critic.pt`), which are excluded from version control via `.gitignore`.

---

## Authentication, Authorization & Security

### External API Authentication
- **Token Management**: The Hugging Face API token is supplied exclusively through the `HF_TOKEN` environment variable.
- **Protection**:
  - The repository's `.gitignore` explicitly prevents `.env` and credential files from being tracked.
  - `render.yaml` sets `sync: false` for `HF_TOKEN` to ensure secrets are never stored in plain text in repository manifests.

### Cross-Origin Resource Sharing (CORS)
- **Configuration**: `server/app.py:34-41` configures FastAPI `CORSMiddleware`:
  - `allow_origins=["*"]`
  - `allow_credentials=True`
  - `allow_methods=["*"]`
  - `allow_headers=["*"]`
- Allows client web applications (such as a local Vite dev server on port `5173` or external frontend hosts) to invoke engine endpoints seamlessly.

### Execution Sandboxing & AST Security Gates
- When evaluating and benchmarking submitted code in `env.py:165-219` (`_is_code_safe_to_execute`), the environment runs deterministic AST validation:
  - **Module Blacklist**: Blocks execution if imports of dangerous modules are detected: `subprocess`, `socket`, `pty`, `ctypes`, `importlib`, `builtins`, `requests`, `urllib`, `http`, `ftplib`, `telnetlib`.
  - **Function & Magic Attribute Blacklist**: Blocks dangerous execution primitives (`eval`, `exec`, `open`, `compile`, `getattr`, `setattr`, `delattr`) and introspection attributes (`__subclasses__`, `__globals__`, `__code__`, `__builtins__`).
  - **Isolated Execution**: When safe, dynamic test generators run inside isolated sub-processes using `subprocess.run([sys.executable, f_path], timeout=5.0)` and immediately clean up temporary files (`env.py:307, 789`).

---

## Hosting, Platforms & CI/CD

### Hugging Face Spaces
- Configured via metadata headers in `README.md:1-8`:
  - `sdk: docker`
  - `app_port: 7860`
  - `colorFrom: indigo`
  - `colorTo: blue`
- Public Space URL: `https://huggingface.co/spaces/Wall-E-30/aion-code-reviewer`

### Docker & Docker Compose
- **Container Build** (`Dockerfile`):
  - Multi-stage build compiling React 19 frontend into static assets and packaging FastAPI with Python 3.11.
  - Exposes port `7860`.
- **Container Orchestration** (`docker-compose.yml`):
  - Service: `aion-engine`
  - Ports: `7860:7860`
  - Environment pass-through for `HF_TOKEN` and `MODEL_NAME`.

### Render Cloud Platform
- **Service Manifest** (`render.yaml`):
  - Web service name: `aion-code-reviewer-api`
  - Runtime: Python (version 3.11)
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn server.app:app --host 0.0.0.0 --port $PORT`
  - Health check path: `/health`

### Vercel Deployment
- **Configuration** (`frontend/vercel.json`):
  - Framework: `vite`
  - Build command: `npm run build`
  - Output directory: `dist`
  - SPA URL rewrites: `/(.*)` -> `/index.html`

### OpenEnv Task Specification
- **Specification File** (`openenv.yaml`):
  - Complies with OpenEnv v1.0.0 manifest for evaluating code review and bug-fixing agents.
  - Declares three canonical benchmark task categories:
    1. `style-cleanup` (Difficulty: easy)
    2. `efficiency-boost` (Difficulty: medium)
    3. `security-audit` (Difficulty: hard)

---

## Network Protocols & Service Interfaces

### REST HTTP Endpoints (`server/app.py`)
All communication between frontend, external agents, and the backend occurs over HTTP/JSON:

| Endpoint | Method | Request Payload | Response Schema | Description |
|---|---|---|---|---|
| `/health` | `GET` | None | `{"status": "online", ...}` | Liveness check for container orchestrators |
| `/ready` | `GET` | None | `{"status": "ready"}` | Readiness check |
| `/reset` | `POST` | `ResetRequest` (`task_id`, `session_id`) | `Observation` | Initializes task state and returns baseline AST observation |
| `/step` | `POST` | `Action` (`action_type`, `content`, ...) | Step dict (`observation`, `reward`, `done`, `info`) | Executes code edit action and computes AST reward |
| `/optimize` | `POST` | `OptimizeRequest` (`code`, `task_type`, `language`) | `OptimizeResponse` | Performs single targeted optimization pass |
| `/optimize_full` | `POST` | `OptimizeRequest` (`code`, ...) | `OptimizeResponse` | Chains style -> efficiency -> security optimization passes |
| `/diff` | `POST` | `DiffRequest` (`original`, `modified`) | `{"diff": [...]}` | Generates structured diff data for UI rendering |
| `/state` | `GET` | None | State dict | Returns current task state and score |
| `/run_benchmark` | `POST` | `ResetRequest` (`task_id`, `session_id`) | Trajectory benchmark dict | Runs multi-step automated agent optimization trajectory |

### Development Reverse Proxy
- During frontend development, `frontend/vite.config.js` proxies API requests (`/optimize`, `/optimize_full`, `/reset`, `/step`, `/state`, `/run_benchmark`) from `http://localhost:5173` to `http://127.0.0.1:7860`.

---

## Environment Variables & Configuration

The application reads configuration through system environment variables (or root `.env` file):

| Variable | Type | Default Value | Source Files | Purpose & Sensitivity |
|---|---|---|---|---|
| `PORT` | Integer | `7860` | `server/app.py`, `Dockerfile`, `render.yaml` | Port for the Uvicorn ASGI server. Low sensitivity. |
| `HF_TOKEN` | String | *(Unset)* | `inference.py`, `docker-compose.yml`, `render.yaml` | Hugging Face user access token for remote LLM inference. **High sensitivity (Secret)**. When absent, activates `MockOpenAI`. |
| `MODEL_NAME` | String | `Qwen/Qwen2.5-72B-Instruct` | `inference.py`, `docker-compose.yml`, `Dockerfile`, `render.yaml` | Model identifier string sent to the remote LLM router. Low sensitivity. |
| `API_BASE_URL` | String | `https://router.huggingface.co/v1` | `inference.py`, `Dockerfile`, `render.yaml` | OpenAI client base URL pointing to the LLM completion gateway. Low sensitivity. |
| `VITE_API_URL` | String | `""` (empty string) | `frontend/src/App.jsx` | Base URL for API requests in the React app. When empty, defaults to same-origin relative paths. Low sensitivity. |
| `AION_NO_UI` | Flag (`"1"`) | *(Unset)* | `inference.py:1151` | When set to `"1"`, suppresses the Gradio dashboard from launching during standalone inference runs. Low sensitivity. |
| `PYTHON_VERSION`| String | `"3.11"` | `render.yaml` | Specifies the Python runtime version for Render deployment. Low sensitivity. |
