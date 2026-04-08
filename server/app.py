import sys
import os
from fastapi import FastAPI
import gradio as gr

# Ensure the system can find your other files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env import CodeReviewEnv
from models import Action
from inference import build_ui

# 1. Initialize the FastAPI server and your OpenEnv Environment
app = FastAPI()
code_env = CodeReviewEnv()

# 2. Mandatory Endpoints for the Automated Judge (Phase 1 checks)
@app.post("/reset")
async def reset_endpoint():
    obs = code_env.reset()
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

# 3. Mount the Gradio UI for the Human Judges
demo = build_ui()
app = gr.mount_gradio_app(app, demo, path="/")