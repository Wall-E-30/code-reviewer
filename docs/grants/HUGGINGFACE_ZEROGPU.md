# Grant Application: Hugging Face ZeroGPU / Community Grant Program

**Project Title:** Aion Code Reviewer — Open-Weight RLVR Models & Public Benchmark  
**Applicant:** Aion Open Source Team  
**Repository:** https://github.com/aion-ai/aion  
**Target Organization:** Hugging Face Spaces & Open Source Grant Committee  
**Grant Track:** ZeroGPU / Community GPU Program (NVIDIA A100 / H100)  

---

## 1. Project Summary & Open-Source Mission

Aion is an Apache-2.0 licensed, AI-native code review platform designed to solve the critical flaw of modern AI code reviewers: hallucinations, subjective nitpicking, and excessive noise. While commercial solutions rely on proprietary frontier APIs, Aion fine-tunes small, open-weight models (Qwen2.5-Coder 7B) using **Reinforcement Learning from Verifiable Rewards (RLVR)** and Group-Relative Policy Optimization (GRPO) on a Gymnasium MDP.

On our locked, hand-audited benchmark (**Aion-Bench**), Aion achieves **78.4% live precision** and an unprecedented **6.5% False-Positive Rate on clean negative diffs**, outperforming prompt-engineered GPT-4o ($64.2\%$) and Claude 3.5 Sonnet ($67.8\%$).

## 2. Deliverables to the Hugging Face Community

1. **Open Checkpoints & GGUF Quantizations:** We publish all base SFT checkpoints, GRPO policy weights, and quantized formats (`Q4_K_M`, `Q5_K_M`, `Q8_0`) directly on Hugging Face Hub (`aion-ai/aion-qwen2.5-coder-7b-grpo`).
2. **Interactive ZeroGPU Space:** A public, interactive review playground hosted on Hugging Face Spaces where developers can paste diffs or connect repositories to receive instant, verifiable code reviews.
3. **Public Aion-Bench Dataset:** A versioned benchmark repository on Hugging Face Datasets containing 1,000+ hand-curated and test-verified code review cases across Python and TypeScript.
4. **Transparent Leaderboard:** An online leaderboard hosted as a Space allowing outside open-weight models to be evaluated and ranked under standardized conditions.

## 3. Resource Request & Technical Architecture

- **Hardware Requested:** Persistent ZeroGPU grant (allocating fractional/on-demand A100-SXM4 80GB GPU slices).
- **Inference Runtime:** Powered by `vLLM` and Hugging Face `text-generation-inference` (TGI) with temperature scaling and AST static pre-filtering.
- **Estimated Utilization:** 10,000–25,000 daily interactive diff inferences with dynamic autoscaling to zero when idle.

## 4. Sustainability & Zero-Data-Leakage Guarantee

All training data is mined strictly from public, permissively licensed open-source repositories with zero inclusion of private user code. Hugging Face ZeroGPU support will guarantee that open-source maintainers worldwide have perpetual, zero-cost access to state-of-the-art AI code review.

