"""
action/github_client.py

Zero-dependency GitHub REST API client for Aion Code Reviewer.
Uses standard urllib.request to interact with GitHub Pull Requests:
- Fetch raw PR unified diffs
- Retrieve PR metadata and commit SHAs
- Fetch existing review comments to avoid duplicates
- Post complete pull request reviews with inline suggestion comments
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GitHubClient:
    """Lightweight GitHub REST API client using standard urllib."""

    def __init__(
        self,
        token: str,
        base_url: str = "https://api.github.com",
        timeout: float = 10.0,
    ) -> None:
        self.token = token.strip() if token else ""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _headers(self, accept: str = "application/vnd.github.v3+json") -> Dict[str, str]:
        """Construct standard HTTP headers for GitHub REST API requests."""
        headers = {
            "Accept": accept,
            "User-Agent": "Aion-Code-Reviewer/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
    ) -> tuple[int, bytes, Dict[str, str]]:
        """Execute HTTP request with robust error handling and header tracking."""
        req_headers = headers if headers is not None else self._headers()
        req = urllib.request.Request(
            url,
            data=data,
            headers=req_headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.status
                body = resp.read()
                resp_headers = dict(resp.headers)
                return status_code, body, resp_headers
        except urllib.error.HTTPError as e:
            err_body = e.read()
            logger.warning(
                "GitHub API HTTPError %d for %s %s: %s",
                e.code,
                method,
                url,
                err_body[:200],
            )
            return e.code, err_body, dict(e.headers)
        except urllib.error.URLError as e:
            logger.error("GitHub API network error for %s %s: %s", method, url, e)
            raise

    def get_pull_request_diff(self, repo: str, pr_number: int) -> str:
        """
        Retrieve unified diff for a pull request.

        Uses Accept: application/vnd.github.v3.diff header.
        """
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
        headers = self._headers(accept="application/vnd.github.v3.diff")
        status, body, _ = self._request(url, method="GET", headers=headers)

        if status != 200:
            logger.warning(
                "Failed to fetch diff for %s PR #%d (status %d)",
                repo,
                pr_number,
                status,
            )
            return ""

        return body.decode("utf-8", errors="replace")

    def get_pull_request_info(self, repo: str, pr_number: int) -> Dict[str, Any]:
        """Fetch pull request metadata (head sha, title, author, base branch)."""
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
        status, body, _ = self._request(url, method="GET")

        if status != 200:
            logger.warning(
                "Failed to fetch PR info for %s PR #%d (status %d)",
                repo,
                pr_number,
                status,
            )
            return {}

        try:
            return json.loads(body.decode("utf-8"))
        except Exception as e:
            logger.warning("Failed to parse PR info JSON: %s", e)
            return {}

    def get_existing_review_comments(
        self, repo: str, pr_number: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieve existing review comments posted on this PR.

        Used to prevent posting duplicate review comments across re-runs.
        """
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}/comments?per_page=100"
        status, body, _ = self._request(url, method="GET")

        if status != 200:
            logger.debug(
                "Failed to fetch existing comments for %s PR #%d (status %d)",
                repo,
                pr_number,
                status,
            )
            return []

        try:
            data = json.loads(body.decode("utf-8"))
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.warning("Failed to parse comments JSON: %s", e)
            return []

    def get_comment_reactions(self, repo: str, comment_id: int) -> List[Dict[str, Any]]:
        """
        Fetch reactions for a specific pull request review comment (HARD-03).
        Official REST endpoint: GET /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions
        """
        url = f"{self.base_url}/repos/{repo}/pulls/comments/{comment_id}/reactions"
        status, body, _ = self._request(url, method="GET")
        if status != 200:
            return []
        try:
            data = json.loads(body.decode("utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def post_review(
        self,
        repo: str,
        pr_number: int,
        commit_sha: str,
        body: str,
        comments: Optional[List[Dict[str, Any]]] = None,
        event: str = "COMMENT",
    ) -> Dict[str, Any]:
        """
        Post a comprehensive PR review with optional inline comments.

        Each inline comment object should have:
            path: file path
            line: line number in modified file
            side: "RIGHT"
            body: comment text formatted with markdown suggestion block
        """
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}/reviews"
        headers = self._headers(accept="application/vnd.github.v3+json")
        headers["Content-Type"] = "application/json"

        payload: Dict[str, Any] = {
            "body": body,
            "event": event,
        }
        if commit_sha:
            payload["commit_id"] = commit_sha
        if comments:
            payload["comments"] = comments

        data = json.dumps(payload).encode("utf-8")
        status, resp_body, _ = self._request(url, method="POST", headers=headers, data=data)

        # Handle 422 errors (e.g. inline comment placement error or self-review REQUEST_CHANGES/APPROVE)
        if status == 422:
            logger.warning(
                "GitHub API returned 422. Retrying review as COMMENT with summary fallback..."
            )
            # Append findings to review body as fallback
            fallback_body = body
            if comments:
                fallback_body += "\n\n### 📝 Inline Findings (Summary Fallback)\n"
                for c in comments:
                    fallback_body += f"\n- **{c.get('path')}:{c.get('line')}**\n{c.get('body')}\n"

            payload_fallback = {
                "body": fallback_body,
                "event": "COMMENT",
            }
            if commit_sha:
                payload_fallback["commit_id"] = commit_sha

            data_fallback = json.dumps(payload_fallback).encode("utf-8")
            status, resp_body, _ = self._request(
                url, method="POST", headers=headers, data=data_fallback
            )

        if status not in (200, 201):
            logger.warning(
                "Failed to post review for %s PR #%d (status %d): %s",
                repo,
                pr_number,
                status,
                resp_body[:200],
            )
            return {"status": status, "error": resp_body.decode("utf-8", errors="replace")}

        try:
            return json.loads(resp_body.decode("utf-8"))
        except Exception:
            return {"status": status, "success": True}

    def post_issue_comment(
        self,
        repo: str,
        pr_number: int,
        body: str,
    ) -> Dict[str, Any]:
        """
        Post a comment directly to the PR conversation thread using the issue comments API.

        Endpoint: POST /repos/{repo}/issues/{pr_number}/comments
        Useful as a direct timeline comment or fallback when post_review is restricted.
        """
        url = f"{self.base_url}/repos/{repo}/issues/{pr_number}/comments"
        headers = self._headers(accept="application/vnd.github.v3+json")
        headers["Content-Type"] = "application/json"
        data = json.dumps({"body": body}).encode("utf-8")
        status, resp_body, _ = self._request(url, method="POST", headers=headers, data=data)

        if status not in (200, 201):
            logger.warning(
                "Failed to post issue comment on %s PR #%d (status %d): %s",
                repo,
                pr_number,
                status,
                resp_body[:200],
            )
            return {"status": status, "error": resp_body.decode("utf-8", errors="replace")}

        try:
            return json.loads(resp_body.decode("utf-8"))
        except Exception:
            return {"status": status, "success": True}

