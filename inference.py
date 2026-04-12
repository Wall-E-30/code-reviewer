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


async def run_task(task_id):
    env = CodeReviewEnv()
    obs = env.reset(task_id=task_id)
    print(f"[START] task={task_id} env=aion-code-reviewer model={MODEL_NAME}", flush=True)

    step_idx, total_rewards = 1, []
    final_code = obs.code_content

    while step_idx <= 5:
        prompt = f"""
        TASK: {task_id}
        You are a Senior Software Engineer. Your goal is to fix the code correctly.

        CRITERIA FOR A PERFECT SCORE:
        - If 'security-audit': Remove ALL f-strings from SQL queries and use '?' parameter placeholders.
          Example: cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        - If 'efficiency-boost': Refactor the nested O(n^2) for loops into a SINGLE for loop using a set.
          IMPORTANT: Do NOT use a list comprehension — use an explicit for loop with a set lookup.
          Example:
            set_b = set(arr2)
            dupes = []
            for i in arr1:
                if i in set_b:
                    dupes.append(i)
        - If 'style-cleanup': Remove the unused 'import sys' line AND fix ALL indentation to 4 spaces.

        CURRENT CODE:
        {obs.code_content}

        LINTER WARNINGS:
        {obs.linter_report}

        Return the COMPLETE fixed file in this JSON format:
        {{"action_type": "apply_fix", "content": "FIXED_CODE_HERE"}}
        """
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a JSON-only code fix bot. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            json_content = clean_json_string(response.choices[0].message.content)
            agent_action = Action(**json.loads(json_content))
            obs, reward, done, _ = env.step(agent_action)

            total_rewards.append(reward)
            final_code = obs.code_content

            print(f"[STEP] step={step_idx} action={agent_action.action_type} reward={reward} done={str(done).lower()} error=null", flush=True)

            # BUG FIX: break threshold updated from 0.88 to match the new max reward of 0.89
            # Previously used 0.89 which matched perfectly, but done in env was 0.98 (unreachable).
            # Now env.done triggers at reward >= 0.88, so `done` will be True here as well.
            if done or reward >= 0.88:
                break
            step_idx += 1

        except Exception as e:
            print(f"[STEP] step={step_idx} action=error reward=0.01 done=true error={str(e)}", flush=True)
            total_rewards.append(0.01)
            break

    success = max(total_rewards) if total_rewards else 0.01
    # BUG FIX: was printing success=true/false (boolean string).
    # Validator parses success= as a float score → float("true") raises ValueError.
    # Now prints the actual numeric score e.g. success=0.89
    print(f"[END] success={success} steps={step_idx} rewards={','.join(str(r) for r in total_rewards)}", flush=True)

    return final_code, success


async def evaluate_and_optimize(user_code, task_type):
    if user_code is None or not user_code.strip():
        return 0.01, "⚠️ Error: Please paste some code first!", 0.01

    env = CodeReviewEnv()
    env.load_custom_code(user_code, task_type)
    initial_score = env._calculate_reward()

    prompt = f"""
    TASK: {task_type}
    You are a Senior Software Engineer. Fix the code for a perfect score.

    CRITERIA:
    - If 'security-audit': Remove f-strings from SQL and use '?' placeholders.
    - If 'efficiency-boost': Refactor nested loops into a single for loop using a set (not a list comprehension).
    - If 'style-cleanup': Remove 'import sys' AND fix all indentation to 4 spaces.

    USER CODE:
    {user_code}

    Return the COMPLETE fixed file in JSON format:
    {{"action_type": "apply_fix", "content": "FIXED_CODE"}}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a specialized code optimization agent. Return only JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        json_content = clean_json_string(response.choices[0].message.content)
        agent_action = Action(**json.loads(json_content))

        env.step(agent_action)
        final_score = env._calculate_reward()

        return float(initial_score), agent_action.content, float(final_score)
    except Exception as e:
        return float(initial_score), f"Error: {str(e)}", 0.01


def build_ui():
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🏢 Aion Code Reviewer & Optimizer")

        with gr.Tabs():
            with gr.TabItem("Hackathon Benchmark"):
                gr.Markdown("### Automated Task Evaluation")
                with gr.Row():
                    task_selector = gr.Dropdown(
                        ["style-cleanup", "efficiency-boost", "security-audit"],
                        label="Benchmark Task", value="style-cleanup"
                    )
                    run_btn = gr.Button("Run Benchmark", variant="primary")
                with gr.Row():
                    output_code = gr.Code(label="Agent Fix", language="python")
                    score_display = gr.Number(label="Final Score")
                run_btn.click(
                    lambda t: asyncio.run(run_task(t)),
                    inputs=[task_selector],
                    outputs=[output_code, score_display]
                )

            with gr.TabItem("Paste & Optimize"):
                gr.Markdown("### Custom Code Optimizer")
                custom_task_type = gr.Radio(
                    ["style-cleanup", "efficiency-boost", "security-audit"],
                    label="Optimize For:", value="efficiency-boost"
                )
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
    return demo


if __name__ == "__main__":
    print("--- RUNNING AUTOMATED BASELINE FOR PHASE 2 ---", flush=True)

    try:
        asyncio.run(run_task("style-cleanup"))
        asyncio.run(run_task("efficiency-boost"))
        asyncio.run(run_task("security-audit"))
    except Exception as e:
        print(f"CRITICAL ERROR IN BASELINE: {str(e)}", flush=True)
        traceback.print_exc()

    print("--- BASELINE COMPLETE ---", flush=True)
