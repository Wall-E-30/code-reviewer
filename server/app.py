import sys
import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import gradio as gr

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env import CodeReviewEnv
from models import Action, Reward
from inference import build_ui

app = FastAPI()
code_env = CodeReviewEnv()


# BUG FIX: /reset must accept a task_id so the validator can test each task individually.
# Previously it always reset to "style-cleanup" with no way to select a task.
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

    # UPDATED: Returns primitive float as required by Phase 2 guidelines
    # to ensure the validator's regex parser handles the value correctly.
    return {
        "observation": obs,
        "reward": float(reward),
        "done": bool(done),
        "info": info
    }


@app.get("/state")
async def state_endpoint():
    return code_env.state()


# Mount the Gradio UI for human judges
demo = build_ui()
app = gr.mount_gradio_app(app, demo, path="/")


def main():
    """Entry point required by the OpenEnv validator for multi-mode deployment."""
    print("Starting Aion Code Reviewer Server...")
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
