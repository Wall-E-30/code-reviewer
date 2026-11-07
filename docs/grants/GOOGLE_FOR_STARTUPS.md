# Grant Application: Google Cloud for Startups & TPU Research Cloud (TRC)

**Project Title:** Scaling RLVR Code Review Policies on Google Cloud & Cloud TPUs  
**Applicant:** Aion Core Engineering  
**Repository:** https://github.com/aion-ai/aion  
**Target Organization:** Google Cloud for Startups & TPU Research Cloud Committee  
**Grant Track:** AI-First Startups / TPU Research Cloud Compute Credits  

---

## 1. Project Background & Research Objective

Code review consumes an estimated 20–30% of software engineering hours globally, yet automated AI solutions have generated severe developer backlash due to false positives and ungrounded stylistic nitpicking.

Aion has demonstrated that Reinforcement Learning with Verifiable Rewards (RLVR) provides a principled solution. By structuring code review as a Gymnasium Markov Decision Process (`ReviewEnv`), evaluating policy actions against real compiler/linter diagnostics and unit test execution, and penalizing unwarranted comments on clean negative diffs, Aion trains open code models (1.5B–7B) to outperform 100x larger frontier models on review precision ($78.4\%$ vs $64.2\%$).

With Google Cloud support, we seek to scale our RL training pipeline from 10,000 to **100,000+ verified review episodes** across multi-language domains.

## 2. Research Plan & Google Cloud Architecture

1. **TPU-Accelerated GRPO Policy Optimization:**
   - Implement TPU-optimized training loops using PyTorch/XLA and JAX for Group-Relative Policy Optimization.
   - Run parallel policy rollouts across groups $G=8$ without requiring a memory-intensive critic network.
2. **Google Kubernetes Engine (GKE) Execution Sandboxes:**
   - Host ephemeral, rootless container sandboxes on GKE Autopilot to execute differential unit tests and AST security linters on generated code patches.
   - Enforce strict compute boundaries and resource cgroups to isolate untrusted code.
3. **Artifact Publishing & Model Sharing:**
   - Model weights and training code made available under Apache-2.0, with technical paper submission to NeurIPS / ICLR open workshops on verifiable reinforcement learning.

## 3. Resource Request Breakdown

- **Cloud TPU Access:** 4–8 Cloud TPU v5e or v4 slices for a 60-day training campaign to fine-tune open code foundations (Qwen2.5-Coder, Gemma 2, CodeGemma).
- **GKE / Cloud Compute Credits:** $25,000–$50,000 in Google Cloud credits to manage rollout sandboxes, dataset generation pipelines, and public Aion-Bench leaderboard backend.
- **Cloud Storage:** Multi-region buckets for hosting 100k+ verified test patch datasets.

## 4. Expected Impact

The project will validate the efficacy of Cloud TPUs for post-training reinforcement learning on complex software engineering environments, demonstrating an open-source, reproducible counterweight to closed commercial AI developer tools.

