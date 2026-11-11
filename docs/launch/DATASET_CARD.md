---
language:
- en
- python
- javascript
- typescript
license: apache-2.0
tags:
- code-review
- rlvr
- diff-analysis
- synthetic-bugs
- bug-detection
pretty_name: Aion Code Reviewer Dataset (Training v2 & Bench Real)
size_categories:
- 1K<n<10K
---

# Dataset Card: Aion Code Review Dataset (v2.0.0)

## Dataset Summary
The Aion Code Review Dataset consists of real mined code reviews, human-in-the-loop pilot feedback, clean-diff hard negative controls, and test-verified synthetic bug injections designed for training and evaluating reinforcement-learning-driven code review policies.

- **Dataset Version:** 2.0.0 (`TRAIN2-01`, `REAL-01`)
- **Repository:** https://github.com/Wall-E-30/code-reviewer
- **License:** Apache 2.0

## Dataset Composition & Mixture Standard

In compliance with Milestone v1.1 requirements (`TRAIN2-01`), synthetic data is strictly capped at $\le 50\%$ of the training mixture:

| Data Stream | Count | Proportion | Lineage Tag | Description |
|:---|:---:|:---:|:---:|:---|
| **Real Mined Reviews** | 80 | 30.77% | `[REAL-OFFLINE]` | Human pull request reviews mined from un-reserved open-source repositories. |
| **Pilot Maintainer Feedback** | 40 | 15.38% | `[LIVE-PILOT]` | Opt-in reactions and dismissals collected during live pilot reviews. |
| **Hard Negatives (Clean Diffs)** | 40 | 15.38% | `[REAL-OFFLINE]` | Merged clean PR diffs with zero bugs; policy trained to emit silence. |
| **Test-Verified Synthetic Bugs** | 100 | 38.46% | `[SYNTHETIC]` | Injected bugs verified by reproduction test failure (clean passes, buggy fails). |
| **Total Combined Dataset** | **260** | **100.0%** | Mixed | Synthetic ratio: **38.46%** (strictly $\le 50.0\%$). |

### Dataset Slices & Cryptographic Digests
The full dataset manifest is documented in `data/training_v2/manifest.json`.
- **Training Slice (`data/training_v2/train_v2.json`):** 221 records, SHA-256: `7010572b44c5d131f5e821893ee3426e9482e330a91b8d9916974f502eb2d75e`
- **Validation Slice (`data/training_v2/val_v2.json`):** 39 records, SHA-256: `273c16991b4840268cb77cc097e8a9f185a6105e1daa4830796e9dba531cdb76`

## Evaluation Benchmark & Contamination Invariants

The evaluation benchmark (`bench_real`) is maintained in complete isolation from the training data:
- **Reserved Benchmark Repositories:**
  - `bottlepy/bottle`
  - `aio-libs/aiohttp`
  - `tornadoweb/tornado`
  - `starlette/starlette`
  - `simonw/datasette`
- **Contamination Guard:** Every candidate in the training mixture is validated by `bench_real.contamination.ContaminationChecker` using exact repo path matching and 64-permutation MinHash Jaccard diff similarity ($\text{threshold} \le 0.80$). Overlap is strictly 0.
- **Evaluation Benchmark Slices:**
  - `bench_real/splits/val.json` ($N=100$, 75 real defect PRs, 25 clean PR negatives).
  - `bench_real/splits/test_locked.json` ($N=100$, sealed held-out test split).

## Data Quality, Verification & Privacy

1. **Test-Verified Bug Injection:** All synthetic mutations are verified via an automated test runner (`rl/training_v2/bug_generator.py`). Clean code must pass the test suite; the mutated buggy code must fail the test suite (`TRAIN2-02`).
2. **Secret Redaction:** All diffs and source code snippets are automatically sanitized by `action/redactor.py` prior to inclusion in datasets. AWS tokens, GitHub personal access tokens, OpenAI keys, private keys, and bearer tokens are scrubbed (`HARD-03b`).
3. **Data Policy:** No proprietary code is stored or used. Telemetry is opt-in, and only anonymized public open-source diffs are processed.
