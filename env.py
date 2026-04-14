import ast
from pydantic import BaseModel
from typing import List

# --- DATA: The Baseline Tasks ---
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
        self.max_score_seen = 0.0

    def reset(self, task_id: str = "style-cleanup") -> Observation:
        if task_id not in TASKS:
            task_id = "style-cleanup"
        self.current_task_id = task_id
        self.code = TASKS[task_id]["code"]
        self.original_code = self.code
        self.step_count = 0
        self.max_score_seen = 0.0
        return self._get_observation()

    def state(self) -> dict:
        return {
            "task_id": self.current_task_id,
            "code_content": self.code,
            "steps_taken": self.step_count,
            "total_score": self.max_score_seen
        }

    def step(self, action):
        self.step_count += 1
        if action.action_type == "apply_fix" and action.content:
            self.code = action.content

        current_score = self._calculate_reward()
        
        # End the episode if the max steps are reached or the fix is perfect (0.99)
        done = self.step_count >= self.max_steps or reward >= 0.98
        
        return self._get_observation(), reward, done, {"total_score": self.max_score_seen}

    def load_custom_code(self, code: str, task_type: str) -> Observation:
        self.code = code
        self.original_code = code
        self.current_task_id = task_type
        self.step_count = 0
        return self._get_observation()

    def _get_observation(self) -> Observation:
        task = TASKS.get(self.current_task_id, {})
        linter = task.get("linter", ["Custom code analysis."])
        file_name = task.get("file_name", "custom.py")
        diff = self._build_diff(self.original_code, self.code)
        return Observation(file_name=file_name, code_content=self.code, diff=diff, linter_report=linter, current_task=self.current_task_id)

    def _build_diff(self, original: str, current: str) -> str:
        if original == current: return ""
        orig_lines, curr_lines = original.splitlines(), current.splitlines()
        diff_lines = []
        for i, (o, c) in enumerate(zip(orig_lines, curr_lines)):
            if o != c:
                diff_lines.extend([f"- {o}", f"+ {c}"])
        if len(curr_lines) > len(orig_lines):
            diff_lines.extend([f"+ {line}" for line in curr_lines[len(orig_lines):]])
        elif len(orig_lines) > len(curr_lines):
            diff_lines.extend([f"- {line}" for line in orig_lines[len(curr_lines):]])
        return "\n".join(diff_lines)

    def _calculate_reward(self) -> float:
        """AST-Based Grader: Returns a score strictly between (0.01 and 0.9)"""
        # Start at 0.01 instead of 0.0 to satisfy the strict > 0 rule
        score = 0.01 
        
        try:
            tree = ast.parse(self.code)
        except SyntaxError:
            return 0.01  # Syntax error gets the absolute minimum valid score

        if self.current_task_id == "style-cleanup":
            # Max score will be 0.01 + 0.45 + 0.45 = 0.91
            if "import sys" not in self.code: 
                score += 0.45
            if "    print(" in self.code: 
                score += 0.45
                
        elif self.current_task_id == "efficiency-boost":
            for_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.For)]
            if len(for_nodes) == 1:
                score = 0.9  # Perfect success
            elif len(for_nodes) == 0:
                score = 0.01  # Deleted the loops entirely
            else:
                score = 0.5  # Partial progress (still nested)
                
        elif self.current_task_id == "security-audit":
            has_fstring = any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree))
            uses_params = any(x in self.code for x in ["?", "%s", ":"])

            if not has_fstring and uses_params:
                score = 0.9  # Perfect success
            elif not has_fstring:
                score = 0.5  # Partial fix (f-string gone, but no parameters)
            else:
                score = 0.01  # Still vulnerable

        # This forces the score to never drop below 0.01 and never go above 0.9
        return float(max(0.01, min(0.9, score)))
