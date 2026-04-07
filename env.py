import os
from typing import Tuple, Dict, Any

# Updated imports based on your library's structure
from openenv.core.env_server import Environment
from models import Action, Observation, Reward

# Change the class name from CodeReviewEnv(OpenEnv) to CodeReviewEnv(Environment)
class CodeReviewEnv(Environment):
    def __init__(self):
        # In the new version, spec loading is often handled via the CLI 
        # or you can just initialize the base class directly.
        super().__init__() 
        self.current_task_id = None
        self.code = ""
        self.step_count = 0
        self.max_steps = 5 

    # ... the rest of your methods (reset, step, etc.) remain the same ...

    def reset(self, task_id: str = "style-cleanup") -> Observation:
        """Starts a new task session."""
        self.current_task_id = task_id
        self.step_count = 0
        
        # Load the buggy code from our data folder
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
        """Handles the agent's move and returns the reward."""
        self.step_count += 1
        reward_val = 0.0
        done = False

        # Logic: If the agent provides a fix, update our internal 'code' state
        if action.action_type == "apply_fix":
            self.code = action.content
            reward_val = self._calculate_reward() # Partial progress
        
        elif action.action_type == "submit":
            reward_val = self._calculate_reward()
            done = True

        if self.step_count >= self.max_steps:
            done = True

        return self._get_observation(), reward_val, done, {}

    def _get_observation(self) -> Observation:
        """Returns what the agent sees right now."""
        return Observation(
            file_name=f"{self.current_task_id}.py",
            code_content=self.code,
            diff="Changes applied to buffer.",
            linter_report=self._mock_linter(),
            current_task=self.current_task_id
        )

    def _mock_linter(self):
        """A simple linter to guide the agent."""
        errors = []
        if "import sys" in self.code and self.current_task_id == "style-cleanup":
            errors.append("L001: Unused import 'sys' detected.")
        if "f\"SELECT" in self.code and self.current_task_id == "security-audit":
            errors.append("S001: SQL Injection vulnerability detected.")
        return errors

    def _calculate_reward(self) -> float:
        """
        CRITICAL: Deterministic grading logic.
        This is where 25% of your score comes from.
        """
        score = 0.0
        
        if self.current_task_id == "style-cleanup":
            # Reward for fixing indentation AND removing the unused import
            if "import sys" not in self.code: score += 0.5
            if "    print(\"Indentation" in self.code: score += 0.5
            
        elif self.current_task_id == "security-audit":
            # Reward for using parameterized queries instead of f-strings
            if "execute(query)" not in self.code and ("?" in self.code or "," in self.code):
                score = 1.0
                
        elif self.current_task_id == "efficiency-boost":
            # Reward for getting rid of the nested loop
            if self.code.count("for ") == 1: # Suggests they used a set or dict
                score = 1.0

        return min(max(score, 0.0), 1.0) # Ensure it stays in [0, 1]

    def state(self) -> Dict[str, Any]:
        return {"code": self.code, "task": self.current_task_id}