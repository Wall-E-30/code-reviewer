import os
import json
import asyncio
from openai import OpenAI
from env import CodeReviewEnv
from models import Action

API_KEY = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
print("DEBUG: Here are the environment variables the Space can see:")
print(list(os.environ.keys()))
if not API_KEY:
    print("❌ ERROR: HF_TOKEN not found.")
    exit(1)

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

def log_start(task: str, model: str):
    print(f"[START] task={task} env=aion-code-reviewer model={model}", flush=True)

def log_step(step: int, action_type: str, reward: float, done: bool, error: str = "null"):
    done_str = str(done).lower()
    print(f"[STEP] step={step} action={action_type} reward={reward:.2f} done={done_str} error={error}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: list):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

async def run_inference():
    env = CodeReviewEnv()
    for task_id in ["style-cleanup", "efficiency-boost", "security-audit"]:
        obs = env.reset(task_id=task_id)
        log_start(task_id, MODEL_NAME)
        step_idx, total_rewards, is_success = 1, [], False
        
        while step_idx <= 5:
            # 1. Enhanced Prompt: Clearer instructions on when to STOP
            prompt = f"""
            You are an expert Code Reviewer.
            CURRENT TASK: {obs.current_task}
            LINTER ERRORS: {obs.linter_report}
            CODE TO REVIEW:
            \"\"\"
            {obs.code_content}
            \"\"\"

            INSTRUCTIONS:
            1. If there are errors or inefficiencies, use "apply_fix" and provide the FULL corrected code.
            2. IF THE ERRORS ARE GONE and the code is optimal, you MUST use "submit" to end the session.
            3. Response MUST be a single JSON object. Use double quotes for keys.
            
            REQUIRED JSON FORMAT:
            {{
                "action_type": "apply_fix" or "submit",
                "content": "the entire code string here",
                "line_number": 0
            }}
            """
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "system", "content": "Respond ONLY with valid JSON."}, {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                if not content: raise ValueError("Empty response")
                
                agent_action = Action(**json.loads(content))
                obs, reward, done, _ = env.step(agent_action)
                if reward >= 1.0:
                    done = True
    
                total_rewards.append(reward)
                log_step(step_idx, agent_action.action_type, reward, done)
                
                if done:
                    is_success = reward >= 0.8
                    break
                step_idx += 1
            except Exception as e:
                log_step(step_idx, "error", 0.0, True, error=str(e))
                break
        log_end(is_success, step_idx, max(total_rewards) if total_rewards else 0.0, total_rewards)

if __name__ == "__main__":
    asyncio.run(run_inference())

    import http.server
    import socketserver
    
    PORT = 7860
    Handler = http.server.SimpleHTTPRequestHandler
    
    print(f"All tasks done! Starting dummy server on port {PORT} to keep the Space alive...")
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()