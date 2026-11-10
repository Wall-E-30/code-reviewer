"""
action/redactor.py

Diff Secret Redaction & Minimal Context Window Engine (HARD-03b).
Redacts credentials, API keys, tokens, and private keys from diffs before LLM calls
or CI logging, and bounds diff context to minimize leakage and token consumption.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Comprehensive regex patterns for credentials and tokens
SECRET_PATTERNS = [
    # AWS Access Key ID
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "AWS_ACCESS_KEY"),
    # AWS Secret Key pattern
    (re.compile(r"(?i)\b(aws_secret_access_key|aws_secret_key)\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"), "AWS_SECRET_KEY"),
    # GitHub Tokens (Personal, OAuth, User-to-Server, Server-to-Server, Refresh)
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b"), "GITHUB_TOKEN"),
    (re.compile(r"\b(github_pat_[A-Za-z0-9_]{82})\b"), "GITHUB_FINE_GRAINED_PAT"),
    # OpenAI API Key
    (re.compile(r"\b(sk-[A-Za-z0-9]{20,T3BlbkFJ[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{32,})\b"), "OPENAI_API_KEY"),
    # Anthropic API Key
    (re.compile(r"\b(sk-ant-[A-Za-z0-9_\-]{32,})\b"), "ANTHROPIC_API_KEY"),
    # Generic Private Key (RSA, DSA, EC, OPENSSH)
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "PRIVATE_KEY"),
    # Slack Tokens (Bot, User, Webhook)
    (re.compile(r"\b(xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9_\-]*)\b"), "SLACK_TOKEN"),
    # Generic High-Entropy API Key / Bearer Token assignment
    (re.compile(r"(?i)\b(api_key|apikey|secret_key|auth_token|bearer_token)\s*[:=]\s*['\"]([A-Za-z0-9_\-\.]{24,})['\"]"), "GENERIC_SECRET"),
]


def redact_secrets_from_diff(diff_text: str) -> Tuple[str, List[str]]:
    """
    Scan a diff string and replace sensitive tokens with [REDACTED_SECRET:<type>].

    Returns:
        (redacted_diff_text, list_of_redacted_types)
    """
    if not diff_text:
        return "", []

    redacted = diff_text
    found_types: List[str] = []

    for pattern, secret_type in SECRET_PATTERNS:
        matches = pattern.findall(redacted)
        if matches:
            found_types.append(secret_type)
            # Handle patterns with capture groups vs single match
            if secret_type in ("AWS_SECRET_KEY", "GENERIC_SECRET"):
                def _replace_kv(m):
                    prefix = m.group(1)
                    return f"{prefix} = \"[REDACTED_SECRET:{secret_type}]\""
                redacted = pattern.sub(_replace_kv, redacted)
            else:
                redacted = pattern.sub(f"[REDACTED_SECRET:{secret_type}]", redacted)

    return redacted, found_types


def extract_minimal_diff_context(diff_text: str, max_surrounding_lines: int = 25) -> str:
    """
    Bound surrounding unchanged context lines in a unified diff hunk to at most
    max_surrounding_lines above and below modified lines, minimizing token consumption
    and preventing leakage of adjacent unrelated source code.
    """
    if not diff_text or not diff_text.strip():
        return ""

    lines = diff_text.splitlines()
    output_lines: List[str] = []

    in_hunk = False
    context_buffer: List[str] = []

    for line in lines:
        if line.startswith("@@"):
            in_hunk = True
            output_lines.extend(context_buffer[-max_surrounding_lines:])
            context_buffer.clear()
            output_lines.append(line)
        elif not in_hunk:
            output_lines.append(line)
        else:
            if line.startswith("+") or line.startswith("-"):
                # Modified line: flush context buffer (capped)
                if context_buffer:
                    output_lines.extend(context_buffer[-max_surrounding_lines:])
                    context_buffer.clear()
                output_lines.append(line)
            else:
                # Unchanged context line
                context_buffer.append(line)
                if len(context_buffer) > max_surrounding_lines * 2:
                    context_buffer.pop(0)

    if context_buffer:
        output_lines.extend(context_buffer[:max_surrounding_lines])

    return "\n".join(output_lines)


def sanitize_log_message(msg: str) -> str:
    """
    Scrub secrets and tokens from log messages before outputting to stdout or CI.
    """
    redacted, _ = redact_secrets_from_diff(msg)
    return redacted
