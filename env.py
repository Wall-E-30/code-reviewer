import ast
from pydantic import BaseModel

# --- DATA: The Baseline Tasks ---
TASKS = {
    "style-cleanup": {
        "code": "import sys\ndef hello_world():\nprint('Hello')\n",
        "linter": "Unused import 'sys' detected. Indentation error on print statement."
    },
    "efficiency-boost": {
        "code": "def find_duplicates(arr1, arr2):\n    dupes = []\n    for i in arr1:\n        for j in arr2:\n            if i == j:\n                dupes.append(i)\n    return dupes\n",
        "linter": "Nested loops detected (O(n^2)). Refactor to use a dictionary or set for O(n) lookups."
    },
    "security-audit": {
        "code": "def get_user(db, user_id):\n    query = f'SELECT * FROM users WHERE id = {user_id}'\n    db.execute(query)\n",
        "linter": "SQL Injection vulnerability. Remove f-string and use parameterized queries (?, %s, or :)."
    }
}

# --- OBSERVATION MODEL ---
# Defines what the AI sees at each step
class Observation(BaseModel):
    current_task: str
    code_content: str
    linter_report: str

class CodeReviewEnv:
    def __init__(self):
        self.current_task_id = "style-cleanup"
        self.code = TASKS[self.current_task_id]["code"]
        self.step_count = 0
        self.max_steps = 5

    def reset(self, task_id: str = "style-cleanup") -> Observation:
        """Required by OpenEnv: Resets the environment for a new episode."""
        # Fallback to style-cleanup if an unknown task is requested
        if task_id not in TASKS:
            task_id = "style-cleanup"
            
        self.current_task_id = task_id
        self.code = TASKS[task_id]["code"]
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
        
        # Apply the AI's code fix
        if action.action_type == "apply_fix" and action.content:
            self.code = action.content
        
        # Grade the new code
        reward = self._calculate_reward()
        
        # FIX: Align 'done' threshold with the max possible reward (0.9)
        done = self.step_count >= self.max_steps or reward >= 0.89
        
        # Return observation, reward, done, info
        return self._get_observation(), reward, done, {}

    def load_custom_code(self, code: str, task_type: str) -> Observation:
        """Custom tool for the Gradio Dashboard to allow human testing."""
        self.code = code
        self.current_task_id = task_type
        self.step_count = 0
        return self._get_observation()

    def _get_observation(self) -> Observation:
        """Helper to package the current state into the Pydantic observation."""
        linter = TASKS.get(self.current_task_id, {}).get("linter", "Custom code analysis.")
        return Observation(
            current_task=self.current_task_id,
            code_content=self.code,
            linter_report=linter
        )

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
            
            # 2. Check for indentation of the print statement
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

        # NEW: Ensure 2nd decimal precision
        final_score = round(float(max(0.01, min(0.9, score))), 2)
        return final_score
