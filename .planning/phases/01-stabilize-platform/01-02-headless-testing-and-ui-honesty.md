---
phase: 01-stabilize-platform
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - inference.py
  - frontend/src/App.jsx
  - test_suite.py
autonomous: true
requirements:
  - PLAT-01
  - PLAT-04
  - SCOPE-01
must_haves:
  truths:
    - Gradio import is lazy in inference.py, allowing headless test runners to import inference helpers without installing Gradio.
    - test_suite.py passes cleanly from command line without GUI dependencies.
    - Frontend displays honest metric labels (AST structural complexity and node count deltas) rather than polynomial speedup percentages.
    - Frontend language dropdown explicitly badges Python and TypeScript/JavaScript as Supported (Tier-1), and marks all other languages as Experimental.
  artifacts:
    - inference.py
    - frontend/src/App.jsx
    - test_suite.py
  key_links:
    - test_suite.py imports from inference.py without raising ModuleNotFoundError.
    - frontend/src/App.jsx renders honest metrics aligned with backend AST capabilities.
---

<objective>
Decouple Gradio UI from inference core so test_suite.py runs headless in lean CI environments, replace synthetic speedup/memory metrics in the React dashboard with honest labels, and formalize Tier-1 language scope.

Purpose: Enable headless testing in clean CI pipelines, restore trust in displayed dashboard metrics, and clearly communicate supported versus experimental language tiers.
Output: Decoupled inference.py, passing test_suite.py, and updated App.jsx.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/01-stabilize-platform/RESEARCH.md
</execution_context>

<tasks>

<task type="tracer">
  <name>Decouple Gradio & Enable Headless test_suite.py Execution</name>
  <files>inference.py, test_suite.py</files>
  <action>
1. In `inference.py`, remove top-level `import gradio as gr`. Move the import inside `build_ui()` wrapped in a try/except or dynamic import, raising a clean runtime error only when Gradio UI launch is explicitly invoked.
2. Ensure core helpers (`clean_json_string`, `robust_repair_code`, `evaluate_and_optimize`, `run_full_optimization`, `estimate_ast_improvements`) can be imported without importing Gradio.
3. Verify that `python test_suite.py` executes all test cases without failing on Gradio imports.
  </action>
  <verify>
    <automated>python -c "import inference; assert not hasattr(inference, 'gr') or getattr(inference, 'gr', None) is None or callable(getattr(inference, 'build_ui', None))"</automated>
  </verify>
  <done>inference.py can be imported headlessly without Gradio installed, and test_suite.py imports succeed.</done>
</task>

<task type="auto">
  <name>Relabel Metrics to Honest Structural Values in App.jsx</name>
  <files>frontend/src/App.jsx</files>
  <action>
Update the metrics card in `frontend/src/App.jsx`:
1. Replace "Estimated Execution Speedup" and "Estimated Memory Reduction" cards with:
   - "AST Node Delta": showing the exact change in total AST nodes.
   - "Structural Complexity Score": showing AST nesting and branch reduction.
2. Add an honest tooltip/subtext: "Static AST Structural Metric — Real execution benchmarks available via Aion-Bench".
3. Remove polynomial calculation claims from UI text.
  </action>
  <verify>
    <automated>python -c "content = open('frontend/src/App.jsx', encoding='utf-8').read(); assert 'Execution Speedup' not in content or 'AST Structural' in content"</automated>
  </verify>
  <done>Frontend displays honest structural AST metrics instead of simulated speedup percentages.</done>
</task>

<task type="auto">
  <name>Configure Tier-1 Language Badging in App.jsx Language Selector</name>
  <files>frontend/src/App.jsx</files>
  <action>
In `frontend/src/App.jsx`:
1. Update the language options list to group languages:
   - **Supported (Tier-1):** Python, TypeScript, JavaScript.
   - **Experimental:** Java, C++, C, Go, Rust, Ruby, Kotlin, Swift, C#, PHP, HTML, CSS, SQL, Bash.
2. In the dropdown UI, render a clean badge or label: `(Supported)` next to Python, TypeScript, and JavaScript, and `(Experimental)` next to the others.
3. When an experimental language is selected, display an informational banner: "Language is in experimental static preview mode. Full AST grading active for Python & TypeScript."
  </action>
  <verify>
    <automated>python -c "content = open('frontend/src/App.jsx', encoding='utf-8').read(); assert 'Supported' in content and 'Experimental' in content"</automated>
  </verify>
  <done>Language selector clearly distinguishes Tier-1 supported languages from experimental ones.</done>
</task>

</tasks>

