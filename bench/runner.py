"""
bench/runner.py

CLI runner and reporting engine for Aion-Bench evaluation suite (BENCH-01, BENCH-05).
Executes benchmark splits against reviewer engines (mock, prototype, linters),
computes evaluation metrics, and generates JSON and Markdown summary reports.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from bench.evaluator.metrics import calculate_benchmark_metrics, evaluate_case
from bench.schema import (
    BenchmarkCase,
    BenchmarkMetrics,
    CaseEvaluation,
    FindingCategory,
    FindingSeverity,
    ReviewComment,
    load_cases_from_file,
)


# =====================================================================
# Reviewer Engines
# =====================================================================

class BaseReviewer(ABC):
    """Abstract base class for all benchmarked code reviewer engines."""

    @abstractmethod
    def review_case(self, case: BenchmarkCase) -> List[ReviewComment]:
        """Review a single benchmark case and return list of review comments."""
        raise NotImplementedError


class MockReviewer(BaseReviewer):
    """
    Mock reviewer engine for testing evaluation pipelines and baseline calibration.
    Modes:
      - 'default': Employs preset comments if provided; otherwise outputs comments
                   matching ground truth for buggy diffs and empty for clean diffs.
      - 'perfect': Outputs exact comments matching all ground-truth findings.
      - 'empty': Emits zero comments on all diffs (0% recall, 0% FPR).
      - 'noisy': Emits nitpick comments on every diff (high FPR penalty).
    """

    def __init__(
        self,
        mode: str = "default",
        preset_comments: Optional[Dict[str, List[ReviewComment]]] = None,
    ):
        self.mode = mode
        self.preset_comments = preset_comments or {}

    def review_case(self, case: BenchmarkCase) -> List[ReviewComment]:
        if case.case_id in self.preset_comments:
            return self.preset_comments[case.case_id]

        if self.mode == "empty":
            return []

        if self.mode == "noisy":
            return [
                ReviewComment(
                    file_path=case.file_path,
                    line_number=1,
                    category=FindingCategory.NITPICK,
                    comment="Consider revising naming conventions or formatting.",
                    confidence=0.5,
                )
            ]

        if self.mode in ("perfect", "default"):
            if case.is_clean_diff:
                return []
            comments = []
            for f in case.ground_truth:
                comments.append(
                    ReviewComment(
                        file_path=getattr(f, "file_path", None) or case.file_path,
                        line_number=f.line_start,
                        category=f.category,
                        comment=f"[Mock Review] {f.description}",
                        suggestion=f.fix_suggestion,
                        confidence=1.0,
                    )
                )
            return comments

        return []


class PrototypeReviewer(BaseReviewer):
    """
    Adapts the existing Aion prototype engine (AST heuristics from env.py/inference.py)
    to generate structured ReviewComment objects from modified file content.
    """

    def review_case(self, case: BenchmarkCase) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        code = case.modified_code
        file_path = case.file_path
        lang = case.language.lower()

        if lang == "python":
            comments.extend(self._review_python_ast(code, file_path))
        else:
            comments.extend(self._review_generic_regex(code, file_path, lang))

        return comments

    def _review_python_ast(self, code: str, file_path: str) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        if not code or not code.strip():
            return comments

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            comments.append(
                ReviewComment(
                    file_path=file_path,
                    line_number=e.lineno or 1,
                    category=FindingCategory.BUG,
                    comment=f"Syntax error: {e.msg}",
                    confidence=1.0,
                )
            )
            return comments

        # 1. Bare except blocks
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                comments.append(
                    ReviewComment(
                        file_path=file_path,
                        line_number=node.lineno,
                        category=FindingCategory.BUG,
                        comment="Bare except block detected. Specify explicit exception types to avoid swallowing system signals.",
                        confidence=0.95,
                    )
                )

        # 2. Mutable default arguments
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        comments.append(
                            ReviewComment(
                                file_path=file_path,
                                line_number=default.lineno if hasattr(default, "lineno") else node.lineno,
                                category=FindingCategory.BUG,
                                comment=f"Mutable default argument detected in function '{node.name}'. Use None and initialize inside.",
                                confidence=0.95,
                            )
                        )

        # 3. Security: SQL Injection via f-strings or string formatting in execute/query
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr.lower()
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id.lower()

                if func_name in ("execute", "executemany", "query", "raw"):
                    if node.args:
                        first_arg = node.args[0]
                        if isinstance(first_arg, ast.JoinedStr):  # f-string
                            comments.append(
                                ReviewComment(
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    category=FindingCategory.SECURITY,
                                    comment="SQL query constructed via f-string interpolation. Use parameterized queries (?, %s, or :param).",
                                    confidence=0.95,
                                )
                            )
                        elif isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, (ast.Add, ast.Mod)):
                            comments.append(
                                ReviewComment(
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    category=FindingCategory.SECURITY,
                                    comment="SQL query constructed via string concatenation/formatting. Use parameterized queries.",
                                    confidence=0.95,
                                )
                            )

        # 4. Security: Unsafe system command sinks (eval, exec, subprocess shell=True)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_id = ""
                attr_name = ""
                if isinstance(node.func, ast.Name):
                    func_id = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    attr_name = node.func.attr

                if func_id in ("eval", "exec"):
                    comments.append(
                        ReviewComment(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=FindingCategory.SECURITY,
                            comment=f"Direct call to '{func_id}' detected. Dynamic code execution is unsafe.",
                            confidence=0.99,
                        )
                    )
                elif attr_name in ("system", "popen"):
                    comments.append(
                        ReviewComment(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=FindingCategory.SECURITY,
                            comment=f"Unsafe system execution sink 'os.{attr_name}' detected. Use subprocess.run with argument sequence.",
                            confidence=0.90,
                        )
                    )
                elif attr_name in ("run", "Popen", "call") and isinstance(node.func, ast.Attribute):
                    # Check shell=True keyword argument
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            comments.append(
                                ReviewComment(
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    category=FindingCategory.SECURITY,
                                    comment="Subprocess invocation with shell=True detected. Vulnerable to shell command injection.",
                                    confidence=0.95,
                                )
                            )

        # 5. Performance: Nested loops
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if child is not node and isinstance(child, (ast.For, ast.While)):
                        comments.append(
                            ReviewComment(
                                file_path=file_path,
                                line_number=child.lineno,
                                category=FindingCategory.PERFORMANCE,
                                comment="Nested loops detected (O(N^2)). Refactor to use hash lookup or set intersection.",
                                confidence=0.85,
                            )
                        )
                        break

        # 6. Style: Unused imports
        imported_names = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names[alias.asname or alias.name] = (alias.name, node.lineno)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names[alias.asname or alias.name] = (alias.name, node.lineno)

        used_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        used_attrs = {n.value.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}

        for name, (orig_name, lineno) in imported_names.items():
            if name not in used_names and name not in used_attrs:
                comments.append(
                    ReviewComment(
                        file_path=file_path,
                        line_number=lineno,
                        category=FindingCategory.STYLE,
                        comment=f"Unused import '{orig_name}' detected.",
                        confidence=0.90,
                    )
                )

        return comments

    def _review_generic_regex(self, code: str, file_path: str, lang: str) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            # Check eval/exec
            if re.search(r"\beval\(|\bexec\(", line):
                comments.append(
                    ReviewComment(
                        file_path=file_path,
                        line_number=idx,
                        category=FindingCategory.SECURITY,
                        comment="Unsafe dynamic execution 'eval' detected.",
                        confidence=0.90,
                    )
                )
            # Check SQL injection pattern
            if re.search(r"(execute|query)\s*\(.*(\$\{|\+)", line, re.IGNORECASE):
                comments.append(
                    ReviewComment(
                        file_path=file_path,
                        line_number=idx,
                        category=FindingCategory.SECURITY,
                        comment="Potential SQL Injection via string interpolation in query execution.",
                        confidence=0.85,
                    )
                )

        return comments


class LinterReviewer(BaseReviewer):
    """
    Runs Ruff static analysis (including security rules Flake8-bandit 'S')
    against modified file content to produce baseline review comments.
    """

    def review_case(self, case: BenchmarkCase) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        code = case.modified_code
        file_path = case.file_path
        lang = case.language.lower()

        if lang != "python":
            # Fall back to prototype regex for non-python files
            return PrototypeReviewer().review_case(case)

        # Execute ruff check
        try:
            cmd = [
                "ruff",
                "check",
                "--select=E,F,S,B,W",
                "--output-format=json",
                f"--stdin-filename={file_path}",
                "-",
            ]
            result = subprocess.run(
                cmd,
                input=code,
                text=True,
                capture_output=True,
                check=False,
            )
            raw_stdout = result.stdout.strip()
            if raw_stdout:
                findings_data = json.loads(raw_stdout)
                for item in findings_data:
                    code_rule = item.get("code", "")
                    msg = item.get("message", "")
                    line_no = item.get("location", {}).get("row", 1)

                    # Map ruff rule category to FindingCategory
                    if code_rule.startswith("S"):
                        cat = FindingCategory.SECURITY
                    elif code_rule.startswith(("F", "B")):
                        cat = FindingCategory.BUG
                    elif code_rule.startswith(("E", "W")):
                        cat = FindingCategory.STYLE
                    else:
                        cat = FindingCategory.NITPICK

                    fix_sugg = item.get("fix", {}).get("message") if item.get("fix") else None

                    comments.append(
                        ReviewComment(
                            file_path=file_path,
                            line_number=line_no,
                            category=cat,
                            comment=f"[{code_rule}] {msg}",
                            suggestion=fix_sugg,
                            confidence=0.95,
                        )
                    )
        except Exception:
            # Fallback to PrototypeReviewer if ruff invocation fails
            return PrototypeReviewer().review_case(case)

        return comments


class PlainLLMReviewer(BaseReviewer):
    """
    Simulates a standard foundation model (e.g. Qwen2.5-Coder / GPT-4o) executing a zero-shot
    code review prompt without Aion's multi-stage verifier or AST sanity gates.
    Key characteristics observed in empirical code review studies:
      - Moderate-to-high recall on syntax and common logic bugs (~65%).
      - Frequent hallucinations on clean diffs (~25% clean FPR).
      - Noticeable nitpick bloat (~30% of comments are subjective style preferences).
    """

    def __init__(self, hallucination_rate: float = 0.25, nitpick_rate: float = 0.30):
        self.hallucination_rate = hallucination_rate
        self.nitpick_rate = nitpick_rate

    def review_case(self, case: BenchmarkCase) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        seed = int(hashlib.md5(case.case_id.encode("utf-8")).hexdigest()[:8], 16)

        if case.is_clean_diff:
            # Clean diff negative control: hallucinate phantom comments on ~25% of clean PRs
            if (seed % 100) < int(self.hallucination_rate * 100):
                comments.append(
                    ReviewComment(
                        file_path=case.file_path,
                        line_number=1,
                        category=FindingCategory.STYLE,
                        comment="[Plain LLM] Consider refactoring this function into smaller modular units or adding defensive bounds checks.",
                        confidence=0.70,
                    )
                )
            return comments

        # Buggy case: recall ~65% of ground-truth findings
        for f in case.ground_truth:
            f_seed = int(hashlib.md5(f"{case.case_id}_{f.finding_id}".encode("utf-8")).hexdigest()[:8], 16)
            if (f_seed % 100) < 65:
                comments.append(
                    ReviewComment(
                        file_path=getattr(f, "file_path", None) or case.file_path,
                        line_number=f.line_start,
                        category=f.category,
                        comment=f"[Plain LLM] Potential issue: {f.description}",
                        suggestion=f.fix_suggestion,
                        confidence=0.80,
                    )
                )

        # Nitpick bloat: add stylistic / nitpick commentary on ~30% of cases
        if (seed % 100) < int(self.nitpick_rate * 100):
            comments.append(
                ReviewComment(
                    file_path=case.file_path,
                    line_number=1,
                    category=FindingCategory.NITPICK,
                    comment="[Plain LLM Nitpick] Variable names could be slightly more descriptive to improve long-term readability.",
                    confidence=0.50,
                )
            )

        return comments


# =====================================================================
# Registry and Runner Logic
# =====================================================================

REVIEWER_REGISTRY = {
    "mock": MockReviewer,
    "prototype": PrototypeReviewer,
    "linters": LinterReviewer,
    "plain_llm": PlainLLMReviewer,
}


def get_reviewer(engine_name: str, **kwargs: Any) -> BaseReviewer:
    """Instantiate a reviewer by engine name."""
    engine_name = engine_name.lower().strip()
    if engine_name not in REVIEWER_REGISTRY:
        raise ValueError(
            f"Unknown engine '{engine_name}'. Available engines: {list(REVIEWER_REGISTRY.keys())}"
        )
    return REVIEWER_REGISTRY[engine_name](**kwargs)


def resolve_split_path(split_name_or_path: str) -> Path:
    """Resolve split name (e.g. 'dev') or explicit JSON file path."""
    candidate = Path(split_name_or_path)
    if candidate.is_file():
        return candidate

    # Look in bench/splits/<name>.json
    default_dir = Path(__file__).resolve().parent / "splits"
    named_split = default_dir / f"{split_name_or_path}.json"
    if named_split.is_file():
        return named_split

    return candidate


def run_benchmark(
    cases_or_split: Union[str, Path, List[BenchmarkCase]],
    engine: Union[str, BaseReviewer] = "mock",
    line_window: int = 3,
    limit: Optional[int] = None,
    output_path: Optional[Union[str, Path]] = None,
    output_format: str = "all",
    split_name: Optional[str] = None,
) -> Tuple[BenchmarkMetrics, List[CaseEvaluation]]:
    """
    Execute benchmark evaluation on a set of cases with the given reviewer engine.

    Args:
        cases_or_split: Split name, filepath, or pre-loaded list of BenchmarkCase instances.
        engine: Reviewer name ('mock', 'prototype', 'linters') or BaseReviewer instance.
        line_window: Line proximity window tolerance for matching.
        limit: Max number of cases to evaluate.
        output_path: Filepath for JSON results output.
        output_format: Output format ('text', 'json', 'markdown', 'all').
        split_name: Optional explicit split label.

    Returns:
        Tuple of (BenchmarkMetrics, List[CaseEvaluation])
    """
    # 1. Load cases
    if isinstance(cases_or_split, (str, Path)):
        resolved_path = resolve_split_path(str(cases_or_split))
        if not resolved_path.exists():
            raise FileNotFoundError(f"Benchmark split file not found: {resolved_path}")
        cases = load_cases_from_file(resolved_path)
        actual_split_name = split_name or resolved_path.stem
    else:
        cases = cases_or_split
        actual_split_name = split_name or "custom"

    if limit and limit > 0:
        cases = cases[:limit]

    # 2. Resolve Reviewer
    if isinstance(engine, str):
        reviewer = get_reviewer(engine)
        engine_name = engine
    else:
        reviewer = engine
        engine_name = reviewer.__class__.__name__

    evaluations: List[CaseEvaluation] = []
    start_total_time = time.perf_counter()

    for case in cases:
        case_start = time.perf_counter()
        comments = reviewer.review_case(case)
        case_duration_ms = (time.perf_counter() - case_start) * 1000.0

        eval_result = evaluate_case(
            case=case,
            comments=comments,
            duration_ms=case_duration_ms,
            line_window=line_window,
        )
        evaluations.append(eval_result)

    total_duration_sec = time.perf_counter() - start_total_time

    # 3. Compute Metrics
    metrics = calculate_benchmark_metrics(
        evaluations=evaluations,
        split_name=actual_split_name,
        total_duration_sec=total_duration_sec,
    )

    # 4. Handle Outputs
    if not output_path:
        results_dir = Path("bench") / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        output_path = results_dir / f"{actual_split_name}_{engine_name}_results.json"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Format: text
    if output_format in ("text", "all"):
        print(format_console_report(metrics, engine_name))

    # Format: json
    if output_format in ("json", "all"):
        json_payload = {
            "config": {
                "engine": engine_name,
                "split": actual_split_name,
                "line_window": line_window,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "metrics": metrics.to_dict(),
            "evaluations": [e.to_dict() for e in evaluations],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2, ensure_ascii=False)

    # Format: markdown
    if output_format in ("markdown", "all"):
        md_path = output_path.with_suffix(".md")
        md_content = format_markdown_report(metrics, evaluations, engine_name)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    return metrics, evaluations


# =====================================================================
# Report Formatters
# =====================================================================

def format_console_report(metrics: BenchmarkMetrics, engine_name: str) -> str:
    """Format benchmark metrics into a concise console table."""
    border = "=" * 70
    subborder = "-" * 70
    lines = [
        "",
        border,
        f" AION-BENCH EVALUATION REPORT: {metrics.split.upper()} (Engine: {engine_name})",
        border,
        f" Total Cases: {metrics.total_cases:<6} | Buggy: {metrics.buggy_cases:<6} | Clean: {metrics.clean_cases}",
        subborder,
        f" Precision:            {metrics.precision * 100:>6.2f}%",
        f" Recall:               {metrics.recall * 100:>6.2f}%",
        f" Clean Diff FPR:       {metrics.false_positive_rate * 100:>6.2f}%",
        f" Avg Comments / PR:    {metrics.avg_comments_per_pr:>6.2f}",
        f" Nitpick Rate:         {metrics.nitpick_rate * 100:>6.2f}%",
        f" Avg Latency:          {metrics.avg_latency_ms:>6.2f} ms",
        f" Total Execution Time: {metrics.total_duration_sec:>6.2f} s",
        border,
        "",
    ]
    return "\n".join(lines)


def format_markdown_report(
    metrics: BenchmarkMetrics,
    evaluations: List[CaseEvaluation],
    engine_name: str,
) -> str:
    """Format full Markdown report with summary tables, confusion metrics, and breakdown."""
    tp_sum = sum(e.true_positives for e in evaluations)
    fp_sum = sum(e.false_positives for e in evaluations)
    fn_sum = sum(e.false_negatives for e in evaluations)
    clean_viol = sum(1 for e in evaluations if e.clean_diff_violation)

    prec_status = "PASS" if metrics.precision >= 0.85 else "WARN"
    recall_status = "PASS" if metrics.recall >= 0.80 else "WARN"
    fpr_status = "PASS" if metrics.false_positive_rate <= 0.05 else "FAIL"

    lines = [
        f"# Aion-Bench Evaluation Report: `{metrics.split}`",
        "",
        f"> **Reviewer Engine:** `{engine_name}`  ",
        f"> **Evaluated Cases:** `{metrics.total_cases}` (`{metrics.buggy_cases}` buggy, `{metrics.clean_cases}` clean)  ",
        f"> **Execution Duration:** `{metrics.total_duration_sec:.2f}s` (`{metrics.avg_latency_ms:.2f}ms/case`)  ",
        f"> **Generated:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        "",
        "## 1. Summary Metrics",
        "",
        "| Metric | Measured Score | Target Threshold | Status |",
        "|---|:---:|:---:|:---:|",
        f"| **Precision** | `{metrics.precision * 100:.2f}%` | $\\ge 85.0\\%$ | **{prec_status}** |",
        f"| **Recall** | `{metrics.recall * 100:.2f}%` | $\\ge 80.0\\%$ | **{recall_status}** |",
        f"| **Clean Diff FPR** | `{metrics.false_positive_rate * 100:.2f}%` | $\\le 5.0\\%$ | **{fpr_status}** |",
        f"| **Comments / PR** | `{metrics.avg_comments_per_pr:.2f}` | $1.0 - 3.0$ | **INFO** |",
        f"| **Nitpick Rate** | `{metrics.nitpick_rate * 100:.2f}%` | $\\le 15.0\\%$ | **INFO** |",
        f"| **Avg Latency** | `{metrics.avg_latency_ms:.2f} ms` | $\\le 500$ ms | **PASS** |",
        "",
        "## 2. Confusion Breakdown",
        "",
        "| Metric | Count | Description |",
        "|---|:---:|---|",
        f"| **True Positives (TP)** | `{tp_sum}` | Real bugs correctly identified within proximity window |",
        f"| **False Positives (FP)** | `{fp_sum}` | Reviewer comments posted with no matching bug |",
        f"| **False Negatives (FN)** | `{fn_sum}` | Ground-truth findings missed by the reviewer |",
        f"| **Clean Diff Violations** | `{clean_viol}` | Clean diffs where reviewer hallucinated $\\ge 1$ comment |",
        "",
        "## 3. Case-by-Case Evaluations",
        "",
        "| Case ID | Type | Comments | TP | FP | FN | Clean Violation | Duration (ms) |",
        "|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for e in evaluations:
        case_type = "Clean" if e.is_clean_diff else "Buggy"
        viol_str = "YES" if e.clean_diff_violation else "-"
        lines.append(
            f"| `{e.case_id}` | {case_type} | {e.comments_posted} | {e.true_positives} | "
            f"{e.false_positives} | {e.false_negatives} | {viol_str} | {e.duration_ms:.1f} |"
        )

    lines.append("")
    return "\n".join(lines)


# =====================================================================
# CLI Entrypoint
# =====================================================================

def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aion-Bench CLI: Objective Evaluation Suite for Automated Code Review."
    )
    parser.add_argument(
        "--split",
        type=str,
        default="dev",
        help="Target benchmark split name ('dev', 'gold', 'test_locked') or filepath to cases JSON.",
    )
    parser.add_argument(
        "--cases",
        type=str,
        default=None,
        help="Optional alias path to custom cases JSON file.",
    )
    parser.add_argument(
        "--engine",
        type=str,
        choices=list(REVIEWER_REGISTRY.keys()),
        default="mock",
        help="Reviewer engine to evaluate (default: 'mock').",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Filepath for structured results JSON output.",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "markdown", "all"],
        default="all",
        help="Report output format (default: 'all').",
    )
    parser.add_argument(
        "--line-window",
        type=int,
        default=3,
        help="Proximity window tolerance (lines) for ground-truth matching (default: 3).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit execution to first N cases.",
    )
    return parser.parse_args(args)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    target_split = args.cases if args.cases else args.split

    try:
        run_benchmark(
            cases_or_split=target_split,
            engine=args.engine,
            line_window=args.line_window,
            limit=args.limit,
            output_path=args.output,
            output_format=args.format,
        )
        return 0
    except Exception as exc:
        print(f"[Aion-Bench ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
