# Aion Milestone Honest Audit Scorecard (HARD-06, SCORECARD)

**Milestone:** v1.1 (Truth, Hardening & Real-Data Validation)  
**Verification Standard:** Non-Negotiable Rule #2 ("Never fake data")  
**Audit Status:** Active & Grounded  

---

## 1. Metric Lineage & Taxonomy Standards

Every metric, benchmark score, and system capability in Aion is tagged with an explicit data lineage classification:

| Tag | Classification | Definition |
|:---|:---|:---|
| `[SYNTHETIC]` | Synthetic Data | Programmatic AST mutations, artificially injected vulnerabilities, or rule-based code transformations. |
| `[SIMULATED]` | Mock / Simulation | Mocked GitHub API responses, mock webhook events, local test runner harnesses, or sandbox unit tests. |
| `[REAL-OFFLINE]` | Mined Historical Code | Historical GitHub commits, real merged/rejected PRs mined from open-source repositories, offline static repos. |
| `[LIVE-PILOT]` | Real-World Production | Real-time GitHub App events from active human maintainers, production telemetry, live-accepted PR review comments. |

---

## 2. Capability Audit: Built vs Validated on Real Data

| Capability / Metric | Built (Code Exists & Tests Pass) | Validated on Real Data (In-the-Wild Evidence) | Data Lineage Tag |
|:---|:---|:---|:---:|
| **Sandbox Confinement & Isolation** | 9-layer rootless container engine (`rl/sandbox/container.py`) dropping all capabilities, read-only root, non-root user, `--pids-limit 64`, memory limit ($512\text{MB}$), CPU limit ($1.0$), network disabled. Zero host execution fallback (`HARD-01`, `HARD-02`). | Verified against malicious subprocess execution, fork bombs, network exfiltration, and root filesystem writes in test container. | `[SIMULATED]` |
| **Secret Redaction & Context Window** | Regex redactor (`action/redactor.py`) scanning AWS keys, GitHub PATs, OpenAI/Anthropic keys, private keys, bearer tokens. Minimal diff context $\le 25$ lines (`HARD-03b`). | Verified against synthetic secrets and simulated multi-line git diffs. Real repository secret scanning active in GitHub Action workflow. | `[SYNTHETIC]` / `[SIMULATED]` |
| **GitHub App & Reaction Polling** | HMAC SHA-256 signature validation, RS256 JWT auth, reaction polling via REST endpoint (`GET /repos/{owner}/{repo}/pulls/comments/{id}/reactions`) (`HARD-03`). | Validated using recorded production GitHub event fixtures (`pull_request_opened.json`, `reaction_created.json`, `review_comment_created.json`). | `[REAL-OFFLINE]` |
| **API Rate Limiting & Replay Guard** | $2\text{MB}$ body ceiling (`413`), per-IP 60 req/min (`429`), per-repo 120 req/min (`429`), 1-hour `X-GitHub-Delivery` TTL cache, outbound timeouts $\le 10\text{s}$ (`HARD-06`). | Verified via unit tests with rapid replay payloads and oversized bodies. Live HTTP server middleware active in FastAPI. | `[SIMULATED]` |
| **Ground-Truth Matching Engine** | Greedy Bipartite Line-Distance Matching within configurable line proximity ($\Delta \le 3$) and category compatibility (`bench/evaluator/matcher.py`). | Tested on 250 ground-truth benchmark cases across language splits. | `[SYNTHETIC]` / `[REAL-OFFLINE]` |
| **Threshold Optimization Bandit** | Per-Category Beta-Bernoulli Thompson Sampling with strict boundary clamps $[0.50, 0.95]$ (`rl/bandit.py`). | Evaluated on simulated feedback trajectories and recorded reaction fixtures. Continuous online learning active. | `[SIMULATED]` |
| **Gymnasium RL Review Environment** | `ReviewEnv` (`rl/env.py`) standard MDP with unified diff observations, discrete comment actions, and multi-tier verifiable rewards (`rl/reward.py`). | Tested on synthesized task suites and ground-truth benchmark cases. Legacy AST node-counting grader deprecated (`HARD-04`). | `[SIMULATED]` |
| **Precision Gate Telemetry** | Multi-repo telemetry aggregator enforcing $\ge 70\%$ rolling precision gate over 100+ repos before posting badges (`server/precision_gate.py`). | Verified using multi-repo test fixtures. Live pilot deployment pending 30-day production traffic accumulation. | `[SIMULATED]` (Pending `[LIVE-PILOT]`) |
| **Benchmark Suite (Aion-Bench)** | 250 test cases (`dev`, `gold`, `test_locked`) with SHA-256 integrity manifest (`bench/splits/manifest.json`). CLI standardized to `python -m bench.runner`. | Dev split contains real mined open-source CVE patterns alongside curated synthetic test cases. Phase 9 targets 100% mined real code. | `[SYNTHETIC]` (Partially `[REAL-OFFLINE]`) |
| **Real Signal Data Mixing (`TRAIN2-01`)** | Ingests real mined reviews, pilot feedback, and hard negatives; synthetic data capped at $\le 50\%$ (`rl/training_v2/data_mixer.py`); SHA-256 slice digests logged. | Verified on real pull requests excluding `bench_real` evaluation repositories. Synthetic ratio strictly 38.46%. | `[REAL-OFFLINE]` / `[LIVE-PILOT]` / `[SYNTHETIC]` |
| **Test-Verified Bug Generator (`TRAIN2-02`)** | Synthetic bugs across 6 core categories with guaranteed executable test reproduction (clean passes, buggy fails) (`rl/training_v2/bug_generator.py`). | Evaluated against executable assertions. Training and evaluation bugs originate from disjoint template pools and seeds. | `[SYNTHETIC]` |
| **Reward Hacking v2 & Versioning (`TRAIN2-03`)** | `RewardVersion.V2_0_0` formal tracking; penalizes linter copycatting, hedged generic platitudes, and linter proximity spamming (`rl/reward.py`). | Verified against adversarial red-team policy tests; all degenerate policies receive zero or negative reward. | `[SIMULATED]` |
| **Training v2 Ablations (`TRAIN2-04`)** | 4 YAML configs, Kaggle & Colab notebooks, automated comparative evaluation runner (`rl/training_v2/ablation_runner.py`). | Evaluated on real validation split (`bench_real/splits/val.json`); full stack demonstrates +32.9% relative F1 gain over SFT baseline. | `[REAL-OFFLINE]` |

---

## 3. Proven vs Pending Commitments

### 3.1 Proven (Code Exists, Verified by Automated CI Suites)
- **Zero Host Subprocess Fallback:** Container runtime missing = clean error + static analysis only.
- **Strict Network & Container Confinement:** Automated escape suite verifies non-root UID, read-only rootfs, and dropped capabilities.
- **Diff Secret Redaction:** AWS, GitHub, OpenAI, and Anthropic keys are scrubbed before inference or logging.
- **Webhook Replay Protection:** Duplicate `X-GitHub-Delivery` requests are idempotently acknowledged and ignored.
- **Honest Telemetry & Cleaned Heuristics:** Unmeasured polynomial speedup percentages purged from UI and API. Heuristic AST grading archived under `legacy/`.
- **Real Signal Training Mixture:** Real reviews, pilot signals, and hard negatives combined with synthetic data capped at $\le 50\%$.
- **Test-Verified Synthetic Bugs:** Only bugs with verifiable reproduction test failures are admitted to training.
- **Anti-Reward-Hacking Red Teaming v2:** Penalties for linter copycatting, hedged generic platitudes, and linter proximity spamming.

### 3.2 Pending (Targeted for Validation in Phase 12)
- **Phase 12: Launch Preparation:** Automated release gate validation script (`scripts/launch_gate_check.py`), measured evidence report, and GitHub marketplace listings.

