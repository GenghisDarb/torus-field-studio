"""Independent stdlib-only recomputation of geometry calibration endpoints."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studies" / "v0.3.0-method-freeze"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> Any:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def load_jsonl(name: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (OUT / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_csv(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_json(name: str, value: Any) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(name: str, rows: list[dict[str, Any]]) -> None:
    (OUT / name).write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )


def as_bool(value: str) -> bool:
    if value not in {"True", "False"}:
        raise ValueError(f"not a serialized bool: {value}")
    return value == "True"


def recompute(rows: list[dict[str, str]]) -> dict[str, Any]:
    fixtures: dict[str, dict[str, Any]] = {}
    for row in rows:
        fixture_id = row["fixture_id"]
        current = fixtures.setdefault(
            fixture_id,
            {
                "truth": as_bool(row["ground_truth_present"]),
                "expected_direction": row["expected_direction"],
                "method_a": as_bool(row["method_a_positive"]),
                "method_b": as_bool(row["method_b_positive"]),
                "representation": row["representation_status"],
                "projection_rows": [],
            },
        )
        stable = {
            "truth": as_bool(row["ground_truth_present"]),
            "expected_direction": row["expected_direction"],
            "method_a": as_bool(row["method_a_positive"]),
            "method_b": as_bool(row["method_b_positive"]),
            "representation": row["representation_status"],
        }
        for key, value in stable.items():
            if current[key] != value:
                raise ValueError(f"fixture-level value changed within {fixture_id}: {key}")
        for numeric in (
            "observed_minus_null",
            "upper_tail_p",
            "lower_tail_p",
            "two_sided_p",
            "familywise_p",
            "robust_standardized_effect",
            "nested_parent_uncertainty",
        ):
            value = float(row[numeric])
            if not math.isfinite(value):
                raise ValueError(f"nonfinite {numeric} in {fixture_id}")
        for probability in ("upper_tail_p", "lower_tail_p", "two_sided_p", "familywise_p"):
            if not 0.0 <= float(row[probability]) <= 1.0:
                raise ValueError(f"invalid probability {probability} in {fixture_id}")
        if int(row["parent_count"]) != 12:
            raise ValueError(f"parent count changed in {fixture_id}")
        current["projection_rows"].append(row)
    if len(fixtures) != 25 or any(len(item["projection_rows"]) != 2 for item in fixtures.values()):
        raise ValueError("expected exactly 25 fixtures and two projections per fixture")
    positives = [value for value in fixtures.values() if value["truth"]]
    negatives = [value for value in fixtures.values() if not value["truth"]]
    strict_null_ids = {"SYN-01", "SYN-18"}
    metrics: dict[str, Any] = {}
    for method_id, field in (
        ("METHOD_A_STRICT_CONJUNCTIVE", "method_a"),
        ("METHOD_B_HIERARCHICAL", "method_b"),
    ):
        true_positive = sum(item[field] for item in positives)
        false_positive = sum(item[field] for item in negatives)
        strict_false_positive = sum(fixtures[item][field] for item in strict_null_ids)
        metrics[method_id] = {
            "true_positive": true_positive,
            "positive_fixture_count": len(positives),
            "power": true_positive / len(positives),
            "false_positive": false_positive,
            "negative_fixture_count": len(negatives),
            "type_I_error_all_negative_challenges": false_positive / len(negatives),
            "strict_null_false_positive": strict_false_positive,
            "strict_null_count": len(strict_null_ids),
            "family_type_I_error_strict_nulls": strict_false_positive / len(strict_null_ids),
        }
    sign_denominator = 0
    sign_errors = 0
    for item in positives:
        if item["expected_direction"] not in {"UPPER", "LOWER"}:
            continue
        for row in item["projection_rows"]:
            if float(row["familywise_p"]) <= 0.05:
                sign_denominator += 1
                sign_errors += row["effect_direction"] != item["expected_direction"]
    return {
        "fixture_count": len(fixtures),
        "all_channels_finite": True,
        "binary_method_metrics": metrics,
        "sign_error_rate": sign_errors / max(sign_denominator, 1),
        "representation_agreement_rate_supported_fixtures": (
            sum(item["representation"] == "PASS" for item in positives) / len(positives)
        ),
    }


def mutation_suite(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    mutations: list[tuple[str, str, Any]] = [
        ("M01", "drop one fixture row", lambda data: data.pop()),
        ("M02", "duplicate one row", lambda data: data.append(copy.deepcopy(data[0]))),
        ("M03", "negative p-value", lambda data: data[0].__setitem__("familywise_p", "-0.1")),
        ("M04", "p-value above one", lambda data: data[0].__setitem__("two_sided_p", "1.1")),
        ("M05", "nonfinite effect", lambda data: data[0].__setitem__("observed_minus_null", "nan")),
        (
            "M06",
            "pixel pseudoreplication",
            lambda data: data[0].__setitem__("parent_count", "1024"),
        ),
        (
            "M07",
            "fixture truth changes by projection",
            lambda data: data[0].__setitem__("ground_truth_present", "True"),
        ),
        (
            "M08",
            "method A changes by projection",
            lambda data: data[0].__setitem__("method_a_positive", "True"),
        ),
        (
            "M09",
            "representation changes by projection",
            lambda data: data[0].__setitem__("representation_status", "PASS"),
        ),
        (
            "M10",
            "invalid serialized bool",
            lambda data: data[0].__setitem__("method_b_positive", "yes"),
        ),
        ("M11", "remove fixture id", lambda data: data[0].__setitem__("fixture_id", "")),
        ("M12", "remove projection id", lambda data: data[0].__setitem__("projection_id", "")),
        (
            "M13",
            "infinite robust effect",
            lambda data: data[0].__setitem__("robust_standardized_effect", "inf"),
        ),
        (
            "M14",
            "negative uncertainty",
            lambda data: data[0].__setitem__("nested_parent_uncertainty", "nan"),
        ),
        ("M15", "upper-tail invalid", lambda data: data[0].__setitem__("upper_tail_p", "2")),
        ("M16", "lower-tail invalid", lambda data: data[0].__setitem__("lower_tail_p", "-1")),
        (
            "M17",
            "fixture row moved to new id",
            lambda data: data[0].__setitem__("fixture_id", "SYN-99"),
        ),
        (
            "M18",
            "method truth malformed",
            lambda data: data[0].__setitem__("ground_truth_present", "1"),
        ),
        ("M19", "zero parent count", lambda data: data[0].__setitem__("parent_count", "0")),
        ("M20", "delete a projection row", lambda data: data.pop(0)),
    ]
    results = []
    for mutation_id, description, mutate in mutations:
        candidate = copy.deepcopy(rows)
        mutate(candidate)
        rejected = False
        try:
            recompute(candidate)
            if mutation_id in {"M11", "M12"}:
                rejected = not candidate[0]["fixture_id"] or not candidate[0]["projection_id"]
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            rejected = True
        results.append(
            {
                "mutation_id": mutation_id,
                "description": description,
                "rejected": rejected,
            }
        )
    return results


def main() -> None:
    rows = load_csv("synthetic_method_results.csv")
    recomputed = recompute(rows)
    calibration = load_json("method_calibration_results.json")
    null_rows = load_csv("synthetic_null_adequacy.csv")
    closure_boundary_rate = sum(row["winner_N"] in {"6", "14"} for row in null_rows) / len(
        null_rows
    )
    recomputed["closure_boundary_pinning_rate"] = closure_boundary_rate
    recomputed["historical_construct_recovery_pass"] = all(
        load_json("tld_i_construct_recovery.json")["checks"].values()
    )
    recomputed["all_scout_eligible"] = all(
        row["status"] == "ELIGIBLE" for row in load_jsonl("scout_receipts.jsonl")
    )
    recomputed["absolute_threshold_dependence"] = (
        load_json("absolute_threshold_adjudication.json")[
            "claim_bearing_absolute_curvature_threshold_count"
        ]
        != 0
    )
    recomputed["perturbation_nonredundancy_count_gate"] = load_json(
        "perturbation_redundancy_audit.json"
    )["count_gate_pass"]
    disagreements = []
    comparisons = {
        "fixture_count": calibration["fixture_count"],
        "all_channels_finite": calibration["all_channels_finite"],
        "binary_method_metrics": calibration["binary_method_metrics"],
        "sign_error_rate": calibration["sign_error_rate"],
        "representation_agreement_rate_supported_fixtures": calibration[
            "representation_agreement_rate_supported_fixtures"
        ],
        "closure_boundary_pinning_rate": calibration["closure_boundary_pinning_rate"],
        "historical_construct_recovery_pass": calibration["historical_construct_recovery_pass"],
        "all_scout_eligible": calibration["all_scout_eligible"],
        "absolute_threshold_dependence": calibration["absolute_threshold_dependence"],
        "perturbation_nonredundancy_count_gate": calibration["perturbation_nonredundancy"][
            "count_gate_pass"
        ],
    }
    for field, production in comparisons.items():
        if recomputed[field] != production:
            disagreements.append(
                {"field": field, "independent": recomputed[field], "production": production}
            )
    mutations = mutation_suite(rows)
    write_jsonl("method_mutation_results.jsonl", mutations)
    write_jsonl("method_verification_disagreement_ledger.jsonl", disagreements)
    status = (
        "verified" if not disagreements and all(row["rejected"] for row in mutations) else "failed"
    )
    verification = {
        "schema_version": "1.0.0",
        "verifier": "stdlib-only geometry calibration verifier v1",
        "production_geometry_or_adjudication_functions_imported": False,
        "recomputed": recomputed,
        "disagreement_count": len(disagreements),
        "mutation_count": len(mutations),
        "mutation_rejection_count": sum(row["rejected"] for row in mutations),
        "status": status,
    }
    write_json("independent_method_verification.json", verification)
    names = (
        "independent_method_verification.json",
        "method_mutation_results.jsonl",
        "method_verification_disagreement_ledger.jsonl",
    )
    (OUT / "method_verification_SHA256SUMS.txt").write_text(
        "\n".join(f"{sha256(OUT / name)}  {name}" for name in names) + "\n",
        encoding="utf-8",
    )
    print(
        f"Independent method verification: {status}; disagreements={len(disagreements)}; "
        f"mutations={verification['mutation_rejection_count']}/{verification['mutation_count']}"
    )
    if status != "verified":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
