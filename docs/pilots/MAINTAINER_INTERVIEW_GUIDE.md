# Aion Maintainer Qualitative Interview Protocol
**Version:** 1.1 | **Format:** Semi-structured, 20-minute video or async call | **Status:** `PILOT-05`

> **Ethical & Data Principle:** Maintainer interviews provide qualitative validation of Aion's design hypotheses. No responses or maintainer feedback are ever simulated or synthesized. All scheduled and completed interviews are recorded in `HUMAN_TODO.md`.

---

## Interview Metadata Template
- **Maintainer Name:** [Human Maintainer]
- **Repository:** `owner/repo`
- **Language / Tech Stack:** [Python / TypeScript / Go]
- **Pilot Review Mode Used:** `[ ] Shadow Mode (silent)` / `[ ] Visible Mode (active)`
- **Duration in Pilot:** [e.g. 2 weeks, 4 weeks]
- **Total PRs Reviewed by Aion:** [Count]
- **Date & Time:** [YYYY-MM-DD HH:MM UTC]
- **Interviewer:** [Team Member]

---

## Script & Questions (20 Minutes)

### Section 1: Background & Daily Workflow (3 mins)
*Goal: Understand baseline review burden and pain points.*

1. How many pull requests does your project receive in a typical week?
2. Who currently handles PR triage and code reviews in your team?
3. What percentage of your review time is spent catching bugs vs. stylistic / convention nitpicks?

---

### Section 2: Overall Signal-to-Noise & Volume (4 mins)
*Goal: Validate whether Aion's $\le 5$ comments ceiling and precision verifier prevent noise.*

1. During the pilot period, how did you perceive the comment volume from Aion?
   - *Probing:* Did it ever feel overwhelming, spammy, or distracting?
2. How was the tone of the review comments? Did they feel collaborative, intrusive, or neutral?
3. Did you ever feel the urge to mute or disable Aion?
   - *If yes:* What specific comment or behavior triggered that feeling?

---

### Section 3: False Positives & Dismissal Friction (5 mins)
*Goal: Evaluate false positive frustration and utility of one-click dismiss reasons.*

1. When Aion made an inaccurate or unhelpful suggestion, what was the primary reason?
   - [ ] Factual error / misunderstood context (`wrong`)
   - [ ] Stylistic preference / irrelevant formatting (`nitpick`)
   - [ ] Known tech debt / deliberate trade-off (`already_known`)
   - [ ] Outside the scope of the diff (`out_of_scope`)
2. Did you use the one-click dismiss keywords (e.g. `@aion nitpick`, `@aion wrong`)?
   - *If yes:* Did you notice Aion adapting its suggestions over time?
   - *If no:* Why not? (Unaware, too much effort, preferred ignoring)

---

### Section 4: 1-Click Suggestion Blocks & Applied Fixes (3 mins)
*Goal: Measure developer UX of GitHub markdown suggestion blocks.*

1. Did you or your contributors click GitHub's native "Apply suggestion" button to accept Aion's diffs?
2. How accurate were the code replacement blocks? Did they require manual edits after applying?
3. What made a suggestion immediately acceptable vs. immediately dismissible?

---

### Section 5: Net Promoter Score (NPS) & Value Perception (3 mins)
*Goal: Standardized satisfaction metric.*

1. **On a scale of 0 to 10**, how likely are you to recommend Aion to a fellow open-source maintainer?
   - Score: `[  ] / 10`
2. What is the single primary reason for your score?
3. Would you keep Aion installed on your repository after this pilot concludes?
   - [ ] Yes, in visible mode
   - [ ] Yes, but in shadow mode only
   - [ ] No / undecided

---

### Section 6: Wishlist & Next Steps (2 mins)
*Goal: Uncover high-value future roadmap items.*

1. If you could add or customize one capability in Aion for your repository, what would it be?
   - *Examples:* Custom repo rules, AST linter plugins, CI check gating, multi-file architectural analysis.
2. Any other feedback or suggestions for the team?

---

## Maintainer Post-Interview Checklist
- [ ] Save notes directly to private interview records (no public exposure of unconsented maintainer statements).
- [ ] Log qualitative findings and NPS score in `HUMAN_TODO.md`.
- [ ] Send thank-you note and attribution acknowledgment if maintainer opted in.

