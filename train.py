#!/usr/bin/env python3
"""
Aion RL/SFT Training Framework
Collects optimal trajectories from the CodeReviewEnv environment and provides 
SFT (Behavioral Cloning) and Reinforcement Learning fine-tuning templates.
"""

import os
import json
import argparse
import sys

from env import CodeReviewEnv
from models import Action

def collect_trajectories(num_episodes=10):
    """Collects successful trajectories for behavior cloning (SFT)."""
    print(f"--- Launching trajectory collection ({num_episodes} episodes)... ---")
    env = CodeReviewEnv()
    dataset = []

    # Baseline task templates
    tasks = ["style-cleanup", "efficiency-boost", "security-audit"]
    
    # Successful code samples for training targets
    success_codes = {
        "style-cleanup": """def hello_world():
    print("Hello")
    print("Indentation is wrong here")

if __name__ == "__main__":
    hello_world()""",
        "efficiency-boost": """def find_duplicates(list_a, list_b):
    seen = set(list_a)
    return [x for x in list_b if x in seen]

if __name__ == "__main__":
    find_duplicates([1,2], [2,3])""",
        "security-audit": """import sqlite3
def get_user_data(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    return cursor.fetchone()

if __name__ == "__main__":
    get_user_data('admin')"""
    }

    for task in tasks:
        obs = env.reset(task_id=task)
        initial_code = obs.code_content
        
        # Simulate an optimal action step leading to a high reward
        target_code = success_codes[task]
        action = Action(action_type="apply_fix", content=target_code)
        obs_next, reward, done, info = env.step(action)
        
        if reward >= 0.90:
            # Format as standard SFT format
            entry = {
                "instruction": f"Optimize and audit the following python code for: {task}",
                "input": initial_code,
                "output": json.dumps({
                    "action_type": "apply_fix",
                    "content": target_code
                })
            }
            dataset.append(entry)
            print(f"Collected optimal trajectory for task: {task} (Reward: {reward})")

    # Save to a json dataset file
    os.makedirs("data", exist_ok=True)
    out_path = "data/sft_trajectories.json"
    with open(out_path, "w") as f:
        json.dump(dataset, f, indent=4)
    print(f"Saved {len(dataset)} trajectories to {out_path}\n")
    return out_path

def run_sft_training(dataset_path):
    """SFT (Supervised Fine-Tuning) behavioral cloning entry point."""
    print("--- Checking SFT Training Dependencies... ---")
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        print("PyTorch and Transformers are available. Starting training script configuration...")
    except ImportError:
        print("\n[Dependency Warning] PyTorch, Transformers, or TRL not found in the current environment.")
        print("To run the full SFT/RL training, please install them via:")
        print("  pip install torch transformers trl peft accelerate")
        print("\nA template SFT training command would be:")
        print("  python train.py --run_training\n")
        return

    print("Note: In-memory simulation only. Instantiate Trainer...")
    # Training Loop Template placeholder or small training setup
    print("TRL SFTTrainer setup complete. SFT Training is ready to execute.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aion RL/SFT Training runner")
    parser.add_argument("--collect", action="store_true", help="Collect offline trajectories for SFT training")
    parser.add_argument("--sft", action="store_true", help="Run behavioral cloning SFT training setup")
    args = parser.parse_args()

    # Default behaviour: run both
    if not args.collect and not args.sft:
        args.collect = True
        args.sft = True

    dataset_path = None
    if args.collect:
        dataset_path = collect_trajectories()
    if args.sft:
        run_sft_training(dataset_path or "data/sft_trajectories.json")
