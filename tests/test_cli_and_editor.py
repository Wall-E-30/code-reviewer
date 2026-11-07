"""
tests/test_cli_and_editor.py

Comprehensive test suite for Aion Developer CLI (`aion review --staged`)
and official VS Code extension (`APP-03`).
"""

import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from cli.main import (
    AionLocalReviewer,
    build_parser,
    format_terminal_review,
    get_git_diff_target,
    get_git_staged_diff,
    handle_config_command,
    handle_conventions_command,
    handle_review_command,
    main,
)


def test_cli_argument_parsing():
    """Verify CLI parser constructs valid namespace for review, conventions, and config subcommands."""
    parser = build_parser()

    # 1. Review staged with json
    args_review = parser.parse_args(["review", "--staged", "--json", "--min-confidence", "0.85"])
    assert args_review.subcommand == "review"
    assert args_review.staged is True
    assert args_review.json is True
    assert args_review.min_confidence == 0.85

    # 2. Review specific diff file
    args_diff = parser.parse_args(["review", "--diff-file", "patch.diff", "--max-comments", "3"])
    assert args_diff.diff_file == "patch.diff"
    assert args_diff.max_comments == 3

    # 3. Conventions add & suppress
    args_conv = parser.parse_args(["conventions", "--add", "Prefer explicit typing", "--category", "style"])
    assert args_conv.subcommand == "conventions"
    assert args_conv.add == "Prefer explicit typing"
    assert args_conv.category == "style"

    # 4. Config set provider
    args_cfg = parser.parse_args(["config", "--set-provider", "ollama", "--set-model", "qwen2.5-coder:7b"])
    assert args_cfg.subcommand == "config"
    assert args_cfg.set_provider == "ollama"
    assert args_cfg.set_model == "qwen2.5-coder:7b"


def test_local_reviewer_with_clean_diff():
    """Verify clean staged diff without security flaws or linter violations yields zero findings."""
    reviewer = AionLocalReviewer()
    clean_diff = """--- a/calculator.py
+++ b/calculator.py
@@ -1,3 +1,4 @@
 def add(a: int, b: int) -> int:
-    return 0
+    return a + b
"""
    clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    findings = reviewer.review_diff(clean_diff, {"calculator.py": clean_code})

    assert len(findings) == 0
    formatted = format_terminal_review(findings)
    assert "No actionable issues detected" in formatted


def test_local_reviewer_with_vulnerabilities():
    """Verify dangerous security practices (eval / bare SQL concatenation) are detected and reported."""
    reviewer = AionLocalReviewer()
    vuln_diff = """--- a/auth.py
+++ b/auth.py
@@ -1,2 +1,3 @@
 def check_user(user_input):
+    eval(user_input)
     return True
"""
    vuln_code = "def check_user(user_input):\n    eval(user_input)\n    return True\n"
    findings = reviewer.review_diff(vuln_diff, {"auth.py": vuln_code})

    assert len(findings) > 0
    eval_finding = next((f for f in findings if f["category"] == "security"), None)
    assert eval_finding is not None
    assert eval_finding["file_path"] == "auth.py"
    assert eval_finding["line_number"] == 2
    assert "eval" in eval_finding["comment"]
    assert eval_finding["severity"] in ("critical", "major")


def test_local_reviewer_json_output(capsys):
    """Verify --json emits machine-readable JSON array consumable by editors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        diff_path = os.path.join(tmpdir, "vuln.diff")
        with open(diff_path, "w", encoding="utf-8") as f:
            f.write("""--- a/service.py
+++ b/service.py
@@ -1,2 +1,3 @@
 def run(cmd):
+    eval(cmd)
     return None
""")

        parser = build_parser()
        args = parser.parse_args(["review", "--diff-file", diff_path, "--json"])

        exit_code = handle_review_command(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["file_path"] == "service.py"
        assert "eval" in data[0]["comment"]


def test_conventions_command(capsys):
    """Verify registering and listing custom conventions via CLI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        conv_file = os.path.join(tmpdir, "conventions.json")
        parser = build_parser()

        # Add convention
        args_add = parser.parse_args([
            "conventions",
            "--file", conv_file,
            "--add", "No raw string SQL formatting",
            "--category", "security",
        ])
        rc = handle_conventions_command(args_add)
        assert rc == 0

        # Suppress category
        args_sup = parser.parse_args([
            "conventions",
            "--file", conv_file,
            "--suppress-category", "style",
        ])
        rc2 = handle_conventions_command(args_sup)
        assert rc2 == 0

        # List conventions
        args_list = parser.parse_args(["conventions", "--file", conv_file, "--list"])
        handle_conventions_command(args_list)

        captured = capsys.readouterr()
        assert "No raw string SQL formatting" in captured.out
        assert "Suppressed Categories:" in captured.out
        assert "style" in captured.out


def test_config_command(capsys):
    """Verify local configuration management."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_file = os.path.join(tmpdir, "config.json")
        parser = build_parser()

        # Set provider to mock
        args_set = parser.parse_args(["config", "--file", cfg_file, "--set-provider", "mock"])
        rc = handle_config_command(args_set)
        assert rc == 0
        capsys.readouterr()  # Flush stdout from set command

        # Show config
        args_show = parser.parse_args(["config", "--file", cfg_file, "--show"])
        handle_config_command(args_show)

        captured = capsys.readouterr()
        cfg = json.loads(captured.out)
        assert cfg["provider"] == "mock"


def test_local_reviewer_respects_suppressed_category():
    """Verify convention memory suppresses findings in suppressed category."""
    with tempfile.TemporaryDirectory() as tmpdir:
        conv_file = os.path.join(tmpdir, "conventions.json")
        reviewer = AionLocalReviewer(conventions_path=conv_file)
        reviewer.memory.suppress_category("security")
        reviewer.memory.save(conv_file)

        vuln_diff = """--- a/test_suppressed.py
+++ b/test_suppressed.py
@@ -1,2 +1,3 @@
 def run(cmd):
+    eval(cmd)
     return None
"""
        findings = reviewer.review_diff(vuln_diff, {"test_suppressed.py": "def run(cmd):\n    eval(cmd)\n    return None\n"})
        # Should be suppressed because security category is suppressed
        assert len(findings) == 0


def test_vscode_extension_manifest_validity():
    """Verify package.json manifest adheres to VS Code extension specification."""
    pkg_path = os.path.join("editors", "vscode", "package.json")
    assert os.path.isfile(pkg_path), "editors/vscode/package.json must exist"

    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    assert pkg["name"] == "aion-code-reviewer"
    assert pkg["publisher"] == "aion-ai"
    assert "vscode" in pkg["engines"]
    assert pkg["main"] == "./extension.js"

    contributes = pkg.get("contributes", {})
    command_ids = [c["command"] for c in contributes.get("commands", [])]
    assert "aion.reviewStaged" in command_ids
    assert "aion.reviewCurrentFile" in command_ids
    assert "aion.showConventions" in command_ids

    config_props = contributes.get("configuration", {}).get("properties", {})
    assert "aion.executablePath" in config_props
    assert "aion.provider" in config_props
    assert "aion.minConfidence" in config_props
    assert "aion.autoReviewOnSave" in config_props


def test_vscode_extension_code_syntax():
    """Verify extension.js syntax using Node if available, and verify exports & structure."""
    ext_path = os.path.join("editors", "vscode", "extension.js")
    assert os.path.isfile(ext_path), "editors/vscode/extension.js must exist"

    with open(ext_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Structural checks
    assert "vscode.languages.createDiagnosticCollection" in content
    assert "vscode.CodeActionKind.QuickFix" in content
    assert "aion.reviewStaged" in content
    assert "module.exports" in content

    # Node syntax validation
    try:
        res = subprocess.run(["node", "-c", ext_path], capture_output=True, text=True, check=False)
        assert res.returncode == 0, f"Node syntax error in extension.js: {res.stderr}"
    except FileNotFoundError:
        # Node not installed on this system; structural checks suffice
        pass
