#!/usr/bin/env python3
"""
scripts/install_pilot.py - Automated Aion Pilot Workflow Installer.

Generates and installs `.github/workflows/aion-review.yml` for pilot repositories
with configurable review mode (shadow vs visible) and LLM inference provider.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

WORKFLOW_TEMPLATE = """name: Aion Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  aion-review:
    name: Aion High-Precision Review
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Aion Review Action
        uses: aion-org/code-reviewer@v1.1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          mode: {mode}
          provider: {provider}
          max_comments: {max_comments}
        env:
          {provider_env_var}: ${{{{ secrets.{provider_env_var} }}}}
          AION_KILL_SWITCH: ${{{{ secrets.AION_KILL_SWITCH }}}}
"""

PROVIDER_ENV_VARS = {
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "mock": "MOCK_API_KEY",
    "ollama": "OLLAMA_HOST",
}


def generate_workflow_yaml(
    mode: str = "shadow",
    provider: str = "groq",
    max_comments: int = 5,
) -> str:
    """Generate YAML workflow content for target repository."""
    valid_modes = {"shadow", "visible"}
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of: {sorted(valid_modes)}")

    provider_env = PROVIDER_ENV_VARS.get(provider.lower(), "LLM_API_KEY")
    return WORKFLOW_TEMPLATE.format(
        mode=mode,
        provider=provider,
        max_comments=max_comments,
        provider_env_var=provider_env,
    )


def install_pilot_workflow(
    target_dir: str | Path = ".",
    mode: str = "shadow",
    provider: str = "groq",
    max_comments: int = 5,
    dry_run: bool = False,
) -> Path:
    """Install Aion workflow file into target repository."""
    base_path = Path(target_dir).resolve()
    workflow_dir = base_path / ".github" / "workflows"
    target_file = workflow_dir / "aion-review.yml"

    content = generate_workflow_yaml(mode=mode, provider=provider, max_comments=max_comments)

    if dry_run:
        print(f"[DRY-RUN] Target file: {target_file}")
        print(content)
        return target_file

    workflow_dir.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content, encoding="utf-8")
    print(f"Successfully generated Aion pilot workflow at: {target_file}")
    print(f"  Review Mode : {mode.upper()}")
    print(f"  Provider    : {provider}")
    print(f"  Max Comments: {max_comments}")
    if provider.lower() in ("groq", "openrouter"):
        print(f"Remember to set GitHub Secret: {PROVIDER_ENV_VARS[provider.lower()]}")

    return target_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install Aion code review workflow for pilot repositories."
    )
    parser.add_argument(
        "--mode",
        choices=["shadow", "visible"],
        default="shadow",
        help="Review mode: 'shadow' (silent candidate logging) or 'visible' (PR comments). Default: shadow.",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "openrouter", "mock", "ollama"],
        default="groq",
        help="Inference provider. Default: groq.",
    )
    parser.add_argument(
        "--target-dir",
        default=".",
        help="Target repository directory path. Default: current directory.",
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=5,
        help="Maximum comments allowed per PR. Default: 5.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated workflow without writing to disk.",
    )

    args = parser.parse_args()

    try:
        install_pilot_workflow(
            target_dir=args.target_dir,
            mode=args.mode,
            provider=args.provider,
            max_comments=args.max_comments,
            dry_run=args.dry_run,
        )
        return 0
    except Exception as exc:
        print(f"Error installing workflow: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
