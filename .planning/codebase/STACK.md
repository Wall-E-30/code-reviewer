# Technology Stack

**Analysis Date:** 2026-11-04

## Overview

Aion is an autonomous AI-driven code optimization and evaluation sandbox structured as a full-stack web application with deep integration into reinforcement learning (RL) and Large Language Model (LLM) inference systems. The architecture couples a high-performance Python ASGI backend (`FastAPI`) with a modern JavaScript Single-Page Application (`React 19` via `Vite`). Underpinning the optimization pipeline is an Abstract Syntax Tree (AST) grading environment (`env.py`) compatible with Gymnasium-style step/reset interfaces, paired with dual inference pathways: a remote LLM router client (`OpenAI` SDK configured for Hugging Face endpoints) and a local autoregressive language model policy (`PyTorch` and `Transformers` GPT-2).

---

## Languages & Runtimes

### Backend Runtime
- **Python**: `>=3.10` specified in `pyproject.toml`, with `Python 3.11` specified as the primary container and deployment target in `Dockerfile` (`python:3.11-slim`) and `render.yaml` (`PYTHON_VERSION: "3.11"`).
- **Core Standard Library Utilization**:
  - `ast`: Used extensively in `env.py`, `inference.py`, and `utils.py` for Python AST parsing, tree traversal, indentation analysis, security sink detection, and syntactic correctness scoring.
  - `difflib`: Provides line-by-line diff generation in `server/app.py` (`generate_diff_data`) and unified diff output in `env.py`.
  - `subprocess` & `tempfile`: Used in `env.py` for isolated script execution, differential test generation, and optional node check syntax validation.
  - `asyncio`: Manages asynchronous endpoints and multi-pass optimization pipelines in `server/app.py` and `inference.py`.
  - `logging`, `uuid`, `re`, `json`, `base64`: Handles request tracing, session identifiers, regex parsing, and serialization across `server/app.py` and `inference.py`.

### Frontend Runtime
- **Node.js**: Requires `>=18` (documented in `README.md`), packaged via `Node 22` in `Dockerfile` (`node:22-slim`).
- **JavaScript / ECMAScript**: ECMAScript 2020+ using ES Modules (`"type": "module"` in `frontend/package.json`).
- **JSX**: React 19 JSX transformation compiled via `@vitejs/plugin-react`.

### Multi-Language Parsing & Analysis
- Although the backend engine is written in Python, the syntax detection layer (`utils.py:11-120`) and the UI (`frontend/src/App.jsx:41-53`) support keyword-based language detection and heuristic scoring across 17 languages:
  - Python, JavaScript, TypeScript, Java, C++, C, Go, Rust, Ruby, Kotlin, Swift, C#, PHP, HTML, CSS, SQL, and Bash.

---

## Frameworks & Core Libraries

### Backend API Framework
- **FastAPI** (`fastapi>=0.110.0` in `requirements.txt`): Primary REST API framework providing asynchronous route handlers, OpenAPI documentation (`/docs`, `/redoc`), and HTTP middleware (`server/app.py`).
- **Uvicorn** (`uvicorn>=0.29.0` in `requirements.txt`): Lightning-fast ASGI production web server used as the runtime entry point in `Dockerfile`, `render.yaml`, and `server/app.py:main`.
- **CORSMiddleware** (`fastapi.middleware.cors`): Configured in `server/app.py:34-41` with permissive origins to enable decoupled frontend cross-origin requests.

### Data Modeling & Validation
- **Pydantic** (`pydantic>=2.0` in `requirements.txt`, `pydantic` in `pyproject.toml`):
  - `models.py` defines strictly-typed data schemas:
    - `Action`: Encapsulates action types (`apply_fix`, `comment`, `submit`), line target, content, and session ID.
    - `Observation`: Carries file name, source code content, diff, linter diagnostics, and current task identifier.
    - `Reward`: Validates scalar float scores bounded within `(0.0, 1.0)` per OpenEnv requirements.
    - `OptimizeResponse`: Standardized schema for `/optimize` and `/optimize_full` endpoints.
  - Request body models in `server/app.py`: `ResetRequest`, `OptimizeRequest`, and `DiffRequest`.

### Machine Learning & Reinforcement Learning
- **PyTorch** (`torch>=2.0.0` in `requirements.txt`, `pyproject.toml`):
  - Used in `train_rl.py` and `train_autoregressive_rl.py` for policy gradient updates (REINFORCE with value network baseline) and Actor-Critic architecture.
  - Provides tensor operations, module definitions (`nn.Module`), and AdamW optimizer execution (`torch.optim.AdamW`).
  - Dynamically imported during inference in `server/app.py:138` and `inference.py:96` to optimize server boot time and CPU memory footprint when no local RL model weights are mounted.
- **Hugging Face Transformers** (`transformers>=4.40.0` in `requirements.txt`, `pyproject.toml`):
  - `GPT2LMHeadModel` and `GPT2Tokenizer`: Powers the local autoregressive policy in `inference.py:97-102` and training scripts (`train_autoregressive_rl.py:4`, `train_rl.py`).
- **OpenEnv Core** (`openenv-core` in `pyproject.toml`):
  - Standardized benchmark environment interface defined via `openenv.yaml`.
- **Gymnasium-Style Environment (`CodeReviewEnv`)**:
  - Implemented in `env.py:62-1163`. Coordinates observation states, step transitions, automated backtracking on code score regressions, and AST-based reward grading across style, efficiency, and security benchmarks.

### Large Language Model & Inference Orchestration
- **OpenAI Python SDK** (`openai>=1.0` in `requirements.txt`, `pyproject.toml`):
  - Serves as the client interface to connect to remote inference APIs (`inference.py:8, 439`).
  - Configured to route to Hugging Face Router endpoint (`API_BASE_URL="https://router.huggingface.co/v1"`) with default model `MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"`.
- **MockOpenAI In-Memory Fallback**:
  - Custom mock client class in `inference.py:126-260` that handles task parsing, regex/AST-based transformations, and returns compliant JSON payloads when running offline without external API keys.

### Alternative Dashboard UI
- **Gradio** (`gradio>=4.0.0` in `requirements.txt`, `gradio` in `pyproject.toml`):
  - Standalone dashboard implemented in `inference.py:811-1156` featuring tabs for Live Optimizer and Hackathon Benchmark.
  - Uses `gr.themes.Soft` with custom CSS styling and launch parameters configured for container exposure (`server_name="0.0.0.0"`, `server_port=7860`).

### Frontend SPA Framework
- **React 19** (`react` `^19.2.4`, `react-dom` `^19.2.4` in `frontend/package.json`):
  - Functional components with hooks (`useState`, `useEffect`, `useRef`).
  - Features real-time state management for code buffers, benchmark trajectories, diff rendering, and toast notifications (`frontend/src/App.jsx`).
- **Styling & Design System**:
  - Pure CSS design system dubbed "Midnight Glass" defined in `frontend/src/AionStyles.css` and `frontend/src/index.css`.
  - Implements Bento grid layouts, glassmorphism cards, glowing status pills, and CSS keyframe animations (`shimmer`, `beam`).
  - Zero heavy third-party UI component libraries (no Tailwind or Material UI runtime overhead).

---

## Package Management & Dependencies

### Python Package Management
- **Manifests**:
  - `pyproject.toml`: Modern packaging specification using `setuptools.build_meta` build backend. Declares project metadata (`aion-code-reviewer` v1.0.0), CLI script entry point (`server = "server.app:main"`), and direct dependencies.
  - `requirements.txt`: Pinned version floor requirements (`pydantic>=2.0`, `openai>=1.0`, `fastapi>=0.110.0`, `uvicorn>=0.29.0`, `gradio>=4.0.0`, `torch>=2.0.0`, `transformers>=4.40.0`).
- **Lockfile**:
  - `uv.lock`: Generated by Astral `uv` (version 1, revision 3). Fully resolves the complete transitive dependency tree, platform markers (Windows, Linux, Emscripten), wheel hashes, and source distribution URLs.

#### Python Dependency Summary:
| Dependency | Version Spec | Purpose | Defined In |
|---|---|---|---|
| `fastapi` | `>=0.110.0` | Asynchronous REST API server | `requirements.txt` |
| `uvicorn` | `>=0.29.0` | Production ASGI web server | `requirements.txt` |
| `pydantic` | `>=2.0` | Data modeling & JSON validation | `requirements.txt`, `pyproject.toml` |
| `openai` | `>=1.0` | Remote LLM completion client | `requirements.txt`, `pyproject.toml` |
| `gradio` | `>=4.0.0` | Optional standalone web UI | `requirements.txt`, `pyproject.toml` |
| `torch` | `>=2.0.0` | Deep learning & RL policy computation | `requirements.txt`, `pyproject.toml` |
| `transformers` | `>=4.40.0` | Pretrained language models (GPT-2) | `requirements.txt`, `pyproject.toml` |
| `openenv-core` | `*` | OpenEnv benchmark framework integration | `pyproject.toml` |
| `setuptools` | `>=61.0` | Build backend system | `pyproject.toml` |

### Node.js / JavaScript Package Management
- **Manifest**: `frontend/package.json` declares dependencies and dev scripts.
- **Lockfile**: `frontend/package-lock.json` pins exact semantic versions and integrity hashes.

#### Frontend Dependency Summary:
| Dependency | Version Spec | Purpose | Category |
|---|---|---|---|
| `react` | `^19.2.4` | UI component library | Production |
| `react-dom` | `^19.2.4` | DOM renderer for React | Production |
| `vite` | `^8.0.4` | Next-generation frontend bundler / dev server | Dev |
| `@vitejs/plugin-react` | `^6.0.1` | React Fast Refresh & Babel/Babel-free JSX compilation | Dev |
| `eslint` | `^9.39.4` | Code linting engine | Dev |
| `@eslint/js` | `^9.39.4` | ESLint JavaScript core rules | Dev |
| `eslint-plugin-react-hooks` | `^7.0.1` | React Hooks linting rules | Dev |
| `eslint-plugin-react-refresh` | `^0.5.2` | Fast Refresh linting constraints | Dev |
| `@types/react` | `^19.2.14` | TypeScript type declarations for React | Dev |
| `@types/react-dom` | `^19.2.3` | TypeScript type declarations for React DOM | Dev |
| `globals` | `^17.4.0` | Global identifier definitions for ESLint | Dev |

---

## Build & Development Tooling

### Frontend Build Tooling
- **Vite 8** (`frontend/vite.config.js`):
  - Development server runs on default port `5173`.
  - Configured with reverse-proxy rules forwarding API routes (`/optimize`, `/optimize_full`, `/reset`, `/step`, `/state`, `/run_benchmark`) to `http://127.0.0.1:7860`.
  - Production build command `npm run build` outputs bundled and minified static assets to `frontend/dist/`.
- **ESLint 9** (`frontend/eslint.config.js`):
  - Flat configuration format (`eslint.config.js`).
  - Configures React Recommended, React Hooks, and React Refresh rules targeting browser environments.

### Backend Packaging & Serving
- **Static Asset Serving Integration**:
  - `server/app.py:305-325` resolves `frontend/dist`.
  - In production, FastAPI mounts `/assets` using `StaticFiles` and registers a catch-all route `{full_path:path}` returning `index.html` to support client-side React SPA routing.
  - Fallback JSON message is emitted on `/` if the frontend has not been compiled.

---

## Platform & Deployment Environment

### Containerization
- **Dockerfile** (`Dockerfile`):
  - Two-stage multi-platform container build:
    - **Stage 1 (Build)**: `node:22-slim` installs frontend dependencies and compiles production assets with `npm run build`.
    - **Stage 2 (Runtime)**: `python:3.11-slim` installs Python packages via `pip install --no-cache-dir -r requirements.txt`, copies project code and built assets from Stage 1 into `/app/frontend/dist`, and executes `uvicorn server.app:app --host 0.0.0.0 --port 7860`.
- **Docker Compose** (`docker-compose.yml`):
  - Defines single-node service `aion-engine`.
  - Maps port `7860:7860`.
  - Injects environment defaults for `HF_TOKEN` and `MODEL_NAME=Qwen/Qwen2.5-72B-Instruct`.

### Cloud Deployment Profiles
- **Hugging Face Spaces**:
  - Configured via Docker SDK frontmatter in `README.md` (`sdk: docker`, `app_port: 7860`, `colorFrom: indigo`, `colorTo: blue`).
- **Render** (`render.yaml`):
  - Web service specification (`aion-code-reviewer-api`) running Python 3.11, auto-provisioning `pip install -r requirements.txt`, launching Uvicorn, and validating readiness via `/health`.
- **Vercel** (`frontend/vercel.json`):
  - Standalone frontend deployment configuration mapping Vite build commands and catch-all URL rewrite routes for SPA navigation.
