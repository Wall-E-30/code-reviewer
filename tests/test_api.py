import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from server.app import app

@pytest.fixture
def client():
    """Pytest fixture providing a test client for the FastAPI app."""
    return TestClient(app)


def test_health(client):
    """GET /health returns 200 and online status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("online", "healthy")
    assert data["engine"] == "aion-v3"
    assert "uptime" in data


def test_ready(client):
    """GET /ready returns 200 and ready status."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_reset_endpoint_default(client):
    """POST /reset with empty body returns default Observation schema."""
    response = client.post("/reset", json={})
    assert response.status_code == 200
    data = response.json()
    assert "code_content" in data
    assert "file_name" in data
    assert "diff" in data
    assert "linter_report" in data
    assert data["current_task"] == "style-cleanup"
    assert isinstance(data["linter_report"], list)


def test_reset_endpoint_specific_task(client):
    """POST /reset with task_id and session_id returns corresponding Observation."""
    session_id = "test-session-reset-123"
    response = client.post("/reset", json={
        "task_id": "efficiency-boost",
        "session_id": session_id
    })
    assert response.status_code == 200
    data = response.json()
    assert data["current_task"] == "efficiency-boost"
    assert "find_duplicates" in data["code_content"]
    assert isinstance(data["linter_report"], list)


def test_step_endpoint(client):
    """POST /step applies Action and returns Observation with structured Reward."""
    session_id = "test-session-step-456"
    # First reset session
    client.post("/reset", json={"task_id": "style-cleanup", "session_id": session_id})

    # Apply a fix action
    fixed_code = (
        "def hello_world():\n"
        "    print('Hello')\n"
        "    print('Indentation is wrong here')\n\n"
        "if __name__ == '__main__':\n"
        "    hello_world()"
    )
    step_payload = {
        "action_type": "apply_fix",
        "content": fixed_code,
        "session_id": session_id
    }
    response = client.post("/step", json=step_payload)
    assert response.status_code == 200
    data = response.json()

    assert "observation" in data
    assert "reward" in data
    assert "done" in data
    assert "info" in data

    reward = data["reward"]
    assert "value" in reward
    assert "comment" in reward
    assert 0.01 <= reward["value"] <= 0.99
    assert isinstance(data["done"], bool)
    assert isinstance(data["info"], dict)


def test_optimize_endpoint_valid(client):
    """POST /optimize returns valid OptimizeResponse with score, recommendation, and diff."""
    code = (
        "import sys\n"
        "def hello_world():\n"
        "  print('hello')\n"
    )
    response = client.post("/optimize", json={
        "code": code,
        "task_type": "style-cleanup",
        "language": "python"
    })
    assert response.status_code == 200
    data = response.json()

    assert "initial_score" in data
    assert "fixed_code" in data
    assert "final_score" in data
    assert "perf_gain" in data
    assert "mem_reduction" in data
    assert "recommendation" in data
    assert "diff_data" in data
    assert "request_id" in data
    assert isinstance(data["diff_data"], list)
    assert data["final_score"] >= 0.01


def test_optimize_endpoint_empty_code(client):
    """POST /optimize with empty code returns 400 Bad Request."""
    response = client.post("/optimize", json={
        "code": "   ",
        "task_type": "style-cleanup"
    })
    assert response.status_code == 400
    assert "Code cannot be empty" in response.json()["detail"]


def test_optimize_full_endpoint(client):
    """POST /optimize_full completes chained passes and returns OptimizeResponse."""
    code = (
        "import sys\n"
        "def find_dup(a, b):\n"
        "    for x in a:\n"
        "        for y in b:\n"
        "            if x == y:\n"
        "                return x\n"
    )
    response = client.post("/optimize_full", json={
        "code": code,
        "task_type": "efficiency-boost",
        "language": "python"
    })
    assert response.status_code == 200
    data = response.json()

    assert "initial_score" in data
    assert "fixed_code" in data
    assert "final_score" in data
    assert "diff_data" in data
    assert data["perf_gain"] == "Pipeline Complete"
    assert isinstance(data["diff_data"], list)


def test_diff_endpoint(client):
    """POST /diff returns line-by-line diff metadata."""
    original = "def foo():\n    return 1\n"
    modified = "def foo():\n    return 2\n"

    response = client.post("/diff", json={
        "original": original,
        "modified": modified
    })
    assert response.status_code == 200
    data = response.json()

    assert "diff" in data
    assert isinstance(data["diff"], list)
    assert len(data["diff"]) > 0

    types = [item["type"] for item in data["diff"]]
    assert "unchanged" in types
    assert ("added" in types or "removed" in types)


@pytest.mark.parametrize("payload", [
    "/..%2Fpyproject.toml",
    "/..%2F..%2Fpyproject.toml",
    "/%2e%2e%2fpyproject.toml",
    "/..%2Frequirements.txt",
    "/..%5c..%5cpyproject.toml"
])
def test_path_traversal_security(client, payload):
    """Path traversal payloads must return 403 Forbidden or 404, never disclosing internal files."""
    response = client.get(payload)
    # The server catch_all endpoint validates target_path against canonical_root
    # Traversal attempts outside canonical_root MUST return 403 Forbidden or 404
    assert response.status_code in (403, 404), f"Expected 403 or 404 for traversal {payload}, got {response.status_code}"
    # Verify file contents are NOT disclosed
    assert "aion-code-reviewer" not in response.text
    assert "[build-system]" not in response.text
    assert "dependencies =" not in response.text
