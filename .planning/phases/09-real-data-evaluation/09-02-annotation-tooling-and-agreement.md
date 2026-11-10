---
phase: 09-real-data-evaluation
plan: 02
type: execute
wave: 2
depends_on:
  - 09-01
files_modified:
  - bench_real/annotation/__init__.py
  - bench_real/annotation/tool.py
  - bench_real/annotation/agreement.py
  - HUMAN_TODO.md
  - tests/test_bench_real_annotation.py
autonomous: true
requirements:
  - REAL-02
must_haves:
  truths:
    - An annotation tool CLI/script allows independent review of candidate cases and exports separate label files per annotator.
    - An agreement script computes Cohen's kappa (κ), observed agreement, and extracts detailed disagreement lists.
    - In accordance with non-negotiable rule #2, no agent fabricates human labels. Human annotation tasks and guidelines are logged in HUMAN_TODO.md.
  artifacts:
    - bench_real/annotation/tool.py
    - bench_real/annotation/agreement.py
    - tests/test_bench_real_annotation.py
---

<objective>
Build the human annotation tool and inter-annotator agreement pipeline (`REAL-02`).
Enable two independent annotators to label candidates without bias, compute Cohen's kappa agreement statistics, and extract disagreement sets while isolating real human review duties to `HUMAN_TODO.md`.
</objective>

<tasks>

<task type="tracer">
  <name>Build Annotation CLI Tool and Exporter</name>
  <files>bench_real/annotation/__init__.py, bench_real/annotation/tool.py</files>
  <action>
1. Create `bench_real/annotation/__init__.py`.
2. Create `bench_real/annotation/tool.py`:
   - Interactive CLI command `python -m bench_real.annotation.tool --input candidates.json --annotator <name>`
   - Displays diff hunks, PR context, and metadata.
   - Prompts for actionability (yes/no), category classification, line numbers, and rationale.
   - Saves progress incrementally and exports independent label files (e.g. `annotator_1.json`, `annotator_2.json`).
  </action>
  <verify>
python -c "from bench_real.annotation.tool import AnnotationSession; print('Annotation session ready')"
  </verify>
</task>

<task>
  <name>Build Inter-Annotator Agreement Engine and Human Protocol</name>
  <files>bench_real/annotation/agreement.py, HUMAN_TODO.md, tests/test_bench_real_annotation.py</files>
  <action>
1. Create `bench_real/annotation/agreement.py`:
   - Implements Cohen's kappa ($\kappa = \frac{p_o - p_e}{1 - p_e}$) for binary actionability agreement.
   - Computes multi-class agreement on bug categories.
   - Identifies cases with conflicting votes and outputs `disagreements.json` for tie-breaking/adjudication.
2. Update `HUMAN_TODO.md` with detailed instructions for human annotators on operating `bench_real.annotation.tool` and reviewing candidates.
3. Add `tests/test_bench_real_annotation.py` verifying annotation session loading, export schema, kappa computation (perfect agreement = 1.0, chance agreement = ~0.0), and disagreement extraction.
  </action>
  <verify>
python -m pytest tests/test_bench_real_annotation.py -v
  </verify>
</task>

</tasks>

