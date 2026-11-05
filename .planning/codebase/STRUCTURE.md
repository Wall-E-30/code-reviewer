# Codebase Structure

**Analysis Date:** 2026-11-04

## Directory Layout

```text
code-reviewer/
├── .planning/                     # GSD project planning artifacts & codebase maps
│   └── codebase/                  # Architecture, stack, and convention documentation
├── data/                          # Benchmark problem templates and SFT trajectory datasets
│   ├── logic.py                   # Algorithmic efficiency benchmark file (O(N^2) duplicate search)
│   ├── security.py                # SQL injection vulnerability benchmark file
│   ├── style.py                   # PEP-8 indentation and unused import benchmark file
│   └── sft_trajectories.json      # Pre-generated behavioral cloning training trajectories
├── frontend/                      # React 19 single page application (Vite build system)
│   ├── public/                    # Static web assets
│   │   ├── favicon.svg            # Browser tab icon
│   │   └── icons.svg              # SVG UI icons
│   ├── src/                       # React frontend source files
│   │   ├── assets/                # Visual assets, branding logos, and hero art
│   │   │   ├── hero.png           # Hero banner artwork
│   │   │   ├── react.svg          # React logo
│   │   │   └── vite.svg           # Vite logo
│   │   ├── AionStyles.css         # Midnight Glass design system, bento layout, glow animations
│   │   ├── App.css                # Base App container styling
│   │   ├── App.jsx                # Main React dashboard: Live Optimizer & Benchmark panels
│   │   ├── index.css              # Typography, theme variables, and global CSS resets
│   │   └── main.jsx               # React DOM root render entry point
│   ├── .gitignore                 # Frontend-specific node_modules and dist exclusions
│   ├── eslint.config.js           # ESLint configuration for React 19 hooks and JSX
│   ├── index.html                 # HTML5 template and SPA mount container
│   ├── package.json               # NPM manifest: React 19, Vite, and dev scripts
│   ├── package-lock.json          # Locked NPM dependency graph
│   ├── README.md                  # Frontend quickstart instructions
│   ├── vercel.json                # Vercel deployment route rewrites configuration
│   └── vite.config.js             # Vite bundler configuration & local API reverse proxy
├── server/                        # Backend REST API and web server
│   └── app.py                     # FastAPI application, CORS, session routing, static asset host
├── bugs.md                        # Comprehensive system bug and vulnerability audit document
├── bugs_report.md                 # Summary audit log of fixed defects and improvements
├── concepts.md                    # Core Reinforcement Learning concepts and design journey
├── dashboard_preview.jpg          # Screenshot preview of the Aion dashboard
├── docker-compose.yml             # Docker compose configuration for running the containerized service
├── Dockerfile                     # Multi-stage container build (Node.js build -> Python 3.11 runtime)
├── env.py                         # Gymnasium RL environment (`CodeReviewEnv`) & AST grader
├── index.css                      # Standalone root CSS styles for fallback pages
├── inference.py                   # Model inference runner, local GPT-2, remote HF client, Gradio UI
├── models.py                      # Pydantic schemas: Action, Observation, Reward, OptimizeResponse
├── openenv.yaml                   # OpenEnv benchmark task specifications and difficulty levels
├── pyproject.toml                 # Python packaging and dependency specifications
├── README.md                      # Primary project overview, architecture diagram, and setup guide
├── render.yaml                    # Render Cloud web service deployment specification
├── requirements.txt               # Pinned Python package dependencies for pip install
├── test_suite.py                  # 18-point verification test suite for AST, grading, and API
├── train.py                       # Offline trajectory collector and SFT behavioral cloning script
├── train_autoregressive_rl.py     # Autoregressive Actor-Critic RL training script for GPT-2
├── train_rl.py                    # Unified 2-phase training (SFT + REINFORCE with baseline)
├── utils.py                       # 18-language detection, syntax repair, and indentation normalizer
└── uv.lock                        # UV package manager locked resolution file
```

## Directory Purposes

**`server/`:**
- Purpose: Hosts the backend API gateway that bridges the web frontend and evaluation engines.
- Contains: FastAPI router, middleware, session cache, endpoint handlers, static file mounting.
- Key files: `server/app.py`

**`frontend/`:**
- Purpose: Hosts the client-side single page application built with React 19 and Vite.
- Contains: Component source code, custom CSS styling, build scripts, development server configurations.
- Key files: `frontend/src/App.jsx`, `frontend/src/AionStyles.css`, `frontend/vite.config.js`, `frontend/package.json`

**`frontend/src/`:**
- Purpose: Application source code for the user dashboard.
- Contains: Dashboard views (Live Optimizer, Hackathon Benchmark), state hooks, toast notifications, syntax highlighter, and layout styling.
- Key files: `frontend/src/App.jsx`, `frontend/src/main.jsx`, `frontend/src/AionStyles.css`

**`data/`:**
- Purpose: Stores source code problem definitions and trajectory datasets used for RL evaluation and training.
- Contains: Standalone Python files representing specific code defect categories and JSON formatted datasets.
- Key files: `data/logic.py`, `data/security.py`, `data/style.py`, `data/sft_trajectories.json`

**`.planning/`:**
- Purpose: GSD planning documentation, architectural analyses, and codebase knowledge maps.
- Contains: Codebase maps (`.planning/codebase/`).
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`

## Key File Locations

**Entry Points:**
- `server/app.py`: FastAPI server entry point (`main()` on port 7860).
- `frontend/src/main.jsx`: React DOM initialization and mount point for browser.
- `inference.py`: Standalone CLI and Gradio UI entry point (`build_ui()`).
- `test_suite.py`: Automated test execution entry point.
- `train_rl.py`: RL model training entry point.

**Configuration:**
- `Dockerfile`: Multi-stage Docker build pipeline (Node build -> Python runtime).
- `docker-compose.yml`: Local multi-container development configuration.
- `openenv.yaml`: OpenEnv manifest defining task IDs (`style-cleanup`, `efficiency-boost`, `security-audit`).
- `pyproject.toml`: Python build system and package requirements.
- `requirements.txt`: Python dependencies (`fastapi`, `uvicorn`, `gradio`, `openai`, `torch`, `transformers`).
- `render.yaml`: Production infrastructure deployment manifest on Render.
- `frontend/vite.config.js`: Vite server and reverse proxy settings for port 7860.
- `frontend/eslint.config.js`: ESLint rules and globals.

**Core Logic:**
- `env.py`: Gymnasium RL environment (`CodeReviewEnv`), AST grading logic, dynamic linter, and subprocess test runner.
- `inference.py`: LLM pipeline (`evaluate_and_optimize`, `run_full_optimization`), local GPT-2 loader, and mock optimizer.
- `models.py`: Pydantic data models (`Action`, `Observation`, `Reward`, `OptimizeResponse`).
- `utils.py`: Multi-language detector, deep syntax repair, indentation normalizer.

**Testing:**
- `test_suite.py`: Verification suite verifying AST repairs, normalizers, task scoring, and multi-pass pipelines.

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g. `env.py`, `models.py`, `test_suite.py`, `train_rl.py`).
- React components: `PascalCase.jsx` (e.g. `App.jsx`).
- CSS files: `PascalCase.css` for custom design systems (`AionStyles.css`) and `kebab-case` / `camelCase` for base styles (`index.css`, `App.css`).
- Documentation: `UPPERCASE.md` for planning docs (`ARCHITECTURE.md`, `STRUCTURE.md`) and `kebab-case.md` for project notes (`bugs.md`, `concepts.md`).

**Directories:**
- Root & application directories: `lowercase` (e.g. `server`, `frontend`, `data`).
- Frontend source subdirectories: `lowercase` (e.g. `src`, `assets`, `public`).
- Planning directories: `.kebab-case` (e.g. `.planning/codebase`).

## Where to Add New Code

**New Benchmark Task:**
1. Define the task specification in `openenv.yaml` under `tasks:`.
2. Add baseline file in `data/<task_name>.py`.
3. Register the task entry in `TASKS` dictionary in `env.py:15`.
4. Add AST grading logic inside `_calculate_reward()` and `_generate_dynamic_linter()` in `env.py`.
5. Update `inference.py` mock optimizer and dropdown selections in `frontend/src/App.jsx`.
6. Add unit test verification case in `test_suite.py`.

**New Optimization Rule / Pass:**
1. Implement heuristic or transformation rule in `inference.py` (e.g. within `_optimize_python()` or `_optimize_generic()`).
2. If language-specific syntax repairs are needed, add helper in `utils.py`.
3. If new metrics are calculated, update `estimate_ast_improvements()` in `inference.py:556`.
4. If chained into full review, update sequence in `run_full_optimization()` in `inference.py:779`.

**New API Endpoint:**
1. Define request/response Pydantic models in `models.py`.
2. Add route decorator (`@app.get` or `@app.post`) in `server/app.py`.
3. If proxying through Vite in dev mode, add route to `frontend/vite.config.js:8`.
4. Connect frontend fetch calls in `frontend/src/App.jsx`.

**New Frontend View / Component:**
1. Create new component in `frontend/src/` or embed within `frontend/src/App.jsx`.
2. Add tab trigger to `tabs-header` in `frontend/src/App.jsx:159`.
3. Add corresponding CSS styling in `frontend/src/AionStyles.css`.

**Utilities & Shared Helpers:**
1. Code manipulation, AST helpers, or regex parsers should be placed in `utils.py`.
2. Schema models shared between client and server belong in `models.py`.

## Special Directories

**`frontend/dist/`:**
- Purpose: Contains compiled production bundles (`index.html`, `/assets/*.js`, `/assets/*.css`).
- Generated: Yes (via `npm run build` inside `frontend/`).
- Committed: No (ignored by `.gitignore`). In Docker builds, copied into the production container for FastAPI to serve.

**`models/rl_model/`:**
- Purpose: Local checkpoint storage directory for fine-tuned GPT-2 weights and tokenizer vocabulary files.
- Generated: Yes (by `train_rl.py` or `train_autoregressive_rl.py`).
- Committed: No (contains large model binary weights).

**`.planning/`:**
- Purpose: GSD workflow state and codebase mapping documentation.
- Generated: Yes (by GSD tooling).
- Committed: Yes (tracked by version control).

---

*Structure analysis: 2026-11-04*
