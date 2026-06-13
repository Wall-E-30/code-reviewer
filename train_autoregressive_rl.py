import os
import torch
import torch.optim as optim
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from env import CodeReviewEnv
from models import Action

# Ensure checkpoint dir exists
os.makedirs("models", exist_ok=True)

# 1. Initialize GPT-2 Model & Tokenizer
print("Loading pre-trained GPT-2 model on CPU...", flush=True)
MODEL_NAME = "gpt2"
tokenizer = GPT2Tokenizer.from_pretrained(MODEL_NAME)
model = GPT2LMHeadModel.from_pretrained(MODEL_NAME)

# Set padding token
tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = model.config.eos_token_id

# 2. Define Value Network (Critic)
class ValueNetwork(torch.nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.fc1 = torch.nn.Linear(hidden_dim, 64)
        self.fc2 = torch.nn.Linear(64, 1)
        
    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))

critic = ValueNetwork(model.config.n_embd)

# Create optimizer for both Actor and Critic
optimizer = optim.AdamW(list(model.parameters()) + list(critic.parameters()), lr=1e-5)

# Initialize environment
env = CodeReviewEnv()

# 3. Define Prompts and Tasks
TASKS = [
    {
        "id": "style-cleanup",
        "prompt": "# Goal: Clean up style and imports\ndef run():\n    import sys\n    print(\"Hello\")\n# Cleaned Code:\n",
        "optimal_code": "def run():\n    print(\"Hello\")\n"
    },
    {
        "id": "efficiency-boost",
        "prompt": "# Goal: Optimize nested loop with set\ndef find(a, b):\n    return [x for x in a if x in b]\n# Cleaned Code:\n",
        "optimal_code": "def find(a, b):\n    seen = set(b)\n    return [x for x in a if x in seen]\n"
    },
    {
        "id": "security-audit",
        "prompt": "# Goal: Parameterize database query\ndef fetch(db, uid):\n    return db.execute(\"SELECT * FROM users WHERE id = \" + uid)\n# Cleaned Code:\n",
        "optimal_code": "def fetch(db, uid):\n    return db.execute(\"SELECT * FROM users WHERE id = ?\", (uid,))\n"
    }
]

print("============================================================")
print("Starting Supervised Fine-Tuning (SFT) Warm-Start Phase")
print("============================================================")
for epoch in range(1, 4):
    total_sft_loss = 0.0
    for task in TASKS:
        prompt = task["prompt"]
        opt = task["optimal_code"]
        full_text = prompt + opt + tokenizer.eos_token
        
        encodings = tokenizer(full_text, return_tensors="pt")
        input_ids = encodings["input_ids"]
        
        # Mask prompt tokens
        prompt_len = len(tokenizer.encode(prompt))
        labels = input_ids.clone()
        labels[0, :prompt_len] = -100
        
        outputs = model(input_ids, labels=labels)
        loss = outputs.loss
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        total_sft_loss += loss.item()
    print(f"SFT Epoch {epoch:d} | Average Loss: {total_sft_loss / len(TASKS):.4f}", flush=True)

print("============================================================")
print("Starting Autoregressive RL Training (Paradigm 1: Actor-Critic)")
print("============================================================")

running_baseline = 0.5
beta = 0.9

for step in range(1, 31):
    task = TASKS[(step - 1) % len(TASKS)]
    task_id = task["id"]
    prompt = task["prompt"]
    
    # Tokenize input prompt
    input_ids = tokenizer.encode(prompt, return_tensors="pt")
    prompt_len = input_ids.size(-1)
    
    # 1. Autoregressive token generation in eval mode without gradients
    model.eval()
    critic.eval()
    current_ids = input_ids.clone()
    gen_ids = []
    max_new_tokens = 64
    
    with torch.no_grad():
        for _ in range(max_new_tokens):
            outputs = model(current_ids)
            next_token_logits = outputs.logits[0, -1, :]
            probs = torch.softmax(next_token_logits, dim=-1)
            dist = torch.distributions.Categorical(probs)
            sampled_token = dist.sample()
            gen_ids.append(sampled_token.item())
            current_ids = torch.cat([current_ids, sampled_token.unsqueeze(0).unsqueeze(0)], dim=-1)
            if sampled_token.item() == tokenizer.eos_token_id:
                break
                
    generated_code = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
    
    # 2. Evaluate quality of generated code
    env.reset(task_id=task_id)
    env.load_custom_code(generated_code, task_id, language="python")
    obs, reward, done, _ = env.step(Action(action_type="submit", content=generated_code))
    
    # 3. Dynamic sequence Critic & log_probs evaluation in train mode with gradients
    model.train()
    critic.train()
    
    outputs = model(current_ids, output_hidden_states=True)
    state_repr = outputs.hidden_states[-1][0, -1, :].detach()
    predicted_value = critic(state_repr)
    
    advantage = reward - predicted_value.item()
    
    if len(gen_ids) > 0:
        logits = outputs.logits[0, prompt_len - 1 : -1, :]
        targets = current_ids[0, prompt_len:]
        probs = torch.softmax(logits, dim=-1)
        dist = torch.distributions.Categorical(probs)
        log_probs = dist.log_prob(targets)
        policy_loss = -log_probs.sum() * advantage
    else:
        policy_loss = torch.tensor(0.0, requires_grad=True)
        
    value_loss = torch.nn.functional.mse_loss(predicted_value, torch.tensor([reward], dtype=torch.float32))
    total_loss = policy_loss + value_loss
    
    optimizer.zero_grad()
    total_loss.backward()
    optimizer.step()
    
    running_baseline = beta * running_baseline + (1 - beta) * reward
    
    print(f"Step {step:02d} | Task: {task_id:<17} | Reward: {reward:.3f} | Loss: {total_loss.item():.4f} | Critic Val: {predicted_value.item():.3f} | Baseline: {running_baseline:.3f}", flush=True)
    if step % 5 == 0:
        print(f"       -> Sample Code Output:\n{generated_code}\n------------------------------------------------------------", flush=True)

# Save
model.save_pretrained("models/autoregressive_rl_model")
tokenizer.save_pretrained("models/autoregressive_rl_model")
torch.save(model.state_dict(), "models/autoregressive_rl_model.pt")
torch.save(critic.state_dict(), "models/autoregressive_critic.pt")
print("Saved fine-tuned policy model to models/autoregressive_rl_model", flush=True)
print("Saved fine-tuned policy weights to models/autoregressive_rl_model.pt", flush=True)
print("Saved fine-tuned critic weights to models/autoregressive_critic.pt", flush=True)
