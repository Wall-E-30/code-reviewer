import os
import ast
from typing import Tuple, Dict, Any
from openenv.core.env_server import Environment
from models import Action, Observation, Reward

class CodeReviewEnv(Environment):
    def __init__(self):
        super().__init__()
        self.current_task_id = None
        self.code = ""
        self.step_count = 0
        self.max_steps = 5 

    def load_custom_code(self, code: str, task_type: str):
        """Allows the user to paste custom code for evaluation."""
        self.code = code
        self.current_task_id = task_type
        self.step_count = 0
        return self._get_observation()

    def reset(self, task_id: str = "style-cleanup") -> Observation:
        self.current_task_id = task_id
        self.step_count = 0
        file_map = {
            "style-cleanup": "data/style.py",
            "efficiency-boost": "data/logic.py",
            "security-audit": "data/security.py"
        }
        file_path = file_map.get(task_id, "data/style.py")
        with open(file_path, "r") as f:
            self.code = f.read()
        return self._get_observation()

    def step(self, action: Action) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        self.step_count += 1
        reward_val = 0.0
        done = False

        if action.action_type == "apply_fix":
            self.code = action.content
            reward_val = self._calculate_reward() 
        elif action.action_type == "submit":
            reward_val = self._calculate_reward()
            done = True

        if self.step_count >= self.max_steps:
            done = True

        return self._get_observation(), reward_val, done, {}

    def state(self) -> Dict[str, Any]:
        """
        REQUIRED: Returns the current state of the environment.
        This fixes the TypeError you encountered.
        """
        return {
            "code": self.code,
            "task": self.current_task_id,
            "step_count": self.step_count
        }

    def _calculate_reward(self) -> float:
        score = 0.0
        try:
            tree = ast.parse(self.code)
        except SyntaxError:
            return -0.5  # Heavy penalty for code that won't even run

        if self.current_task_id == "style-cleanup":
            # 0.5 for removing the unused import
            if "import sys" not in self.code: score += 0.5
            # 0.5 for fixing the indentation of the print statement
            if "    print(" in self.code: score += 0.5
            
        elif self.current_task_id == "efficiency-boost":
            # Use AST to count For loops. O(n^2) has 2+, O(n) has 1.
            for_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.For)]
            if len(for_nodes) == 1:
                score = 1.0
            elif len(for_nodes) == 0:
                score = 0.0 # They deleted the loops entirely!
            else:
                score = 0.2 # Still O(n^2)
                
        elif self.current_task_id == "security-audit":
            # 1. Check if they removed the f-string (JoinedStr)
            has_fstring = any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree))
            
            # 2. Check if they are using SQL parameters (?, %s, or :val)
            uses_params = any(x in self.code for x in ["?", "%s", ":"])

            if not has_fstring and uses_params:
                score = 1.0
            elif not has_fstring:
                score = 0.5  # Fixed the f-string, but still not using best practices
            else:
                score = 0.0  # Still vulnerable

        return float(min(max(score, -1.0), 1.0))
    
    def _get_observation(self) -> Observation:
        return Observation(
            file_name=f"{self.current_task_id}.py",
            code_content=self.code,
            diff="Buffer updated.",
            linter_report=self._mock_linter(),
            current_task=self.current_task_id
        )

    def _mock_linter(self):
        errors = []
        if "import sys" in self.code and self.current_task_id == "style-cleanup":
            errors.append("L001: Unused import 'sys' detected.")
        return errors