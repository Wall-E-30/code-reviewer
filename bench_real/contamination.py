"""
bench_real/contamination.py

Extended Contamination & MinHash Fuzzy Diff Isolation Guard (REAL-03).
Prevents evaluation leakage across SFT, GRPO, verifier datasets, and bench_real
using exact SHA-256 digests, repository matching, file path checks, MinHash Jaccard similarity,
and post-model-cutoff temporal slicing.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from bench_real.schema import RealBenchmarkCase

logger = logging.getLogger(__name__)

# Large Mersenne prime for Carter-Wegman universal hashing
_PRIME = 2147483647


def normalize_diff_for_hashing(diff: str) -> str:
    """Strips git metadata headers, whitespace differences, and line endings."""
    if not diff:
        return ""
    lines: List[str] = []
    for line in diff.strip().splitlines():
        # Strip git diff chunk headers and file mode lines
        if line.startswith("@@") or line.startswith("diff --git") or line.startswith("index "):
            continue
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


class MinHashFingerprint:
    """
    MinHash locality-sensitive fingerprint for fuzzy diff deduplication.
    Generates N universal hash permutations to approximate Jaccard similarity.
    """

    def __init__(self, num_hashes: int = 64, shingle_size: int = 4) -> None:
        self.num_hashes = num_hashes
        self.shingle_size = shingle_size
        # Deterministic linear permutation parameters (a * x + b) % PRIME
        self.a_params = [((i * 10007 + 104729) % (_PRIME - 1)) + 1 for i in range(num_hashes)]
        self.b_params = [((i * 32452843 + 8654057) % _PRIME) for i in range(num_hashes)]

    def _get_shingles(self, text: str) -> Set[str]:
        """Extract character k-shingles from normalized text."""
        norm = re.sub(r"\s+", " ", text.strip().lower())
        if len(norm) <= self.shingle_size:
            return {norm} if norm else set()
        return {norm[i : i + self.shingle_size] for i in range(len(norm) - self.shingle_size + 1)}

    def compute(self, text: str) -> List[int]:
        """Computes MinHash signature vector of length num_hashes."""
        shingles = self._get_shingles(text)
        if not shingles:
            return [0] * self.num_hashes

        # Pre-hash shingles to 32-bit integers
        shingle_hashes = [
            int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)
            for s in shingles
        ]

        signature: List[int] = []
        for i in range(self.num_hashes):
            a = self.a_params[i]
            b = self.b_params[i]
            min_val = min(((a * h + b) % _PRIME) for h in shingle_hashes)
            signature.append(min_val)

        return signature

    def jaccard_similarity(self, sig1: List[int], sig2: List[int]) -> float:
        """Estimates Jaccard similarity as fraction of matching min-hash values."""
        if not sig1 or not sig2 or len(sig1) != len(sig2):
            return 0.0
        matches = sum(1 for h1, h2 in zip(sig1, sig2) if h1 == h2)
        return matches / float(len(sig1))


class ExtendedContaminationGuard:
    """
    Comprehensive multi-layer isolation guard verifying bench_real integrity.
    Validates across exact content hashes, repository names, file paths, and MinHash fuzzy diffs.
    """

    def __init__(
        self,
        fuzzy_threshold: float = 0.70,
        model_cutoff_date: str = "2024-06-01T00:00:00Z",
    ) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        self.model_cutoff_dt = datetime.fromisoformat(model_cutoff_date.replace("Z", "+00:00"))
        self.minhash = MinHashFingerprint(num_hashes=64, shingle_size=4)

        # Known training corpora signatures
        self.train_repos: Set[str] = set()
        self.train_exact_hashes: Set[str] = set()
        self.train_file_paths: Set[Tuple[str, str]] = set()  # (repo, file_path)
        self.train_minhash_signatures: List[Tuple[str, List[int]]] = []

    def register_training_episode(
        self,
        repo: str,
        diff: str,
        file_path: Optional[str] = None,
        episode_id: str = "ep",
    ) -> None:
        """Registers a training or validation item to check against."""
        repo_norm = repo.lower().strip()
        if repo_norm:
            self.train_repos.add(repo_norm)

        norm_diff = normalize_diff_for_hashing(diff)
        diff_sha = hashlib.sha256(norm_diff.encode("utf-8")).hexdigest()
        self.train_exact_hashes.add(diff_sha)

        if file_path and repo_norm:
            self.train_file_paths.add((repo_norm, file_path.lower().strip()))

        sig = self.minhash.compute(norm_diff)
        self.train_minhash_signatures.append((f"{episode_id}::{repo_norm}", sig))

    def check_contamination(self, case: RealBenchmarkCase) -> Dict[str, Any]:
        """
        Audits a single benchmark case for contamination against registered training sets.
        Returns detailed check results.
        """
        violations: List[str] = []
        repo = case.repository.lower().strip()

        # 1. Repository overlap check
        if repo in self.train_repos:
            violations.append(f"Repository overlap detected: '{repo}' is in training set")

        # 2. Exact diff SHA-256 hash collision check
        norm_diff = normalize_diff_for_hashing(case.diff)
        diff_sha = hashlib.sha256(norm_diff.encode("utf-8")).hexdigest()
        if diff_sha in self.train_exact_hashes:
            violations.append("Exact SHA-256 diff hash collision detected with training episode")

        # 3. Target file path overlap check
        for finding in case.ground_truth_findings:
            if (repo, finding.file.lower().strip()) in self.train_file_paths:
                violations.append(f"File path overlap: '{finding.file}' in repo '{repo}'")

        # 4. Fuzzy diff MinHash Jaccard similarity check
        case_sig = self.minhash.compute(norm_diff)
        max_jaccard = 0.0
        most_similar_train_ep = None

        for train_id, train_sig in self.train_minhash_signatures:
            sim = self.minhash.jaccard_similarity(case_sig, train_sig)
            if sim > max_jaccard:
                max_jaccard = sim
                most_similar_train_ep = train_id

        if max_jaccard >= self.fuzzy_threshold:
            violations.append(
                f"MinHash fuzzy diff collision (Jaccard={max_jaccard:.2f} >= {self.fuzzy_threshold:.2f}) "
                f"with {most_similar_train_ep}"
            )

        # 5. Temporal cutoff classification
        is_post_cutoff = False
        if case.created_at:
            try:
                case_dt = datetime.fromisoformat(case.created_at.replace("Z", "+00:00"))
                is_post_cutoff = case_dt >= self.model_cutoff_dt
            except Exception:
                pass

        return {
            "case_id": case.case_id,
            "contaminated": len(violations) > 0,
            "violations": violations,
            "max_fuzzy_similarity": round(max_jaccard, 4),
            "is_post_cutoff": is_post_cutoff,
        }


def partition_by_cutoff(
    cases: List[RealBenchmarkCase],
    cutoff_date: str = "2024-06-01T00:00:00Z",
) -> Tuple[List[RealBenchmarkCase], List[RealBenchmarkCase]]:
    """Partitions cases into (post_cutoff, pre_cutoff) sets."""
    cutoff_dt = datetime.fromisoformat(cutoff_date.replace("Z", "+00:00"))
    post_cutoff: List[RealBenchmarkCase] = []
    pre_cutoff: List[RealBenchmarkCase] = []

    for c in cases:
        if c.created_at:
            try:
                c_dt = datetime.fromisoformat(c.created_at.replace("Z", "+00:00"))
                if c_dt >= cutoff_dt:
                    post_cutoff.append(c)
                    continue
            except Exception:
                pass
        pre_cutoff.append(c)

    return post_cutoff, pre_cutoff


def generate_contamination_report(
    cases: List[RealBenchmarkCase],
    guard: ExtendedContaminationGuard,
    output_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Runs full contamination audit over cases and generates a report."""
    results = [guard.check_contamination(c) for c in cases]
    total_cases = len(cases)
    contaminated_cases = [r for r in results if r["contaminated"]]
    post_cutoff_cases = [r for r in results if r["is_post_cutoff"]]

    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases_audited": total_cases,
        "clean_cases": total_cases - len(contaminated_cases),
        "contaminated_cases": len(contaminated_cases),
        "contamination_rate": round(len(contaminated_cases) / max(total_cases, 1), 4),
        "is_uncontaminated": len(contaminated_cases) == 0,
        "post_cutoff_count": len(post_cutoff_cases),
        "post_cutoff_fraction": round(len(post_cutoff_cases) / max(total_cases, 1), 4),
        "fuzzy_threshold_used": guard.fuzzy_threshold,
        "violations_summary": [
            {"case_id": r["case_id"], "violations": r["violations"]}
            for r in contaminated_cases
        ],
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        # Write JSON
        with open(out.with_suffix(".json"), "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # Write Markdown
        md_content = f"""# bench_real Contamination & Leakage Audit Report

- **Date:** {report_data['timestamp']}
- **Total Audited Cases:** {report_data['total_cases_audited']}
- **Clean Cases:** {report_data['clean_cases']}
- **Contaminated Cases:** {report_data['contaminated_cases']}
- **Contamination Rate:** {report_data['contamination_rate']:.2%}
- **Benchmark Uncontaminated:** {"✅ YES" if report_data['is_uncontaminated'] else "❌ NO"}
- **Post-Model-Cutoff Cases:** {report_data['post_cutoff_count']} ({report_data['post_cutoff_fraction']:.2%})
- **MinHash Fuzzy Threshold:** {report_data['fuzzy_threshold_used']:.2f}

## Violations Detail
"""
        if not contaminated_cases:
            md_content += "\nNo contamination violations detected. The benchmark split is cryptographically and temporally isolated from all training corpora.\n"
        else:
            for v in report_data["violations_summary"]:
                md_content += f"\n- **{v['case_id']}**: {'; '.join(v['violations'])}"

        with open(out.with_suffix(".md"), "w", encoding="utf-8") as f:
            f.write(md_content)

    return report_data

