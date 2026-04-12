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
        
        # CRITICAL FIX 1: True Marginal Reward. 
        # Prevents sum(rewards) from exceeding 1.0 if the judge takes 100 empty steps.
        reward = float(round(max(0.0, current_score - self.max_score_seen), 2))
        
        self.max_score_seen = max(self.max_score_seen, current_score)
        done = self.step_count >= self.max_steps or self.max_score_seen >= 0.99
        
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
        score = 0.01
        try:
            tree = ast.parse(self.code)
        except SyntaxError:
            # CRITICAL FIX 2: Return instantly to avoid UnboundLocalError crashes
            return 0.01  
            
        # Safety Check: If the AI deleted the whole function, it fails.
        has_func = any(isinstance(n, ast.FunctionDef) for n in ast.walk(tree))
        if not has_func:
            return 0.01

        if self.current_task_id == "style-cleanup":
            if "import sys" not in self.code:
                score += 0.49
            lines = self.code.splitlines()
            properly_indented = all(
                line.startswith("    ") or not line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("def ") and not line.strip().startswith("import") and not line.strip().startswith("#")
            )
            if properly_indented:
                score += 0.49

        elif self.current_task_id == "efficiency-boost":
            for_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.For)]
            nested = False
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    for child in ast.walk(node):
                        if child is not node and isinstance(child, ast.For):
                            nested = True
                            break
            if not nested:
                score = 0.99
            elif len(for_nodes) >= 2:
                score = 0.5

        elif self.current_task_id == "security-audit":
            has_fstring = any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree))
            uses_params = "?" in self.code or "%s" in self.code or (
                any(isinstance(node, ast.Constant) and isinstance(node.value, str) and ":" in node.value for node in ast.walk(tree))
            )
            if not has_fstring and uses_params:
                score = 0.99
            elif not has_fstring:
                score = 0.5
            else:
                score = 0.1

        return float(round(min(max(score, 0.01), 0.99), 2))
