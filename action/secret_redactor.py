"""
action/secret_redactor.py

High-assurance secret and credential redaction filter (HARD-03b).
Protects confidential developer credentials before transmitting diffs or code to LLMs.
Detects and scrubs:
- OpenAI, Anthropic, HuggingFace, GitHub, Slack API keys
- AWS access keys and secrets
- RSA / OpenSSH private keys
- Password assignments and generic authentication tokens
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

# Comprehensive credential regex patterns
SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    # Private Keys
    (
        "private_key",
        re.compile(
            r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE\s+KEY-----",
            re.MULTILINE,
        ),
    ),
    # GitHub Tokens
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b")),
    # OpenAI API Keys
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,255}\b")),
    # Anthropic API Keys
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,255}\b")),
    # Hugging Face Tokens
    ("huggingface_token", re.compile(r"\bhf_[A-Za-z0-9]{20,255}\b")),
    # AWS Access Key ID
    ("aws_access_key", re.compile(r"\b(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b")),
    # Slack Tokens
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,255}\b")),
    # Generic password / secret assignments in code
    (
        "assigned_secret",
        re.compile(
            r"(?i)\b(password|passwd|pass|db_pass|secret|api_key|apikey|auth_token|access_token|private_token)\s*[:=]\s*['\"]([^'\"]{6,})['\"]",
        ),
    ),
]


def redact_secrets(text: str) -> str:
    """
    Scan input text (diff, code snippet, or prompt) and replace identified credentials
    with [REDACTED_SECRET:<type>] placeholders.
    """
    if not text:
        return text

    sanitized = text

    for secret_type, pattern in SECRET_PATTERNS:
        if secret_type == "assigned_secret":
            # Preserve the variable assignment key, redact only the secret value
            def _replace_assigned(m: re.Match) -> str:
                key_name = m.group(1)
                return f'{key_name}="[REDACTED_SECRET:{key_name.lower()}]"'

            sanitized = pattern.sub(_replace_assigned, sanitized)
        else:
            replacement = f"[REDACTED_SECRET:{secret_type}]"
            sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def contains_secrets(text: str) -> bool:
    """Check whether input text contains unredacted credentials."""
    if not text:
        return False
    for _, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return True
    return False
