"""
cli/main.py

Developer CLI surface for Aion Code Reviewer (APP-03).
Provides pre-commit review capabilities directly in local terminals and code editors:
- aion review --staged
- aion conventions
- aion config
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from action.diff_parser import parse_unified_diff
from action.linters import run_static_linters
from action.providers import CandidateComment
from action.verifier import PrecisionVerifier
from rl.memory import RepoConventionMemory

logger = logging.getLogger("aion.cli")

# ANSI color codes for rich terminal formatting
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_RED = "\033[31m"
COLOR_CYAN = "\033[36m"
COLOR_DIM = "\033[2m"


def get_git_staged_diff(cwd: Optional[str] = None) -> str:
    """
    Extract the staged unified diff from git (git diff --cached --unified=3).
    Returns an empty string if git is not available or no changes are staged.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--unified=3"],
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout
        return ""
    except Exception as e:
        logger.debug("Failed to run git diff --cached: %s", e)
        return ""


def get_git_diff_target(target: str, cwd: Optional[str] = None) -> str:
    """
    Extract unified diff against a target commit, branch, or tree-ish.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", target, "--unified=3"],
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout
        return ""
    except Exception as e:
        logger.debug("Failed to run git diff %s: %s", target, e)
        return ""


class AionLocalReviewer:
    """
    Local review engine combining AST linter analysis, convention memory,
    and the precision verifier gate.
    """

    def __init__(
        self,
        conventions_path: str = ".aion/conventions.json",
        min_confidence: float = 0.70,
        max_comments: int = 5,
    ) -> None:
        self.conventions_path = conventions_path
        self.min_confidence = min_confidence
        self.max_comments = max_comments
        self.memory = RepoConventionMemory.load_or_create(conventions_path)
        self.verifier = PrecisionVerifier(
            default_max_comments=max_comments,
            default_min_confidence=min_confidence,
        )

    def review_diff(
        self,
        diff_str: str,
        file_content_map: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Review a unified diff string and return verified findings.
        """
        if not diff_str or not diff_str.strip():
            return []

        file_diffs = parse_unified_diff(diff_str)
        findings: List[Dict[str, Any]] = []

        for fd in file_diffs:
            if fd.is_binary or fd.is_deleted or not fd.modified_lines:
                continue

            file_path = fd.new_path or fd.old_path or ""
            if not file_path:
                continue

            # Determine file content
            code_content: Optional[str] = None
            if file_content_map and file_path in file_content_map:
                code_content = file_content_map[file_path]
            elif os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        code_content = f.read()
                except Exception:
                    code_content = None

            if not code_content:
                # Synthesize content from hunks if disk file is absent
                added_lines: List[str] = []
                for hunk in fd.hunks:
                    for dline in hunk.lines:
                        if dline.line_type in ("+", " "):
                            added_lines.append(dline.content)
                code_content = "\n".join(added_lines)

            if not code_content.strip():
                continue

            # 1. Run static AST security inspection and Ruff linters
            candidates = run_static_linters(file_path, code_content, fd.language)

            # 2. Filter through convention memory (suppressed patterns/categories)
            unsuppressed: List[CandidateComment] = []
            for c in candidates:
                if not self.memory.is_suppressed(c.category, c.comment, c.rule_id):
                    unsuppressed.append(c)

            # 3. Filter through PrecisionVerifier gate
            verified_comments = self.verifier.filter_candidates(
                candidates=unsuppressed,
                modified_lines=fd.modified_lines,
                max_comments=self.max_comments,
                min_confidence=self.min_confidence,
                file_content=code_content,
            )

            # 4. Map to structured dictionary records
            for c in verified_comments:
                findings.append(
                    {
                        "file_path": c.file_path,
                        "line_number": c.line_number,
                        "category": c.category,
                        "severity": c.severity,
                        "comment": c.comment,
                        "suggestion": c.suggestion,
                        "confidence": round(float(c.confidence), 3),
                        "rule_id": c.rule_id,
                    }
                )

        return findings

    def review_file(
        self,
        file_path: str,
        content: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Review an individual file directly without git diff.
        Treats all lines in the file as targets.
        """
        if content is None:
            if not os.path.isfile(file_path):
                return []
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                return []

        ext = os.path.splitext(file_path)[1]
        language = "python" if ext in (".py", ".pyi") else ext.lstrip(".")
        candidates = run_static_linters(file_path, content, language)

        all_lines = set(range(1, len(content.splitlines()) + 1))
        unsuppressed = [
            c for c in candidates if not self.memory.is_suppressed(c.category, c.comment, c.rule_id)
        ]
        verified = self.verifier.filter_candidates(
            candidates=unsuppressed,
            modified_lines=all_lines,
            max_comments=self.max_comments,
            min_confidence=self.min_confidence,
            file_content=content,
        )

        return [
            {
                "file_path": c.file_path,
                "line_number": c.line_number,
                "category": c.category,
                "severity": c.severity,
                "comment": c.comment,
                "suggestion": c.suggestion,
                "confidence": round(float(c.confidence), 3),
                "rule_id": c.rule_id,
            }
            for c in verified
        ]


def format_terminal_review(findings: List[Dict[str, Any]]) -> str:
    """
    Format findings into human-friendly, colored ANSI terminal output.
    """
    if not findings:
        return f"{COLOR_GREEN}✨ [aion] No actionable issues detected. Ready to commit!{COLOR_RESET}\n"

    lines: List[str] = []
    lines.append(f"{COLOR_BOLD}{COLOR_CYAN}🔍 Aion Code Review Findings ({len(findings)} issues):{COLOR_RESET}\n")

    for idx, item in enumerate(findings, 1):
        sev = item.get("severity", "minor").lower()
        if sev == "critical":
            sev_tag = f"{COLOR_RED}[CRITICAL]{COLOR_RESET}"
        elif sev == "major":
            sev_tag = f"{COLOR_YELLOW}[MAJOR]{COLOR_RESET}"
        else:
            sev_tag = f"{COLOR_DIM}[{sev.upper()}]{COLOR_RESET}"

        cat = item.get("category", "general").upper()
        rule = f" ({item['rule_id']})" if item.get("rule_id") else ""
        header = f"{idx}. {sev_tag} {COLOR_BOLD}{item['file_path']}:{item['line_number']}{COLOR_RESET} [{cat}{rule}]"
        lines.append(header)
        lines.append(f"   {item['comment']}")

        suggestion = item.get("suggestion")
        if suggestion:
            lines.append(f"   {COLOR_GREEN}+ Suggested Fix:{COLOR_RESET}")
            for sug_line in suggestion.splitlines():
                lines.append(f"     {COLOR_GREEN}│ {sug_line}{COLOR_RESET}")
        lines.append("")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """
    Build CLI argument parser for `aion`.
    """
    parser = argparse.ArgumentParser(
        prog="aion",
        description="Aion Code Reviewer: AI-native code review with AST verification and convention memory.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # `aion review`
    review_parser = subparsers.add_parser("review", help="Review staged or targeted code changes")
    review_parser.add_argument(
        "--staged",
        action="store_true",
        default=False,
        help="Review staged git changes (git diff --cached)",
    )
    review_parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Review git diff against target commit or branch (e.g. main, HEAD~1)",
    )
    review_parser.add_argument(
        "--diff-file",
        type=str,
        default=None,
        help="Path to a unified diff file to review directly",
    )
    review_parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to a single file to review directly",
    )
    review_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit raw machine-readable JSON array of findings",
    )
    review_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.70,
        help="Confidence cutoff threshold (default: 0.70)",
    )
    review_parser.add_argument(
        "--max-comments",
        type=int,
        default=5,
        help="Maximum review comments to output (default: 5)",
    )
    review_parser.add_argument(
        "--conventions",
        type=str,
        default=".aion/conventions.json",
        help="Path to conventions file (default: .aion/conventions.json)",
    )

    # `aion conventions`
    conv_parser = subparsers.add_parser("conventions", help="Manage repository conventions and suppressions")
    conv_parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="List repository conventions and active suppressions",
    )
    conv_parser.add_argument(
        "--add",
        type=str,
        default=None,
        help="Register a new convention rule",
    )
    conv_parser.add_argument(
        "--category",
        type=str,
        default="general",
        help="Category for registered convention (default: general)",
    )
    conv_parser.add_argument(
        "--suppress-category",
        type=str,
        default=None,
        help="Suppress an entire comment category (e.g. style)",
    )
    conv_parser.add_argument(
        "--file",
        type=str,
        default=".aion/conventions.json",
        help="Path to conventions file (default: .aion/conventions.json)",
    )

    # `aion config`
    cfg_parser = subparsers.add_parser("config", help="Manage local Aion configuration")
    cfg_parser.add_argument(
        "--show",
        action="store_true",
        default=False,
        help="Display current local configuration",
    )
    cfg_parser.add_argument(
        "--set-provider",
        type=str,
        choices=["ollama", "byok", "mock"],
        default=None,
        help="Set local inference provider (ollama, byok, or mock)",
    )
    cfg_parser.add_argument(
        "--set-model",
        type=str,
        default=None,
        help="Set local model identifier",
    )
    cfg_parser.add_argument(
        "--file",
        type=str,
        default=".aion/config.json",
        help="Path to configuration file",
    )

    return parser


def handle_review_command(args: argparse.Namespace) -> int:
    """Execute `aion review` subcommand."""
    reviewer = AionLocalReviewer(
        conventions_path=getattr(args, "conventions", ".aion/conventions.json"),
        min_confidence=args.min_confidence,
        max_comments=args.max_comments,
    )

    findings: List[Dict[str, Any]] = []

    if args.file:
        findings = reviewer.review_file(args.file)
    elif args.diff_file:
        if not os.path.isfile(args.diff_file):
            sys.stderr.write(f"Error: diff file '{args.diff_file}' not found.\n")
            return 1
        with open(args.diff_file, "r", encoding="utf-8", errors="replace") as f:
            diff_text = f.read()
        findings = reviewer.review_diff(diff_text)
    elif args.target:
        diff_text = get_git_diff_target(args.target)
        findings = reviewer.review_diff(diff_text)
    else:
        # Default behavior: review staged changes (--staged or implicit default)
        diff_text = get_git_staged_diff()
        findings = reviewer.review_diff(diff_text)

    if args.json:
        sys.stdout.write(json.dumps(findings, indent=2) + "\n")
    else:
        sys.stdout.write(format_terminal_review(findings))

    return 0


def handle_conventions_command(args: argparse.Namespace) -> int:
    """Execute `aion conventions` subcommand."""
    conv_file = args.file
    memory = RepoConventionMemory.load_or_create(conv_file)

    modified = False
    if args.add:
        rule = memory.add_convention(args.add, category=args.category)
        sys.stdout.write(f"Added convention [{rule.category}]: {rule.rule_text}\n")
        modified = True

    if args.suppress_category:
        memory.suppress_category(args.suppress_category)
        sys.stdout.write(f"Suppressed category: {args.suppress_category}\n")
        modified = True

    if modified:
        memory.save(conv_file)
        sys.stdout.write(f"Saved conventions to {conv_file}\n")

    if args.list or not modified:
        sys.stdout.write(f"--- Aion Conventions ({conv_file}) ---\n")
        if not memory.state.custom_rules and not memory.state.suppressed_categories and not memory.state.suppressed_patterns:
            sys.stdout.write("No custom conventions or suppressions configured.\n")
        else:
            if memory.state.custom_rules:
                sys.stdout.write("Custom Rules:\n")
                for r in memory.state.custom_rules:
                    sys.stdout.write(f"  - [{r.category}] {r.rule_text}\n")
            if memory.state.suppressed_categories:
                sys.stdout.write("Suppressed Categories:\n")
                for c in memory.state.suppressed_categories:
                    sys.stdout.write(f"  - {c}\n")
            if memory.state.suppressed_patterns:
                sys.stdout.write("Suppressed Patterns:\n")
                for p in memory.state.suppressed_patterns:
                    status = "suppressed" if p.suppressed else f"dismissed ({p.dismissal_count}x)"
                    sys.stdout.write(f"  - {p.pattern} [{status}]\n")

    return 0


def handle_config_command(args: argparse.Namespace) -> int:
    """Execute `aion config` subcommand."""
    config_file = args.file
    config: Dict[str, Any] = {
        "provider": "ollama",
        "model": "aion-reviewer:latest",
        "min_confidence": 0.70,
        "auto_review_on_save": False,
    }

    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception as e:
            logger.warning("Could not read config from %s: %s", config_file, e)

    modified = False
    if args.set_provider:
        config["provider"] = args.set_provider
        modified = True
    if args.set_model:
        config["model"] = args.set_model
        modified = True

    if modified:
        os.makedirs(os.path.dirname(os.path.abspath(config_file)), exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        sys.stdout.write(f"Updated configuration saved to {config_file}\n")

    if args.show or not modified:
        sys.stdout.write(json.dumps(config, indent=2) + "\n")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        # Default behavior when running bare `aion`: review staged changes
        args.subcommand = "review"
        args.staged = True
        args.target = None
        args.diff_file = None
        args.file = None
        args.json = False
        args.min_confidence = 0.70
        args.max_comments = 5
        args.conventions = ".aion/conventions.json"

    if args.subcommand == "review":
        return handle_review_command(args)
    elif args.subcommand == "conventions":
        return handle_conventions_command(args)
    elif args.subcommand == "config":
        return handle_config_command(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
