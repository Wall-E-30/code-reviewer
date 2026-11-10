"""
bench_real/annotation/agreement.py

Inter-annotator agreement engine computing Cohen's kappa (κ),
percent agreement, and disagreement isolation for adjudication (REAL-02).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def compute_cohens_kappa(
    labels_1: Dict[str, Dict[str, Any]],
    labels_2: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Computes Cohen's kappa for binary actionability agreement across two annotators.
    Formula:
        κ = (P_o - P_e) / (1 - P_e)
    """
    common_case_ids = set(labels_1.keys()).intersection(set(labels_2.keys()))
    if not common_case_ids:
        return {
            "n_common_cases": 0,
            "observed_agreement": 0.0,
            "expected_agreement": 0.0,
            "cohens_kappa": 0.0,
            "interpretation": "No overlapping cases",
            "contingency_table": {"a_both_yes": 0, "b_yes_no": 0, "c_no_yes": 0, "d_both_no": 0},
        }

    a = 0  # ann1 True, ann2 True
    b = 0  # ann1 True, ann2 False
    c = 0  # ann1 False, ann2 True
    d = 0  # ann1 False, ann2 False
    category_matches = 0

    for cid in common_case_ids:
        v1 = bool(labels_1[cid].get("actionable", False))
        v2 = bool(labels_2[cid].get("actionable", False))

        if v1 and v2:
            a += 1
        elif v1 and not v2:
            b += 1
        elif not v1 and v2:
            c += 1
        else:
            d += 1

        cat1 = str(labels_1[cid].get("category", "")).lower().strip()
        cat2 = str(labels_2[cid].get("category", "")).lower().strip()
        if cat1 and cat1 == cat2:
            category_matches += 1

    n = len(common_case_ids)
    p_o = (a + d) / n

    p_yes_1 = (a + b) / n
    p_no_1 = (c + d) / n
    p_yes_2 = (a + c) / n
    p_no_2 = (b + d) / n

    p_e = (p_yes_1 * p_yes_2) + (p_no_1 * p_no_2)

    if abs(1.0 - p_e) < 1e-9:
        kappa = 1.0 if abs(p_o - 1.0) < 1e-9 else 0.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    # Standard Landis & Koch interpretation
    if kappa < 0:
        interp = "Poor (less than chance agreement)"
    elif kappa <= 0.20:
        interp = "Slight agreement"
    elif kappa <= 0.40:
        interp = "Fair agreement"
    elif kappa <= 0.60:
        interp = "Moderate agreement"
    elif kappa <= 0.80:
        interp = "Substantial agreement"
    else:
        interp = "Almost perfect agreement"

    return {
        "n_common_cases": n,
        "observed_agreement": round(p_o, 4),
        "expected_agreement": round(p_e, 4),
        "cohens_kappa": round(kappa, 4),
        "category_agreement_rate": round(category_matches / n, 4),
        "interpretation": interp,
        "contingency_table": {
            "a_both_yes": a,
            "b_yes_no": b,
            "c_no_yes": c,
            "d_both_no": d,
        },
    }


def extract_disagreements(
    labels_1: Dict[str, Dict[str, Any]],
    labels_2: Dict[str, Dict[str, Any]],
    candidates_file: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    """
    Extracts all cases with conflicting actionability votes or categories.
    Prepares candidate list for adjudication.
    """
    candidates_map: Dict[str, Any] = {}
    if candidates_file and Path(candidates_file).exists():
        try:
            with open(candidates_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
                candidates_map = {item.get("case_id"): item for item in raw}
        except Exception as e:
            logger.warning("Failed loading candidates for disagreement context: %s", e)

    disagreements: List[Dict[str, Any]] = []
    common_case_ids = set(labels_1.keys()).intersection(set(labels_2.keys()))

    for cid in common_case_ids:
        l1 = labels_1[cid]
        l2 = labels_2[cid]
        v1 = bool(l1.get("actionable", False))
        v2 = bool(l2.get("actionable", False))
        cat1 = str(l1.get("category", "")).lower().strip()
        cat2 = str(l2.get("category", "")).lower().strip()

        # Disagreement occurs if actionability differs or categories differ on actionable cases
        if (v1 != v2) or (v1 and v2 and cat1 != cat2):
            context = candidates_map.get(cid, {})
            disagreements.append({
                "case_id": cid,
                "repository": context.get("repo_owner", "") + "/" + context.get("repo_name", "") if context else "unknown",
                "pr_url": context.get("pr_url", ""),
                "diff_snippet": context.get("diff", "")[:400] if context else "",
                "annotator_1": {
                    "actionable": v1,
                    "category": cat1,
                    "notes": l1.get("notes", ""),
                },
                "annotator_2": {
                    "actionable": v2,
                    "category": cat2,
                    "notes": l2.get("notes", ""),
                },
                "conflict_type": "actionability_mismatch" if v1 != v2 else "category_mismatch",
            })

    return disagreements


def save_disagreements(disagreements: List[Dict[str, Any]], output_path: Path | str) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(disagreements, f, indent=2)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Aion bench_real agreement metrics (REAL-02)")
    parser.add_argument("--ann1", required=True, help="Path to annotator 1 label JSON")
    parser.add_argument("--ann2", required=True, help="Path to annotator 2 label JSON")
    parser.add_argument("--candidates", default="bench_real/data/candidates.json", help="Path to candidates.json")
    parser.add_argument("--output", default="bench_real/data/disagreements.json", help="Path to output disagreements JSON")
    args = parser.parse_args()

    with open(args.ann1, "r", encoding="utf-8") as f:
        l1 = json.load(f)
    with open(args.ann2, "r", encoding="utf-8") as f:
        l2 = json.load(f)

    stats = compute_cohens_kappa(l1, l2)
    print("\n=== Inter-Annotator Agreement Report ===")
    print(f"Common Cases:         {stats['n_common_cases']}")
    print(f"Observed Agreement:   {stats['observed_agreement']:.2%}")
    print(f"Expected Agreement:   {stats['expected_agreement']:.2%}")
    print(f"Cohen's Kappa (κ):    {stats['cohens_kappa']} ({stats['interpretation']})")
    print(f"Category Agreement:   {stats['category_agreement_rate']:.2%}")
    print(f"Contingency Table:    {stats['contingency_table']}\n")

    disagreements = extract_disagreements(l1, l2, candidates_file=args.candidates)
    save_path = save_disagreements(disagreements, args.output)
    print(f"Extracted {len(disagreements)} disagreements to {save_path}")


if __name__ == "__main__":
    main()

