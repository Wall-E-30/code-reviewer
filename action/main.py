"""
action/main.py

Main execution entrypoint for Aion Code Reviewer GitHub Action.
Coordinates the end-to-end pipeline:
1. Parse configuration & GitHub Action event payload
2. Fetch pull request unified diff and metadata via GitHub REST API
3. Parse modified files and line ranges with DiffParser
4. Execute static linters (AST checks + Ruff) on modified files
5. Query BYOK LLM provider (Groq, OpenRouter, Ollama, OpenAI, Mock)
6. Filter candidate comments via PrecisionVerifier (<= 5 comments, suggestion verification)
7. Deduplicate against existing PR comments
8. Post executive review summary and inline suggestion comments to PR
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set

from action.diff_parser import extract_file_context, parse_unified_diff
from action.formatter import format_inline_comment, format_review_summary
from action.github_client import GitHubClient
from action.linters import run_static_linters
from action.providers import CandidateComment, get_provider
from action.reactions import poll_previous_reactions
from action.secret_redactor import redact_secrets
from action.telemetry import TelemetryEvent, TelemetryLogger, hash_identifier
from action.verifier import SEVERITY_WEIGHTS, PrecisionVerifier
from rl.bandit import CategoryBandit
from rl.memory import RepoConventionMemory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aion")


def parse_action_inputs() -> Dict[str, Any]:
    """Parse configuration inputs from environment variables and command line flags."""
    parser = argparse.ArgumentParser(description="Aion Code Reviewer GitHub Action")
    parser.add_argument("--repo", dest="repo", default=None, help="GitHub repository (owner/repo)")
    parser.add_argument("--pr", dest="pr_number", type=int, default=None, help="Pull request number")
    parser.add_argument("--token", dest="token", default=None, help="GitHub API Token")
    parser.add_argument("--provider", dest="provider", default=None, help="Inference provider")
    parser.add_argument("--model", dest="model", default=None, help="Model identifier")
    parser.add_argument("--api-key", dest="api_key", default=None, help="Provider API key")
    parser.add_argument("--max-comments", dest="max_comments", type=int, default=None, help="Max inline comments")
    parser.add_argument("--min-confidence", dest="min_confidence", type=float, default=None, help="Min confidence")
    parser.add_argument("--enable-telemetry", dest="enable_telemetry", default=None, help="Enable telemetry")
    parser.add_argument("--aion-state-dir", dest="aion_state_dir", default=None, help="Aion state directory")
    parser.add_argument("--mode", dest="mode", default=None, help="Review mode: visible (posts comments) or shadow (silent log)")
    parser.add_argument("--kill-switch", dest="kill_switch", action="store_true", help="Force emergency abort")

    args, _ = parser.parse_known_args()

    # 1. GitHub Token
    token = (
        args.token
        or os.getenv("INPUT_GITHUB_TOKEN")
        or os.getenv("INPUT_GITHUB-TOKEN")
        or os.getenv("GITHUB_TOKEN")
        or ""
    )

    # 2. Provider & Model
    provider = (
        args.provider
        or os.getenv("INPUT_PROVIDER")
        or "mock"
    ).strip().lower()

    model = (
        args.model
        or os.getenv("INPUT_MODEL")
        or "qwen-2.5-coder-32b"
    ).strip()

    api_key = (
        args.api_key
        or os.getenv("INPUT_API_KEY")
        or os.getenv("INPUT_API-KEY")
        or os.getenv("AION_API_KEY")
        or ""
    )

    # 3. Precision Parameters
    max_comments_env = os.getenv("INPUT_MAX_COMMENTS") or os.getenv("INPUT_MAX-COMMENTS")
    max_comments = (
        args.max_comments
        if args.max_comments is not None
        else int(max_comments_env) if max_comments_env else 5
    )

    min_conf_env = os.getenv("INPUT_MIN_CONFIDENCE") or os.getenv("INPUT_MIN-CONFIDENCE")
    min_confidence = (
        args.min_confidence
        if args.min_confidence is not None
        else float(min_conf_env) if min_conf_env else 0.7
    )

    telemetry_env = os.getenv("INPUT_ENABLE_TELEMETRY") or "true"
    enable_telemetry = (
        args.enable_telemetry.lower() in ("true", "1", "yes")
        if args.enable_telemetry is not None
        else telemetry_env.lower() in ("true", "1", "yes")
    )

    aion_dir_env = os.getenv("INPUT_AION_STATE_DIR") or os.getenv("AION_STATE_DIR")
    aion_state_dir = (
        args.aion_state_dir
        if args.aion_state_dir is not None
        else aion_dir_env if aion_dir_env else ".aion"
    )

    # 4. Pilot & Operational Controls
    mode_env = os.getenv("INPUT_MODE") or os.getenv("AION_MODE") or "visible"
    mode = (args.mode if args.mode is not None else mode_env).strip().lower()

    kill_switch_env = os.getenv("AION_KILL_SWITCH", "").strip().lower()
    kill_switch = args.kill_switch or (kill_switch_env in ("true", "1", "yes"))

    # 5. GitHub Context
    repo = args.repo or os.getenv("GITHUB_REPOSITORY") or ""
    pr_number = args.pr_number
    commit_sha = os.getenv("GITHUB_SHA") or ""

    # Parse GITHUB_EVENT_PATH if available
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if event_path and os.path.exists(event_path):
        try:
            with open(event_path, "r", encoding="utf-8") as f:
                event_data = json.load(f)
            pr_data = event_data.get("pull_request")
            if pr_data:
                if pr_number is None:
                    pr_number = pr_data.get("number")
                head_sha = pr_data.get("head", {}).get("sha")
                if head_sha:
                    commit_sha = head_sha
        except Exception as e:
            logger.warning("Failed to parse GITHUB_EVENT_PATH payload: %s", e)

    return {
        "token": token,
        "repo": repo,
        "pr_number": pr_number,
        "commit_sha": commit_sha,
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "max_comments": max_comments,
        "min_confidence": min_confidence,
        "enable_telemetry": enable_telemetry,
        "aion_state_dir": aion_state_dir,
        "mode": mode,
        "kill_switch": kill_switch,
    }


def run_action(
    config: Optional[Dict[str, Any]] = None,
    client: Optional[GitHubClient] = None,
    custom_diff: Optional[str] = None,
    memory: Optional[RepoConventionMemory] = None,
    bandit: Optional[CategoryBandit] = None,
) -> int:
    """
    Execute the review action pipeline.

    Returns exit code (0 for success).
    """
    start_time = time.time()
    cfg = config if config is not None else parse_action_inputs()

    repo = cfg.get("repo", "")
    pr_number = cfg.get("pr_number")
    commit_sha = cfg.get("commit_sha", "")
    token = cfg.get("token", "")

    if not repo or pr_number is None:
        logger.info(
            "Aion Code Reviewer: No pull request context detected (repo='%s', pr=%s). "
            "Skipping review execution.",
            repo,
            pr_number,
        )
        return 0

    # PILOT-03: Global Kill Switch
    if cfg.get("kill_switch", False) or os.getenv("AION_KILL_SWITCH", "").lower() in ("true", "1", "yes"):
        logger.warning("Aion review aborted: global kill switch AION_KILL_SWITCH is active.")
        return 0

    gh_client = client or GitHubClient(token=token)

    # Initialize Flywheel components (FLY-01 RepoConventionMemory & FLY-02 CategoryBandit)
    aion_dir = cfg.get("aion_state_dir", ".aion")
    conventions_path = os.path.join(aion_dir, "conventions.json")
    bandit_path = os.path.join(aion_dir, "bandit_state.json")

    conv_memory = memory or RepoConventionMemory.load_or_create(conventions_path)
    cat_bandit = bandit or CategoryBandit.load_or_create(bandit_path)

    # PILOT-03: Repository-level Mute check
    if conv_memory.is_muted():
        logger.info("Aion review skipped: repository %s is muted (%s).", repo, conv_memory.state.muted_reason)
        return 0

    bandit_thresholds = cat_bandit.get_all_thresholds(sample=False)
    convention_prompt = conv_memory.build_prompt_context()

    logger.info("Starting Aion review on %s PR #%d (commit: %s)", repo, pr_number, commit_sha[:8] if commit_sha else "head")

    # 1. Fetch Pull Request Diff
    if custom_diff is not None:
        diff_text = custom_diff
    else:
        diff_text = gh_client.get_pull_request_diff(repo, pr_number)

    # Enforce HARD-03b: Scrub secrets from diff prior to parsing and provider inference
    diff_text = redact_secrets(diff_text)

    if not diff_text or not diff_text.strip():
        logger.info("Empty diff retrieved for %s PR #%d. Nothing to review.", repo, pr_number)
        return 0

    # 2. Parse Unified Diff
    diff_files = parse_unified_diff(diff_text)
    if not diff_files:
        logger.info("No modifiable code files found in diff for %s PR #%d.", repo, pr_number)
        return 0

    # 3. Initialize Provider & Verifier
    provider = get_provider(
        provider_type=cfg.get("provider", "mock"),
        api_key=cfg.get("api_key"),
        model=cfg.get("model"),
    )
    max_comments = cfg.get("max_comments", 5)
    min_confidence = cfg.get("min_confidence", 0.7)
    verifier = PrecisionVerifier(
        default_max_comments=max_comments,
        default_min_confidence=min_confidence,
        category_thresholds=bandit_thresholds,
    )

    all_candidates: List[CandidateComment] = []
    analyzed_count = 0

    for df in diff_files:
        if not df.new_path or df.is_binary or df.is_deleted:
            continue

        analyzed_count += 1
        file_path = df.new_path
        language = df.language

        # Read file content if available in workspace
        file_content = ""
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    file_content = f.read()
            except Exception as e:
                logger.debug("Could not read local file %s: %s", file_path, e)

        # A. Static Linters Pre-Filtering
        if file_content:
            linter_comments = run_static_linters(file_path, file_content, language)
            all_candidates.extend(linter_comments)

        # B. Provider Review per Hunk
        for hunk in df.hunks:
            hunk_text = hunk.header + "\n" + "\n".join(
                (line.line_type + line.content if line.line_type in ("+", "-") else " " + line.content)
                for line in hunk.lines
            )

            context = ""
            if file_content and hunk.new_start:
                context = extract_file_context(
                    file_content,
                    line_start=hunk.new_start,
                    line_end=hunk.new_start + max(1, hunk.new_length),
                )
            else:
                context = hunk_text

            provider_comments = provider.generate_review(
                file_path=file_path,
                diff_hunk=hunk_text,
                context=context,
                language=language,
                convention_context=convention_prompt,
            )
            all_candidates.extend(provider_comments)

    # Filter candidates through RepoConventionMemory (suppressed categories & patterns)
    active_candidates = [
        c
        for c in all_candidates
        if not conv_memory.is_suppressed(
            category=c.category,
            comment_text=c.comment,
            rule_id=c.rule_id,
        )
    ]

    # 4. Precision Verifier Filtering
    filtered_candidates: List[CandidateComment] = []
    for df in diff_files:
        if not df.new_path:
            continue
        mod_lines = df.added_lines
        file_cands = [c for c in active_candidates if c.file_path == df.new_path]

        file_content = ""
        if os.path.exists(df.new_path):
            try:
                with open(df.new_path, "r", encoding="utf-8", errors="replace") as f:
                    file_content = f.read()
            except Exception:
                pass

        verified = verifier.filter_candidates(
            candidates=file_cands,
            modified_lines=mod_lines,
            max_comments=max_comments,
            min_confidence=min_confidence,
            file_content=file_content,
            category_thresholds=bandit_thresholds,
        )
        filtered_candidates.extend(verified)

    # Re-enforce global ceiling
    filtered_candidates.sort(
        key=lambda x: (
            SEVERITY_WEIGHTS.get(x.severity.lower(), 1),
            x.confidence,
        ),
        reverse=True,
    )
    final_candidates = filtered_candidates[:max_comments]

    # 5. Deduplicate Against Previously Posted Comments & Poll Reactions
    reaction_summary = poll_previous_reactions(
        github_client=gh_client,
        repo=repo,
        pr_number=pr_number,
        modified_lines_map={df.new_path: df.added_lines for df in diff_files if df.new_path},
    )

    # Update Flywheel (Bandit & Convention Memory) from maintainer reaction signals
    for detail in reaction_summary.reaction_details:
        cat = detail.get("category", "bug")
        r_id = detail.get("rule_id")
        body_text = detail.get("body", "")

        if detail.get("resolved") or detail.get("positive", 0) > 0:
            cat_bandit.update(cat, reward=1.0)
        if detail.get("dismissed") or detail.get("negative", 0) > 0:
            cat_bandit.update(cat, reward=-1.5)
            pattern_key = r_id or (body_text.splitlines()[0] if body_text else cat)
            conv_memory.record_dismissal(
                category=cat,
                rule_id=r_id,
                pattern=pattern_key,
                reason="Maintainer negative feedback / dismissal",
            )

    # Persist updated Flywheel state
    try:
        os.makedirs(aion_dir, exist_ok=True)
        conv_memory.save(conventions_path)
        cat_bandit.save(bandit_path)
        logger.debug("Persisted updated Aion flywheel state to %s", aion_dir)
    except Exception as e:
        logger.warning("Failed to persist Aion flywheel state: %s", e)

    existing_comments = gh_client.get_existing_review_comments(repo, pr_number)

    # PILOT-03: Process Maintainer Inline Commands (@aion mute / unmute / dismiss reasons)
    for ec in existing_comments:
        c_body = str(ec.get("body", "")).lower()
        if "@aion mute" in c_body or "/aion mute" in c_body:
            conv_memory.mute(reason="Maintainer comment issued @aion mute")
            try:
                os.makedirs(aion_dir, exist_ok=True)
                conv_memory.save(conventions_path)
            except Exception:
                pass
            logger.info("Aion review aborted: Repository %s was muted by maintainer command.", repo)
            return 0
        elif "@aion unmute" in c_body or "/aion unmute" in c_body:
            conv_memory.unmute()
            try:
                os.makedirs(aion_dir, exist_ok=True)
                conv_memory.save(conventions_path)
            except Exception:
                pass
            logger.info("Repository %s was unmuted by maintainer command.", repo)

        # One-click dismiss reasons
        for reason_tag in ("wrong", "nitpick", "already_known", "out_of_scope"):
            if f"`{reason_tag}`" in c_body or f" {reason_tag}" in c_body or c_body == reason_tag:
                cat_bandit.update("bug" if reason_tag == "wrong" else "style", reward=-1.0)
                conv_memory.record_dismissal(
                    category="bug" if reason_tag == "wrong" else "style",
                    rule_id=None,
                    pattern=reason_tag,
                    reason=f"One-click dismiss: {reason_tag}",
                )

    existing_line_paths: Set[tuple[str, int]] = {
        (str(ec.get("path")), int(ec.get("line")))
        for ec in existing_comments
        if ec.get("path") and ec.get("line") is not None
    }

    fresh_candidates = [
        c
        for c in final_candidates
        if (c.file_path, c.line_number) not in existing_line_paths
    ]

    logger.info(
        "Aion Filter: %d raw candidates -> %d verified -> %d fresh comments to post.",
        len(all_candidates),
        len(final_candidates),
        len(fresh_candidates),
    )

    # 6. Format Review Summary and Inline Comments
    formatted_inline = [
        {
            "path": c.file_path,
            "line": c.line_number,
            "side": "RIGHT",
            "body": format_inline_comment(c),
        }
        for c in fresh_candidates
    ]

    duration_sec = time.time() - start_time
    summary_body = format_review_summary(
        results=fresh_candidates,
        files_analyzed=analyzed_count,
        linter_count=1,
        duration_sec=duration_sec,
    )

    # PILOT-01: Check review mode (visible vs shadow)
    is_shadow = cfg.get("mode", "visible").strip().lower() == "shadow"

    if is_shadow:
        # Shadow mode: Log what would have been posted without posting to PR
        logger.info(
            "Aion SHADOW MODE active: %d comments verified (logged silently, no PR comments posted).",
            len(fresh_candidates),
        )
        shadow_log_path = os.path.join(aion_dir, "shadow_reviews.jsonl")
        try:
            os.makedirs(aion_dir, exist_ok=True)
            with open(shadow_log_path, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps({
                        "repo": repo,
                        "pr_number": pr_number,
                        "timestamp": time.time(),
                        "comments_count": len(fresh_candidates),
                        "comments": [c.to_dict() for c in fresh_candidates],
                        "summary": summary_body,
                    }) + "\n"
                )
        except Exception as e:
            logger.warning("Failed to append to shadow reviews log: %s", e)
        resp = {"status": "shadow_logged", "comments_count": len(fresh_candidates)}
    else:
        # 7. Post Pull Request Review
        resp = gh_client.post_review(
            repo=repo,
            pr_number=pr_number,
            commit_sha=commit_sha,
            body=summary_body,
            comments=formatted_inline,
        )

    # 8. Record Anonymized Telemetry
    if cfg.get("enable_telemetry", True):
        t_logger = TelemetryLogger(enabled=True)
        event = TelemetryEvent(
            repo_hash=hash_identifier(repo),
            pr_hash=hash_identifier(str(pr_number)),
            provider=cfg.get("provider", "mock"),
            model=cfg.get("model", "qwen-2.5-coder-32b"),
            candidates_generated=len(all_candidates),
            comments_posted=len(fresh_candidates),
            comments_suppressed=max(0, len(all_candidates) - len(fresh_candidates)),
            finding_categories=[c.category for c in fresh_candidates],
            confidences=[c.confidence for c in fresh_candidates],
            reactions_summary=reaction_summary.to_dict(),
        )
        t_logger.log_event(event)

    logger.info("Aion Review posted successfully: %s", resp.get("status", "ok"))
    return 0


def main() -> None:
    """CLI entrypoint."""
    sys.exit(run_action())


if __name__ == "__main__":
    main()

