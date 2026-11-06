"""
action/linters.py

Static linter pre-filtering engine for Aion Code Reviewer.
Runs Ruff and AST vulnerability inspection (SQL injection, dangerous eval/exec,
bare except, shell=True) on modified files before LLM inference.
"""

from __future__ import annotations

import ast
import json
import logging
import re
import subprocess
import sys
from typing import List, Optional

from action.providers import CandidateComment

logger = logging.getLogger(__name__)

SQL_KEYWORDS_RE = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|FROM|WHERE)\b", re.IGNORECASE
)


class ASTSecurityVisitor(ast.NodeVisitor):
    """Inspects Python Abstract Syntax Trees for critical defects and vulnerabilities."""

    def __init__(self, file_path: str, code_lines: List[str]) -> None:
        self.file_path = file_path
        self.code_lines = code_lines
        self.findings: List[CandidateComment] = []
        self.flagged_sqli_lines: set[int] = set()

    def _get_line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.code_lines):
            return self.code_lines[lineno - 1]
        return ""

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Detect SQL injection via string concatenation or %-formatting."""
        if isinstance(node.op, (ast.Add, ast.Mod)) and node.lineno not in self.flagged_sqli_lines:
            has_sql = False
            for side in (node.left, node.right):
                if isinstance(side, ast.Constant) and isinstance(side.value, str):
                    if SQL_KEYWORDS_RE.search(side.value):
                        has_sql = True
                        break
            if has_sql:
                self.flagged_sqli_lines.add(node.lineno)
                line_str = self._get_line(node.lineno)
                suggestion = (
                    line_str.replace("+", ",").replace("%", ",") + "  # Parameterize query"
                    if line_str
                    else None
                )
                self.findings.append(
                    CandidateComment(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        category="security",
                        severity="critical",
                        comment="Potential SQL Injection vulnerability: dynamic SQL query constructed via string concatenation or formatting. Use parameterized SQL queries.",
                        suggestion=suggestion,
                        confidence=0.95,
                        rule_id="sql-injection-risk",
                    )
                )
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """Detect SQL injection via f-string formatting."""
        if node.lineno not in self.flagged_sqli_lines:
            has_formatted = any(isinstance(v, ast.FormattedValue) for v in node.values)
            if has_formatted:
                has_sql = any(
                    isinstance(v, ast.Constant)
                    and isinstance(v.value, str)
                    and SQL_KEYWORDS_RE.search(v.value)
                    for v in node.values
                )
                if has_sql:
                    self.flagged_sqli_lines.add(node.lineno)
                    line_str = self._get_line(node.lineno)
                    self.findings.append(
                        CandidateComment(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            category="security",
                            severity="critical",
                            comment="Potential SQL Injection vulnerability: dynamic SQL query constructed via f-string formatting. Use parameterized SQL queries.",
                            suggestion=line_str + "  # Parameterize query" if line_str else None,
                            confidence=0.95,
                            rule_id="sql-injection-risk",
                        )
                    )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Detect bare except or broad BaseException catches."""
        if node.type is None:
            # Bare except:
            line_str = self._get_line(node.lineno)
            suggestion = line_str.replace("except:", "except Exception:") if line_str else "except Exception:"
            self.findings.append(
                CandidateComment(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    category="bug",
                    severity="major",
                    comment="Bare 'except:' catches BaseException (including SystemExit, KeyboardInterrupt). Catch 'Exception' or specific errors instead.",
                    suggestion=suggestion,
                    confidence=0.95,
                    rule_id="bare-except",
                )
            )
        elif isinstance(node.type, ast.Name) and node.type.id == "BaseException":
            line_str = self._get_line(node.lineno)
            suggestion = line_str.replace("BaseException", "Exception") if line_str else "except Exception:"
            self.findings.append(
                CandidateComment(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    category="bug",
                    severity="major",
                    comment="Catching 'BaseException' catches system exit and interrupt signals. Catch 'Exception' instead.",
                    suggestion=suggestion,
                    confidence=0.95,
                    rule_id="broad-base-exception",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Detect dangerous dynamic calls (eval/exec), shell=True, and SQL string concatenation."""
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # 1. Insecure eval / exec
        if func_name in ("eval", "exec") and isinstance(node.func, ast.Name):
            line_str = self._get_line(node.lineno)
            if func_name == "eval":
                suggestion = line_str.replace("eval(", "ast.literal_eval(") if line_str else "ast.literal_eval(...)"
            else:
                suggestion = line_str.replace("exec(", "# Avoid exec - use structured execution\n") if line_str else None
            self.findings.append(
                CandidateComment(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    category="security",
                    severity="critical",
                    comment=f"Use of dangerous '{func_name}()' allows arbitrary remote code execution. Use safer alternatives like 'ast.literal_eval' or structured parsing.",
                    suggestion=suggestion,
                    confidence=0.95,
                    rule_id=f"insecure-{func_name}",
                )
            )

        # 2. Dangerous subprocess with shell=True
        if func_name in ("run", "Popen", "call", "check_call", "check_output"):
            for kw in node.keywords:
                if kw.arg == "shell":
                    is_true = False
                    if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        is_true = True
                    if is_true:
                        line_str = self._get_line(node.lineno)
                        suggestion = line_str.replace("shell=True", "shell=False") if line_str else None
                        self.findings.append(
                            CandidateComment(
                                file_path=self.file_path,
                                line_number=node.lineno,
                                category="security",
                                severity="critical",
                                comment="Subprocess invocation with 'shell=True' is vulnerable to command injection. Pass command arguments as a list with shell=False.",
                                suggestion=suggestion,
                                confidence=0.95,
                                rule_id="subprocess-shell-true",
                            )
                        )

        # 3. SQL Injection concatenation in execute / query calls
        if func_name in ("execute", "executemany", "raw", "select"):
            if node.args:
                first_arg = node.args[0]
                is_sqli = False

                if isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, (ast.Add, ast.Mod)):
                    is_sqli = True
                elif isinstance(first_arg, ast.JoinedStr):
                    has_formatted = any(isinstance(v, ast.FormattedValue) for v in first_arg.values)
                    if has_formatted:
                        for v in first_arg.values:
                            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                                if SQL_KEYWORDS_RE.search(v.value):
                                    is_sqli = True
                                    break

                if is_sqli and node.lineno not in self.flagged_sqli_lines:
                    self.flagged_sqli_lines.add(node.lineno)
                    line_str = self._get_line(node.lineno)
                    suggestion = (
                        line_str.replace("+", ",").replace("%", ",") + "  # Parameterize query"
                        if line_str
                        else None
                    )
                    self.findings.append(
                        CandidateComment(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            category="security",
                            severity="critical",
                            comment="Potential SQL Injection vulnerability: dynamic SQL query constructed via string concatenation or formatting. Use parameterized SQL queries.",
                            suggestion=suggestion,
                            confidence=0.95,
                            rule_id="sql-injection-risk",
                        )
                    )

        self.generic_visit(node)


def run_ruff_linter(file_path: str, code_content: str) -> List[CandidateComment]:
    """Run ruff check on code content and return candidate comments."""
    findings: List[CandidateComment] = []
    lines = code_content.splitlines()

    try:
        cmd = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--output-format=json",
            "--stdin-filename",
            file_path,
            "-",
        ]
        proc = subprocess.run(
            cmd,
            input=code_content.encode("utf-8"),
            capture_output=True,
            timeout=15,
        )
        stdout = proc.stdout.decode("utf-8").strip()
        if not stdout:
            return []

        ruff_data = json.loads(stdout)
        if not isinstance(ruff_data, list):
            return []

        for item in ruff_data:
            loc = item.get("location", {})
            row = loc.get("row")
            if not isinstance(row, int):
                continue

            rule_code = str(item.get("code", "")).upper()
            message = str(item.get("message", ""))

            # Categorize based on ruff rule prefix
            category = "bug"
            severity = "major"
            if rule_code.startswith("S"):  # Bandit security rules
                category = "security"
                severity = "critical"
            elif rule_code.startswith("F821") or rule_code.startswith("E9"):
                category = "bug"
                severity = "critical"
            elif rule_code.startswith("E") or rule_code.startswith("W"):
                category = "style"
                severity = "minor"

            orig_line = lines[row - 1] if 1 <= row <= len(lines) else ""
            suggestion = None
            if orig_line:
                # Add inline noqa or placeholder suggestion if actionable
                suggestion = f"{orig_line}  # fix: {rule_code.lower()}"

            findings.append(
                CandidateComment(
                    file_path=file_path,
                    line_number=row,
                    category=category,
                    severity=severity,
                    comment=f"Ruff [{rule_code}]: {message}",
                    suggestion=suggestion,
                    confidence=0.95,
                    rule_id=f"ruff-{rule_code.lower()}",
                )
            )

    except Exception as e:
        logger.debug("Ruff execution skipped or failed: %s", e)

    return findings


def run_static_linters(
    file_path: str, code_content: str, language: str
) -> List[CandidateComment]:
    """
    Run static linters (Ruff and AST security inspection) on file content.

    Returns high-confidence (0.95) candidate review comments.
    """
    if not code_content or not code_content.strip():
        return []

    findings: List[CandidateComment] = []
    lines = code_content.splitlines()

    is_python = language.lower() == "python" or file_path.endswith(".py")
    if not is_python:
        return []

    # 1. AST Security Analysis
    try:
        tree = ast.parse(code_content, filename=file_path)
        visitor = ASTSecurityVisitor(file_path=file_path, code_lines=lines)
        visitor.visit(tree)
        findings.extend(visitor.findings)
    except SyntaxError as e:
        err_line = e.lineno or 1
        findings.append(
            CandidateComment(
                file_path=file_path,
                line_number=err_line,
                category="bug",
                severity="critical",
                comment=f"Syntax Error: {e.msg}",
                suggestion=lines[err_line - 1] if 1 <= err_line <= len(lines) else None,
                confidence=0.99,
                rule_id="syntax-error",
            )
        )

    # 2. Ruff Linter
    ruff_findings = run_ruff_linter(file_path, code_content)
    findings.extend(ruff_findings)

    return findings
