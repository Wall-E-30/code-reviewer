---
phase: 10-live-pilots
plan: 04
type: execute
wave: 2
depends_on:
  - 10-01
  - 10-02
files_modified:
  - docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md
  - HUMAN_TODO.md
autonomous: true
requirements:
  - PILOT-05
must_haves:
  truths:
    - docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md provides a structured 20-minute qualitative interview script for pilot repo maintainers.
    - Questions cover noise perception, false positive frustration, suggestion block usability, and willingness to recommend.
    - All human outreach, partner recruitment, and interview scheduling are tracked strictly in HUMAN_TODO.md.
  artifacts:
    - docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md
    - HUMAN_TODO.md
---

<objective>
Draft the maintainer interview guide and isolate human outreach duties in `HUMAN_TODO.md` (`PILOT-05`).
Equip team members with a structured qualitative interview protocol for pilot maintainers, while preserving data honesty and recording human tasks in `HUMAN_TODO.md`.
</objective>

<tasks>

<task type="tracer">
  <name>Draft Maintainer Qualitative Interview Guide</name>
  <files>docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md</files>
  <action>
1. Author `docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md`:
   - 20-minute interview script:
     - Section 1: Background & PR review load
     - Section 2: Experience with Aion (signal-to-noise ratio, comment volume, tone)
     - Section 3: False positive friction & dismiss reasons (`wrong`, `nitpick`, `already_known`)
     - Section 4: Suggestion blocks & automated fixes
     - Section 5: Net Promoter Score (NPS) & willingness to recommend
     - Section 6: Feature requests and custom rule needs
  </action>
  <verify>
python -c "import os; assert os.path.exists('docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md')"
  </verify>
</task>

<task>
  <name>Update HUMAN_TODO.md with Pilot Recruitment and Outreach Plan</name>
  <files>HUMAN_TODO.md</files>
  <action>
1. Update `HUMAN_TODO.md`:
   - List target candidate repositories for pilot recruitment (10-20 active open source repos in Python/TypeScript).
   - Detail outreach message templates and permission checklists.
   - Schedule interview slots and logging templates for qualitative responses.
  </action>
  <verify>
python -c "with open('HUMAN_TODO.md') as f: assert 'Pilot Repo Recruitment' in f.read()"
  </verify>
</task>

</tasks>

