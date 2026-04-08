# Aion Code Reviewer & Optimizer

**Aion Code Reviewer** is a robust, interactive sandbox environment designed for the **Meta OpenEnv Hackathon**. It evaluates the ability of Large Language Models (LLMs) to perform professional code audits, refactoring, and security hardening using a deterministic, AST-based grading system.

## Overview
Most code-generation benchmarks only check if code *runs*. **Aion** goes further by analyzing the **structure** of the code using Abstract Syntax Trees (AST). It simulates a real-world developer workflow where an agent must not only fix a bug but do so efficiently and securely.

### Key Features
* **OpenEnv Compliant:** Fully implements the `step()`, `reset()`, and `state()` interface with Pydantic-typed models.
* **AST-Based Grading:** Uses Python's `ast` module to verify optimizations (e.g., ensuring $O(n^2)$ logic was actually refactored to $O(n)$).
* **Incremental Rewards:** Provides partial credit ($0.5$) for progress, encouraging agents to solve complex problems step-by-step.
* **Dual-Mode Interface:** A Gradio dashboard featuring a **Hackathon Benchmark** tab and a **Custom Optimizer** tab.

---

## 🛠️ Technical Specification

### Observation Space
The agent receives a rich context at each step:
* `file_name`: The target script.
* `code_content`: The current state of the code buffer.
* `linter_report`: Simulated feedback highlighting specific style or security flaws.

### Action Space
Agents interact via JSON actions:
* `action_type`: `apply_fix` or `submit`.
* `content`: The complete, updated source code.

---

## Task Environments

| Task ID | Difficulty | Focus | Success Criteria (1.0 Reward) |
| :--- | :--- | :--- | :--- |
| **style-cleanup** | Easy | Linting | Remove unused `import sys` AND fix 4-space indentation. |
| **efficiency-boost** | Medium | Algorithms | Refactor nested `for` loops into a hash-map/dictionary lookup. |
| **security-audit** | Hard | Security | Remove SQL f-strings and implement parameterized queries (`?`). |

---

## The Dashboard

### 1. Hackathon Benchmark
This mode runs the standardized baseline. It pulls the buggy files from the `data/` directory and tracks the agent's trajectory through the task. Results are emitted to system `stdout` in the required `[START]`, `[STEP]`, `[END]` format.

### 2. Paste & Optimize (The "Wow" Factor)
A custom tool allowing users to paste their own Python snippets. The environment performs an initial "Quality Score" audit, lets the AI agent attempt a fix, and then re-evaluates the code to show the "Optimized Quality Score" jump.

---

## Setup & Deployment

### Local Development
1. **Clone & Install:**
   ```bash
   pip install -r requirements.txt
   ```
   
2. Run Locally:
    ```bash
    python inference.py
    ```
Note: Ensure HF_TOKEN is set in your environment variables.

**Docker Deployment**
Build and run the containerized version:

    ```bash
    docker build -t aion-reviewer .
    docker run -e HF_TOKEN="your_token" -p 7860:7860 aion-reviewer
    ```
    
Evaluated using Qwen/Qwen2.5-72B-Instruct via the Hugging Face Inference API.
Developed for the Meta OpenEnv Hackathon 2026.
1. **Clone & Install:**
   ```bash
   pip install -r requirements.txt
