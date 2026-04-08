# Aion Code Reviewer (OpenEnv Benchmark)

## Environment Overview and Motivation
The **Aion Code Reviewer** is an interactive, AI-powered sandbox designed to evaluate a Large Language Model's capability to perform real-world code review and bug-fixing tasks. 

In professional software development, human reviewers must analyze code context, interpret linter warnings, identify logical or security flaws, and apply precise fixes. This environment simulates that workflow. Agents are presented with buggy code, provided with mock linter feedback, and tasked with applying optimal fixes before officially submitting their review. It tests not just code generation, but code comprehension, security auditing, and iterative refinement.

---

## Action and Observation Spaces

The environment strictly adheres to the OpenEnv specification using typed Pydantic models.

### Observation Space
At each step, the agent receives an `Observation` containing the current state of the workspace:
* `file_name` (str): The name of the file currently under review.
* `code_content` (str): The full content of the buggy/current code.
* `diff` (str): Changes applied to the buffer so far.
* `linter_report` (List[str]): Simulated terminal output guiding the agent toward syntax or security issues.
* `current_task` (str): The ID of the active task.

### Action Space
The agent interacts with the environment by emitting an `Action` object formatted as JSON:
* `action_type` (str): The chosen action (`"apply_fix"` to modify code, `"submit"` to end the review).
* `content` (str): The corrected code string to replace the buffer.
* `line_number` (Optional[int]): Target line for specific actions.

---

## Task Descriptions

The benchmark includes three progressive tasks requiring different levels of developer expertise:

1. **Style & Linting (`style-cleanup`)**
   * **Difficulty:** Easy
   * **Objective:** Clean up Python code by fixing indentation errors and removing unused imports (`import sys`) based on linter warnings.
   * **Grader:** Deterministic string matching checking for the absence of unused imports and corrected indentation strings.

2. **Algorithm Optimization (`efficiency-boost`)**
   * **Difficulty:** Medium
   * **Objective:** Identify an inefficient nested loop ($O(n^2)$) and refactor it into a more efficient dictionary or set lookup ($O(n)$).
   * **Grader:** Static analysis evaluating the reduction of `for` loop counts in the abstract syntax tree/code structure.

3. **Security Vulnerability (`security-audit`)**
   * **Difficulty:** Hard
   * **Objective:** Audit database interaction code, identify a critical SQL Injection vulnerability caused by Python f-strings, and refactor it to use parameterized queries.
   * **Grader:** Deterministic parsing ensuring the removal of unsafe string interpolation and the presence of safe parameter binding mechanisms.

---

## Setup and Usage Instructions

This environment is fully containerized and designed to run on Hugging Face Spaces or locally via Docker.

### Local Docker Execution
1. Clone the repository and navigate to the root directory.
2. Ensure your `data/` directory contains the target code files (`style.py`, `logic.py`, `security.py`).
3. Build the container:
   ```bash
   docker build -t aion-code-reviewer .
