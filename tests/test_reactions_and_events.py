"""
tests/test_reactions_and_events.py

Verifies GitHub reaction polling and App webhook events using recorded real API fixtures (HARD-03):
- Action subsequent-run polling over recorded GitHub PR review comments.
- App reaction event dispatching (+1, -1) adjusting bandit thresholds.
- App review thread resolved events (+1.0 reward to category).
- App comment deleted events (-1.5 penalty and dismissal recorded).
"""

import json
import os
from unittest.mock import MagicMock
import pytest

from action.reactions import poll_previous_reactions
from server.github_app import GitHubAppHandler
from rl.bandit import CategoryBandit
from rl.memory import RepoConventionMemory

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "github")


def load_fixture(filename: str):
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_action_reaction_polling_with_real_comments_fixture():
    """Verify poll_previous_reactions correctly parses reactions and replies from real GitHub comment payloads."""
    raw_comments = load_fixture("pr_comments.json")

    mock_client = MagicMock()
    mock_client.get_existing_review_comments.return_value = raw_comments

    # Test polling
    summary = poll_previous_reactions(
        github_client=mock_client,
        repo="owner/repo",
        pr_number=42,
        modified_lines_map={"app/auth.py": {42}},
    )

    # 2 Aion comments in fixture (1001 and 1003)
    assert summary.total_tracked == 2
    assert summary.positive_reactions == 3  # comment 1001 has 2 +1 and 1 heart reactions
    assert summary.negative_reactions == 2  # comment 1003 has 1 -1 and 1 confused
    assert summary.resolved_count == 1      # comment 1001 has reply "Fixed in latest commit"
    assert summary.dismissed_count == 1     # comment 1003 has reply "wontfix"


def test_app_webhook_reaction_created_fixture():
    """Verify GitHub App reaction webhook updates CategoryBandit."""
    payload = load_fixture("webhook_reaction_created.json")
    bandit = CategoryBandit()
    initial_sec_threshold = bandit.get_threshold("security")

    handler = GitHubAppHandler(bandit=bandit)
    result = handler.dispatch_event("reaction", payload)

    assert result["status"] == "processed"
    assert result["category"] == "security"
    assert result["reaction"] == "+1"
    assert result["reward"] == 1.0


def test_app_webhook_comment_deleted_fixture():
    """Verify GitHub App comment deleted event records dismissal in RepoConventionMemory."""
    payload = load_fixture("webhook_comment_deleted.json")
    bandit = CategoryBandit()
    memory = RepoConventionMemory()

    handler = GitHubAppHandler(bandit=bandit, convention_memory=memory)
    result = handler.dispatch_event("pull_request_review_comment", payload)

    assert result["status"] == "dismissal_recorded"
    assert "Unused import" in result["pattern"]
    assert len(memory.state.suppressed_patterns) >= 1


def test_app_webhook_thread_resolved_fixture():
    """Verify GitHub App thread resolved event rewards the category."""
    payload = load_fixture("webhook_thread_resolved.json")
    bandit = CategoryBandit()

    handler = GitHubAppHandler(bandit=bandit)
    result = handler.dispatch_event("pull_request_review_thread", payload)

    assert result["status"] == "thread_processed"
    assert result["action"] == "resolved"
    assert result["category"] == "security"
    assert result["reward"] == 1.0
