# HUMAN_TODO.md — Human Actions & Outside Approvals Required

This document tracks all tasks in Milestone v1.1 that require external human intervention, external access, recruiting, real data labeling, or explicit user sign-off. In accordance with Non-Negotiable Rule #2 ("Never fake data"), the agent will not fabricate data, simulate human actions, or invent results.

---

## 1. Security Review & Audits
- [ ] **Outside Developer Security Review**: Have an independent security engineer audit `docs/SANDBOX_THREAT_MODEL.md` and the container sandbox constraints (`--pids-limit`, `--cap-drop ALL`, `--security-opt no-new-privileges`, read-only root, non-root user).

## 2. Real-Data Annotation (Phase 9)
- [ ] **Independent Annotator 1**: Label collected `bench_real/` candidates using the annotation CLI/web tool.
- [ ] **Independent Annotator 2**: Independently label the same cases to establish Cohen's kappa agreement and resolve the disagreement list.
- [ ] **Review Real Disagreements**: Review borderline cases where Annotators 1 & 2 disagreed before finalizing the ground-truth benchmark split.

## 3. Live Pilot Recruitment & Interviews (Phase 10)
- [ ] **Pilot Repo Recruitment**: Reach out to 10-20 active open-source repository maintainers to recruit for Shadow and Visible review pilots.
- [ ] **Conduct Maintainer Interviews**: Run interviews using the `docs/pilots/MAINTAINER_INTERVIEW_GUIDE.md` protocol to collect feedback on noise, comment utility, and workflow integration.
- [ ] **Install Authorizations**: Obtain repository admin approval and installation of the GitHub App on external pilot repositories.

## 4. Compute & Cloud Decisions (Phase 11)
- [ ] **GPU Compute Decisions**: Authorize long-running training runs (e.g. allocating Kaggle/Colab GPU hours or cloud compute credits).
- [ ] **Hugging Face / Model Hub Upload**: Authenticate credentials for pushing fine-tuned model checkpoints to public Hugging Face repositories.

## 5. Grants & Launch Timing (Phase 12)
- [ ] **Grant Applications**: Submit prepared grant dossiers to Hugging Face ZeroGPU, Google TRC, AWS Activate, and Microsoft Founders Hub.
- [ ] **Launch Timing & Show HN**: Authorize timing and execute external submissions (Show HN, GitHub Marketplace listing publication).

