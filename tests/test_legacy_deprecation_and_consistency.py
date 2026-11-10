"""
tests/test_legacy_deprecation_and_consistency.py

Verification suite for Wave 3 (HARD-04, HARD-05):
- Legacy AST Prototype Files Deprecation & Archive (HARD-04)
- Server Endpoints (/reset, /step) Migration to ReviewEnv (HARD-04)
- Purging Unmeasured Polynomial Speedup & Memory Percentages (HARD-04)
- Documentation and Code Consistency Reconciliation (HARD-05)
"""

import os
import sys
import warnings
import pytest
from fastapi.testclient import TestClient

from server.app import app, get_env, ServerReviewEnv
from rl.env import ReviewEnv
from bench.evaluator.matcher import match_comments_to_findings
from rl.bandit import CategoryBandit


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_legacy_prototype_files_archived():
    """Verify legacy prototype files and explanatory README exist in legacy/."""
    assert os.path.isdir("legacy"), "legacy/ directory must exist"
    readme_path = os.path.join("legacy", "README.md")
    assert os.path.isfile(readme_path), "legacy/README.md must exist"

    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()

    assert "Reward Hacking" in readme_content or "reward hacking" in readme_content.lower()
    assert "ReviewEnv" in readme_content
    assert "HARD-04" in readme_content

    for legacy_file in ["env.py", "train_rl.py", "train_autoregressive_rl.py"]:
        path = os.path.join("legacy", legacy_file)
        assert os.path.isfile(path), f"Expected legacy file {path} to exist"


def test_root_deprecation_warnings():
    """Importing deprecated root files should emit DeprecationWarning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        if "env" in sys.modules:
            del sys.modules["env"]
        import env  # noqa: F401
        deprecation_warnings = [item for item in w if issubclass(item.category, DeprecationWarning)]
        assert len(deprecation_warnings) > 0, "Root env.py must emit DeprecationWarning on import"
        assert "deprecated" in str(deprecation_warnings[0].message).lower()


def test_server_env_is_review_env_subclass():
    """Verify server environment instances inherit from Gymnasium ReviewEnv."""
    env_instance = get_env("test-session-deprecate")
    assert isinstance(env_instance, ServerReviewEnv)
    assert isinstance(env_instance, ReviewEnv)


def test_server_reset_and_step_endpoints(client):
    """POST /reset and /step must function through ReviewEnv across standard tasks."""
    # 1. Reset with style-cleanup
    r1 = client.post("/reset", json={"task_id": "style-cleanup", "session_id": "s-style"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["current_task"] == "style-cleanup"
    assert "style_sample.py" in d1["file_name"]

    # 2. Reset with efficiency-boost
    r2 = client.post("/reset", json={"task_id": "efficiency-boost", "session_id": "s-eff"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["current_task"] == "efficiency-boost"
    assert "find_duplicates" in d2["code_content"]

    # 3. Step execution
    step_payload = {
        "action_type": "apply_fix",
        "content": "def hello_world():\n    print('Hello World')\n",
        "session_id": "s-style",
    }
    r3 = client.post("/step", json=step_payload)
    assert r3.status_code == 200
    d3 = r3.json()
    assert "observation" in d3
    assert "reward" in d3
    assert 0.01 <= d3["reward"]["value"] <= 0.99
    assert d3["reward"]["value"] > 0

    # 4. State endpoint
    r4 = client.get("/state")
    assert r4.status_code == 200
    d4 = r4.json()
    assert "task_id" in d4
    assert "code_content" in d4


def test_unmeasured_speedup_purged_from_optimize(client):
    """POST /optimize must return honest static metric labels, never fabricated speedup percentages."""
    payload = {
        "code": "def find_dup(a, b):\n    return [x for x in a if x in b]\n",
        "task_type": "efficiency-boost",
        "language": "python",
    }
    response = client.post("/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Must contain honest labels, not fake percentages
    assert "perf_gain" in data
    assert "mem_reduction" in data
    assert "Static Analysis" in data["perf_gain"]
    assert "AST" in data["mem_reduction"]
    # Verify no fake percentage like +95.2% or memory like -25.5MB is reported as fact
    assert "%" not in data["perf_gain"]
    assert "MB" not in data["mem_reduction"]


def test_matcher_greedy_bipartite_documentation():
    """bench/evaluator/matcher.py must document Greedy Bipartite Line-Distance Matching."""
    import bench.evaluator.matcher as matcher_mod
    doc = matcher_mod.__doc__ or ""
    assert "Greedy Bipartite Line-Distance Matching" in doc
    assert "not Hungarian" in doc or "not Hungarian/Kuhn-Munkres" in doc

    fn_doc = match_comments_to_findings.__doc__ or ""
    assert "Greedy Bipartite Line-Distance Matching" in fn_doc


def test_bandit_thompson_sampling_documentation():
    """rl/bandit.py must document Per-Category Beta-Bernoulli Thompson Sampling with [0.50, 0.95] bounds."""
    import rl.bandit as bandit_mod
    doc = bandit_mod.__doc__ or ""
    assert "Thompson Sampling" in doc
    assert "Beta-Bernoulli" in doc
    assert "[0.50, 0.95]" in doc

    cls_doc = CategoryBandit.__doc__ or ""
    assert "Beta-Bernoulli Thompson Sampling" in cls_doc
    assert "[0.50, 0.95]" in cls_doc


def test_architecture_doc_consistency():
    """docs/ARCHITECTURE.md must document python -m bench.runner, ReviewEnv, and algorithm specifications."""
    arch_path = os.path.join("docs", "ARCHITECTURE.md")
    assert os.path.isfile(arch_path), "docs/ARCHITECTURE.md must exist"

    with open(arch_path, "r", encoding="utf-8") as f:
        arch_content = f.read()

    assert "python -m bench.runner" in arch_content
    assert "ReviewEnv" in arch_content
    assert "Greedy Bipartite Line-Distance Matching" in arch_content
    assert "Beta-Bernoulli Thompson Sampling" in arch_content
    assert "HARD-04" in arch_content
    assert "HARD-05" in arch_content
