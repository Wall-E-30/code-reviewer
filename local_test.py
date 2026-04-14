import subprocess
import re

def run_test():
    print("Running Local Phase 2 Validator...")
    # Run your inference script and capture what it prints
    result = subprocess.run(["python", "inference.py"], capture_output=True, text=True)
    logs = result.stdout
    
    print("\n--- EXTRACTED LOGS ---")
    print(logs)
    print("----------------------\n")

    # Find all reward instances in the logs
    step_rewards = re.findall(r"reward=([0-9.]+)", logs)
    end_rewards = re.findall(r"rewards=([0-9.,]+)", logs)
    
    all_scores = []
    for sr in step_rewards:
        all_scores.append(float(sr))
        
    for er_string in end_rewards:
        for val in er_string.split(','):
            all_scores.append(float(val))

    if not all_scores:
        print("FAILED: No scores found in logs. Did inference.py run the baseline?")
        return

    # Check the strict (0, 1) bounds
    passed = True
    for score in all_scores:
        if score <= 0.0 or score >= 1.0:
            print(f"FAILED: Found out-of-bounds score: {score}")
            passed = False
            
    if passed:
        print("SUCCESS: All scores are strictly between 0 and 1!")
        print("You are clear to submit to the hackathon portal.")

if __name__ == "__main__":
    run_test()