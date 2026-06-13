#!/usr/bin/env python3
"""
Correct Reinforcement Learning (SFT + REINFORCE with baseline) Training Script.
Trains a GPT-2 language model policy to directly generate optimized code based on environment feedback.
"""

import os
import sys
import math
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import List, Dict, Any

from env import CodeReviewEnv
from models import Action

# --- BACKWARD COMPATIBILITY STUBS ---
class QNetwork(nn.Module):
    def __init__(self, state_dim, action_dim):
        super().__init__()
        self.fc = nn.Linear(state_dim, action_dim)
    def forward(self, x):
        return self.fc(x)

def extract_features(code: str, task_id: str) -> np.ndarray:
    return np.zeros(771, dtype=np.float32)

ACTION_MUTATORS = {
    0: lambda code: code,
    1: lambda code: code,
    2: lambda code: code,
    3: lambda code: code,
    4: lambda code: code
}

# --- UNIFIED AUTOREGRESSIVE RL TRAINING ---

# Safe paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RL_MODEL_PATH = os.path.join(BASE_DIR, "models", "rl_model")

# Prompt formatter
def format_prompt(task_id: str, code: str) -> str:
    return f"Task: {task_id}\nCode:\n{code}\nOptimized:\n"

# SFT Training Dataset
SFT_DATA = [
    {
        "task_id": "style-cleanup",
        "original": (
            "import os\n"
            "import sys # Unused import\n"
            "def hello_world():\n"
            "  print(\"Hello\")\n"
            "  print(\"Indentation is wrong here\")\n\n"
            "if __name__ == \"__main__\":\n"
            "    hello_world()"
        ),
        "optimized": (
            "def hello_world():\n"
            "    print(\"Hello\")\n"
            "    print(\"Indentation is wrong here\")\n\n"
            "if __name__ == \"__main__\":\n"
            "    hello_world()"
        )
    },
    {
        "task_id": "efficiency-boost",
        "original": (
            "def find_duplicates(list_a, list_b):\n"
            "    # Very slow O(N^2) approach\n"
            "    duplicates = []\n"
            "    for item_a in list_a:\n"
            "        for item_b in list_b:\n"
            "            if item_a == item_b:\n"
            "                duplicates.append(item_a)\n"
            "    return duplicates\n\n"
            "if __name__ == \"__main__\":\n"
            "    find_duplicates([1,2], [2,3])"
        ),
        "optimized": (
            "def find_duplicates(list_a, list_b):\n"
            "    seen = set(list_a)\n"
            "    return [x for x in list_b if x in seen]\n\n"
            "if __name__ == \"__main__\":\n"
            "    find_duplicates([1,2], [2,3])"
        )
    },
    {
        "task_id": "security-audit",
        "original": (
            "import sqlite3\n"
            "def get_user_data(user_id):\n"
            "    conn = sqlite3.connect('users.db')\n"
            "    cursor = conn.cursor()\n"
            "    query = f\"SELECT * FROM users WHERE id = '{user_id}'\"\n"
            "    cursor.execute(query)\n"
            "    return cursor.fetchone()\n\n"
            "if __name__ == \"__main__\":\n"
            "    get_user_data('admin')"
        ),
        "optimized": (
            "import sqlite3\n"
            "def get_user_data(user_id):\n"
            "    conn = sqlite3.connect('users.db')\n"
            "    cursor = conn.cursor()\n"
            "    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))\n"
            "    return cursor.fetchone()\n\n"
            "if __name__ == \"__main__\":\n"
            "    get_user_data('admin')"
        )
    }
]

def train():
    print("--- STARTING RL TRAINING PIPELINE ---", flush=True)
    
    # 1. Load GPT-2 tokenizer and model
    try:
        from transformers import GPT2LMHeadModel, GPT2Tokenizer
        print("Loading pre-trained GPT-2 model...", flush=True)
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        tokenizer.pad_token = tokenizer.eos_token
        model = GPT2LMHeadModel.from_pretrained("gpt2")
    except Exception as e:
        print(f"Error loading model/transformers: {e}. RL training aborted.", flush=True)
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = optim.AdamW(model.parameters(), lr=5e-5)
    
    # 2. PHASE 1: Supervised Fine-Tuning (SFT) Warm-start
    print("--- Phase 1: Supervised Fine-Tuning (SFT) ---", flush=True)
    model.train()
    
    for epoch in range(3):
        epoch_loss = 0.0
        random.shuffle(SFT_DATA)
        for item in SFT_DATA:
            prompt = format_prompt(item["task_id"], item["original"])
            target = item["optimized"] + tokenizer.eos_token
            
            prompt_ids = tokenizer.encode(prompt)
            target_ids = tokenizer.encode(target)
            
            input_ids = torch.tensor([prompt_ids + target_ids], dtype=torch.long, device=device)
            
            # Mask out the prompt tokens in labels so we do not compute loss on prompt
            labels = input_ids.clone()
            labels[0, :len(prompt_ids)] = -100
            
            optimizer.zero_grad()
            outputs = model(input_ids, labels=labels)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            
        print(f"SFT Epoch {epoch+1}/3 - Loss: {epoch_loss/len(SFT_DATA):.4f}", flush=True)

    # 3. PHASE 2: Reinforcement Learning (REINFORCE with Baseline)
    print("--- Phase 2: Reinforcement Learning (REINFORCE) ---", flush=True)
    env = CodeReviewEnv()
    
    # Running baselines for each task to reduce variance
    baselines = {"style-cleanup": 0.5, "efficiency-boost": 0.5, "security-audit": 0.5}
    alpha = 0.1 # Baseline update rate
    
    for episode in range(5):
        episode_reward = 0.0
        for task_id in ["style-cleanup", "efficiency-boost", "security-audit"]:
            env.reset(task_id=task_id)
            prompt = format_prompt(task_id, env.code)
            prompt_ids = tokenizer.encode(prompt)
            prompt_tensor = torch.tensor([prompt_ids], dtype=torch.long, device=device)
            
            # Autoregressive generation with log probabilities
            model.eval()
            generated_ids = []
            log_probs = []
            
            input_seq = prompt_tensor.clone()
            for _ in range(128):
                with torch.no_grad():
                    outputs = model(input_seq)
                next_token_logits = outputs.logits[0, -1, :]
                probs = torch.softmax(next_token_logits, dim=-1)
                
                # Sample token
                dist = torch.distributions.Categorical(probs)
                token = dist.sample()
                
                generated_ids.append(token.item())
                log_probs.append(dist.log_prob(token))
                
                if token.item() == tokenizer.eos_token_id:
                    break
                input_seq = torch.cat([input_seq, token.unsqueeze(0).unsqueeze(0)], dim=-1)
            
            generated_code = tokenizer.decode(generated_ids, skip_special_tokens=True)
            
            # Evaluate using environment
            action = Action(action_type="apply_fix", content=generated_code)
            _, reward, _, _ = env.step(action)
            
            # Update baseline
            baseline = baselines[task_id]
            advantage = reward - baseline
            baselines[task_id] = baseline + alpha * advantage
            
            # Calculate Policy Loss
            # Policy gradient loss: - log_probs.sum() * advantage
            if len(log_probs) > 0:
                model.train()
                optimizer.zero_grad()
                
                # Re-calculate gradients correctly for the generated sequence
                input_ids = torch.tensor([prompt_ids + generated_ids], dtype=torch.long, device=device)
                outputs = model(input_ids)
                
                # Align logits with generated tokens
                logits = outputs.logits[0, len(prompt_ids)-1:-1, :]
                targets = input_ids[0, len(prompt_ids):]
                
                token_probs = torch.softmax(logits, dim=-1)
                dist = torch.distributions.Categorical(token_probs)
                active_log_probs = dist.log_prob(targets)
                
                policy_loss = -active_log_probs.sum() * advantage
                policy_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                
            episode_reward += reward
            
        print(f"RL Episode {episode+1}/5 - Average Reward: {episode_reward/3:.2f}", flush=True)

    # 4. Save fine-tuned model
    print(f"Saving fine-tuned RL model to {RL_MODEL_PATH}...", flush=True)
    os.makedirs(RL_MODEL_PATH, exist_ok=True)
    model.save_pretrained(RL_MODEL_PATH)
    tokenizer.save_pretrained(RL_MODEL_PATH)
    print("--- RL TRAINING COMPLETE & MODEL SAVED ---", flush=True)

if __name__ == "__main__":
    train()
