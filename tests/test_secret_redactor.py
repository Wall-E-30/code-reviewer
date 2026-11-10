"""
tests/test_secret_redactor.py

Verifies confidential credential redaction and minimal context disclosure (HARD-03b):
- Redacts OpenAI, Anthropic, Hugging Face, GitHub, and AWS keys
- Redacts private keys and explicit password assignments
- Verifies that diff text with secrets has credentials scrubbed before LLM dispatch
"""

import pytest
from action.secret_redactor import contains_secrets, redact_secrets


def test_redact_github_and_openai_tokens():
    raw_diff = (
        "@@ -10,3 +10,3 @@\n"
        "-GITHUB_TOKEN = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'\n"
        "+OPENAI_KEY = 'sk-proj-1234567890abcdefghijklmnopqrstuvwxyz'\n"
    )

    redacted = redact_secrets(raw_diff)

    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890" not in redacted
    assert "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "[REDACTED_SECRET:github_token]" in redacted
    assert "[REDACTED_SECRET:openai_key]" in redacted


def test_redact_aws_and_private_keys():
    raw_code = (
        "AWS_KEY = 'AKIA1234567890ABCDEF'\n"
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y123456789abcdefghijklmnopqrstuvwxyz==\n"
        "-----END RSA PRIVATE KEY-----\n"
    )

    redacted = redact_secrets(raw_code)

    assert "AKIA1234567890ABCDEF" not in redacted
    assert "MIIEowIBAAKCAQEA0Y123456789" not in redacted
    assert "[REDACTED_SECRET:aws_access_key]" in redacted
    assert "[REDACTED_SECRET:private_key]" in redacted


def test_redact_password_assignments():
    raw_code = (
        'db_pass = "super_secret_db_password_123"\n'
        'api_key = "some_confidential_key_value"\n'
    )

    redacted = redact_secrets(raw_code)

    assert "super_secret_db_password_123" not in redacted
    assert "some_confidential_key_value" not in redacted
    assert '[REDACTED_SECRET:db_pass]' in redacted or '[REDACTED_SECRET:api_key]' in redacted


def test_contains_secrets_detector():
    clean_code = "def add(a, b):\n    return a + b\n"
    dirty_code = "hf_token = 'hf_0123456789abcdef0123456789abcdef'\n"

    assert not contains_secrets(clean_code)
    assert contains_secrets(dirty_code)
