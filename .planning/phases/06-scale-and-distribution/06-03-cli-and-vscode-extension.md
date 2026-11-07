---
phase: 06-scale-and-distribution
plan: 03
type: execute
wave: 3
depends_on:
  - 06-01
files_modified:
  - cli/__init__.py
  - cli/main.py
  - pyproject.toml
  - editors/vscode/package.json
  - editors/vscode/extension.js
  - editors/vscode/README.md
  - tests/test_cli_and_editor.py
autonomous: true
requirements:
  - APP-03
must_haves:
  truths:
    - aion review --staged command inspects git staged diffs via git diff --staged, runs static linters, fetches repo conventions, executes review inference, and outputs actionable suggestions in terminal.
    - pyproject.toml exposes the aion CLI executable entry point.
    - CLI supports offline mode and local Ollama inference without requiring external cloud accounts.
    - VS Code extension manifest package.json declares aion.reviewStaged and aion.reviewCurrentFile commands with settings configuration.
    - VS Code extension runtime extension.js registers diagnostic squiggles and 1-click CodeAction quickfixes for suggested code replacements.
  artifacts:
    - cli/main.py
    - pyproject.toml
    - editors/vscode/package.json
    - editors/vscode/extension.js
    - editors/vscode/README.md
    - tests/test_cli_and_editor.py
  key_links:
    - cli/main.py reuses action review pipeline components (action/diff_parser.py, action/linters.py, action/verifier.py) and rl/memory.py.
    - editors/vscode/ invokes or interfaces with the aion review CLI engine.
---

<objective>
Build and release the Developer CLI surface (`aion review --staged`) and the official VS Code extension (`APP-03`).
Provide pre-commit review capabilities directly in local terminals and code editors, reusing the core linter pipeline, convention memory, and precision verifier engine.

Purpose: Enable developers to catch bugs, security issues, and convention deviations before committing or pushing code, shortening the review feedback cycle from hours to seconds.
Output: `cli/main.py`, updated `pyproject.toml`, `editors/vscode/` package, and `tests/test_cli_and_editor.py`.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/06-scale-and-distribution/RESEARCH.md
@pyproject.toml
@action/diff_parser.py
@action/linters.py
@action/verifier.py
@rl/memory.py
@rl/bandit.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Local Diff Inspector and Staged Review Engine</name>
  <files>cli/__init__.py, cli/main.py</files>
  <action>
1. Create `cli/__init__.py`.
2. In `cli/main.py`:
   - Implement `get_git_staged_diff(cwd: Optional[str] = None) -> str`:
     - Runs `git diff --cached --unified=3` (or accepts custom diff string in tests).
     - Returns raw unified diff string.
   - Implement `AionLocalReviewer`:
     - Integrates `action.diff_parser.parse_unified_diff`.
     - Runs static linters (`action.linters.run_ast_linter`).
     - Loads repository convention memory (`.aion/conventions.json`).
     - Filters candidates via `PrecisionVerifier`.
     - `review_diff(diff_str: str, file_content_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]`:
       - Returns structured findings with `file_path`, `line_number`, `category`, `comment`, `suggestion`.
  </action>
  <verify>
python -c "from cli.main import AionLocalReviewer; r = AionLocalReviewer(); sample_diff = '--- a/t.py\n+++ b/t.py\n@@ -1 +1 @@\n-a = 1\n+eval(x)\n'; res = r.review_diff(sample_diff, {'t.py': 'eval(x)\n'}); assert len(res) > 0 and res[0]['category'] == 'security'; print('CLI reviewer tracer verified')"
  </verify>
</task>

<task>
  <name>Implement aion CLI Commands and Register in pyproject.toml</name>
  <files>cli/main.py, pyproject.toml</files>
  <action>
1. In `cli/main.py`:
   - Build CLI argument parser:
     - `aion review [--staged] [--target <ref>] [--json]`:
       - `--staged`: Reviews staged git index.
       - `--target <ref>`: Reviews commit or branch diff.
       - `--json`: Emits raw machine-readable JSON array (consumed by VS Code extension).
       - Default: Pretty-prints ANSI colored terminal review with line anchors and suggestion blocks.
     - `aion conventions [--add <rule>] [--list]`:
       - Lists or appends custom repository conventions.
     - `aion config [--show] [--set-provider <provider>]`:
       - Manages local provider preferences (`ollama`, `byok`, `mock`).
     - `main()` entrypoint function returning exit code (0 if clean or reviews formatted, 1 on error).
2. In `pyproject.toml`:
   - Under `[project.scripts]`, add:
     `aion = "cli.main:main"`
   - Under `[tool.setuptools]`, add `"cli"` to `packages`.
  </action>
  <verify>
python -c "from cli.main import build_parser; p = build_parser(); args = p.parse_args(['review', '--staged', '--json']); assert args.staged is True and args.json is True; print('CLI arguments parser verified')"
  </verify>
</task>

<task>
  <name>Build VS Code Extension Package and Diagnostics Provider</name>
  <files>editors/vscode/package.json, editors/vscode/extension.js, editors/vscode/README.md</files>
  <action>
1. In `editors/vscode/package.json`:
   - Extension name: `aion-code-reviewer`.
   - Contributes commands:
     - `aion.reviewStaged`: "Aion: Review Staged Changes"
     - `aion.reviewCurrentFile`: "Aion: Review Current File"
     - `aion.showConventions`: "Aion: Show Repository Conventions"
   - Contributes configuration:
     - `aion.executablePath`: Path to `aion` CLI binary.
     - `aion.provider`: `"ollama" | "byok" | "mock"`.
     - `aion.minConfidence`: Cutoff confidence (default `0.70`).
     - `aion.autoReviewOnSave`: Boolean (default `false`).
2. In `editors/vscode/extension.js`:
   - `activate(context)`:
     - Initializes `vscode.languages.createDiagnosticCollection("aion")`.
     - Registers command handlers executing `aion review --json` in workspace root.
     - Maps review findings to `vscode.Diagnostic` objects with severity (`Error` for security, `Warning` for bugs/performance).
     - Registers `CodeActionProvider` offering "Apply Aion Suggestion" QuickFix for findings with code suggestions.
   - `deactivate()`: Cleans up diagnostic collections.
3. In `editors/vscode/README.md`:
   - Documents extension setup, configuration keys, and keyboard shortcuts.
  </action>
  <verify>
python -c "import json; pkg = json.load(open('editors/vscode/package.json')); assert pkg['name'] == 'aion-code-reviewer'; assert 'aion.reviewStaged' in [c['command'] for c in pkg['contributes']['commands']]; print('VS Code extension package verified')"
  </verify>
</task>

<task>
  <name>Build CLI and Editor Surface Test Suite</name>
  <files>tests/test_cli_and_editor.py</files>
  <action>
1. In `tests/test_cli_and_editor.py`, write test cases:
   - `test_cli_argument_parsing()`: Tests review, conventions, and config subcommands.
   - `test_local_reviewer_with_clean_diff()`: Confirms clean staged diff yields empty findings.
   - `test_local_reviewer_with_vulnerabilities()`: Confirms security bugs (eval/sql) are caught and formatted.
   - `test_local_reviewer_json_output()`: Tests machine-readable JSON formatting for editor consumption.
   - `test_conventions_command()`: Tests listing and registering conventions via CLI.
   - `test_vscode_extension_manifest_validity()`: Verifies `package.json` schema and command contributions.
   - `test_vscode_extension_code_syntax()`: Checks syntax of `extension.js`.
  </action>
  <verify>
python -m pytest tests/test_cli_and_editor.py -v
  </verify>
</task>

</tasks>

