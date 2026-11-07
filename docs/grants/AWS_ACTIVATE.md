# Grant Application: AWS Activate & Open Source Cloud Credits

**Project Title:** Scaled Ephemeral Sandboxing & Telemetry Infrastructure for Aion  
**Applicant:** Aion Core Project  
**Repository:** https://github.com/aion-ai/aion  
**Target Organization:** AWS Activate Program & AWS Open Source Credits Committee  
**Grant Track:** AWS Activate Founders / Open Source Cloud Computing Grant  

---

## 1. Executive Summary

Aion is an open-source, RL-driven code review engine built to deliver high-precision, low-noise reviews on GitHub pull requests. To evaluate prospective code reviews objectively, Aion operates an OpenEnv Gymnasium environment (`ReviewEnv`) where proposed code patches and suggestions are executed against dynamic AST linters, security scanners, and containerized test suites.

We are requesting AWS Promotional Cloud Credits to deploy and scale our containerized execution infrastructure on **AWS Fargate** and host our multi-repository telemetry aggregator and public benchmark datasets on **Amazon S3** and **Amazon ECS**.

## 2. Technical Architecture on AWS

1. **Serverless Ephemeral Rollout Sandboxes (AWS Fargate):**
   - Each RL rollout runs inside an ephemeral, non-root container with strict memory (1GB) and CPU (1 vCPU) limits.
   - Executes compiler runs and unit test patches to score policy action rewards in under 2 seconds per episode.
   - Eliminates persistent infrastructure costs by scaling to zero when no PR rollouts are active.
2. **Multi-Repo Telemetry & 30-Day Precision Gate:**
   - Aggregates maintainer reaction feedback (`+1`, `-1`, resolved comments) across $\ge 100$ active open-source repositories over a rolling 30-day window.
   - Enforces the permanent precision gate ($\ge 70\%$ precision) to guarantee continuous model quality.
3. **Public S3 Data Lake for Aion-Bench:**
   - Hosts public, versioned diff evaluation cases, mined human review episodes, and baseline result json files with Amazon S3 lifecycle management.

## 3. Resource & Budget Plan

| AWS Service | Use Case | Estimated Monthly Cost |
|---|---|:---:|
| **AWS Fargate / ECS** | Ephemeral sandbox execution for 50,000 monthly rollouts | \$800 |
| **Amazon EC2 (g5.xlarge)** | Periodic QLoRA SFT model calibration runs | \$650 |
| **Amazon S3 + CloudFront** | Hosting benchmark cases, SVG badges, and leaderboard | \$250 |
| **Amazon RDS (PostgreSQL)** | Persistent telemetry events and convention memory state | \$200 |
| **Total Requested:** | **\$25,000 in AWS Activate Promotional Credits** | Covers 12 months |

## 4. Open-Source Commitment

All code, CDK deployment scripts, and container manifests are distributed under Apache-2.0. Aion is permanently free for public open-source projects, and AWS will be acknowledged as a primary compute sponsor in repository documentation and the public leaderboard.

