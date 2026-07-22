from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION = ROOT / "data" / "recovery-proof-preregistration.json"
LOCKED_STATUS = "DRAFT-LOCKED"
SIGNED_STATUS = "AUTHOR-SIGNED"


def load_preregistration(path: Path = PREREGISTRATION) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_preregistration(payload)
    return payload


def validate_preregistration(payload: dict[str, Any]) -> None:
    required = {
        "version", "status", "execution_authorized", "author_signature", "signed_date",
        "frozen_git_commit", "analysis_unit", "population", "human_judgment",
        "relation_degrees", "observed_metric", "chance_model", "comparison", "publication_gate",
    }
    missing = required - set(payload)
    if missing:
        raise ValueError(f"Proof preregistration is missing fields: {sorted(missing)}")
    if payload["version"] != 1 or payload["analysis_unit"] != "lexical-family":
        raise ValueError("Unsupported proof preregistration version or analysis unit")
    if payload["status"] not in {LOCKED_STATUS, SIGNED_STATUS}:
        raise ValueError(f"Invalid proof preregistration status: {payload['status']}")
    if payload["status"] == LOCKED_STATUS:
        if payload["execution_authorized"] or payload["author_signature"]:
            raise ValueError("A locked proof preregistration cannot authorize execution")
        return

    required_signature = ("author_signature", "signed_date", "frozen_git_commit")
    if not payload["execution_authorized"] or any(not payload.get(field) for field in required_signature):
        raise ValueError("Signed proof preregistration lacks execution authority or signature metadata")
    population = payload["population"]
    if not population.get("languages") or not population.get("source_snapshots"):
        raise ValueError("Signed proof preregistration lacks its frozen population")
    if any(population.get(field) in {None, "", "UNSPECIFIED"} for field in (
        "loan_exclusion_rule", "proper_name_rule",
    )):
        raise ValueError("Signed proof preregistration leaves an eligibility rule unspecified")
    human = payload["human_judgment"]
    if human.get("semantic_match_rule") in {None, "", "UNSPECIFIED"}:
        raise ValueError("Signed proof preregistration leaves the semantic rule unspecified")
    chance = payload["chance_model"]
    if chance.get("algorithm") in {None, "", "UNSPECIFIED"}:
        raise ValueError("Signed proof preregistration leaves the chance algorithm unspecified")
    if not chance.get("preserved_properties"):
        raise ValueError("Signed proof preregistration does not freeze preserved perturbation properties")
    if not isinstance(chance.get("iterations"), int) or chance["iterations"] <= 0:
        raise ValueError("Signed proof preregistration needs a positive iteration count")
    if not isinstance(chance.get("seed"), int):
        raise ValueError("Signed proof preregistration needs an integer random seed")
    comparison = payload["comparison"]
    if any(comparison.get(field) in {None, "", "UNSPECIFIED"} for field in (
        "uncertainty_method", "multiple_comparison_rule",
    )):
        raise ValueError("Signed proof preregistration leaves a comparison rule unspecified")
    trigger = payload.get("execution_trigger")
    if trigger is not None:
        thresholds = trigger.get("thresholds", {})
        if (
            not isinstance(thresholds.get("total_eligible_reviewed_families"), int)
            or thresholds["total_eligible_reviewed_families"] <= 0
            or not isinstance(thresholds.get("min_eligible_reviewed_families_per_language"), int)
            or thresholds["min_eligible_reviewed_families_per_language"] <= 0
            or not trigger.get("attestation_required")
        ):
            raise ValueError("Signed proof preregistration carries a malformed execution trigger")


def require_execution_authority(payload: dict[str, Any]) -> None:
    validate_preregistration(payload)
    if payload["status"] != SIGNED_STATUS or not payload["execution_authorized"]:
        raise PermissionError("Proof execution is locked until the author signs the frozen preregistration")
    trigger = payload.get("execution_trigger")
    if trigger is not None:
        attestation = ROOT / str(trigger.get("attestation_required", ""))
        if not trigger.get("attestation_required") or not attestation.exists():
            raise PermissionError(
                "Proof execution is armed by signature but stays locked until the preregistered "
                "run trigger is met and attested at " + str(trigger.get("attestation_required"))
            )
