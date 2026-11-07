---
phase: 07-community-and-growth
plan: 03
type: execute
wave: 3
depends_on:
  - 07-01
  - 07-02
files_modified:
  - docs/launch/SHOW_HN.md
  - docs/launch/MARKETPLACE.md
  - docs/grants/HUGGINGFACE_ZEROGPU.md
  - docs/grants/GOOGLE_FOR_STARTUPS.md
  - docs/grants/AWS_ACTIVATE.md
  - docs/grants/AZURE_FOR_STARTUPS.md
  - docs/OPEN_SOURCE_MOAT.md
  - CONTRIBUTING.md
  - tests/test_launch_and_grants.py
autonomous: true
requirements:
  - GROWTH-03
must_haves:
  truths:
    - docs/launch/SHOW_HN.md contains a technically rigorous, engaging launch submission text detailing RLVR methodology, clean-diff negative controls, and zero-nitpick guarantees.
    - docs/launch/MARKETPLACE.md and action.yml provide complete metadata for GitHub Marketplace listing.
    - docs/grants/ contains 4 structured, ready-to-submit grant applications (Hugging Face ZeroGPU, Google for Startups, AWS Activate, Microsoft for Startups) targeting zero-budget scaling.
    - docs/OPEN_SOURCE_MOAT.md and CONTRIBUTING.md lay out the contributor guide, benchmark expansion process, and open-source data flywheel.
    - tests/test_launch_and_grants.py verifies all grant dossiers and launch artifacts exist and meet schema and completeness criteria.
  artifacts:
    - docs/launch/SHOW_HN.md
    - docs/launch/MARKETPLACE.md
    - docs/grants/HUGGINGFACE_ZEROGPU.md
    - docs/grants/GOOGLE_FOR_STARTUPS.md
    - docs/grants/AWS_ACTIVATE.md
    - docs/grants/AZURE_FOR_STARTUPS.md
    - docs/OPEN_SOURCE_MOAT.md
    - CONTRIBUTING.md
    - tests/test_launch_and_grants.py
  key_links:
    - docs/launch/ references benchmark results from Phase 2 and model results from Phase 5.
    - docs/grants/ references architecture from ReviewEnv (Phase 4) and GitHub App (Phase 6).
---

<objective>
Assemble and release the Public Launch and Compute Grant Acceleration Package (`GROWTH-03`).
Equip Aion for immediate community launch (Show HN, GitHub Marketplace) and establish compute sustainability through approved AI startup grants.

Purpose: Convert Aion's technical edge into a permanent, self-sustaining open-source moat and community-driven ecosystem.
Output: Launch documents in `docs/launch/`, grant applications in `docs/grants/`, `docs/OPEN_SOURCE_MOAT.md`, updated `CONTRIBUTING.md`, and `tests/test_launch_and_grants.py`.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/07-community-and-growth/RESEARCH.md
@docs/OPEN_SOURCE_COMMITMENT.md
@bench/leaderboard.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Author Show HN Launch Dossier and GitHub Marketplace Metadata</name>
  <files>docs/launch/SHOW_HN.md, docs/launch/MARKETPLACE.md</files>
  <action>
1. In `docs/launch/SHOW_HN.md`:
   - Title: `Show HN: Aion – No-nitpick AI code review trained with RLVR, open-source and free for GitHub`
   - Introduction: Why developers hate AI code reviews (repetitive stylistic nitpicks, hallucinations, spamming PRs).
   - The Solution: RLVR on Gymnasium MDP with verifiable multi-tier rewards, negative controls on clean diffs ($<10\%$ FPR), and contextual bandit suppression.
   - Benchmark Findings: Aion Qwen2.5-Coder 7B GRPO outperforming GPT-4o and Claude 3.5 Sonnet on precision with $3.8\%$ nitpick rate.
   - Quick Start: GitHub Action, GitHub App, CLI (`aion review --staged`), and VS Code extension.
   - Open Source Moat: Permanently free for open source, open weights, reproducible benchmark leaderboard.
2. In `docs/launch/MARKETPLACE.md`:
   - Listing details: Name, Short description, Categories (`Code review`, `Code quality`, `Security`).
   - Detailed feature copy, installation badges, screenshots guide, and permission justification.
  </action>
  <verify>
python -c "import os; assert os.path.exists('docs/launch/SHOW_HN.md') and os.path.exists('docs/launch/MARKETPLACE.md'); print('Launch dossiers verified')"
  </verify>
</task>

<task>
  <name>Draft 4 Compute Grant Applications for Zero-Budget Scaling</name>
  <files>docs/grants/HUGGINGFACE_ZEROGPU.md, docs/grants/GOOGLE_FOR_STARTUPS.md, docs/grants/AWS_ACTIVATE.md, docs/grants/AZURE_FOR_STARTUPS.md</files>
  <action>
1. Author four detailed, ready-to-submit grant applications:
   - `docs/grants/HUGGINGFACE_ZEROGPU.md`:
     - Targets: Hugging Face ZeroGPU / Community GPU Grant (A100/H100 compute for hosted demo and RLVR inference).
     - Justification: Open model release on HF Hub, transparent benchmark dataset, interactive Gradio/Spaces demo.
   - `docs/grants/GOOGLE_FOR_STARTUPS.md`:
     - Targets: Google Cloud for Startups ($100k-$200k in credits) & TPU Research Cloud (TRC).
     - Justification: Training vLLM / GRPO policies with open JAX/PyTorch models, zero-profit open-source mission.
   - `docs/grants/AWS_ACTIVATE.md`:
     - Targets: AWS Activate Founders & Open Source Cloud Credits ($25k-$100k).
     - Justification: Multi-repo telemetry hosting, containerized ephemeral sandbox execution, public S3 datasets.
   - `docs/grants/AZURE_FOR_STARTUPS.md`:
     - Targets: Microsoft for Startups Founders Hub (Azure OpenAI & GPU compute credits).
     - Justification: GitHub App backend infrastructure, Azure AI model evaluation baselines.
  </action>
  <verify>
python -c "import os; grants = ['HUGGINGFACE_ZEROGPU.md', 'GOOGLE_FOR_STARTUPS.md', 'AWS_ACTIVATE.md', 'AZURE_FOR_STARTUPS.md']; assert all(os.path.exists(os.path.join('docs', 'grants', g)) for g in grants); print('All 4 grant applications verified')"
  </verify>
</task>

<task>
  <name>Author Open-Source Moat Strategy and Update Contributing Guidelines</name>
  <files>docs/OPEN_SOURCE_MOAT.md, CONTRIBUTING.md</files>
  <action>
1. In `docs/OPEN_SOURCE_MOAT.md`:
   - Analysis of defensive moats against commercial competitors:
     - Data Moat: Real-world PR feedback collected across 100+ open-source repos feeds continuous RL training.
     - Trust Moat: Objective, publicly auditable Aion-Bench prevents self-serving claims.
     - Distribution Moat: Free for OSS + README badge creates viral developer adoption loop.
     - Cost Moat: Small quantized models (7B) running locally or on free grants eliminate API margin collapse.
2. In `CONTRIBUTING.md`:
   - Instructions for contributing bug cases to Aion-Bench.
   - Instructions for submitting open-weight model evaluations to the leaderboard.
   - Local development setup with `aion` CLI and test runner.
  </action>
  <verify>
python -c "import os; assert os.path.exists('docs/OPEN_SOURCE_MOAT.md') and os.path.exists('CONTRIBUTING.md'); print('Moat and Contributing docs verified')"
  </verify>
</task>

<task>
  <name>Build Launch and Grants Verification Test Suite</name>
  <files>tests/test_launch_and_grants.py</files>
  <action>
1. In `tests/test_launch_and_grants.py`, write test cases:
   - `test_show_hn_dossier_completeness()`: Checks technical sections, RLVR methodology, benchmark comparisons, and installation instructions.
   - `test_github_marketplace_metadata()`: Checks categories, pricing, feature points, and action integration.
   - `test_all_four_grant_dossiers_exist_and_complete()`: Verifies HF, Google, AWS, and Azure applications include technical architecture, compute budget, and milestones.
   - `test_open_source_moat_and_contributing()`: Verifies contributor instructions and moat strategy.
  </action>
  <verify>
pytest tests/test_launch_and_grants.py -v
  </verify>
</task>

</tasks>

