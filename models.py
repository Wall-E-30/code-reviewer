from pydantic import BaseModel, Field
from typing import Optional, List


class Action(BaseModel):
    # The agent chooses what to do
    action_type: str = Field(..., description="Values: 'comment', 'apply_fix', or 'submit'")
    line_number: Optional[int] = Field(None, description="The line number to act upon")
    content: str = Field(..., description="The text of the comment or the code to replace")


# BUG FIX: There were TWO conflicting Observation definitions:
#   - models.py had: file_name, code_content, diff, linter_report (List[str]), current_task
#   - env.py had:    current_task, code_content, linter_report (str)  ← missing fields, wrong type
# env.py now imports and uses THIS single Observation so the /reset and /step
# API responses match what the validator expects.
class Observation(BaseModel):
    # What the agent 'sees' every turn
    file_name: str
    code_content: str
    diff: str
    linter_report: List[str]
    current_task: str


class Reward(BaseModel):
    # The score given back to the agent
    # gt=0.0 and lt=1.0 enforce the strict (0, 1) range required by the validator
    value: float = Field(..., gt=0.0, lt=1.0)
    comment: str
