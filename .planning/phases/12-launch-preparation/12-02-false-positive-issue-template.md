---
phase: 12-launch-preparation
plan: 02
type: execute
wave: 2
depends_on: []
files_modified:
  - .github/ISSUE_TEMPLATE/false_positive_report.yml
  - tests/test_issue_template.py
autonomous: true
requirements:
  - LAUNCH-02
must_haves:
  truths:
    - GitHub Issue Form template exists at .github/ISSUE_TEMPLATE/false_positive_report.yml.
    - Template is syntactically valid YAML matching GitHub Issue Forms specifications.
    - Template captures repo, PR URL, file & line, comment body, category reason dropdown, and diff context.
    - Standard issue labels false-positive and triage are automatically assigned.
  artifacts:
    - .github/ISSUE_TEMPLATE/false_positive_report.yml
    - tests/test_issue_template.py
---

<objective>
Implement the False-Positive GitHub Issue Template (`LAUNCH-02`).
Create `.github/ISSUE_TEMPLATE/false_positive_report.yml` to give open-source developers a structured, frictionless path to report inaccurate, noisy, or hallucinated review comments.
</objective>

<tasks>

<task type="tracer">
<name>Create False Positive Issue Form Template</name>
<files>.github/ISSUE_TEMPLATE/false_positive_report.yml</files>
<action>
1. Ensure `.github/ISSUE_TEMPLATE` directory exists.
2. Create `.github/ISSUE_TEMPLATE/false_positive_report.yml` adhering to GitHub Issue Form schema:
   - `name`: False Positive Review Report
   - `description`: Report an inaccurate, hallucinated, or unhelpful comment posted by Aion.
   - `title`: "[False Positive]: <brief summary>"
   - `labels`: ["false-positive", "triage"]
   - `body`:
     - Introduction markdown disclaimer.
     - Repository & PR link (input, required).
     - File path & line number (input, required).
     - Aion's comment text (textarea, required).
     - Reason for False Positive (dropdown, required):
       - "Incorrect logic claim (the code was actually correct)"
       - "Broken or invalid suggestion replacement (syntax error / test fail)"
       - "Subjective style / formatting nitpick (violates policy)"
       - "Already known or existing pattern in codebase"
       - "Out of scope / irrelevant to PR diff"
     - Code snippet / Diff context (textarea, required).
     - Expected behavior vs What happened (textarea, required).
     - Checklist confirming secret scrubbing and reproducible context.
</action>
<verify>
python -c "import yaml; yaml.safe_load(open('.github/ISSUE_TEMPLATE/false_positive_report.yml', encoding='utf-8')); print('Valid YAML issue template')"
</verify>
</task>

<task>
<name>Unit Test Issue Template Validation</name>
<files>tests/test_issue_template.py</files>
<action>
Create `tests/test_issue_template.py` verifying:
1. File exists at `.github/ISSUE_TEMPLATE/false_positive_report.yml`.
2. Valid YAML parsing without errors.
3. Top-level keys include `name`, `description`, `title`, `labels`, and `body`.
4. Required fields (PR URL, file/line, comment text, reason dropdown, diff snippet) are present and marked `required: true`.
5. Labels include `false-positive`.
</action>
<verify>
pytest tests/test_issue_template.py -v
</verify>
</task>

</tasks>

