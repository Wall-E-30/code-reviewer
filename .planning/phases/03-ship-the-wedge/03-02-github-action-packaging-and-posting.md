---
phase: 03-ship-the-wedge
plan: 02
type: execute
wave: 2
depends_on:
  - 03-01
files_modified:
  - action.yml
  - action/github_client.py
  - action/formatter.py
  - action/main.py
  - tests/test_github_client.py
autonomous: true
requirements:
  - GH-01
  - GH-02
must_haves:
  truths:
    - action.yml exposes a zero-hosting GitHub Composite Action with clear inputs for tokens, BYOK API keys, providers, and confidence limits.
    - GitHub client communicates with the GitHub REST API using lightweight standard HTTP to fetch PR diffs, existing review comments, and post multi-line reviews.
    - Formatter produces clean, professional inline review comments with valid GitHub suggestion blocks and a comprehensive PR summary body.
    - Entrypoint in action/main.py ties the diff parser, linter, provider, verifier, and GitHub client into a robust, exit-code-safe workflow.
  artifacts:
    - action.yml
    - action/github_client.py
    - action/formatter.py
    - action/main.py
    - tests/test_github_client.py
  key_links:
    - action.yml runs action/main.py in user CI.
    - action/main.py calls action/github_client.py to retrieve PR diffs and post review comments.
    - action/formatter.py renders candidate comments into GitHub suggestion blocks.
---

<objective>
Package Aion into an automated GitHub Action: build the GitHub REST API client for reading PRs and posting reviews, format inline comments with valid suggestion blocks and summary headers, and assemble the main CLI entrypoint executed by `action.yml`.

Purpose: Deliver the core developer interface where PR reviews are posted directly inside user pull requests.
Output: `action.yml`, GitHub API client, comment formatter, and action entrypoint.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/03-ship-the-wedge/RESEARCH.md
@.planning/phases/03-ship-the-wedge/03-01-hybrid-pipeline-and-providers.md
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement GitHub REST API Client in action/github_client.py</name>
  <files>action/github_client.py</files>
  <action>
1. In `action/github_client.py`, implement `GitHubClient` using Python's standard `urllib.request` (zero heavy external HTTP dependencies):
   - Auth header: `Authorization: Bearer <token>`, `Accept: application/vnd.github.v3+json`.
   - Methods:
     - `get_pull_request_diff(repo: str, pr_number: int) -> str`: Requests PR with `Accept: application/vnd.github.v3.diff` header.
     - `get_pull_request_info(repo: str, pr_number: int) -> Dict[str, Any]`: Fetches PR title, author, base, head SHA, commit count.
     - `get_existing_review_comments(repo: str, pr_number: int) -> List[Dict[str, Any]]`: Retrieves existing comments to avoid duplicate postings.
     - `post_review(repo: str, pr_number: int, commit_sha: str, body: str, comments: List[Dict[str, Any]], event: str = "COMMENT") -> Dict[str, Any]`:
       - Posts a formal PR review with top-level `body` and list of inline `comments: [{"path": file_path, "line": line_no, "side": "RIGHT", "body": comment_body}]`.
     - Error handling: Graceful handling of rate limits (`403`), network timeouts, and permissions errors.
  </action>
  <verify>
python -c "from action.github_client import GitHubClient; client = GitHubClient(token='fake_token'); assert hasattr(client, 'get_pull_request_diff'); assert hasattr(client, 'post_review'); print('GitHubClient verified')"
  </verify>
</task>

<task>
  <name>Build High-Precision Comment and Summary Formatter in action/formatter.py</name>
  <files>action/formatter.py</files>
  <action>
1. In `action/formatter.py`, implement comment and summary formatting:
   - `format_inline_comment(candidate: CandidateComment) -> str`:
     - Header: Category icon (`🛡️ Security`, `🐛 Bug`, `⚡ Performance`, `🧹 Code Quality`).
     - Metadata line: Confidence score and severity badge.
     - Description: Concise explanation of the defect and why it matters.
     - Fix suggestion: Valid GitHub suggestion markdown block:
       ```suggestion
       <replacement code>
       ```
     - Attribution & Privacy footer: Link to Aion and `DATA_POLICY.md`.
   - `format_review_summary(results: List[CandidateComment], files_analyzed: int, linter_count: int, duration_sec: float) -> str`:
     - Clean Markdown overview:
       - Header banner (`### 🛡️ Aion Code Review Report`).
       - Status badge (`Passed - No issues detected` or `2 Actionable Findings Detected`).
       - Overview table with Analyzed Files, Linters Ran, Defect Count, Execution Time.
       - Quick checklist of findings.
       - Data policy privacy guarantee statement.
  </action>
  <verify>
python -c "from action.formatter import format_inline_comment, format_review_summary; from action.providers import CandidateComment; c = CandidateComment('a.py', 10, 'bug', 'critical', 'Off-by-one error', 'for i in range(n):', 0.95); body = format_inline_comment(c); assert '```suggestion' in body; assert 'Off-by-one' in body; print('Formatter verified')"
  </verify>
</task>

<task>
  <name>Build Action Workflow action.yml, Entrypoint action/main.py, and Tests</name>
  <files>action.yml, action/main.py, tests/test_github_client.py</files>
  <action>
1. Create `action.yml` defining the GitHub Action:
   - Name: `Aion Code Reviewer`
   - Description: `High-precision, verifiable AI code reviewer for GitHub Pull Requests`
   - Inputs:
     - `github-token` (required, default `${{ github.token }}`)
     - `api-key` (optional, BYOK)
     - `provider` (default `mock`)
     - `model` (default `qwen-2.5-coder-32b`)
     - `max-comments` (default `5`)
     - `min-confidence` (default `0.7`)
     - `enable-telemetry` (default `true`)
   - Runs as composite action on Python 3.11/3.12, invoking `python -m action.main`.
2. In `action/main.py`:
   - Parse inputs from `GITHUB_ACTIONS` environment variables.
   - Detect GitHub repository and PR number from `GITHUB_REPOSITORY` and `GITHUB_EVENT_PATH`.
   - Orchestrate pipeline:
     a. Fetch PR diff via `GitHubClient`.
     b. Parse modified files via `DiffParser`.
     c. Run pre-filter linters on changed files.
     d. Query LLM provider on changed hunks with scope context.
     e. Run `PrecisionVerifier` (max 5 comments, suggestion check, confidence filter).
     f. Check against existing PR comments to prevent duplicate comments on re-runs.
     g. Post review via `GitHubClient.post_review`.
3. In `tests/test_github_client.py`:
   - Unit tests with mock HTTP responses for `GitHubClient`.
   - Test formatter suggestion rendering.
   - Test `action/main.py` pipeline execution in mock mode.
  </action>
  <verify>
python -m pytest tests/test_github_client.py -v
  </verify>
</task>

</tasks>

