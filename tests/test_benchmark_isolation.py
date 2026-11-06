"""
tests/test_benchmark_isolation.py

Data leakage guard and split isolation tests for Aion-Bench (BENCH-04, DATA-02).
Guarantees:
  1. Complete disjointness of case IDs across dev, gold, and test_locked splits.
  2. Zero diff or code content collision between dev and test_locked.
  3. Cryptographic SHA-256 manifest integrity against test_locked.json and gold.json.
  4. Strict Pydantic schema validation for all cases across all splits.
  5. Ground-truth consistency (clean diffs have empty findings; buggy diffs have >= 1 finding).
"""

import json
from pathlib import Path
import pytest

from bench.schema import BenchmarkCase, load_cases_from_file
from bench.splits.splitter import compute_case_hash, compute_file_hash


SPLITS_DIR = Path("bench/splits")
DEV_PATH = SPLITS_DIR / "dev.json"
GOLD_PATH = SPLITS_DIR / "gold.json"
LOCKED_PATH = SPLITS_DIR / "test_locked.json"
MANIFEST_PATH = SPLITS_DIR / "manifest.json"


@pytest.fixture(scope="module")
def dev_cases():
    assert DEV_PATH.exists(), f"dev.json missing at {DEV_PATH}"
    return load_cases_from_file(DEV_PATH)


@pytest.fixture(scope="module")
def gold_cases():
    assert GOLD_PATH.exists(), f"gold.json missing at {GOLD_PATH}"
    return load_cases_from_file(GOLD_PATH)


@pytest.fixture(scope="module")
def locked_cases():
    assert LOCKED_PATH.exists(), f"test_locked.json missing at {LOCKED_PATH}"
    return load_cases_from_file(LOCKED_PATH)


@pytest.fixture(scope="module")
def manifest_data():
    assert MANIFEST_PATH.exists(), f"manifest.json missing at {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_disjoint_case_ids(dev_cases, gold_cases, locked_cases):
    """Test 1: Assert 100% disjoint case IDs across dev, gold, and test_locked splits."""
    dev_ids = {c.case_id for c in dev_cases}
    gold_ids = {c.case_id for c in gold_cases}
    locked_ids = {c.case_id for c in locked_cases}

    assert len(dev_ids) == len(dev_cases), "Duplicate case_id found in dev.json"
    assert len(gold_ids) == len(gold_cases), "Duplicate case_id found in gold.json"
    assert len(locked_ids) == len(locked_cases), "Duplicate case_id found in test_locked.json"

    # Intersections must be empty
    dev_gold_overlap = dev_ids.intersection(gold_ids)
    dev_locked_overlap = dev_ids.intersection(locked_ids)
    gold_locked_overlap = gold_ids.intersection(locked_ids)

    assert not dev_gold_overlap, f"Leakage detected: dev and gold share case IDs: {dev_gold_overlap}"
    assert not dev_locked_overlap, f"Leakage detected: dev and test_locked share case IDs: {dev_locked_overlap}"
    assert not gold_locked_overlap, f"Leakage detected: gold and test_locked share case IDs: {gold_locked_overlap}"


def test_zero_diff_and_code_leakage(dev_cases, locked_cases):
    """Test 2: Assert zero exact diff or modified_code overlap between dev and test_locked."""
    dev_diffs = {c.diff.strip() for c in dev_cases if c.diff.strip()}
    locked_diffs = {c.diff.strip() for c in locked_cases if c.diff.strip()}

    diff_overlap = dev_diffs.intersection(locked_diffs)
    assert not diff_overlap, f"Data leakage: identical diffs found in dev and test_locked: {len(diff_overlap)}"

    dev_code = {c.modified_code.strip() for c in dev_cases}
    locked_code = {c.modified_code.strip() for c in locked_cases}

    code_overlap = dev_code.intersection(locked_code)
    assert not code_overlap, f"Data leakage: identical modified_code found in dev and test_locked: {len(code_overlap)}"


def test_cryptographic_manifest_integrity(manifest_data, gold_cases, locked_cases):
    """Test 3: Verify cryptographic SHA-256 checksums in manifest.json match current splits."""
    # 1. Verify file-level SHA-256 hashes
    current_gold_file_hash = compute_file_hash(GOLD_PATH)
    current_locked_file_hash = compute_file_hash(LOCKED_PATH)

    manifest_gold_file_hash = manifest_data["splits"]["gold"]["file_sha256"]
    manifest_locked_file_hash = manifest_data["splits"]["test_locked"]["file_sha256"]

    assert current_gold_file_hash == manifest_gold_file_hash, (
        f"Gold split file hash mismatch! Expected {manifest_gold_file_hash}, got {current_gold_file_hash}"
    )
    assert current_locked_file_hash == manifest_locked_file_hash, (
        f"Locked split file hash mismatch! Expected {manifest_locked_file_hash}, got {current_locked_file_hash}"
    )

    # 2. Verify case-level SHA-256 hashes for test_locked cases
    locked_manifest_hashes = manifest_data["splits"]["test_locked"]["case_hashes"]
    assert len(locked_manifest_hashes) == len(locked_cases)
    for c in locked_cases:
        expected_hash = locked_manifest_hashes.get(c.case_id)
        assert expected_hash is not None, f"Case {c.case_id} missing from manifest.json"
        actual_hash = compute_case_hash(c)
        assert actual_hash == expected_hash, f"Hash tampering detected for locked case {c.case_id}"

    # 3. Verify case-level SHA-256 hashes for gold cases
    gold_manifest_hashes = manifest_data["splits"]["gold"]["case_hashes"]
    assert len(gold_manifest_hashes) == len(gold_cases)
    for c in gold_cases:
        expected_hash = gold_manifest_hashes.get(c.case_id)
        assert expected_hash is not None, f"Case {c.case_id} missing from manifest.json"
        actual_hash = compute_case_hash(c)
        assert actual_hash == expected_hash, f"Hash tampering detected for gold case {c.case_id}"


def test_schema_conformance(dev_cases, gold_cases, locked_cases):
    """Test 4: Assert all cases strictly conform to BenchmarkCase Pydantic model validation."""
    all_cases = dev_cases + gold_cases + locked_cases
    assert len(all_cases) >= 200, f"Expected >= 200 total cases, got {len(all_cases)}"

    for c in all_cases:
        validated = BenchmarkCase.model_validate(c)
        assert validated.case_id
        assert validated.repository
        assert validated.language in ("python", "typescript", "javascript")
        assert validated.file_path
        assert validated.modified_code
        assert isinstance(validated.is_clean_diff, bool)


def test_ground_truth_consistency(dev_cases, gold_cases, locked_cases):
    """Test 5: Verify clean diffs have empty findings, and buggy diffs have >= 1 ground-truth finding."""
    all_cases = dev_cases + gold_cases + locked_cases
    clean_count = 0
    buggy_count = 0

    for c in all_cases:
        if c.is_clean_diff:
            clean_count += 1
            assert len(c.ground_truth) == 0, (
                f"Clean case {c.case_id} must have 0 ground-truth findings, found {len(c.ground_truth)}"
            )
        else:
            buggy_count += 1
            assert len(c.ground_truth) >= 1, (
                f"Buggy case {c.case_id} must have >= 1 ground-truth finding, found {len(c.ground_truth)}"
            )
            for f in c.ground_truth:
                assert f.finding_id
                assert f.line_start >= 1
                assert f.line_end >= f.line_start
                assert f.category
                assert f.severity

    # Assert adequate clean negative balance (at least 20% of all cases)
    assert clean_count >= int(len(all_cases) * 0.20), f"Insufficient clean diff negative controls: {clean_count}"
    assert buggy_count >= int(len(all_cases) * 0.50), f"Insufficient buggy cases: {buggy_count}"


def test_stratified_representation(dev_cases, gold_cases, locked_cases):
    """Test 6: Verify multi-language representation across all three splits."""
    for split_name, split_cases in [("dev", dev_cases), ("gold", gold_cases), ("locked", locked_cases)]:
        languages = {c.language.lower() for c in split_cases}
        assert "python" in languages, f"Split {split_name} missing Python cases"
        assert "typescript" in languages, f"Split {split_name} missing TypeScript cases"
