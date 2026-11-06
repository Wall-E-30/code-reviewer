"""
action: Core GitHub Action Review Intelligence Engine.
Provides unified diff parsing, multi-provider LLM review generation,
static linters, and precision verifier filtering.
"""

from action.diff_parser import (
    DiffFile,
    DiffHunk,
    DiffLine,
    ReviewContext,
    extract_file_context,
    parse_unified_diff,
)
from action.formatter import format_inline_comment, format_review_summary
from action.github_client import GitHubClient
from action.linters import run_static_linters
from action.main import run_action
from action.providers import (
    BaseReviewProvider,
    CandidateComment,
    GroqProvider,
    HuggingFaceProvider,
    MockReviewProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
    get_provider,
)
from action.reactions import ReactionSummary, poll_previous_reactions
from action.telemetry import TelemetryEvent, TelemetryLogger, hash_identifier
from action.verifier import PrecisionVerifier

__all__ = [
    "DiffFile",
    "DiffHunk",
    "DiffLine",
    "ReviewContext",
    "extract_file_context",
    "parse_unified_diff",
    "CandidateComment",
    "BaseReviewProvider",
    "MockReviewProvider",
    "GroqProvider",
    "OpenRouterProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "HuggingFaceProvider",
    "get_provider",
    "run_static_linters",
    "PrecisionVerifier",
    "GitHubClient",
    "format_inline_comment",
    "format_review_summary",
    "run_action",
    "TelemetryEvent",
    "TelemetryLogger",
    "hash_identifier",
    "ReactionSummary",
    "poll_previous_reactions",
]
