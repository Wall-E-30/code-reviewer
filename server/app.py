import sys
import os

# Ensure the root directory is in the path so we can import env.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env import CodeReviewEnv

def main():
    """
    Standard OpenEnv server entry point.
    Initializes the environment for multi-mode deployment.
    """
    env = CodeReviewEnv()
    print("Aion Code Reviewer Environment successfully initialized for serving.")

if __name__ == "__main__":
    main()