"""
action/diff_parser.py

Unified diff parser and file context extractor for GitHub Action code review.
Parses multi-file unified diffs, tracks line numbering, maps languages,
identifies added/modified line boundaries, and extracts surrounding code scope.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set

# Extension to language mapping
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".pyx": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
}

HUNK_HEADER_RE = re.compile(
    r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)$"
)
GIT_DIFF_RE = re.compile(
    r"^diff --git\s+(?:\"?a/(.*?)\"?|\"?(\S+)\"?)\s+(?:\"?b/(.*?)\"?|\"?(\S+)\"?)$"
)
SCOPE_PATTERN_RE = re.compile(
    r"^\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\(|"
    r"^\s*class\s+([a-zA-Z0-9_]+)|"
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)|"
    r"^\s*(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\("
)


@dataclass
class DiffLine:
    """A single line inside a unified diff hunk."""

    line_type: str  # '+', '-', ' ', '\\'
    content: str
    old_line_number: Optional[int] = None
    new_line_number: Optional[int] = None


@dataclass
class DiffHunk:
    """A parsed hunk within a file diff."""

    old_start: int
    old_length: int
    new_start: int
    new_length: int
    header: str
    lines: List[DiffLine] = field(default_factory=list)
    added_lines: Set[int] = field(default_factory=set)
    modified_lines: Set[int] = field(default_factory=set)


@dataclass
class DiffFile:
    """A parsed file diff containing one or more hunks."""

    old_path: Optional[str]
    new_path: Optional[str]
    hunks: List[DiffHunk] = field(default_factory=list)
    language: str = "unknown"
    is_new: bool = False
    is_deleted: bool = False
    is_binary: bool = False
    added_lines: Set[int] = field(default_factory=set)
    modified_lines: Set[int] = field(default_factory=set)


@dataclass
class ReviewContext:
    """Context window surrounding modified code prepared for LLM review."""

    file_path: str
    language: str
    hunk_diff: str
    enclosing_scope: str = ""
    surrounding_code: str = ""
    modified_lines: Set[int] = field(default_factory=set)
    target_line: Optional[int] = None


def detect_language(file_path: Optional[str]) -> str:
    """Determine programming language identifier from file extension."""
    if not file_path:
        return "unknown"
    _, ext = os.path.splitext(file_path.lower())
    return LANGUAGE_EXTENSIONS.get(ext, "unknown")


def _clean_path(raw: str) -> Optional[str]:
    """Clean diff file path by stripping git prefixes (a/, b/) and quotes."""
    path_str = raw.strip()
    if (path_str.startswith('"') and path_str.endswith('"')) or (
        path_str.startswith("'") and path_str.endswith("'")
    ):
        path_str = path_str[1:-1]
    if not path_str or path_str == "/dev/null":
        return None
    if "\t" in path_str:
        path_str = path_str.split("\t")[0].strip()
    if path_str.startswith("a/") or path_str.startswith("b/"):
        return path_str[2:]
    return path_str


def parse_unified_diff(diff_str: str) -> List[DiffFile]:
    """
    Parse a unified diff string into structured DiffFile and DiffHunk objects.

    Tracks old and new line numbers, identifies added and modified line sets,
    and infers file languages.
    """
    if not diff_str or not diff_str.strip():
        return []

    files: List[DiffFile] = []
    current_file: Optional[DiffFile] = None
    current_hunk: Optional[DiffHunk] = None
    old_lineno: int = 0
    new_lineno: int = 0

    lines = diff_str.splitlines()

    for line in lines:
        if line.startswith("diff --git"):
            # New file encountered
            if current_file is not None:
                files.append(current_file)
            m = GIT_DIFF_RE.match(line)
            old_p = None
            new_p = None
            if m:
                old_p = m.group(1) or m.group(2)
                new_p = m.group(3) or m.group(4)
                if old_p:
                    old_p = _clean_path(old_p)
                if new_p:
                    new_p = _clean_path(new_p)

            current_file = DiffFile(
                old_path=old_p,
                new_path=new_p,
                language=detect_language(new_p or old_p),
            )
            current_hunk = None
            continue

        if line.startswith("--- "):
            raw_path = line[4:]
            cleaned = _clean_path(raw_path)
            # If current_file already has hunks, this is a new file diff
            if current_file is not None and len(current_file.hunks) > 0:
                files.append(current_file)
                current_file = None

            if current_file is None:
                current_file = DiffFile(
                    old_path=cleaned,
                    new_path=None,
                    is_new=(cleaned is None),
                    language=detect_language(cleaned),
                )
            else:
                current_file.old_path = cleaned
                if cleaned is None:
                    current_file.is_new = True
                if current_file.language == "unknown" and cleaned:
                    current_file.language = detect_language(cleaned)
            continue

        if line.startswith("+++ "):
            raw_path = line[4:]
            cleaned = _clean_path(raw_path)
            if current_file is None:
                current_file = DiffFile(
                    old_path=None,
                    new_path=cleaned,
                    is_deleted=(cleaned is None),
                    language=detect_language(cleaned),
                )
            else:
                current_file.new_path = cleaned
                if cleaned is None:
                    current_file.is_deleted = True
                if cleaned:
                    current_file.language = detect_language(cleaned)
            continue

        if line.startswith("Binary files ") and " differ" in line:
            if current_file is not None:
                current_file.is_binary = True
            continue

        if line.startswith("deleted file mode"):
            if current_file is not None:
                current_file.is_deleted = True
            continue

        if line.startswith("new file mode"):
            if current_file is not None:
                current_file.is_new = True
            continue

        hunk_match = HUNK_HEADER_RE.match(line)
        if hunk_match:
            if current_file is None:
                current_file = DiffFile(
                    old_path="unknown",
                    new_path="unknown",
                    language="unknown",
                )

            old_start = int(hunk_match.group(1))
            old_length = (
                int(hunk_match.group(2))
                if hunk_match.group(2) is not None
                else 1
            )
            new_start = int(hunk_match.group(3))
            new_length = (
                int(hunk_match.group(4))
                if hunk_match.group(4) is not None
                else 1
            )

            current_hunk = DiffHunk(
                old_start=old_start,
                old_length=old_length,
                new_start=new_start,
                new_length=new_length,
                header=line,
            )
            current_file.hunks.append(current_hunk)
            old_lineno = old_start
            new_lineno = new_start
            continue

        # In-hunk line processing
        if current_hunk is not None and current_file is not None:
            if line.startswith("+"):
                content = line[1:]
                diff_line = DiffLine(
                    line_type="+",
                    content=content,
                    old_line_number=None,
                    new_line_number=new_lineno,
                )
                current_hunk.lines.append(diff_line)
                current_hunk.added_lines.add(new_lineno)
                current_hunk.modified_lines.add(new_lineno)
                current_file.added_lines.add(new_lineno)
                current_file.modified_lines.add(new_lineno)
                new_lineno += 1
            elif line.startswith("-"):
                content = line[1:]
                diff_line = DiffLine(
                    line_type="-",
                    content=content,
                    old_line_number=old_lineno,
                    new_line_number=None,
                )
                current_hunk.lines.append(diff_line)
                current_hunk.modified_lines.add(new_lineno)
                current_file.modified_lines.add(new_lineno)
                old_lineno += 1
            elif line.startswith(" ") or line == "":
                content = line[1:] if line.startswith(" ") else line
                diff_line = DiffLine(
                    line_type=" ",
                    content=content,
                    old_line_number=old_lineno,
                    new_line_number=new_lineno,
                )
                current_hunk.lines.append(diff_line)
                old_lineno += 1
                new_lineno += 1
            elif line.startswith("\\"):
                diff_line = DiffLine(
                    line_type="\\",
                    content=line,
                    old_line_number=None,
                    new_line_number=None,
                )
                current_hunk.lines.append(diff_line)

    if current_file is not None:
        files.append(current_file)

    return files


def extract_file_context(
    file_content: str,
    line_start: int,
    line_end: int,
    window: int = 15,
) -> str:
    """
    Extract enclosing scope and surrounding context window around modified lines.

    Returns formatted lines with line numbers and scope header comment.
    """
    if not file_content:
        return ""

    lines = file_content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return ""

    line_start = max(1, min(line_start, total_lines))
    line_end = max(line_start, min(line_end, total_lines))

    # Detect enclosing function or class by scanning upwards
    scope_header = ""
    scope_lineno = 0
    for idx in range(line_start - 2, -1, -1):
        line = lines[idx]
        if SCOPE_PATTERN_RE.match(line):
            scope_header = line.strip()
            scope_lineno = idx + 1
            break

    ctx_start = max(1, line_start - window)
    ctx_end = min(total_lines, line_end + window)

    formatted_lines: List[str] = []
    if scope_header:
        formatted_lines.append(f"# Enclosing Scope: {scope_header} (line {scope_lineno})")
        if scope_lineno < ctx_start:
            formatted_lines.append("# ...")

    for lineno in range(ctx_start, ctx_end + 1):
        raw_line = lines[lineno - 1]
        marker = ">" if line_start <= lineno <= line_end else " "
        formatted_lines.append(f"{marker} {lineno:4d} | {raw_line}")

    return "\n".join(formatted_lines)
