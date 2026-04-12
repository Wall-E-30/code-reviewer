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
        
        # End the episode if the max steps are reached or the fix is perfect (0.99)
        done = self.step_count >= self.max_steps or reward >= 0.88
        
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
                score = 0.89  # Perfect success
            elif len(for_nodes) == 0:
                score = 0.01  # Deleted the loops entirely
            else:
                score = 0.5  # Partial progress (still nested)
                
        elif self.current_task_id == "security-audit":
            has_fstring = any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree))
            uses_params = any(x in self.code for x in ["?", "%s", ":"])

            if not has_fstring and uses_params:
                score = 0.89  # Perfect success
            elif not has_fstring:
                score = 0.5  # Partial fix (f-string gone, but no parameters)
            else:
                score = 0.01  # Still vulnerable

        # This forces the score to never drop below 0.01 and never go above 0.9
        return float(max(0.01, min(0.89, score)))