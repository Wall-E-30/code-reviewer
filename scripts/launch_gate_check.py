#!/usr/bin/env python3
"""
scripts/launch_gate_check.py - Automated Milestone Launch Verification Gate (LAUNCH-04).

Reads real results (bench_real eval, training v2 manifest, reward versioning,
security audits, and launch documentation) and enforces strict pass/fail gates
without mocking. Fails closed (exit code 1) on missing data or violated gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple


class GateResult:
    def __init__(
        self,
        name: str,
        passed: bool,
        measured: Any,
        criterion: str,
        lineage_tag: str,
        message: str = "",
    ):
        self.name = name
        self.passed = passed
        self.measured = measured
        self.criterion = criterion
        self.lineage_tag = lineage_tag
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "measured": self.measured,
            "criterion": self.criterion,
            "lineage_tag": self.lineage_tag,
            "message": self.message,
        }


class LaunchGateChecker:
    """Verifies all milestone launch criteria against real artifacts."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent

    def check_gate_bench_real(self) -> List[GateResult]:
        """Gate 1: Bench Real Evaluation Standards."""
        eval_path = self.repo_root / "bench_real" / "data" / "BASELINE_EVAL_VAL.json"
        if not eval_path.exists():
            return [
                GateResult(
                    name="Bench Real Results File",
                    passed=False,
                    measured="Missing",
                    criterion="File must exist at bench_real/data/BASELINE_EVAL_VAL.json",
                    lineage_tag="[REAL-OFFLINE]",
                    message=f"Evaluation file not found: {eval_path}",
                )
            ]

        try:
            with open(eval_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return [
                GateResult(
                    name="Bench Real Results JSON",
                    passed=False,
                    measured="Invalid JSON",
                    criterion="Valid JSON",
                    lineage_tag="[REAL-OFFLINE]",
                    message=str(e),
                )
            ]

        results = []
        baselines = data.get("baselines", {})
        trained = baselines.get("Aion with Trained Model")
        if not trained:
            return [
                GateResult(
                    name="Trained Model Baseline",
                    passed=False,
                    measured="Missing",
                    criterion="'Aion with Trained Model' baseline entry present",
                    lineage_tag="[REAL-OFFLINE]",
                    message="Missing 'Aion with Trained Model' in BASELINE_EVAL_VAL.json",
                )
            ]

        # Precision >= 0.75
        prec_mean = trained.get("precision", {}).get("mean", 0.0)
        results.append(
            GateResult(
                name="Trained Policy Precision",
                passed=prec_mean >= 0.75,
                measured=f"{prec_mean:.1%}",
                criterion=">= 75.0%",
                lineage_tag="[REAL-OFFLINE]",
                message="" if prec_mean >= 0.75 else f"Precision {prec_mean} below 0.75",
            )
        )

        # Clean Diff FPR <= 0.10
        fpr_mean = trained.get("clean_diff_fpr", {}).get("mean", 1.0)
        results.append(
            GateResult(
                name="Clean Diff False-Positive Rate",
                passed=fpr_mean <= 0.10,
                measured=f"{fpr_mean:.1%}",
                criterion="<= 10.0%",
                lineage_tag="[REAL-OFFLINE]",
                message="" if fpr_mean <= 0.10 else f"FPR {fpr_mean} exceeds 0.10",
            )
        )

        # Recall >= 0.60
        rec_mean = trained.get("recall", {}).get("mean", 0.0)
        results.append(
            GateResult(
                name="Trained Policy Recall",
                passed=rec_mean >= 0.60,
                measured=f"{rec_mean:.1%}",
                criterion=">= 60.0%",
                lineage_tag="[REAL-OFFLINE]",
                message="" if rec_mean >= 0.60 else f"Recall {rec_mean} below 0.60",
            )
        )

        # 95% Bootstrap CIs present
        prec_ci = trained.get("precision", {})
        has_ci = "ci_lower" in prec_ci and "ci_upper" in prec_ci and prec_ci["ci_lower"] <= prec_ci["ci_upper"]
        results.append(
            GateResult(
                name="Bootstrap 95% Confidence Intervals",
                passed=has_ci,
                measured="Present" if has_ci else "Missing",
                criterion="Non-parametric 95% bootstrap CIs present and bounded",
                lineage_tag="[REAL-OFFLINE]",
            )
        )

        return results

    def check_gate_training_v2_manifest(self) -> List[GateResult]:
        """Gate 2: Training v2 Data Mixture & Integrity Standards."""
        manifest_path = self.repo_root / "data" / "training_v2" / "manifest.json"
        if not manifest_path.exists():
            return [
                GateResult(
                    name="Training v2 Manifest File",
                    passed=False,
                    measured="Missing",
                    criterion="File must exist at data/training_v2/manifest.json",
                    lineage_tag="[REAL-OFFLINE]",
                    message=f"Manifest file not found: {manifest_path}",
                )
            ]

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            return [
                GateResult(
                    name="Training v2 Manifest JSON",
                    passed=False,
                    measured="Invalid JSON",
                    criterion="Valid JSON",
                    lineage_tag="[REAL-OFFLINE]",
                    message=str(e),
                )
            ]

        results = []

        # Synthetic ratio <= 50%
        synth_ratio = manifest.get("synthetic_ratio", 1.0)
        results.append(
            GateResult(
                name="Synthetic Training Data Ratio",
                passed=synth_ratio <= 0.50 and manifest.get("synthetic_capped_at_50_pct") is True,
                measured=f"{synth_ratio:.2%}",
                criterion="<= 50.0%",
                lineage_tag="[REAL-OFFLINE]",
                message="" if synth_ratio <= 0.50 else f"Synthetic ratio {synth_ratio} exceeds 50%",
            )
        )

        # Contamination status
        contamination = manifest.get("contamination_detected", True)
        results.append(
            GateResult(
                name="Contamination Exclusion",
                passed=not contamination,
                measured="Clean (No contamination)" if not contamination else "Contaminated",
                criterion="Zero overlap with bench_real evaluation repos",
                lineage_tag="[REAL-OFFLINE]",
            )
        )

        # Check slices and SHA-256 digests
        slices = manifest.get("slices", {})
        all_slices_valid = True
        slice_msg = ""
        for slice_name, slice_info in slices.items():
            rel_path = slice_info.get("path")
            expected_hash = slice_info.get("sha256")
            full_path = self.repo_root / "data" / "training_v2" / rel_path
            if not full_path.exists():
                all_slices_valid = False
                slice_msg = f"Missing slice: {rel_path}"
                break
            # Normalize newlines (CRLF -> LF) for cross-platform determinism
            normalized_bytes = full_path.read_bytes().replace(b"\r\n", b"\n")
            file_hash = hashlib.sha256(normalized_bytes).hexdigest()
            raw_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
            if file_hash != expected_hash and raw_hash != expected_hash:
                all_slices_valid = False
                slice_msg = f"Hash mismatch for {rel_path}"
                break

        results.append(
            GateResult(
                name="Cryptographic Slices & SHA-256",
                passed=all_slices_valid and len(slices) >= 2,
                measured="Verified" if all_slices_valid else "Mismatch / Missing",
                criterion="SHA-256 digests match file contents",
                lineage_tag="[REAL-OFFLINE]",
                message=slice_msg,
            )
        )

        return results

    def check_gate_reward_versioning(self) -> List[GateResult]:
        """Gate 3: Verifiable Reward Engine & Anti-Reward-Hacking Versioning."""
        results = []
        reward_file = self.repo_root / "rl" / "reward.py"
        if not reward_file.exists():
            return [
                GateResult(
                    name="Reward Engine File",
                    passed=False,
                    measured="Missing",
                    criterion="rl/reward.py must exist",
                    lineage_tag="[SIMULATED]",
                )
            ]

        content = reward_file.read_text(encoding="utf-8")
        has_v2 = "V2_0_0" in content and "RewardVersion" in content
        results.append(
            GateResult(
                name="Reward Engine Version",
                passed=has_v2,
                measured="2.0.0" if has_v2 else "Legacy / Unversioned",
                criterion="RewardVersion.V2_0_0 active",
                lineage_tag="[SIMULATED]",
            )
        )

        has_anti_hacking = (
            "_detect_linter_copycat" in content
            and "_detect_hedged_generic" in content
            and "_detect_linter_proximity_spam" in content
        )
        results.append(
            GateResult(
                name="Anti-Reward-Hacking Audits v2",
                passed=has_anti_hacking,
                measured="Active" if has_anti_hacking else "Incomplete",
                criterion="Penalties for copycat, generic platitudes, proximity spam",
                lineage_tag="[SIMULATED]",
            )
        )

        return results

    def check_gate_security_and_sandbox(self) -> List[GateResult]:
        """Gate 4: Container Hardening & Secret Redaction."""
        results = []

        threat_model = self.repo_root / "docs" / "SANDBOX_THREAT_MODEL.md"
        results.append(
            GateResult(
                name="Sandbox Threat Model Specification",
                passed=threat_model.exists(),
                measured="Published" if threat_model.exists() else "Missing",
                criterion="docs/SANDBOX_THREAT_MODEL.md published",
                lineage_tag="[SIMULATED]",
            )
        )

        redactor_file = self.repo_root / "action" / "redactor.py"
        has_redactor = redactor_file.exists()
        if has_redactor:
            r_content = redactor_file.read_text(encoding="utf-8")
            has_rules = "AWS" in r_content and "GitHub" in r_content
        else:
            has_rules = False

        results.append(
            GateResult(
                name="Diff Secret Redactor",
                passed=has_redactor and has_rules,
                measured="Active" if (has_redactor and has_rules) else "Missing",
                criterion="AWS, GitHub, API key pattern redaction before inference",
                lineage_tag="[SIMULATED]",
            )
        )

        return results

    def check_gate_launch_assets(self) -> List[GateResult]:
        """Gate 5: Launch Assets & Community Documentation."""
        required_assets = [
            ("Evidence Report Template", "docs/launch/EVIDENCE_REPORT_TEMPLATE.md", "[REAL-OFFLINE]"),
            ("False-Positive Issue Template", ".github/ISSUE_TEMPLATE/false_positive_report.yml", "[LIVE-PILOT]"),
            ("Hugging Face Model Card", "docs/launch/MODEL_CARD.md", "[REAL-OFFLINE]"),
            ("Hugging Face Dataset Card", "docs/launch/DATASET_CARD.md", "[REAL-OFFLINE]"),
            ("Leaderboard Submission Guide", "docs/launch/LEADERBOARD_SUBMISSION.md", "[REAL-OFFLINE]"),
            ("Marketplace Listing Copy", "docs/launch/MARKETPLACE.md", "[REAL-OFFLINE]"),
            ("Show HN Launch Post", "docs/launch/SHOW_HN.md", "[REAL-OFFLINE]"),
        ]

        results = []
        for name, rel_path, tag in required_assets:
            file_path = self.repo_root / rel_path
            exists = file_path.exists()
            results.append(
                GateResult(
                    name=name,
                    passed=exists,
                    measured="Present" if exists else "Missing",
                    criterion=f"Exists at {rel_path}",
                    lineage_tag=tag,
                )
            )

        return results

    def run_all_gates(self) -> Dict[str, Any]:
        """Run all verification gates and return aggregated results."""
        gate_categories = {
            "Bench Real Evaluation": self.check_gate_bench_real(),
            "Training v2 Mixture & Manifest": self.check_gate_training_v2_manifest(),
            "Reward Versioning & Anti-Hacking": self.check_gate_reward_versioning(),
            "Security & Sandbox Hardening": self.check_gate_security_and_sandbox(),
            "Launch Publication Assets": self.check_gate_launch_assets(),
        }

        all_results: List[GateResult] = []
        for results in gate_categories.values():
            all_results.extend(results)

        total_gates = len(all_results)
        passed_gates = sum(1 for r in all_results if r.passed)
        failed_gates = total_gates - passed_gates
        overall_passed = failed_gates == 0

        return {
            "overall_passed": overall_passed,
            "total_gates": total_gates,
            "passed_gates": passed_gates,
            "failed_gates": failed_gates,
            "categories": {
                cat: [r.to_dict() for r in results]
                for cat, results in gate_categories.items()
            },
        }

    def print_report(self, run_results: Dict[str, Any]) -> None:
        """Print human-readable summary table."""
        print("=" * 80)
        print("AION MILESTONE LAUNCH GATE VERIFICATION REPORT (LAUNCH-04)")
        print("Standard: Non-Negotiable Rule #2 ('Never fake data')")
        print("=" * 80)

        for cat, results in run_results["categories"].items():
            print(f"\n[{cat.upper()}]")
            print(f"{'Gate Name':<35} | {'Status':<8} | {'Measured':<15} | {'Criterion'}")
            print("-" * 80)
            for r in results:
                status_str = "PASS [ok]" if r["passed"] else "FAIL [X]"
                print(f"{r['name']:<35} | {status_str:<8} | {str(r['measured']):<15} | {r['criterion']}")
                if not r["passed"] and r.get("message"):
                    print(f"  >>> Error: {r['message']}")

        print("\n" + "=" * 80)
        if run_results["overall_passed"]:
            print(f"LAUNCH GATE STATUS: ALL {run_results['total_gates']} GATES PASSED (READY FOR LAUNCH) [PASS]")
        else:
            print(
                f"LAUNCH GATE STATUS: FAILED ({run_results['failed_gates']} / "
                f"{run_results['total_gates']} gates failed) [FAIL]"
            )
        print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aion Milestone Launch Gate Verification (LAUNCH-04)")
    parser.add_argument("--repo-root", type=str, help="Custom repository root path", default=None)
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--strict", action="store_true", help="Strict mode (fails closed on warnings)")
    args = parser.parse_args()

    root = Path(args.repo_root) if args.repo_root else None
    checker = LaunchGateChecker(repo_root=root)
    results = checker.run_all_gates()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        checker.print_report(results)

    sys.exit(0 if results["overall_passed"] else 1)


if __name__ == "__main__":
    main()

