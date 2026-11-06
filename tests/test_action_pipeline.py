"""
tests/test_action_pipeline.py

Unit test suite for Phase 3 Action Pipeline:
- Diff parser & context extraction
- BYOK Providers & Mock provider
- Static linters (Ruff & AST security rules)
- Precision verifier & comment ceiling
"""

from typing import List, Set
import pytest

from action.diff_parser import (
    DiffFile,
    detect_language,
    extract_file_context,
    parse_unified_diff,
)
from action.linters import run_static_linters
from action.providers import (
    CandidateComment,
    GroqProvider,
    HuggingFaceProvider,
    MockReviewProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
    get_provider,
)
from action.verifier import PrecisionVerifier


# ============================================================================
# 1. Diff Parser Tests
# ============================================================================


def test_diff_parser_standard_git_diff() -> None:
    diff_text = """diff --git a/src/calc.py b/src/calc.py
index 1234567..89abcdef 100644
--- a/src/calc.py
+++ b/src/calc.py
@@ -10,4 +10,5 @@ def add(a, b):
     res = a + b
-    return res
+    validated = True
+    return res if validated else 0
"""
    files: List[DiffFile] = parse_unified_diff(diff_text)
    assert len(files) == 1
    f = files[0]
    assert f.new_path == "src/calc.py"
    assert f.language == "python"
    assert 11 in f.added_lines
    assert 12 in f.added_lines
    assert len(f.hunks) == 1
    hunk = f.hunks[0]
    assert hunk.new_start == 10


def test_diff_parser_minimal_unified_diff() -> None:
    diff_text = """--- a/test.ts
+++ b/test.ts
@@ -1,3 +1,3 @@
 const x = 1;
-const y = 2;
+const y = 3;
 export default x + y;
"""
    files = parse_unified_diff(diff_text)
    assert len(files) == 1
    assert files[0].new_path == "test.ts"
    assert files[0].language == "typescript"
    assert 2 in files[0].added_lines


def test_diff_parser_new_and_deleted_files() -> None:
    diff_text = """--- /dev/null
+++ b/new_module.py
@@ -0,0 +1,2 @@
+def greet():
+    print("Hello")
--- a/old_module.js
+++ /dev/null
@@ -1,2 +0,0 @@
-const deprecated = true;
-console.log(deprecated);
"""
    files = parse_unified_diff(diff_text)
    assert len(files) == 2
    assert files[0].is_new is True
    assert files[0].new_path == "new_module.py"
    assert files[0].language == "python"
    assert 1 in files[0].added_lines
    assert 2 in files[0].added_lines

    assert files[1].is_deleted is True
    assert files[1].old_path == "old_module.js"
    assert files[1].language == "javascript"


def test_detect_language() -> None:
    assert detect_language("app.py") == "python"
    assert detect_language("component.tsx") == "typescript"
    assert detect_language("index.js") == "javascript"
    assert detect_language("server.go") == "go"
    assert detect_language("main.rs") == "rust"
    assert detect_language("README.md") == "markdown"
    assert detect_language("unknown.xyz123") == "unknown"
    assert detect_language(None) == "unknown"


def test_extract_file_context_with_scope() -> None:
    content = """import os

class OrderProcessor:
    def __init__(self):
        self.orders = []

    def process(self, order_id):
        if not order_id:
            return None
        total = 0
        for item in self.orders:
            total += item.price
        return total
"""
    # Target lines 10-12
    context = extract_file_context(content, line_start=10, line_end=12, window=3)
    assert "Enclosing Scope" in context
    assert "def process" in context
    assert "total = 0" in context
    assert ">   10 |" in context or ">   11 |" in context


# ============================================================================
# 2. Provider Tests
# ============================================================================


def test_provider_factory() -> None:
    p_mock = get_provider("mock")
    assert isinstance(p_mock, MockReviewProvider)

    p_groq = get_provider("groq", api_key="test_key")
    assert isinstance(p_groq, GroqProvider)

    p_openrouter = get_provider("openrouter", api_key="test_key")
    assert isinstance(p_openrouter, OpenRouterProvider)

    p_ollama = get_provider("ollama")
    assert isinstance(p_ollama, OllamaProvider)

    p_openai = get_provider("openai", api_key="test_key")
    assert isinstance(p_openai, OpenAIProvider)

    p_hf = get_provider("huggingface", api_key="test_key")
    assert isinstance(p_hf, HuggingFaceProvider)

    with pytest.raises(ValueError):
        get_provider("unsupported_provider_xyz")


def test_mock_provider_deterministic() -> None:
    provider = get_provider("mock")
    # Empty diff -> no findings
    assert provider.generate_review("test.py", "", "", "python") == []

    # Diff with added line -> generates finding
    diff = "@@ -1,2 +1,2 @@\n def f():\n-    x = 1\n+    x = 2\n"
    comments = provider.generate_review("test.py", diff, "def f():\n    x = 2\n", "python")
    assert len(comments) > 0
    assert comments[0].line_number == 2
    assert comments[0].suggestion is not None


def test_mock_provider_canned_comments() -> None:
    canned = [
        CandidateComment(
            file_path="foo.py",
            line_number=5,
            category="bug",
            severity="critical",
            comment="Canned bug comment",
            suggestion="    fixed_line = True",
            confidence=0.98,
            rule_id="canned-rule",
        )
    ]
    p = MockReviewProvider(canned_comments=canned)
    results = p.generate_review("foo.py", "+ x = 1", "", "python")
    assert len(results) == 1
    assert results[0].comment == "Canned bug comment"


def test_openai_compatible_response_parsing() -> None:
    provider = OpenAIProvider(api_key="mock_key")
    json_response = """
    ```json
    [
      {
        "line_number": 42,
        "category": "security",
        "severity": "critical",
        "comment": "SQL injection detected.",
        "suggestion": "cursor.execute(query, (id,))",
        "confidence": 0.99,
        "rule_id": "sqli-found"
      }
    ]
    ```
    """
    comments = provider._parse_response_json(json_response, "db/query.py")
    assert len(comments) == 1
    c = comments[0]
    assert c.line_number == 42
    assert c.category == "security"
    assert c.confidence == 0.99
    assert c.rule_id == "sqli-found"


# ============================================================================
# 3. Static Linters Tests
# ============================================================================


def test_static_linters_ast_eval() -> None:
    code = """def evaluate(user_input):
    return eval(user_input)
"""
    findings = run_static_linters("calc.py", code, "python")
    eval_findings = [f for f in findings if f.rule_id == "insecure-eval"]
    assert len(eval_findings) >= 1
    assert eval_findings[0].category == "security"
    assert eval_findings[0].severity == "critical"
    assert eval_findings[0].confidence >= 0.90


def test_static_linters_ast_bare_except() -> None:
    code = """def run():
    try:
        do_something()
    except:
        pass
"""
    findings = run_static_linters("task.py", code, "python")
    bare_except_findings = [f for f in findings if f.rule_id == "bare-except"]
    assert len(bare_except_findings) >= 1
    assert bare_except_findings[0].category == "bug"
    assert bare_except_findings[0].suggestion is not None
    assert "except Exception:" in bare_except_findings[0].suggestion


def test_static_linters_ast_shell_true() -> None:
    code = """import subprocess
def execute(cmd):
    return subprocess.run(cmd, shell=True)
"""
    findings = run_static_linters("runner.py", code, "python")
    shell_findings = [f for f in findings if f.rule_id == "subprocess-shell-true"]
    assert len(shell_findings) >= 1
    assert shell_findings[0].severity == "critical"


def test_static_linters_ast_sql_injection() -> None:
    code = """def query_user(user_id):
    query = "SELECT * FROM users WHERE id = '" + user_id + "'"
    cursor.execute(query)
"""
    findings = run_static_linters("db.py", code, "python")
    sqli_findings = [f for f in findings if f.rule_id == "sql-injection-risk"]
    assert len(sqli_findings) >= 1
    assert sqli_findings[0].category == "security"


def test_static_linters_non_python() -> None:
    ts_code = "const x: number = 42;"
    findings = run_static_linters("app.ts", ts_code, "typescript")
    assert findings == []


# ============================================================================
# 4. Precision Verifier Tests
# ============================================================================


def test_verifier_line_sanity_check() -> None:
    verifier = PrecisionVerifier()
    candidates = [
        CandidateComment(
            file_path="app.py",
            line_number=5,
            category="bug",
            severity="major",
            comment="Bug on line 5",
            suggestion="    fix_line = 5",
            confidence=0.85,
        ),
        CandidateComment(
            file_path="app.py",
            line_number=20,
            category="bug",
            severity="major",
            comment="Bug on un-modified line 20",
            suggestion="    fix_line = 20",
            confidence=0.90,
        ),
    ]
    # Line 20 was NOT modified
    modified_lines: Set[int] = {5, 6, 7}
    filtered = verifier.filter_candidates(candidates, modified_lines=modified_lines)
    assert len(filtered) == 1
    assert filtered[0].line_number == 5


def test_verifier_confidence_threshold() -> None:
    verifier = PrecisionVerifier(default_min_confidence=0.7)
    candidates = [
        CandidateComment(
            file_path="app.py",
            line_number=5,
            category="bug",
            severity="major",
            comment="Low confidence guess",
            suggestion="    fix()",
            confidence=0.55,
        ),
        CandidateComment(
            file_path="app.py",
            line_number=6,
            category="bug",
            severity="major",
            comment="High confidence finding",
            suggestion="    valid_fix()",
            confidence=0.88,
        ),
    ]
    filtered = verifier.filter_candidates(candidates, modified_lines={5, 6})
    assert len(filtered) == 1
    assert filtered[0].line_number == 6


def test_verifier_nitpick_suppression() -> None:
    verifier = PrecisionVerifier()
    candidates = [
        CandidateComment(
            file_path="app.py",
            line_number=5,
            category="nitpick",
            severity="minor",
            comment="Consider renaming variable x to item_count",
            suggestion="    item_count = 1",
            confidence=0.95,
        ),
        CandidateComment(
            file_path="app.py",
            line_number=6,
            category="style",
            severity="minor",
            comment="Cosmetic formatting taste issue",
            suggestion="    x = 2",
            confidence=0.95,
        ),
        CandidateComment(
            file_path="app.py",
            line_number=7,
            category="bug",
            severity="critical",
            comment="Real null dereference bug",
            suggestion="    if item is not None:\n        item.run()",
            confidence=0.95,
        ),
    ]
    filtered = verifier.filter_candidates(candidates, modified_lines={5, 6, 7})
    assert len(filtered) == 1
    assert filtered[0].line_number == 7


def test_verifier_suggestion_validation_and_no_op() -> None:
    verifier = PrecisionVerifier()
    file_content = "def test():\n    x = 1\n    return x\n"
    candidates = [
        # Missing suggestion
        CandidateComment(
            file_path="test.py",
            line_number=2,
            category="bug",
            severity="major",
            comment="No suggestion attached",
            suggestion=None,
            confidence=0.90,
        ),
        # Duplicate / no-op suggestion matching original line
        CandidateComment(
            file_path="test.py",
            line_number=2,
            category="bug",
            severity="major",
            comment="Duplicate suggestion",
            suggestion="    x = 1",
            confidence=0.90,
        ),
        # Syntactically broken python suggestion
        CandidateComment(
            file_path="test.py",
            line_number=2,
            category="bug",
            severity="major",
            comment="Invalid syntax",
            suggestion="    def def broken {{",
            confidence=0.90,
        ),
        # Valid actionable suggestion
        CandidateComment(
            file_path="test.py",
            line_number=2,
            category="bug",
            severity="major",
            comment="Valid change",
            suggestion="    x = 2",
            confidence=0.90,
        ),
    ]
    filtered = verifier.filter_candidates(
        candidates,
        modified_lines={2},
        file_content=file_content,
    )
    assert len(filtered) == 1
    assert filtered[0].suggestion == "    x = 2"


def test_verifier_deduplication() -> None:
    verifier = PrecisionVerifier()
    # Multiple comments on the exact same line
    candidates = [
        CandidateComment(
            file_path="app.py",
            line_number=10,
            category="bug",
            severity="minor",
            comment="Minor remark",
            suggestion="    y = 1",
            confidence=0.75,
        ),
        CandidateComment(
            file_path="app.py",
            line_number=10,
            category="security",
            severity="critical",
            comment="Critical vulnerability",
            suggestion="    safe_call()",
            confidence=0.95,
        ),
    ]
    filtered = verifier.filter_candidates(candidates, modified_lines={10})
    assert len(filtered) == 1
    assert filtered[0].severity == "critical"
    assert filtered[0].comment == "Critical vulnerability"


def test_verifier_hard_ceiling() -> None:
    verifier = PrecisionVerifier(default_max_comments=3)
    candidates = [
        CandidateComment(
            file_path="app.py",
            line_number=i,
            category="bug",
            severity="major",
            comment=f"Defect {i}",
            suggestion=f"    fix_{i}()",
            confidence=0.80 + (i * 0.01),
        )
        for i in range(1, 10)
    ]
    modified = set(range(1, 10))
    filtered = verifier.filter_candidates(candidates, modified_lines=modified, max_comments=3)
    assert len(filtered) == 3
    # Top 3 highest confidence should be selected
    assert filtered[0].line_number == 9
    assert filtered[1].line_number == 8
    assert filtered[2].line_number == 7

