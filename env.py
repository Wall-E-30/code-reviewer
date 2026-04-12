import ast
from pydantic import BaseModel
from typing import List

# --- DATA: The Baseline Tasks ---
# BUG FIX #1: Updated code strings to match the actual data files (style.py, logic.py, security.py)
TASKS = {
    "style-cleanup": {
        "file_name": "style.py",
        "code": "import os\nimport sys # Unused import\ndef hello_world():\n  print(\"Hello\")\n  print(\"Indentation is wrong here\")\n",
        "linter": ["Unused import 'sys' detected.", "Indentation error: expected 4 spaces, got 2."]
    },
    "efficiency-boost": {
        "file_name": "logic.py",
        "code": "def find_duplicates(list_a, list_b):\n    # Very slow O(N^2) approach\n    duplicates = []\n    for item_a in list_a:\n        for item_b in list_b:\n            if item_a == item_b:\n                duplicates.append(item_a)\n    return duplicates\n",
        "linter": ["Nested loops detected (O(n^2)). Refactor to use a dictionary or set for O(n) lookups."]
    },
    "security-audit": {
        "file_name": "security.py",
        "code": "import sqlite3\ndef get_user_data(user_id):\n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n    query = f\"SELECT * FROM users WHERE id = '{user_id}'\"\n    cursor.execute(query)\n    return cursor.fetchone()\n",
        "linter": ["SQL Injection vulnerability. Remove f-string and use parameterized queries (?, %s, or :param)."]
    }
}

# --- OBSERVATION MODEL ---
# BUG FIX #2: Observation model now matches models.py exactly
# (added file_name, diff; changed linter_report to List[str])
class Observation(BaseModel):
    file_name: str
    code_content: str
    diff: str
    linter_report: List[str]
    current_task: str


class CodeReviewEnv:
    def __init__(self):
        self.current_task_id = "style-cleanup"
        self.code = TASKS[self.current_task_id]["code"]
        self.original_code = self.code
        self.step_count = 0
        self.max_steps = 5

    def reset(self, task_id: str = "style-cleanup") -> Observation:
        """Required by OpenEnv: Resets the environment for a new episode."""
        if task_id not in TASKS:
            task_id = "style-cleanup"

        self.current_task_id = task_id
        self.code = TASKS[task_id]["code"]
        self.original_code = self.code
        self.step_count = 0
        return self._get_observation()

    def state(self) -> dict:
        """Required by OpenEnv: Returns the current internal state."""
        return {
            "task_id": self.current_task_id,
            "code_content": self.code,
            "steps_taken": self.step_count
        }

    def step(self, action):
        """Required by OpenEnv: Applies the agent's action and calculates rewards."""
        self.step_count += 1

        if action.action_type == "apply_fix" and action.content:
            self.code = action.content

        reward = self._calculate_reward()

        # SAFETY-FIRST: done threshold updated to handle new max reward
        done = self.step_count >= self.max_steps or reward >= 0.98

        return self._get_observation(), reward, done, {}

    def load_custom_code(self, code: str, task_type: str) -> Observation:
        """Custom tool for the Gradio Dashboard to allow human testing."""
        self.code = code
        self.original_code = code
        self.current_task_id = task_type
        self.step_count = 0
        return self._get_observation()

    def _get_observation(self) -> Observation:
        """Helper to package the current state into the Pydantic observation."""
        task = TASKS.get(self.current_task_id, {})
        linter = task.get("linter", ["Custom code analysis."])
        file_name = task.get("file_name", "custom.py")

        # Build a simple unified diff string
        diff = self._build_diff(self.original_code, self.code)

        return Observation(
            file_name=file_name,
            code_content=self.code,
            diff=diff,
            linter_report=linter,
            current_task=self.current_task_id
        )

    def _build_diff(self, original: str, current: str) -> str:
        """Builds a simple line-by-line diff string."""
        if original == current:
            return ""
        orig_lines = original.splitlines()
        curr_lines = current.splitlines()
        diff_lines = []
        for i, (o, c) in enumerate(zip(orig_lines, curr_lines)):
            if o != c:
                diff_lines.append(f"- {o}")
                diff_lines.append(f"+ {c}")
        # Handle added/removed lines
        if len(curr_lines) > len(orig_lines):
            for line in curr_lines[len(orig_lines):]:
                diff_lines.append(f"+ {line}")
        elif len(orig_lines) > len(curr_lines):
            for line in orig_lines[len(curr_lines):]:
                diff_lines.append(f"- {line}")
        return "\n".join(diff_lines)

    def _calculate_reward(self) -> float:
        """AST-Based Grader: Returns a score strictly between [0.1 and 0.99]"""
        score = 0.1

        try:
            tree = ast.parse(self.code)
        except SyntaxError:
            pass  # Stay at score = 0.1 and pass through the clamp

        if self.current_task_id == "style-cleanup":
            if "import sys" not in self.code:
                score += 0.4
            # BUG FIX #4a: original check was "    print(" which matched ANY 4-space indented print.
            # Now we check for proper 4-space indentation on ALL def bodies using AST.
            func_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            if func_defs:
                lines = self.code.splitlines()
                body_lines = [lines[n.lineno - 1] for fd in func_defs for n in ast.walk(fd) if hasattr(n, 'lineno') and n is not fd]
                properly_indented = all(
                    line.startswith("    ") or not line.strip()
                    for line in lines
                    if line.strip() and not line.strip().startswith("def ") and not line.strip().startswith("import") and not line.strip().startswith("#")
                )
                if properly_indented:
                    score += 0.49
            # Max = 0.1 + 0.4 + 0.49 = 0.99

        elif self.current_task_id == "efficiency-boost":
            for_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.For)]
            # BUG FIX #4b: list comprehension fix produced 0 for_nodes → score = 0.01 (wrong!)
            # A comprehension-based solution is also valid O(n) — check for nested for loops instead
            nested = False
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    # Check if there's another For directly inside
                    for child in ast.walk(node):
                        if child is not node and isinstance(child, ast.For):
                            nested = True
                            break
            if not nested:
                # No nested loops → O(n) solution (works for both for-loop and comprehension fixes)
                score = 0.99
            elif len(for_nodes) >= 2:
                score = 0.5  # Still nested

        elif self.current_task_id == "security-audit":
            has_fstring = any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree))
            # BUG FIX #4c: uses_params checked for ":" which matched "def get_user(db, user_id):"
            # Now we check more specifically for parameterized query patterns
            uses_params = "?" in self.code or "%s" in self.code or (
                # Match :param style only inside string literals
                any(
                    isinstance(node, ast.Constant) and isinstance(node.value, str) and ":" in node.value
                    for node in ast.walk(tree)
                )
            )

            if not has_fstring and uses_params:
                score = 0.99
            elif not has_fstring:
                score = 0.5
            else:
                score = 0.1

        return float(round(min(max(score, 0.1), 0.99), 2))
