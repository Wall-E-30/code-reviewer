# Aion Open-Source Commitment (GROWTH-01)

**Effective Date:** 2026-11-07  
**Status:** Permanent & Irrevocable Policy  

---

## 1. The Open-Source Guarantee

Aion was founded on the principle that world-class, AI-native code review should not be a walled garden restricted to well-funded enterprises. High-precision automated code review is essential infrastructure for open-source sustainability, maintainer mental health, and global software security.

We make the following **permanent and irrevocable commitments**:

1. **Permanently Free for Public Open Source:**
   The full Aion review pipeline—including the GitHub Action, webhook-driven GitHub App, local CLI (`aion review --staged`), and official VS Code extension—is **100% free forever** for all public repositories licensed under an [OSI-approved open-source license](https://opensource.org/licenses).
2. **No Rate-Limit Paywalls on Quality:**
   Open-source repositories receive the exact same high-precision, AST-verified review models, actionability verifiers, and contextual bandit optimizations as enterprise deployments. There are no synthetic downgrades, crippled models, or artificial comment limits.
3. **No Private Code Exploitation:**
   Aion will **never** train models on private user repositories without explicit, opt-in consent. For open-source repositories, telemetry is strictly confined to anonymized comment acceptance signals (thumbs up, thumbs down, comment resolution) to train open-weight community models.
4. **Open Weights & Open Benchmark:**
   All fine-tuned code models, verifier weights, training pipelines (SFT, GRPO / RLVR), and evaluation benchmarks (`Aion-Bench`) are released openly under Apache-2.0 to foster collaborative AI research.

---

## 2. "Reviewed by Aion" README Badge

Open-source maintainers who use Aion are invited to display the live **Reviewed by Aion** badge in their repository README. The badge dynamically reflects your project's rolling review precision, signaling to contributors that code quality is automatically verified.

### Markdown Embed

```markdown
[![Reviewed by Aion](https://aion.openenv.org/api/badge/{owner}/{repo})](https://github.com/aion-ai/aion)
```

### HTML Embed

```html
<a href="https://github.com/aion-ai/aion">
  <img src="https://aion.openenv.org/api/badge/{owner}/{repo}" alt="Reviewed by Aion" />
</a>
```

### Badge Status Thresholds

| Badge Value | Color | Threshold | Meaning |
|---|:---:|:---:|---|
| **`passing` / `≥70% precision`** | **Green** (`#2ea44f`) | $\ge 70.0\%$ | Production-grade precision gate passed; low review noise. |
| **`monitoring` / `50–69% precision`** | **Yellow** (`#dfb317`) | $50.0\% - 69.9\%$ | Active learning phase; contextual bandit is adapting. |
| **`low precision` / `<50% precision`** | **Red** (`#cb2431`) | $< 50.0\%$ | Elevated rejection rate; maintainer conventions needed. |
| **`unverified`** | **Gray** (`#9f9f9f`) | No reviews yet | Repository newly registered; pending first review run. |

---

## 3. Public Repository Quality Dashboard

Maintainers can query their live repository quality profile at any time:

```bash
curl -s https://aion.openenv.org/api/repos/{owner}/{repo}/quality
```

**Sample Response:**

```json
{
  "repo_id": "facebook/react",
  "precision": 0.824,
  "precision_percentage": "82.4%",
  "comments_posted": 34,
  "comments_accepted": 28,
  "comments_rejected": 6,
  "status": "PASS ✅",
  "badge_url": "/api/badge/facebook/react",
  "badge_markdown": "[![Reviewed by Aion](/api/badge/facebook/react)](https://github.com/aion-ai/aion)",
  "free_tier": "Free for Open Source (Guaranteed)"
}
```

---

## 4. Governance and Sustainability

Our free-for-open-source pledge is made financially sustainable through:
- **Zero-Host Architecture:** The GitHub Action and local CLI run compute directly on user runners or local hardware at zero hosting cost to the project.
- **Compute Grants:** Cloud and GPU compute credits from partner foundations (Hugging Face ZeroGPU, Google Cloud for Startups, AWS Activate, Microsoft for Startups).
- **Commercial Hosted SaaS:** Private organizations with proprietary codebases pay for managed hosting and SLA guarantees, directly subsidizing open-source compute.

