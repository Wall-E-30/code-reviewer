# HUMAN_TODO.md — Human Actions & Outside Approvals Required

This document tracks all tasks in Milestone v1.1 that require external human intervention, external access, recruiting, real data labeling, or explicit user sign-off. In accordance with Non-Negotiable Rule #2 ("Never fake data"), the agent will not fabricate data, simulate human actions, or invent results.

---

## 1. Security Review & Audits
- [ ] **Outside Developer Security Review**: Have an independent security engineer audit `docs/SANDBOX_THREAT_MODEL.md` and the container sandbox constraints (`--pids-limit`, `--cap-drop ALL`, `--security-opt no-new-privileges`, read-only root, non-root user).

## 2. Real-Data Annotation (Phase 9: REAL-02)
- [ ] **Independent Annotator 1**:
  - Run the CLI annotation session:
    ```bash
    python -m bench_real.annotation.tool --annotator annotator_1 --input bench_real/data/candidates.json --output bench_real/data/labels_annotator_1.json
    ```
  - Label all 320 candidates across `actionable` (yes/no), `category` (bug/security/performance/style/clean), and rationale notes.
- [ ] **Independent Annotator 2**:
  - Run independent CLI annotation session (without viewing Annotator 1's output):
    ```bash
    python -m bench_real.annotation.tool --annotator annotator_2 --input bench_real/data/candidates.json --output bench_real/data/labels_annotator_2.json
    ```
  - Label all 320 candidates independently.
- [ ] **Inter-Annotator Agreement & Disagreement Resolution**:
  - Compute Cohen's kappa (κ) and extract disagreement cases:
    ```bash
    python -m bench_real.annotation.agreement --ann1 bench_real/data/labels_annotator_1.json --ann2 bench_real/data/labels_annotator_2.json --candidates bench_real/data/candidates.json --output bench_real/data/disagreements.json
    ```
  - Adjudicate borderline cases in `bench_real/data/disagreements.json` with a third senior reviewer to finalize the ground truth splits (`bench_real/splits/val.json` and `bench_real/splits/test_locked.json`).

## 3. Live Pilot Recruitment & Interviews (Phase 10: PILOT-01 to PILOT-05)

### 3.1 Candidate Pilot Repositories (10-20 Active OSS Projects)
Target active Python and TypeScript repositories with 5-30 PRs/week, active maintainers, and permissive open-source licenses:
- [ ] `psf/requests` (Python)
- [ ] `encode/starlette` (Python)
- [ ] `pallets/flask` (Python)
- [ ] `samuelcolvin/pydantic` (Python)
- [ ] `tiangolo/fastapi` (Python)
- [ ] `marshmallow-code/marshmallow` (Python)
- [ ] `encode/httpx` (Python)
- [ ] `tornadoweb/tornado` (Python)
- [ ] `simonw/datasette` (Python)
- [ ] `pre-commit/pre-commit` (Python)
- [ ] `facebook/jest` (TypeScript)
- [ ] `sindresorhus/got` (TypeScript)
- [ ] `expressjs/express` (JavaScript)
- [ ] `fastify/fastify` (JavaScript)
- [ ] `colinhacks/zod` (TypeScript)

### 3.2 Outreach Message Template (Shadow Mode Pilot Invitation)
> **Subject:** Invitation to pilot Aion: Zero-noise automated PR review (Silent Shadow Mode)
>
> Hi [Maintainer Name],
>
> I'm reaching out because I love your work maintaining [Repo Name]. We are developing **Aion**, an open-source automated code reviewer focused strictly on precision ($\ge 85\%$) and zero noise ($\le 5$ comments/PR ceiling with 1-click suggestion diffs).
>
> We would love to invite [Repo Name] to our pilot program:
> - **Week 1-2 (Shadow Mode):** Runs completely silently as a GitHub Action on your PRs. It analyzes diffs and logs candidate comments locally without posting anything to your contributors or maintainers.
> - **Zero Clutter:** Zero PR comments, zero notification noise.
> - **Security & Privacy:** Requires minimal read-only permissions (`contents: read`), scrubs all secrets/tokens before analysis, and retains zero code in memory.
> - **Review Tooling:** We share a weekly audit report showing what Aion would have flagged, and you let us know if it caught genuine issues.
>
> You can install the 1-file Action in 30 seconds using:
> `python scripts/install_pilot.py --mode shadow` (or see `docs/pilots/ONBOARDING_GUIDE.md`).
>
> Would you be open to letting Aion run silently in shadow mode on [Repo Name] for 2 weeks?
>
> Best,
> [Your Name] — Aion Project

### 3.3 Maintainer Permission & Security Checklist
- [ ] Maintainer has read `docs/pilots/ONBOARDING_GUIDE.md`.
- [ ] Repository admin permissions granted for GitHub Action runner or GitHub App installation.
- [ ] Mute commands verified (`@aion mute` / `@aion unmute`).
- [ ] Emergency kill switch acknowledged (`AION_KILL_SWITCH=true`).

### 3.4 Pilot Status & Interview Tracker (PILOT-05)
| Repository | Maintainer Contact | Mode | Status | Interview Date | NPS (0-10) | Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| *e.g. org/repo-sample* | *@maintainer* | `shadow` | *Outreach Sent* | *Pending* | - | *Awaiting response* |
| | | | | | | |
| | | | | | | |
| | | | | | | |

*Note: As interviews occur, log transcripts using the 20-minute protocol in `docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md`.*

### 3.5 Weekly Pilot Comment Auditing (PILOT-04)
1. Sample weekly candidate comments across pilot repos:
   ```bash
   python scripts/sample_pilot_comments.py --input .aion/shadow_reviews.jsonl --output-dir docs/pilots/audit_samples --sample-size 50
   ```
2. Annotate sampled comments in `docs/pilots/audit_samples/weekly_audit_sample.csv` (`audit_label`: `accurate` or `false_positive`, `applied`: `yes` or `no`).
3. Generate the weekly audited live precision report with 95% bootstrap confidence intervals:
   ```bash
   python scripts/pilot_audit_report.py --input docs/pilots/audit_samples/weekly_audit_sample.csv --output-md docs/pilots/AUDIT_REPORT_WEEKLY.md --output-json docs/pilots/audit_samples/weekly_metrics.json --repos 10 --muted-repos 0
   ```

## 4. Compute & Cloud Decisions (Phase 11)
- [ ] **GPU Compute Decisions**: Authorize long-running training runs (e.g. allocating Kaggle/Colab GPU hours or cloud compute credits).
- [ ] **Hugging Face / Model Hub Upload**: Authenticate credentials for pushing fine-tuned model checkpoints to public Hugging Face repositories.

## 5. Grants & Launch Timing (Phase 12)
- [ ] **Grant Applications**: Submit prepared grant dossiers to Hugging Face ZeroGPU, Google TRC, AWS Activate, and Microsoft Founders Hub.
- [ ] **Launch Timing & Show HN**: Authorize timing and execute external submissions (Show HN, GitHub Marketplace listing publication).

