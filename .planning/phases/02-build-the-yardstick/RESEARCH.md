# Phase 02: Build the Yardstick (Aion-Bench Evaluation Suite) — Research & Technical Specification

**Phase:** `02-build-the-yardstick`  
**Milestone:** v1.0 — Path to the No. 1 Code Reviewer (Zero-Budget, RL-Driven)  
**Date:** 2026-11-05  
**Requirements Covered:** `BENCH-01`, `BENCH-02`, `BENCH-03`, `BENCH-04`, `BENCH-05`  

---

## 1. Executive Summary & Objective

In code review, you cannot improve what you cannot measure objectively. Currently, AI code reviewers suffer from severe user mistrust because evaluations rely on anecdotal impressions or toy AST counters. 

**Phase 2 establishes "Aion-Bench"**: an open, reproducible, objective benchmark suite for automated code review. Aion-Bench serves as the unchanging yardstick against which every subsequent phase—from GitHub Action prompts (Phase 3) to RL reward functions (Phase 4) and GRPO model training (Phase 5)—is measured.

### Core Success Targets
1. **One-Command CLI:** `python -m bench.runner --split dev` executes in under 60 minutes on local/free commodity hardware, outputting structured JSON and formatted Markdown reports.
2. **200+ Verifiable Cases:** Injected bug mutations with exact ground-truth anchors paired with clean-diff negatives.
3. **Clean-Diff Negative Control:** A dedicated set of valid, bug-free PR diffs where any comment generated is penalized as a false positive (FPR).
4. **Hand-Audited Gold Set:** 100–200 human-reviewed cases for gold-standard calibration.
5. **Locked Private Test Split:** Cryptographically isolated split (`test_locked.json`) with SHA-256 manifests to guarantee zero training contamination (`DATA-02`).
6. **Day-One Baselines Documented:** Baseline scores recorded for the existing Aion prototype, static linters (Ruff + Bandit), and plain LLMs.

---

## 2. Technical Constraints & Design Principles

1. **Zero-Budget & Local Execution:** The benchmark must not require commercial cloud clusters or expensive paid API quotas to run. It must support mock and local evaluation out-of-the-box.
2. **Deterministic Reproducibility:** Every benchmark test case is an immutable, self-contained JSON record containing the original file content, modified file content, unified diff, and ground-truth annotations.
3. **Strict Language Focus:** High-fidelity AST ground truth for Tier-1 supported languages (**Python** and **TypeScript/JavaScript**).
4. **Objective Matching Over LLM Vibes:** Review comments are scored against ground-truth findings using line-proximity windows and semantic categories rather than unconstrained "LLM-as-a-judge" grading.
5. **Clean Separation From Platform Code:** Benchmark assets reside cleanly in a top-level `bench/` package with zero coupling to UI frameworks (React/Gradio) or ephemeral server states.

---

## 3. Aion-Bench Data Schema (`BENCH-01`)

The benchmark architecture centers on strict Pydantic schemas in `bench/schema.py`:

```
bench/
├── __init__.py
├── schema.py                 # Core Pydantic models (BenchmarkCase, Finding, ReviewComment, Metrics)
├── runner.py                 # CLI entrypoint (python -m bench.runner)
├── evaluator/
│   ├── __init__.py
│   ├── matcher.py            # Ground truth line-window & category matching logic
│   └── metrics.py            # Precision, Recall, FPR, Comments/PR, Nitpick Rate, Latency
├── generator/
│   ├── __init__.py
│   ├── injector.py           # Deterministic AST mutation engine (injected bugs)
│   └── clean.py              # Clean-diff negative generator (FPR control)
├── mined/
│   ├── __init__.py
│   └── miner.py              # Real human PR review ingestion pipeline
├── splits/
│   ├── dev.json              # Development set for prompt/agent iteration
│   ├── gold.json             # 100-200 hand-audited calibration cases
│   ├── test_locked.json      # Private locked test split
│   └── manifest.json         # SHA-256 checksums ensuring immutability
└── baselines/
    ├── __init__.py
    ├── run_baselines.py      # Execution harness for day-one baselines
    └── BASELINE_DAY_ONE.md   # Recorded baseline metrics table
```

### 3.1 Pydantic Data Models

```python
class FindingCategory(str, Enum):
    BUG = "bug"                   # Logic errors, runtime crashes, exceptions
    SECURITY = "security"         # Injections, secret leaks, traversal, unsafe sinks
    PERFORMANCE = "performance"   # Algorithmic complexity, leaks, redundant queries
    STYLE = "style"               # Formatting, naming, minor style deviations
    NITPICK = "nitpick"           # Trivial stylistic preferences, subjective commentary

class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"

class GroundTruthFinding(BaseModel):
    finding_id: str
    line_start: int
    line_end: int
    category: FindingCategory
    severity: FindingSeverity
    description: str
    fix_suggestion: Optional[str] = None
    rule_id: Optional[str] = None

class BenchmarkCase(BaseModel):
    case_id: str
    repository: str
    language: str                 # "python" | "typescript" | "javascript"
    file_path: str
    original_code: str
    modified_code: str
    diff: str
    split: str                    # "dev" | "test_locked" | "gold"
    is_clean_diff: bool           # True if no real bugs exist (FPR measurement)
    ground_truth: List[GroundTruthFinding] = []
    metadata: Dict[str, Any] = {}

class ReviewComment(BaseModel):
    file_path: str
    line_number: int
    category: FindingCategory
    comment: str
    suggestion: Optional[str] = None
    confidence: float = 1.0

class CaseEvaluation(BaseModel):
    case_id: str
    comments_posted: int
    true_positives: int
    false_positives: int
    false_negatives: int
    is_clean_diff: bool
    clean_diff_violation: bool   # True if comments were posted on a clean diff
    matched_findings: List[Dict[str, Any]]
    duration_ms: float

class BenchmarkMetrics(BaseModel):
    split: str
    total_cases: int
    clean_cases: int
    buggy_cases: int
    precision: float              # TP / (TP + FP)
    recall: float                 # TP / (TP + FN)
    false_positive_rate: float    # clean diffs with >=1 comment / total clean diffs
    avg_comments_per_pr: float    # total comments / total cases
    nitpick_rate: float           # nitpick comments / total comments
    avg_latency_ms: float
    total_duration_sec: float
```

---

## 4. Evaluation Metrics & Ground-Truth Matching (`BENCH-05`)

### 4.1 Ground-Truth Matching Rules
A generated `ReviewComment` is counted as a **True Positive (TP)** matching a `GroundTruthFinding` if and only if:
1. **File Match:** `comment.file_path == finding.file_path`.
2. **Line Proximity Window:** The comment line falls within a bounded window around the ground truth:
   $$\text{finding.line\_start} - \Delta \le \text{comment.line\_number} \le \text{finding.line\_end} + \Delta$$
   *(Default $\Delta = 3$ lines, accommodating diff framing).*
3. **Category Congruence:** The comment must identify the problem category (e.g. security findings cannot be satisfied by style nitpicks). If the ground truth is a `BUG` or `SECURITY`, a `NITPICK` comment does not match.

### 4.2 Metrics Formulations

1. **Precision:**
   $$\text{Precision} = \frac{\sum \text{TP}}{\sum \text{TP} + \sum \text{FP}}$$
2. **Recall:**
   $$\text{Recall} = \frac{\sum \text{TP}}{\sum \text{Ground Truth Findings}}$$
3. **False-Positive Rate (FPR on Clean Diffs):**
   $$\text{FPR} = \frac{\text{Clean Cases with } \ge 1 \text{ Posted Comment}}{\text{Total Clean Cases}}$$
4. **Comments per PR:**
   $$\text{Avg Comments} = \frac{\text{Total Posted Comments}}{\text{Total Evaluated Cases}}$$
5. **Nitpick Ratio:**
   $$\text{Nitpick Rate} = \frac{\text{Comments categorized as Style or Nitpick}}{\text{Total Posted Comments}}$$

---

## 5. Synthetic Bug Injection & Clean Negatives (`BENCH-02`)

### 5.1 AST Mutation Operators (`bench/generator/injector.py`)
To build reproducible bugs that break real logic, `injector.py` implements AST transformations on Python and TypeScript/JS code:

| Mutation Operator | Code Transformation Pattern | Ground Truth Category | Severity |
|---|---|:---:|:---:|
| `InvertComparison` | `a < b` $\rightarrow$ `a >= b`; `==` $\rightarrow$ `!=` | `BUG` | `CRITICAL` |
| `OffByOne` | `range(len(x))` $\rightarrow$ `range(len(x) + 1)` | `BUG` | `MAJOR` |
| `NoneDereference` | Remove `.get(k, default)` or `if x is not None:` guards | `BUG` | `CRITICAL` |
| `ResourceLeak` | Replace `with open(...)` with unclosed bare `f = open(...)` | `PERFORMANCE` | `MAJOR` |
| `UnsafeCommandSink` | Replace `subprocess.run([cmd, arg])` with `shell=True` format strings | `SECURITY` | `CRITICAL` |
| `SwallowedException` | Replace typed exception handle with bare `except: pass` | `BUG` | `MAJOR` |

### 5.2 Clean-Diff Negative Synthesis (`bench/generator/clean.py`)
AI reviewers frequently hallucinate phantom bugs on harmless refactorings. `clean.py` generates PR diffs containing:
- Code reformatting / PEP 8 whitespace adjustments.
- Adding docstrings and type hints (`def add(a: int, b: int) -> int:`).
- Safe local variable renaming.
- Adding unit test cases or assertion checks.

These cases carry `ground_truth = []` and `is_clean_diff = True`. Posting even a single bug report on these diffs triggers an immediate false-positive penalty.

---

## 6. Mined Human PR Reviews (`BENCH-03`)

Real code reviews contain nuanced architectural feedback that synthetic mutations miss.
`bench/mined/miner.py` ingests real PR review datasets (such as CodeReviewer and curated open-source PR pairs):
- Filters for PRs where a reviewer comment directly prompted a subsequent corrective commit touching the referenced lines.
- Strips conversational and social noise (`"LGTM"`, `"Thanks for the PR!"`, `"Merged"`).
- Normalizes diffs, code contexts, and review comments into the unified `BenchmarkCase` schema.

---

## 7. Gold Set, Locked Test Split & Leakage Guard (`BENCH-04`)

To prevent the common pitfall of training on the test set:

1. **Split Stratification:**
   - `dev.json` (40% of cases): Unlocked for prompt tuning, agent development, and regression testing.
   - `gold.json` (100–200 cases): Meticulously hand-audited by senior developers to serve as the ground-truth benchmark for calibration.
   - `test_locked.json` (locked split): Hidden from training data pipelines and prompt optimization.
2. **Cryptographic Manifest (`manifest.json`):**
   - Stores SHA-256 hashes of every test case payload in `test_locked.json` and `gold.json`.
   - In Phase 4, `DATA-02` (Split Isolation & Leakage Guard) will run automated verification checks asserting $0.0\%$ hash collision between the training set and `manifest.json`.

---

## 8. Baseline Calibration Standards (`BENCH-05`)

Before modifying review prompts in Phase 3 or training models in Phase 5, Phase 2 measures day-one baselines across three standard systems:
1. **Current Aion Prototype:** Evaluates the existing AST heuristic rules and offline MockOpenAI engine.
2. **Static Linters Baseline:** Combines `ruff check` (style/syntax) and `bandit` (security) mapped into review comments.
3. **Plain LLM Baseline:** Direct zero-shot prompt on a standard foundation model (e.g. Qwen2.5-Coder / Mock LLM) without Aion's multi-stage verifier.

Baseline results will be written to `bench/baselines/BASELINE_DAY_ONE.md`.

---

## 9. Phase 2 Plan Decomposition

Phase 2 is structured into 3 sequential, verifiable execution plans:

| Plan | Title | Requirements | Key Deliverables |
|---|---|:---:|---|
| **02-01** | **Benchmark Architecture, Data Schema & CLI Runner** | `BENCH-01` | `bench/schema.py`, `bench/evaluator/`, `bench/runner.py`, end-to-end tracer CLI run with JSON/Markdown reporting. |
| **02-02** | **Bug Injector, Clean Diff Generator & Real Review Miner** | `BENCH-02`, `BENCH-03` | `bench/generator/injector.py`, `bench/generator/clean.py`, `bench/mined/miner.py`, synthesized 200+ case dataset. |
| **02-03** | **Gold Set Curation, Locked Test Split & Baseline Calibration** | `BENCH-04`, `BENCH-05` | `bench/splits/` (`dev`, `gold`, `test_locked`, `manifest.json`), leakage guard tests, day-one baseline runs, and `BASELINE_DAY_ONE.md`. |

