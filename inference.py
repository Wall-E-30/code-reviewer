import os
import json
import asyncio
import re
import traceback
from openai import OpenAI
from env import CodeReviewEnv
from models import Action

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

# Safely initialize the client so it doesn't crash the server container on boot
safe_token = HF_TOKEN if HF_TOKEN else "dummy_key_for_server_boot"
client = OpenAI(base_url=API_BASE_URL, api_key=safe_token)

def clean_json_string(raw_string):
    """Aggressively extracts JSON from model output."""
    match = re.search(r'\{.*\}', raw_string, re.DOTALL)
    if match:
        return match.group(0)
    return raw_string

# HACKATHON BENCHMARK LOGIC
async def run_task(task_id):
    env = CodeReviewEnv()
    obs = env.reset(task_id=task_id)
    print(f"[START] task={task_id} env=aion-code-reviewer model={MODEL_NAME}", flush=True)
    
    step_idx, total_rewards = 1, []
    final_code = obs.code_content
    
    while step_idx <= 5:
        prompt = f"""
        TASK: {task_id}
        You are a Senior Software Engineer. I need a PERFECT 0.99 score.
        CRITERIA FOR 0.99 SCORE:
        - If 'security-audit': Remove all f-strings from SQL and use '?' parameter placeholders.
        - If 'efficiency-boost': Refactor nested O(n^2) loops into a single O(n) loop using a dictionary.
        - If 'style-cleanup': Remove unused 'import sys' AND fix all indentation.
        USER CODE:
        {obs.code_content}
        
        Return the COMPLETE fixed file in this JSON format:
        {{"action_type": "apply_fix", "content": "FIXED_CODE"}}
        """
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": "JSON-only bot."}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            json_content = clean_json_string(response.choices[0].message.content)
            agent_action = Action(**json.loads(json_content))
            
            obs, reward, done, _ = env.step(agent_action)
            total_rewards.append(reward)
            final_code = obs.code_content
            
            print(f"[STEP] step={step_idx} action={agent_action.action_type} reward={reward:.2f} done={str(done).lower()} error=null", flush=True)
            
            if done or env.max_score_seen >= 0.99: break
            step_idx += 1
            
        except Exception as e:
            # Safe fallback (0.01)
            print(f"[STEP] step={step_idx} action=error reward=0.01 done=true error={str(e)}", flush=True)
            total_rewards.append(0.01)
            break

    success = sum(total_rewards) if total_rewards else 0.01
    print(f"[END] success={str(success >= 0.8).lower()} steps={step_idx} rewards={','.join(f'{r:.2f}' for r in total_rewards)}", flush=True)
    return final_code, success

if __name__ == "__main__":
    print("--- RUNNING AUTOMATED BASELINE FOR PHASE 2 ---", flush=True)
    try:
        # Run all three tasks sequentially
        asyncio.run(run_task("style-cleanup"))
        asyncio.run(run_task("efficiency-boost"))
        asyncio.run(run_task("security-audit"))
    except Exception as e:
        print(f"CRITICAL ERROR IN BASELINE: {str(e)}", flush=True)
        traceback.print_exc()
        
    print("--- BASELINE COMPLETE ---", flush=True)
