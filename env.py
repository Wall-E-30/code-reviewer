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
        self.max_score_seen = 0.01

    def reset(self, task_id: str = "style-cleanup") -> Observation:
        if task_id not in TASKS:
            task_id = "style-cleanup"
        self.current_task_id = task_id
        self.code = TASKS[task_id]["code"]
        self.original_code = self.code
        self.step_count = 0
        self.max_score_seen = 0.01
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

        reward = self._calculate_reward()
        self.max_score_seen = max(self.max_score_seen, reward)
        
        # End the episode if the max steps are reached or the fix is perfect
        done = self.step_count >= self.max_steps or reward >= 0.89
        
        return self._get_observation(), reward, done, {"total_score": self.max_score_seen}

    def load_custom_code(self, code: str, task_type: str) -> Observation:
        self.code = code
        self.original_code = code
        self.current_task_id = task_type
        self.step_count = 0
        self.max_score_seen = 0.01
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
        """AST-Based Grader: Returns a score strictly between [0.01 and 0.9]"""
        score = 0.01 
        
        try:
            tree = ast.parse(self.code)
        except SyntaxError:
            return 0.01

        if self.current_task_id == "style-cleanup":
            # 1. Check for unused import 'sys'
            has_sys_import = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == 'sys':
                            has_sys_import = True
                elif isinstance(node, ast.ImportFrom) and node.module == 'sys':
                    has_sys_import = True
            
            if not has_sys_import:
                score += 0.45
            
            # 2. Check for indentation of statements (AST col_offset)
            is_indented = True
            if "def " in self.code:
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if not node.body:
                            is_indented = False
                        for stmt in node.body:
                            if stmt.col_offset <= node.col_offset:
                                is_indented = False
                if is_indented:
                    score += 0.45
                
        elif self.current_task_id == "efficiency-boost":
            all_loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While))]
            
            # Detect nested loops
            is_nested = False
            for node in all_loops:
                for child in ast.walk(node):
                    if child is node: continue
                    if isinstance(child, (ast.For, ast.While)):
                        is_nested = True
                        break
            
            # Detect efficient lookups/modern Python
            uses_efficient_lookup = any(isinstance(node, ast.Call) and getattr(node.func, 'id', '') in ['set', 'dict'] for node in ast.walk(tree))
            uses_comp = any(isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)) for node in ast.walk(tree))

            if is_nested:
                score = 0.5
            elif uses_efficient_lookup or uses_comp or len(all_loops) == 1:
                score = 0.9
            elif len(all_loops) == 0:
                score = 0.01
            else:
                score = 0.3
                
        elif self.current_task_id == "security-audit":
            vulnerable = False
            found_execute = False
            for node in ast.walk(tree):
                # Search for .execute() calls
                if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'execute':
                    found_execute = True
                    if node.args:
                        query_arg = node.args[0]
                        if isinstance(query_arg, ast.JoinedStr):
                            vulnerable = True
                        if isinstance(query_arg, ast.BinOp) and isinstance(query_arg.op, ast.Mod):
                            vulnerable = True
                        if len(node.args) < 2 and not vulnerable:
                            if any(isinstance(n, ast.Name) for n in ast.walk(query_arg)):
                                vulnerable = True

            if found_execute and not vulnerable:
                score = 0.9
            elif found_execute and vulnerable:
                score = 0.1
            else:
                score = 0.01

        # Ensure 2nd decimal precision
        final_score = round(float(max(0.01, min(0.9, score))), 2)
        return final_score
