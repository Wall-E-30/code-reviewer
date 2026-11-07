# Contributing to Aion Code Reviewer

Thank you for your interest in contributing to **Aion**, the open-source, RL-driven code reviewer!

We welcome contributions of all kinds: new benchmark cases, model fine-tunings, AST linter rules, bug fixes, documentation improvements, and editor integrations.

---

## 1. Development Setup

### Prerequisites
- Python 3.10 or higher
- Git
- Node.js 18+ (for frontend and VS Code extension development)

### Local Installation

Clone the repository and install in editable mode with development dependencies:

```bash
git clone https://github.com/aion-ai/aion.git
cd aion

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install package and test dependencies
pip install -e .
pip install pytest pytest-asyncio
```

### Running Tests

Execute the automated test suite:

```bash
pytest tests/ -v
```

---

## 2. Using Aion to Review Your Own Changes

Before committing changes, run the local staged reviewer:

```bash
aion review --staged
```

To view or add repository conventions:

```bash
aion conventions --list
```

---

## 3. Contributing Benchmark Cases to Aion-Bench

Aion-Bench is our objective yardstick for measuring code review precision and false-positive rates. We welcome real-world bug cases and clean negative diffs.

### Benchmark Case Format

Each test case adheres to the `BenchmarkCase` schema defined in `bench/schema.py`:

```json
{
  "case_id": "py-sql-injection-auth-01",
  "language": "python",
  "file_path": "services/auth.py",
  "diff": "--- a/auth.py\n+++ b/auth.py\n@@ -5,2 +5,3 @@\n def get_user(db, username):\n+    query = f\"SELECT * FROM users WHERE user = '{username}'\"\n     return db.execute(query)\n",
  "is_clean": false,
  "ground_truth_findings": [
    {
      "file_path": "services/auth.py",
      "line_number": 6,
      "category": "security",
      "severity": "critical",
      "rule_id": "sql-injection-fstring",
      "description": "SQL injection vulnerability via unparameterized f-string in database query.",
      "accepted_suggestions": [
        "query = \"SELECT * FROM users WHERE user = :username\"\nreturn db.execute(query, {'username': username})"
      ]
    }
  ]
}
```

To add cases:
1. Place case definitions in `bench/cases/`.
2. Ensure you specify `is_clean: true` for negative controls (clean diffs with zero defects).
3. Run the benchmark runner to verify:
   ```bash
   python -m bench.runner --cases bench/cases/
   ```

---

## 4. Submitting Model Evaluations to the Leaderboard

We encourage research labs and open-source developers to submit evaluations of new code models (open-weight, hybrid, or commercial) to the public **Aion-Bench Leaderboard**:

1. **Evaluate on Held-Out Test Split:**
   ```bash
   aion bench evaluate --model <your-model-slug> --split test --output results.json
   ```
2. **Submit via API or Pull Request:**
   - **API:**
     ```bash
     curl -X POST https://aion.openenv.org/api/leaderboard/submit \
       -H "Content-Type: application/json" \
       -d @results.json
     ```
   - **Pull Request:** Add your entry to `data/leaderboard.json` with a reproducible replication recipe.

---

## 5. Code Style & Review Guidelines

- We enforce strict typing and PEP 8 standards formatted with **Ruff**.
- All PRs must maintain or improve test coverage.
- PRs touching the core review pipeline must pass all security checks in `tests/test_action_pipeline.py`.
- Licensed under [Apache-2.0](LICENSE).

