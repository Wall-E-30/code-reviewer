---
phase: 03-ship-the-wedge
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - action/__init__.py
  - action/diff_parser.py
  - action/linters.py
  - action/providers.py
  - action/verifier.py
  - tests/test_action_pipeline.py
autonomous: true
requirements:
  - GH-03
  - GH-04
must_haves:
  truths:
    - Diff parser extracts modified files, line ranges, and surrounding context for Python and TypeScript/JS files.
    - Multi-provider client supports Groq, OpenRouter, Ollama, OpenAI, and hermetic Mock providers using Bring-Your-Own-Key (BYOK).
    - Pre-filter linters (Ruff / Bandit) detect static syntax and security flaws before LLM inference.
    - Precision verifier validates suggestion syntax, suppresses nitpicks, enforces confidence thresholds, and strictly caps comments to at most 5 per PR.
  artifacts:
    - action/diff_parser.py
    - action/providers.py
    - action/linters.py
    - action/verifier.py
    - tests/test_action_pipeline.py
  key_links:
    - action/diff_parser.py breaks PR diffs into file-level review contexts.
    - action/providers.py queries configured model backends to generate candidate comments.
    - action/verifier.py filters candidate comments to ensure <= 5 high-precision comments.
---

<objective>
Build the core review intelligence pipeline for the GitHub Action: PR diff parsing, multi-provider BYOK LLM client (Groq, OpenRouter, Ollama, OpenAI, Mock), static linter pre-filtering, and the multi-stage precision verifier that guarantees high signal-to-noise ratio.

Purpose: Provide the fast, multi-model review engine that extracts actionable defect candidates and rigorously filters them before posting.
Output: `action/` core modules and pipeline test suite.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/03-ship-the-wedge/RESEARCH.md
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Unified Diff Parser and Context Extractor in action/diff_parser.py</name>
  <files>action/__init__.py, action/diff_parser.py</files>
  <action>
1. Create `action/__init__.py` making `action` an importable package.
2. In `action/diff_parser.py`, implement diff analysis tools:
   - Data structures: `DiffLine`, `DiffHunk`, `DiffFile`, `ReviewContext`.
   - `parse_unified_diff(diff_str: str) -> List[DiffFile]`:
     - Parses standard unified diff format (`diff --git`, `--- a/...`, `+++ b/...`, `@@ -l,s +l,s @@`).
     - Tracks old line numbers, new line numbers, and line types (`+`, `-`, ` `).
     - Identifies target file language based on extension (`.py` -> python, `.ts`/`.tsx` -> typescript, `.js`/`.jsx` -> javascript).
     - Extracts all added or modified line numbers where inline comments can legitimately be placed.
   - `extract_file_context(file_content: str, line_start: int, line_end: int, window: int = 15) -> str`:
     - Extracts the enclosing scope (class/function definition) and surrounding context lines to feed into LLM review prompts.
  </action>
  <verify>
python -c "from action.diff_parser import parse_unified_diff; hunks = parse_unified_diff('--- a/test.py\n+++ b/test.py\n@@ -1,3 +1,3 @@\n def f():\n-    x = 1\n+    x = 2\n     return x\n'); assert len(hunks) == 1 and hunks[0].new_path == 'test.py'; assert 2 in hunks[0].added_lines; print('Diff parser verified')"
  </verify>
</task>

<task>
  <name>Implement Multi-Provider BYOK Client in action/providers.py</name>
  <files>action/providers.py</files>
  <action>
1. In `action/providers.py`, define candidate comment schemas:
   - `CandidateComment(file_path: str, line_number: int, category: str, severity: str, comment: str, suggestion: Optional[str], confidence: float, rule_id: Optional[str])`.
2. Implement base interface `BaseReviewProvider`:
   - `def generate_review(self, file_path: str, diff_hunk: str, context: str, language: str) -> List[CandidateComment]`.
3. Implement provider backends:
   - `MockReviewProvider`: Deterministic offline provider for CI and testing with customizable mock behaviors.
   - `GroqProvider`: Uses Groq API with fast models (`qwen-2.5-coder-32b`, `llama-3.3-70b-versatile`).
   - `OpenRouterProvider`: Connects to OpenRouter free and commercial endpoints.
   - `OllamaProvider`: Connects to local Ollama (`http://localhost:11434/v1`).
   - `OpenAIProvider`: Direct OpenAI API (`gpt-4o-mini`, `gpt-4o`).
   - `HuggingFaceProvider`: HF Serverless Inference Router.
4. Implement factory function:
   - `get_provider(provider_type: str, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None) -> BaseReviewProvider`.
5. Prompts must instruct models to output structured JSON array of findings with mandatory `suggestion` replacements.
  </action>
  <verify>
python -c "from action.providers import get_provider; p = get_provider('mock'); comments = p.generate_review('test.py', '+ x = 1\n', 'def foo():\n    x = 1\n', 'python'); assert len(comments) > 0; print(f'Provider verified: {len(comments)} candidate comments')"
  </verify>
</task>

<task>
  <name>Implement Static Linters and Precision Verifier in action/linters.py and action/verifier.py</name>
  <files>action/linters.py, action/verifier.py, tests/test_action_pipeline.py</files>
  <action>
1. In `action/linters.py`:
   - `run_static_linters(file_path: str, code_content: str, language: str) -> List[CandidateComment]`:
     - Runs `ruff check` in-memory or on temp file for Python files.
     - Runs basic AST vulnerability checks (SQLi string concat, insecure eval/exec, bare except).
     - Converts findings into `CandidateComment` objects with high confidence (0.95).
2. In `action/verifier.py`:
   - Implement `PrecisionVerifier`:
     - Method `filter_candidates(candidates: List[CandidateComment], modified_lines: Set[int], max_comments: int = 5, min_confidence: float = 0.7) -> List[CandidateComment]`:
       a. Line sanity check: Drop comments whose `line_number` does not fall on an added/modified line in the diff.
       b. Deduplication: Merge identical or overlapping linter and LLM comments.
       c. Suggestion validation: Verify suggestion block exists and does not duplicate existing code without changes.
       d. Nitpick suppression: Discard subjective taste comments (variable naming, redundant comments) lacking concrete defects.
       e. Confidence threshold: Discard any comment with `confidence < min_confidence`.
       f. Hard ceiling: Sort remaining candidates by severity (`critical` > `major` > `minor`) and confidence, returning top $K \le \text{max\_comments}$ (default 5).
3. In `tests/test_action_pipeline.py`:
   - Unit tests covering diff parsing, provider factory, mock generation, linter integration, suggestion validation, and verifier ceiling enforcement.
  </action>
  <verify>
python -m pytest tests/test_action_pipeline.py -v
  </verify>
</task>

</tasks>

