"""
action/formatter.py

High-precision comment and review summary formatter for Aion Code Reviewer.
Renders GitHub inline review comments with 1-click suggestion blocks (```suggestion)
and formats executive PR review summaries with status badges, metrics, and data guarantees.
"""

from __future__ import annotations

from typing import List, Optional

from action.providers import CandidateComment

CATEGORY_METADATA = {
    "security": {
        "icon": "🛡️",
        "title": "Security Vulnerability",
    },
    "bug": {
        "icon": "🐛",
        "title": "Logic Bug",
    },
    "performance": {
        "icon": "⚡",
        "title": "Performance Issue",
    },
    "style": {
        "icon": "🧹",
        "title": "Code Quality Finding",
    },
    "nitpick": {
        "icon": "🔍",
        "title": "Stylistic Note",
    },
}

DEFAULT_FOOTER = (
    "*Reported by [Aion Code Reviewer](https://github.com/Wall-E-30/code-reviewer) "
    "• [Data & Privacy Policy](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/DATA_POLICY.md)*"
)

PRIVACY_STATEMENT = (
    "*🔒 Zero-Retention Guarantee: Source code is examined strictly in-memory "
    "within your GitHub Action runner. No code is stored, logged, or retained. "
    "Read our [Data & Privacy Policy](file:///c:/Users/Sharanya%20Nagar/Desktop/Projects/code-reviewer/DATA_POLICY.md).*"
)


def format_inline_comment(
    candidate: CandidateComment,
    footer: Optional[str] = None,
) -> str:
    """
    Format a CandidateComment into a professional GitHub inline review comment
    containing severity badge, explanation, and 1-click suggestion replacement block.
    """
    cat_info = CATEGORY_METADATA.get(
        candidate.category.lower(),
        {"icon": "💡", "title": "Finding"},
    )
    icon = cat_info["icon"]
    title = cat_info["title"]

    rule_str = f" (`{candidate.rule_id}`)" if candidate.rule_id else ""
    header = f"### {icon} Aion Finding: {title}{rule_str}"

    confidence_pct = int(round(candidate.confidence * 100))
    metadata = f"**Confidence:** {confidence_pct}% | **Severity:** {candidate.severity.capitalize()}"

    description = candidate.comment.strip()

    parts = [header, metadata, "", description]

    if candidate.suggestion is not None and candidate.suggestion.strip():
        # Ensure suggestion is formatted inside a GitHub suggestion markdown block
        clean_suggestion = candidate.suggestion.rstrip()
        parts.extend(["", "```suggestion", clean_suggestion, "```"])

    comment_footer = footer if footer is not None else DEFAULT_FOOTER
    parts.extend(["", comment_footer])

    return "\n".join(parts)


def format_review_summary(
    results: List[CandidateComment],
    files_analyzed: int,
    linter_count: int,
    duration_sec: float,
) -> str:
    """
    Format an executive Markdown review summary for the top-level pull request review.
    """
    findings_count = len(results)

    header = "### 🛡️ Aion Code Review Report"

    if findings_count == 0:
        status_callout = (
            "> ✅ **Passed — No actionable defects or security vulnerabilities detected.**\n"
            "> Your pull request changes meet high-precision quality and security criteria."
        )
    else:
        finding_noun = "Finding" if findings_count == 1 else "Findings"
        status_callout = (
            f"> ⚠️ **{findings_count} Actionable {finding_noun} Detected — Review suggested fixes below.**\n"
            f"> All inline comments include 1-click GitHub suggestion blocks to apply fixes directly."
        )

    overview_table = (
        "| Metric | Value |\n"
        "|:---|:---|\n"
        f"| **Files Analyzed** | `{files_analyzed}` |\n"
        f"| **Static Linters Active** | `{linter_count}` |\n"
        f"| **Actionable Findings** | `{findings_count}` |\n"
        f"| **Analysis Latency** | `{duration_sec:.2f}s` |"
    )

    parts = [header, "", status_callout, "", overview_table]

    if findings_count > 0:
        checklist_rows = [
            "#### Findings Overview",
            "| Location | Category | Severity | Summary |",
            "|:---|:---:|:---:|:---|",
        ]
        for f in results:
            cat_info = CATEGORY_METADATA.get(f.category.lower(), {"icon": "💡"})
            icon = cat_info["icon"]
            loc = f"`{f.file_path}:{f.line_number}`"
            cat = f"{icon} {f.category.capitalize()}"
            sev = f.severity.capitalize()
            # Truncate summary if long
            summary_txt = f.comment.replace("\n", " ").strip()
            if len(summary_txt) > 75:
                summary_txt = summary_txt[:72] + "..."
            checklist_rows.append(f"| {loc} | {cat} | {sev} | {summary_txt} |")

        parts.extend(["", "\n".join(checklist_rows)])

    parts.extend(["", "---", PRIVACY_STATEMENT])

    return "\n".join(parts)

