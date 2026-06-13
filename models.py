from pydantic import BaseModel, Field
from typing import Optional, List

class Action(BaseModel):
    """
    Representation of an agent action in the Code Reviewer environment.
    An agent can apply a fix, make a comment, or submit the code review.
    """
    action_type: str = Field(..., description="Must be one of: 'apply_fix', 'comment', or 'submit'")
    line_number: Optional[int] = Field(None, description="Optional target line number for the action")
    content: str = Field(..., description="The code snippet to replace, comment text, or full file content")
    session_id: Optional[str] = Field("default", description="Session identifier for concurrent environment isolation")

class Observation(BaseModel):
    """
    Representation of the environment state observed by the agent at each step.
    """
    file_name: str = Field(..., description="Name of the file currently being reviewed")
    code_content: str = Field(..., description="The current source code under review")
    diff: str = Field(..., description="The diff showing changes made so far in the current session")
    linter_report: List[str] = Field(..., description="Simulated/generated linter and compiler messages")
    current_task: str = Field(..., description="The active task ID (e.g. 'style-cleanup')")

class Reward(BaseModel):
    """
    Scalar reward feedback conforming to the strict (0.0, 1.0) OpenEnv validator requirements.
    """
    value: float = Field(..., gt=0.0, lt=1.0, description="Quality score of the current code state")
    comment: str = Field(..., description="Detailed feedback explaining the code quality score")

class OptimizeResponse(BaseModel):
    """
    Response schema for the API optimization endpoints.
    """
    initial_score: float = Field(..., description="Quality score of the code before optimization")
    final_score: float = Field(..., description="Quality score of the code after optimization")
    fixed_code: str = Field(..., description="Optimized source code")
    perf_gain: str = Field(..., description="Estimated performance improvement percentage")
    mem_reduction: str = Field(..., description="Estimated memory savings")
    recommendation: str = Field(..., description="AI insight and summary of changes made")
    diff_data: Optional[List[dict]] = None
    request_id: Optional[str] = None
