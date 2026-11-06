"""
tests/test_data_engine_isolation.py

Data engine cryptographic isolation and dataset distribution verification (DATA-01, DATA-02):
1. Assert 0 SHA-256 hash collisions between generated training episodes and bench/splits/manifest.json.
2. Assert zero repository-level overlap with benchmark test/gold splits.
3. Verify total episode count in training_manifest.json is >= 10,000.
4. Verify language balance (>= 40% Python and >= 40% TypeScript).
5. Verify clean-diff representation (>= 25% clean negatives to prevent false positive over-commenting).
6. Verify LeakageGuard accurately detects intentional collisions and blacklisted repos.
"""

import json
import os
import pytest
from rl.data_engine.isolation import LeakageGuard, compute_content_hash

MANIFEST_PATH = "data/episodes/training_manifest.json"
STREAM_PATH = "data/episodes/episodes_stream.jsonl"
BENCH_MANIFEST_PATH = "bench/splits/manifest.json"
GOLD_PATH = "bench/splits/gold.json"
TEST_LOCKED_PATH = "bench/splits/test_locked.json"


@pytest.fixture(scope="module")
def training_manifest():
    """Load training manifest data."""
    assert os.path.exists(MANIFEST_PATH), f"Missing {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def benchmark_protected_signatures():
    """Extract all protected SHA-256 digests and repositories from benchmark splits."""
    with open(BENCH_MANIFEST_PATH, "r", encoding="utf-8") as f:
        bench_manifest = json.load(f)

    splits = bench_manifest.get("splits", {})
    protected_hashes = set()
    for s_name in ("gold", "test_locked"):
        case_hashes = splits.get(s_name, {}).get("case_hashes", {})
        for h in case_hashes.values():
            protected_hashes.add(h.lower())

    protected_repos = set()
    for p in (GOLD_PATH, TEST_LOCKED_PATH):
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                cases = json.load(f)
            for c in cases:
                repo = c.get("repository", "").strip().lower()
                if repo:
                    protected_repos.add(repo)
                c_hash = compute_content_hash(
                    c.get("original_code", ""),
                    c.get("modified_code", ""),
                    c.get("diff", ""),
                )
                protected_hashes.add(c_hash.lower())

    return protected_hashes, protected_repos


def test_zero_hash_collisions_with_benchmark_splits(benchmark_protected_signatures):
    """
    Test 1: Assert 0 SHA-256 hash collisions between generated training episodes
    and Aion-Bench test splits (DATA-02).
    """
    protected_hashes, _ = benchmark_protected_signatures
    guard = LeakageGuard()

    collisions = []
    audited = 0

    assert os.path.exists(STREAM_PATH), f"Missing {STREAM_PATH}"
    with open(STREAM_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            ep = json.loads(line)
            audited += 1

            ep_hash = guard.compute_episode_hash(ep).lower()
            if ep_hash in protected_hashes:
                collisions.append(ep.get("case_id"))

    assert len(collisions) == 0, f"Detected {len(collisions)} hash collisions: {collisions[:5]}"
    assert audited >= 10000


def test_zero_repository_overlap_with_benchmark_splits(benchmark_protected_signatures):
    """
    Test 2: Assert zero repository-level overlap with benchmark test/gold splits (DATA-02).
    """
    _, protected_repos = benchmark_protected_signatures
    repo_violations = set()

    with open(STREAM_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            ep = json.loads(line)
            repo = ep.get("repository", "").strip().lower()
            if repo in protected_repos:
                repo_violations.add(repo)

    assert len(repo_violations) == 0, f"Detected repository overlap: {repo_violations}"


def test_total_episode_count_target(training_manifest):
    """
    Test 3: Verify total episode count in training_manifest.json is >= 10,000 (DATA-01).
    """
    total = training_manifest.get("total_episodes", 0)
    assert total >= 10000, f"Expected >= 10,000 episodes, found {total}"
    assert training_manifest.get("leakage_collisions", -1) == 0
    assert training_manifest.get("cryptographic_isolation_verified") is True


def test_language_balance(training_manifest):
    """
    Test 4: Verify language balance (>= 40% Python and >= 40% TypeScript).
    """
    breakdown = training_manifest.get("language_breakdown", {})
    py_ratio = breakdown.get("python", {}).get("ratio", 0.0)
    ts_ratio = breakdown.get("typescript", {}).get("ratio", 0.0)

    assert py_ratio >= 0.40, f"Python ratio {py_ratio} is below 40%"
    assert ts_ratio >= 0.40, f"TypeScript ratio {ts_ratio} is below 40%"


def test_clean_diff_representation(training_manifest):
    """
    Test 5: Verify clean-diff representation (>= 25% of episodes are clean negatives).
    """
    dist = training_manifest.get("case_type_distribution", {})
    clean_ratio = dist.get("clean_negative_ratio", 0.0)

    assert clean_ratio >= 0.25, f"Clean negative ratio {clean_ratio} is below 25%"
    assert dist.get("clean_negative", 0) >= 2500


def test_leakage_guard_detection_accuracy():
    """
    Test 6: Verify LeakageGuard actively detects and flags intentional collisions
    and blacklisted repositories.
    """
    guard = LeakageGuard()

    # Episode with blacklisted repo from benchmark
    contaminated_repo_ep = {
        "case_id": "ep-fake-01",
        "repository": "facebook/react",  # Protected repo!
        "original_code": "const a = 1;",
        "modified_code": "const a = 2;",
        "diff": "@@ -1 +1 @@\n-const a = 1;\n+const a = 2;\n",
    }
    assert guard.is_leaked(contaminated_repo_ep) is True

    # Episode with clean safe repo
    safe_ep = {
        "case_id": "ep-safe-01",
        "repository": "aion-training/py-core-utils",
        "original_code": "def func():\n    return 1\n",
        "modified_code": "def func():\n    return 2\n",
        "diff": "@@ -1,2 +1,2 @@\n def func():\n-    return 1\n+    return 2\n",
    }
    assert guard.is_leaked(safe_ep) is False
