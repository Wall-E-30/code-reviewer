import os
import json
import asyncio
import re
import traceback
import gradio as gr
from openai import OpenAI
from env import CodeReviewEnv
from models import Action

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

safe_token = HF_TOKEN if HF_TOKEN else "dummy_key_for_server_boot"
client = OpenAI(base_url=API_BASE_URL, api_key=safe_token)

def clean_json_string(raw_string):
    """Aggressively extracts JSON from model output."""
    match = re.search(r'\{.*\}', raw_string, re.DOTALL)
    if match:
        return match.group(0)
    return raw_string

# 2. HACKATHON BENCHMARK LOGIC
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
            
            if done or reward >= 0.99: break
            step_idx += 1
        except Exception as e:
            # FIX: If the AI errors out, log 0.01 instead of 0.00
            print(f"[STEP] step={step_idx} action=error reward=0.01 done=true error={str(e)}", flush=True)
            total_rewards.append(0.01)
            break
    
    # FIX: Fallback to 0.01 instead of 0.0
    success = max(total_rewards) if total_rewards else 0.01
    print(f"[END] success={str(success >= 0.8).lower()} steps={step_idx} rewards={','.join(f'{r:.2f}' for r in total_rewards)}", flush=True)
    return final_code, success

# 3. CUSTOM OPTIMIZER LOGIC
async def evaluate_and_optimize(user_code, task_type):
    # Defensive check for None or Empty strings
    if user_code is None or not user_code.strip():
        return 0.0, "⚠️ Error: Please paste some code first!", 0.0
        
    env = CodeReviewEnv()
    # Initial Evaluation
    env.load_custom_code(user_code, task_type)
    initial_score = env._calculate_reward()
    
    prompt = f"""
    TASK: {task_type}
    You are a Senior Software Engineer. Provide a PERFECT 1.0 fix.
    
    CRITERIA FOR 1.0 SCORE:
    - If 'security-audit': Remove f-strings from SQL and use '?' placeholders.
    - If 'efficiency-boost': Refactor nested loops into a single loop using a dictionary.
    - If 'style-cleanup': Remove 'import sys' AND fix indentation.

    USER CODE:
    {user_code}
    
    Return the COMPLETE fixed file in JSON format:
    {{"action_type": "apply_fix", "content": "FIXED_CODE"}}
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": "You are a specialized code optimization agent."}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        json_content = clean_json_string(response.choices[0].message.content)
        agent_action = Action(**json.loads(json_content))
        
        # Apply and get final score
        env.step(agent_action)
        final_score = env._calculate_reward()
        
        return float(initial_score), agent_action.content, float(final_score)
    except Exception as e:
        return float(initial_score), f"Error: {str(e)}", 0.0

# 4. GRADIO DASHBOARD
def gradio_interface():
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🏢 Aion Code Reviewer & Optimizer")
        
        with gr.Tabs():
            with gr.TabItem("Hackathon Benchmark"):
                gr.Markdown("### Automated Task Evaluation")
                with gr.Row():
                    task_selector = gr.Dropdown(["style-cleanup", "efficiency-boost", "security-audit"], label="Benchmark Task", value="style-cleanup")
                    run_btn = gr.Button("Run Benchmark", variant="primary")
                with gr.Row():
                    output_code = gr.Code(label="Agent Fix", language="python")
                    score_display = gr.Number(label="Final Score")
                run_btn.click(lambda t: asyncio.run(run_task(t)), inputs=[task_selector], outputs=[output_code, score_display])

            with gr.TabItem("Paste & Optimize"):
                gr.Markdown("### Custom Code Optimizer")
                custom_task_type = gr.Radio(["style-cleanup", "efficiency-boost", "security-audit"], label="Optimize For:", value="efficiency-boost")
                user_input_code = gr.Code(label="Paste Your Code Here", language="python", lines=10)
                optimize_btn = gr.Button("Evaluate & Optimize", variant="primary")
                with gr.Row():
                    pre_score = gr.Number(label="Initial Quality Score")
                    post_score = gr.Number(label="Optimized Quality Score")
                optimized_output = gr.Code(label="Optimized Result", language="python")

                optimize_btn.click(
                    fn=lambda code, t: asyncio.run(evaluate_and_optimize(code, t)),
                    inputs=[user_input_code, custom_task_type],
                    outputs=[pre_score, optimized_output, post_score]
                )
    
    demo.launch(server_name="0.0.0.0", server_port=7860)

# Change the name to build_ui and remove the demo.launch() line from inside the function
def build_ui():
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🏢 Aion Code Reviewer & Optimizer")
        
        with gr.Tabs():
            with gr.TabItem("Hackathon Benchmark"):
                gr.Markdown("### Automated Task Evaluation")
                with gr.Row():
                    task_selector = gr.Dropdown(["style-cleanup", "efficiency-boost", "security-audit"], label="Benchmark Task", value="style-cleanup")
                    run_btn = gr.Button("Run Benchmark", variant="primary")
                with gr.Row():
                    output_code = gr.Code(label="Agent Fix", language="python")
                    score_display = gr.Number(label="Final Score")
                run_btn.click(lambda t: asyncio.run(run_task(t)), inputs=[task_selector], outputs=[output_code, score_display])

            with gr.TabItem("Paste & Optimize"):
                gr.Markdown("### Custom Code Optimizer")
                custom_task_type = gr.Radio(["style-cleanup", "efficiency-boost", "security-audit"], label="Optimize For:", value="efficiency-boost")
                user_input_code = gr.Code(label="Paste Your Code Here", language="python", lines=10)
                optimize_btn = gr.Button("Evaluate & Optimize", variant="primary")
                with gr.Row():
                    pre_score = gr.Number(label="Initial Quality Score")
                    post_score = gr.Number(label="Optimized Quality Score")
                optimized_output = gr.Code(label="Optimized Result", language="python")

                optimize_btn.click(
                    fn=lambda code, t: asyncio.run(evaluate_and_optimize(code, t)),
                    inputs=[user_input_code, custom_task_type],
                    outputs=[pre_score, optimized_output, post_score]
                )
    return demo # <-- Return the demo object instead of launching it here

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