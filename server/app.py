import sys
import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

# Ensure the system can find env.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env import CodeReviewEnv
from models import Action

app = FastAPI()
code_env = CodeReviewEnv()

class ResetRequest(BaseModel):
    task_id: Optional[str] = "style-cleanup"

@app.post("/reset")
async def reset_endpoint(request: ResetRequest = None):
    task_id = (request.task_id if request else None) or "style-cleanup"
    obs = code_env.reset(task_id=task_id)
    return obs

@app.post("/step")
async def step_endpoint(action: Action):
    obs, reward, done, info = code_env.step(action)
    return {
        "observation": obs,
        "reward": float(reward),
        "done": bool(done),
        "info": info
    }

@app.get("/state")
async def state_endpoint():
    return code_env.state()

def main():
    """Entry point required by the OpenEnv validator for multi-mode deployment."""
    print("Starting Aion Code Reviewer Headless API Server...")
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
