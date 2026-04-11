from pydantic import BaseModel, Field
from typing import Optional, List

class Action(BaseModel):
    # The agent chooses what to do
    action_type: str = Field(..., description="Values: 'comment', 'apply_fix', or 'submit'")
    line_number: Optional[int] = Field(None, description="The line number to act upon")
    content: str = Field(..., description="The text of the comment or the code to replace")

class Observation(BaseModel):
    # What the agent 'sees' every turn
    file_name: str
    code_content: str
    diff: str
    linter_report: List[str]
    current_task: str

class Reward(BaseModel):
    # The score given back to the agent
    value: float = Field(..., gt=0.0, lt=1.0)
    comment: str