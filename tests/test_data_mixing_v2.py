"""
tests/test_data_mixing_v2.py

Verification suite for Plan 11-01 (TRAIN2-01: Real Signal Data Mixing):
- Real signal streams merging (mined reviews, pilot feedback, hard negatives)
- Strict <= 50% synthetic cap enforcement
- Strict exclusion of bench_real reserved evaluation repositories
- Cryptographic SHA-256 slice hashing in manifest.json
"""

import hashlib
import json
import os
import pytest
from rl.training_v2.data_mixer import DataMixer, StreamType, TrainingItem


@pytest.fixture
def mixer():
    return DataMixer(output_dir="data/training_v2_test")


def test_data_mixing_build_and_cap(mixer):
    """Synthetic ratio must strictly be <= 50% of the combined mixture."""
    manifest = mixer.build_mixture(synthetic_cap_ratio=0.50)
    assert manifest["synthetic_ratio"] <= 0.50
    assert manifest["synthetic_capped_at_50_pct"] is True
    assert manifest["total_items"] > 0
    assert manifest["train_count"] > 0
    assert manifest["val_count"] > 0

    breakdown = manifest["stream_breakdown"]
    assert breakdown[StreamType.REAL_MINED.value] > 0
    assert breakdown[StreamType.PILOT_FEEDBACK.value] > 0
    assert breakdown[StreamType.HARD_NEGATIVE.value] > 0
    assert breakdown[StreamType.SYNTHETIC.value] > 0

    total = sum(breakdown.values())
    synth_ratio = breakdown[StreamType.SYNTHETIC.value] / total
    assert synth_ratio <= 0.50


def test_bench_real_contamination_exclusion(mixer):
    """No repository or diff from bench_real reserved splits may enter training data."""
    manifest = mixer.build_mixture()
    reserved = set(mixer.reserved_repos)
    assert len(reserved) > 0, "Expected bench_real reserved repos to be populated"

    train_file = mixer.output_dir / "train_v2.json"
    val_file = mixer.output_dir / "val_v2.json"

    with open(train_file, "r", encoding="utf-8") as f:
        train_items = json.load(f)
    with open(val_file, "r", encoding="utf-8") as f:
        val_items = json.load(f)

    for item in train_items + val_items:
        repo = item["repository"].lower().strip()
        assert repo not in reserved, f"Contamination: reserved repo '{repo}' leaked into training dataset"
        assert not mixer.is_contaminated(repo, item["diff"]), "Contamination: diff hash collision with bench_real"


def test_manifest_sha256_cryptographic_verification(mixer):
    """Manifest SHA-256 digests must match the actual file contents."""
    manifest = mixer.build_mixture()
    manifest_path = mixer.output_dir / "manifest.json"
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        saved_manifest = json.load(f)

    for split_key, slice_info in saved_manifest["slices"].items():
        slice_path = mixer.output_dir / slice_info["path"]
        assert slice_path.exists()
        normalized_bytes = slice_path.read_bytes().replace(b"\r\n", b"\n")
        computed_sha = hashlib.sha256(normalized_bytes).hexdigest()
        raw_sha = hashlib.sha256(slice_path.read_bytes()).hexdigest()
        assert (
            computed_sha == slice_info["sha256"] or raw_sha == slice_info["sha256"]
        ), f"SHA-256 mismatch for {split_key}"


def test_hard_negatives_and_pilot_feedback_integrity(mixer):
    """Hard negatives must be flagged clean and pilot feedback must preserve maintainer signals."""
    mixer.build_mixture()
    train_file = mixer.output_dir / "train_v2.json"
    with open(train_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    pilot_items = [it for it in items if it["stream_type"] == StreamType.PILOT_FEEDBACK.value]
    hard_neg_items = [it for it in items if it["stream_type"] == StreamType.HARD_NEGATIVE.value]

    assert len(pilot_items) > 0
    assert len(hard_neg_items) > 0

    for neg in hard_neg_items:
        assert neg["is_clean_diff"] is True
        assert neg["target_comment"] is None

    for pilot in pilot_items:
        assert "pilot_reaction" in pilot["metadata"]
        assert pilot["feedback_score"] in (1.0, -1.0)

