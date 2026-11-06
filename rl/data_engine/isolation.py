"""
rl/data_engine/isolation.py

Cryptographic Leakage Guard for Aion Code Reviewer (DATA-02).
Prevents evaluation benchmark contamination by enforcing strict isolation:
1. Zero SHA-256 hash collision between training episodes and Aion-Bench test sets
   (gold.json and test_locked.json recorded in bench/splits/manifest.json).
2. Repository-level isolation permanently blacklisting all repositories represented
   in Aion-Bench test splits.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_PATH = "bench/splits/manifest.json"
DEFAULT_GOLD_PATH = "bench/splits/gold.json"
DEFAULT_TEST_LOCKED_PATH = "bench/splits/test_locked.json"


def normalize_code(code: str) -> str:
    """Normalize whitespace and line endings for content hashing."""
    if not code:
        return ""
    lines = [line.rstrip() for line in code.strip().splitlines()]
    return "\n".join(lines)


def compute_content_hash(original_code: str, modified_code: str, diff: str) -> str:
    """Compute normalized SHA-256 digest across original code, modified code, and diff."""
    norm_orig = normalize_code(original_code)
    norm_mod = normalize_code(modified_code)
    norm_diff = normalize_code(diff)
    payload = f"{norm_orig}\n===MODIFIED===\n{norm_mod}\n===DIFF===\n{norm_diff}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LeakageGuard:
    """
    Cryptographic isolation engine protecting benchmark integrity.
    """

    def __init__(
        self,
        manifest_path: Optional[Union[str, Path]] = None,
        gold_path: Optional[Union[str, Path]] = None,
        test_locked_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.manifest_path = Path(manifest_path or DEFAULT_MANIFEST_PATH)
        self.gold_path = Path(gold_path or DEFAULT_GOLD_PATH)
        self.test_locked_path = Path(test_locked_path or DEFAULT_TEST_LOCKED_PATH)

        self.protected_hashes: Set[str] = set()
        self.protected_repos: Set[str] = set()
        self.protected_case_ids: Set[str] = set()

        self._load_protected_signatures()

    def _load_protected_signatures(self) -> None:
        """Load cryptographic checksums and repository identifiers from benchmark splits."""
        # 1. Load SHA-256 digests from manifest.json
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                splits = manifest.get("splits", {})

                for split_name in ("gold", "test_locked"):
                    split_data = splits.get(split_name, {})
                    case_hashes = split_data.get("case_hashes", {})
                    for case_id, h in case_hashes.items():
                        self.protected_hashes.add(h.lower())
                        self.protected_case_ids.add(case_id.lower())
            except Exception as e:
                logger.warning("Failed to load benchmark manifest %s: %s", self.manifest_path, e)

        # 2. Extract protected repositories and content hashes from gold and test_locked splits
        for path in (self.gold_path, self.test_locked_path):
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        cases = json.load(f)
                    if isinstance(cases, list):
                        for c in cases:
                            repo = c.get("repository", "").strip().lower()
                            if repo:
                                self.protected_repos.add(repo)
                            c_id = c.get("case_id", "").strip().lower()
                            if c_id:
                                self.protected_case_ids.add(c_id)

                            # Compute normalized content hash
                            c_hash = compute_content_hash(
                                c.get("original_code", ""),
                                c.get("modified_code", ""),
                                c.get("diff", ""),
                            )
                            self.protected_hashes.add(c_hash.lower())

                            # Canonical dict hash matching splitter
                            canonical = json.dumps(c, sort_keys=True, ensure_ascii=False)
                            self.protected_hashes.add(
                                hashlib.sha256(canonical.encode("utf-8")).hexdigest().lower()
                            )
                except Exception as e:
                    logger.warning("Failed to load benchmark cases from %s: %s", path, e)

        logger.debug(
            "LeakageGuard initialized: %d protected hashes, %d protected repos.",
            len(self.protected_hashes),
            len(self.protected_repos),
        )

    def compute_episode_hash(self, episode: Dict[str, Any]) -> str:
        """Compute normalized SHA-256 digest for a training episode."""
        orig = episode.get("original_code", "")
        mod = episode.get("modified_code", "")
        diff = episode.get("diff", "")
        return compute_content_hash(orig, mod, diff)

    def is_leaked(self, episode: Dict[str, Any]) -> bool:
        """
        Check whether a candidate training episode contaminates Aion-Bench evaluation splits.

        Returns:
            True if any hash collision or repository overlap is detected.
        """
        # 1. Repository-level isolation check
        repo = str(episode.get("repository", "")).strip().lower()
        if repo and repo in self.protected_repos:
            return True

        # 2. Case ID overlap check
        case_id = str(episode.get("case_id", "")).strip().lower()
        if case_id and case_id in self.protected_case_ids:
            return True

        # 3. Content-level SHA-256 hash collision check
        ep_hash = self.compute_episode_hash(episode).lower()
        if ep_hash in self.protected_hashes:
            return True

        # 4. Canonical JSON serialization check
        try:
            canonical = json.dumps(episode, sort_keys=True, ensure_ascii=False)
            full_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest().lower()
            if full_hash in self.protected_hashes:
                return True
        except Exception:
            pass

        return False

    def verify_corpus_isolation(self, episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Audit a complete corpus of training episodes and assert 0 collisions.

        Returns:
            Isolation audit report dictionary.
        """
        hash_collisions = 0
        repo_collisions = 0
        collision_case_ids: List[str] = []

        for ep in episodes:
            repo = str(ep.get("repository", "")).strip().lower()
            if repo and repo in self.protected_repos:
                repo_collisions += 1
                collision_case_ids.append(ep.get("case_id", "unknown"))
                continue

            ep_hash = self.compute_episode_hash(ep).lower()
            if ep_hash in self.protected_hashes:
                hash_collisions += 1
                collision_case_ids.append(ep.get("case_id", "unknown"))

        is_isolated = (hash_collisions == 0) and (repo_collisions == 0)

        report = {
            "total_episodes_audited": len(episodes),
            "hash_collisions": hash_collisions,
            "repo_collisions": repo_collisions,
            "total_violations": hash_collisions + repo_collisions,
            "isolated": is_isolated,
            "sample_violations": collision_case_ids[:5],
        }

        return report
