#!/usr/bin/env python3
"""Zero-authority TRAIN evolution archive contracts.

This module is deliberately outside the active Protocol-2.5 assurance state
machine.  It validates and content-addresses engineering records; it does not
execute candidate code, write Git refs, publish statuses, or promote anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import tempfile
from typing import Any, Iterable

from jsonschema import Draft202012Validator

SCHEMA_PATH = pathlib.Path(__file__).resolve().parent / "contracts/rate_split_record.schema.json"
ID_FIELDS = {
    "COST_SMOKE_MANIFEST": "cost_smoke_id",
    "PILOT_MANIFEST": "pilot_id",
    "PROPOSAL": "proposal_id",
    "CANDIDATE": "candidate_id",
    "EVALUATION": "evaluation_id",
    "INTEGRITY": "integrity_id",
    "SELECTION": "selection_id",
    "ARCHIVE_SNAPSHOT": "snapshot_id",
}
COST_FIELDS = (
    "instrumentation",
    "data",
    "training_amortized",
    "inference",
    "probe",
    "execution",
    "verification",
    "fidelity",
    "revalidation",
    "failure_recovery",
    "metalevel_selection",
)
SNAPSHOT_CATEGORIES = (
    "candidate_ids",
    "proposal_ids",
    "evaluation_ids",
    "integrity_ids",
    "selection_ids",
)
ZERO_CREDIT = {
    "calibration": 0,
    "fresh": False,
    "scientific": False,
    "authority": "NONE",
}


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant forbidden: {value}")


def _unique_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON object key forbidden: {key}")
        out[key] = value
    return out


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_constant,
        object_pairs_hook=_unique_pairs,
    )
    if not isinstance(value, dict):
        raise ValueError("archive record must be a JSON object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def artifact_id(source_tree_sha256: str) -> str:
    """Identify executable content independently of lineage, role, or cohort."""
    return sha256_bytes(b"PS-TRAINLAB-ARTIFACT-1\0" + source_tree_sha256.encode("ascii"))


def content_id(value: dict[str, Any], id_field: str) -> str:
    """Return a record-type-separated identity over canonical record bytes."""
    descriptor = dict(value)
    descriptor.pop(id_field, None)
    domain = f"PS-TRAINLAB-RATE-SPLIT-1:{id_field}".encode("ascii") + b"\0"
    return sha256_bytes(domain + canonical_bytes(descriptor))


def bind_content_id(value: dict[str, Any], id_field: str) -> dict[str, Any]:
    out = dict(value)
    out.pop(id_field, None)
    out[id_field] = content_id(out, id_field)
    return out


def schema_errors(record: dict[str, Any], schema_path: pathlib.Path = SCHEMA_PATH) -> list[str]:
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    return [
        f"schema:{'.'.join(str(x) for x in err.absolute_path) or '$'}:{err.message}"
        for err in sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path))
    ]


def _identity_errors(record: dict[str, Any]) -> list[str]:
    record_type = record.get("record_type")
    id_field = ID_FIELDS.get(record_type)
    if id_field is None:
        return ["unsupported_record_type"]
    expected = record.get(id_field)
    observed = content_id(record, id_field)
    return [] if expected == observed else [f"content_id_mismatch:{id_field}"]


def _credit_errors(record: dict[str, Any]) -> list[str]:
    return [] if record.get("supernova_credit") == ZERO_CREDIT else ["nonzero_or_invalid_supernova_credit"]


def validate_cost_smoke(record: dict[str, Any]) -> list[str]:
    errors = schema_errors(record)
    if errors or record.get("record_type") != "COST_SMOKE_MANIFEST":
        return errors or ["record_type_not_cost_smoke_manifest"]
    errors.extend(_identity_errors(record))
    errors.extend(_credit_errors(record))
    rows = record["instances"]
    ids = [row["instance_id"] for row in rows]
    hashes = [row["statement_sha256"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("cost_smoke_instance_ids_not_unique")
    if len(hashes) != len(set(hashes)):
        errors.append("cost_smoke_statement_hashes_not_unique")
    return errors


def validate_pilot(record: dict[str, Any]) -> list[str]:
    errors = schema_errors(record)
    if errors or record.get("record_type") != "PILOT_MANIFEST":
        return errors or ["record_type_not_pilot_manifest"]
    errors.extend(_identity_errors(record))
    errors.extend(_credit_errors(record))
    partitions = record["partitions"]
    diag = partitions["DIAG"]
    select = partitions["SELECT"]
    if len(diag) != 32:
        errors.append("diag_instance_count_not_32")
    if len(select) != 32:
        errors.append("select_instance_count_not_32")
    rows = diag + select
    ids = [row["instance_id"] for row in rows]
    hashes = [row["statement_sha256"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("pilot_instance_ids_not_unique")
    if len(hashes) != len(set(hashes)):
        errors.append("pilot_statement_hashes_not_unique")
    return errors


def validate_candidate(record: dict[str, Any], patch_bytes: bytes | None = None) -> list[str]:
    errors = schema_errors(record)
    if errors or record.get("record_type") != "CANDIDATE":
        return errors or ["record_type_not_candidate"]
    errors.extend(_identity_errors(record))
    errors.extend(_credit_errors(record))
    descriptor = record["descriptor"]
    if record["artifact_id"] != artifact_id(descriptor["source_tree_sha256"]):
        errors.append("artifact_id_mismatch")
    parents = descriptor["parent_candidate_ids"]
    if parents != sorted(set(parents)):
        errors.append("parent_candidate_ids_not_sorted_unique")
    if patch_bytes is not None and sha256_bytes(patch_bytes) != descriptor["source_patch_sha256"]:
        errors.append("source_patch_sha256_mismatch")
    return errors


def validate_proposal(record: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    errors = schema_errors(record)
    if errors or record.get("record_type") != "PROPOSAL":
        return errors or ["record_type_not_proposal"]
    errors.extend(_identity_errors(record))
    errors.extend(_credit_errors(record))
    errors.extend(f"candidate:{x}" for x in validate_candidate(candidate))
    if record["candidate_id"] != candidate.get("candidate_id"):
        errors.append("proposal_candidate_id_mismatch")
    descriptor = candidate.get("descriptor") or {}
    parents = descriptor.get("parent_candidate_ids") or []
    if len(parents) != 1 or record["parent_candidate_id"] != parents[0]:
        errors.append("proposal_parent_candidate_id_mismatch")
    if record["mutation_operator_id"] != descriptor.get("mutation_operator_id"):
        errors.append("proposal_mutation_operator_mismatch")
    if record["mutation_operator_config_sha256"] != descriptor.get("mutation_operator_config_sha256"):
        errors.append("proposal_mutation_config_mismatch")
    return errors


def _partition_rows(pilot: dict[str, Any], partition: str) -> list[dict[str, Any]]:
    return pilot["partitions"][partition]


def _cost_errors(cost: dict[str, Any]) -> list[str]:
    subtotal = sum(cost[field] for field in COST_FIELDS)
    return [] if subtotal == cost["total"] else ["complete_cost_total_mismatch"]


def validate_evaluation(
    record: dict[str, Any],
    pilot: dict[str, Any],
    candidate: dict[str, Any],
) -> list[str]:
    errors = schema_errors(record)
    if errors or record.get("record_type") != "EVALUATION":
        return errors or ["record_type_not_evaluation"]
    errors.extend(_identity_errors(record))
    errors.extend(_credit_errors(record))
    errors.extend(f"pilot:{x}" for x in validate_pilot(pilot))
    errors.extend(f"candidate:{x}" for x in validate_candidate(candidate))
    if record["pilot_id"] != pilot.get("pilot_id"):
        errors.append("evaluation_pilot_id_mismatch")
    if record["candidate_id"] != candidate.get("candidate_id"):
        errors.append("evaluation_candidate_id_mismatch")
    if record["artifact_id"] != candidate.get("artifact_id"):
        errors.append("evaluation_artifact_id_mismatch")
    descriptor = candidate.get("descriptor") or {}
    if record["source_tree_sha256"] != descriptor.get("source_tree_sha256"):
        errors.append("evaluation_source_tree_sha256_mismatch")
    if record["benchmark_snapshot_sha256"] != pilot.get("benchmark", {}).get("snapshot_sha256"):
        errors.append("evaluation_benchmark_snapshot_sha256_mismatch")
    expected = {
        row["instance_id"]: row["statement_sha256"]
        for row in _partition_rows(pilot, record["partition"])
    }
    observed_rows = record["results"]
    observed_ids = [row["instance_id"] for row in observed_rows]
    if len(observed_ids) != len(set(observed_ids)):
        errors.append("evaluation_instance_ids_not_unique")
    if set(observed_ids) != set(expected):
        errors.append("evaluation_partition_coverage_mismatch")
    for row in observed_rows:
        if expected.get(row["instance_id"]) != row["statement_sha256"]:
            errors.append(f"evaluation_statement_sha256_mismatch:{row['instance_id']}")
    errors.extend(_cost_errors(record["complete_cost_microunits"]))
    return errors


def evidence_integrity(
    pilot: dict[str, Any],
    candidate: dict[str, Any],
    evaluation: dict[str, Any] | None,
) -> dict[str, Any]:
    if evaluation is None:
        base = {
            "schema_version": "PS-FORMAL-TRAIN-ARCHIVE-1",
            "record_type": "INTEGRITY",
            "authority": "NONE_ENGINEERING_ONLY",
            "pilot_id": pilot.get("pilot_id"),
            "candidate_id": candidate.get("candidate_id"),
            "evaluation_id": None,
            "partition": None,
            "status": "MISSING",
            "errors": ["evaluation_missing"],
            "exact_coverage": False,
            "hashes_verified": False,
            "score_fields_emitted": False,
            "supernova_credit": dict(ZERO_CREDIT),
        }
        return bind_content_id(base, "integrity_id")

    errors = validate_evaluation(evaluation, pilot, candidate)
    base = {
        "schema_version": "PS-FORMAL-TRAIN-ARCHIVE-1",
        "record_type": "INTEGRITY",
        "authority": "NONE_ENGINEERING_ONLY",
        "pilot_id": pilot.get("pilot_id"),
        "candidate_id": candidate.get("candidate_id"),
        "evaluation_id": evaluation.get("evaluation_id"),
        "partition": evaluation.get("partition"),
        "status": "ADMISSIBLE" if not errors else "QUARANTINED",
        "errors": errors,
        "exact_coverage": not any("coverage" in row or "instance" in row for row in errors),
        "hashes_verified": not any("sha256" in row or "content_id" in row for row in errors),
        "score_fields_emitted": False,
        "supernova_credit": dict(ZERO_CREDIT),
    }
    return bind_content_id(base, "integrity_id")


def validate_integrity(record: dict[str, Any]) -> list[str]:
    errors = schema_errors(record)
    if errors or record.get("record_type") != "INTEGRITY":
        return errors or ["record_type_not_integrity"]
    errors.extend(_identity_errors(record))
    errors.extend(_credit_errors(record))
    return errors


def select_deterministically(
    pilot: dict[str, Any],
    candidates: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
    integrities: list[dict[str, Any]],
    seed_sha256: str,
) -> dict[str, Any]:
    errors = validate_pilot(pilot)
    if errors:
        raise ValueError("invalid pilot: " + ";".join(errors))
    candidates_by_id = {row.get("candidate_id"): row for row in candidates}
    evaluations_by_id = {row.get("evaluation_id"): row for row in evaluations}
    ranked: list[dict[str, Any]] = []
    for integrity in integrities:
        if validate_integrity(integrity) or integrity.get("status") != "ADMISSIBLE":
            continue
        if integrity.get("pilot_id") != pilot["pilot_id"] or integrity.get("partition") != "SELECT":
            continue
        evaluation = evaluations_by_id.get(integrity.get("evaluation_id"))
        candidate = candidates_by_id.get(integrity.get("candidate_id"))
        if evaluation is None or candidate is None:
            continue
        if validate_evaluation(evaluation, pilot, candidate):
            continue
        pass_count = sum(row["outcome"] == "PASS" for row in evaluation["results"])
        total_cost = evaluation["complete_cost_microunits"]["total"]
        tie_break = sha256_bytes(f"{seed_sha256}:{candidate['candidate_id']}".encode("ascii"))
        ranked.append(
            {
                "candidate_id": candidate["candidate_id"],
                "evaluation_id": evaluation["evaluation_id"],
                "integrity_id": integrity["integrity_id"],
                "pass_count": pass_count,
                "total_complete_cost_microunits": total_cost,
                "seeded_tie_break_sha256": tie_break,
            }
        )
    ranked.sort(
        key=lambda row: (
            -row["pass_count"],
            row["total_complete_cost_microunits"],
            row["seeded_tie_break_sha256"],
            row["candidate_id"],
        )
    )
    selected = ranked[0]["candidate_id"] if ranked else None
    for row in ranked:
        row["selection_probability"] = 1.0 if row["candidate_id"] == selected else 0.0
    base = {
        "schema_version": "PS-FORMAL-TRAIN-ARCHIVE-1",
        "record_type": "SELECTION",
        "authority": "NONE_ENGINEERING_ONLY",
        "pilot_id": pilot["pilot_id"],
        "policy_id": "BEST_OBSERVED_THEN_SEEDED_TIEBREAK_V1",
        "seed_sha256": seed_sha256,
        "outcome": "SELECTED_FOR_TRAIN_PARENT" if selected else "NO_ADMISSIBLE_EVIDENCE",
        "selected_candidate_id": selected,
        "ranking": ranked,
        "scientific_claim": False,
        "assurance_transition_requested": False,
        "supernova_credit": dict(ZERO_CREDIT),
    }
    return bind_content_id(base, "selection_id")


def validate_selection(record: dict[str, Any]) -> list[str]:
    errors = schema_errors(record)
    if errors or record.get("record_type") != "SELECTION":
        return errors or ["record_type_not_selection"]
    errors.extend(_identity_errors(record))
    errors.extend(_credit_errors(record))
    return errors


def archive_object_set_root(groups: dict[str, list[str]]) -> str:
    normalized: dict[str, list[str]] = {}
    for category in SNAPSHOT_CATEGORIES:
        values = groups.get(category)
        if not isinstance(values, list):
            raise ValueError(f"snapshot category missing: {category}")
        if values != sorted(set(values)):
            raise ValueError(f"snapshot category must be sorted and unique: {category}")
        normalized[category] = values
    if set(groups) != set(SNAPSHOT_CATEGORIES):
        raise ValueError("snapshot categories are not exact")
    domain = b"PS-TRAINLAB-OBJECT-SET-1\0"
    return sha256_bytes(domain + canonical_bytes(normalized))


def make_archive_snapshot(
    pilot_id: str,
    previous_snapshot_id: str | None,
    groups: dict[str, list[str]],
) -> dict[str, Any]:
    root = archive_object_set_root(groups)
    base = {
        "schema_version": "PS-FORMAL-TRAIN-ARCHIVE-1",
        "record_type": "ARCHIVE_SNAPSHOT",
        "authority": "NONE_ENGINEERING_ONLY",
        "pilot_id": pilot_id,
        "previous_snapshot_id": previous_snapshot_id,
        "object_ids": {key: list(groups[key]) for key in SNAPSHOT_CATEGORIES},
        "object_set_root_sha256": root,
        "scientific_state_effect": "NONE",
        "promotion_eligible": False,
        "supernova_credit": dict(ZERO_CREDIT),
    }
    return bind_content_id(base, "snapshot_id")


def validate_archive_snapshot(record: dict[str, Any]) -> list[str]:
    errors = schema_errors(record)
    if errors or record.get("record_type") != "ARCHIVE_SNAPSHOT":
        return errors or ["record_type_not_archive_snapshot"]
    errors.extend(_identity_errors(record))
    errors.extend(_credit_errors(record))
    groups = record["object_ids"]
    try:
        observed = archive_object_set_root(groups)
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if observed != record["object_set_root_sha256"]:
            errors.append("archive_object_set_root_mismatch")
    return errors


def validate_record(record: dict[str, Any]) -> list[str]:
    record_type = record.get("record_type")
    if record_type == "COST_SMOKE_MANIFEST":
        return validate_cost_smoke(record)
    if record_type == "PILOT_MANIFEST":
        return validate_pilot(record)
    if record_type == "CANDIDATE":
        return validate_candidate(record)
    if record_type == "INTEGRITY":
        return validate_integrity(record)
    if record_type == "SELECTION":
        return validate_selection(record)
    if record_type == "ARCHIVE_SNAPSHOT":
        return validate_archive_snapshot(record)
    errors = schema_errors(record)
    errors.extend(_identity_errors(record) if not errors else [])
    errors.extend(_credit_errors(record) if not errors else [])
    return errors


def put_immutable(archive_root: pathlib.Path, record: dict[str, Any]) -> tuple[str, pathlib.Path, bool]:
    """Store canonical bytes in a single-writer content-addressed archive."""
    errors = validate_record(record)
    if errors:
        raise ValueError("invalid archive record: " + ";".join(errors))
    payload = canonical_bytes(record) + b"\n"
    digest = sha256_bytes(payload)
    target = archive_root / "objects" / "sha256" / digest[:2] / f"{digest[2:]}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != payload:
            raise ValueError("immutable archive object path contains different bytes")
        return digest, target, False
    handle, raw_tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=target.parent)
    tmp = pathlib.Path(raw_tmp)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if target.exists():
            if target.read_bytes() != payload:
                raise ValueError("immutable archive object path contains different bytes")
            return digest, target, False
        tmp.rename(target)
        return digest, target, True
    finally:
        tmp.unlink(missing_ok=True)


def _is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def require_external_archive_root(repo_root: pathlib.Path, archive_root: pathlib.Path) -> None:
    resolved_repo = repo_root.resolve()
    resolved_archive = archive_root.resolve()
    if _is_within(resolved_archive, resolved_repo):
        raise ValueError("archive root must be outside the Git worktree")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate/store zero-authority TRAIN evolution records.")
    parser.add_argument("record")
    parser.add_argument("--root", default=".")
    parser.add_argument("--archive-root")
    args = parser.parse_args(argv)
    repo_root = pathlib.Path(args.root).resolve()
    record_path = pathlib.Path(args.record)
    if not record_path.is_absolute():
        record_path = repo_root / record_path
    record = load_json(record_path)
    errors = validate_record(record)
    result: dict[str, Any] = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "record_type": record.get("record_type"),
        "authority": "NONE_ENGINEERING_ONLY",
        "supernova_credit": dict(ZERO_CREDIT),
    }
    if not errors and args.archive_root:
        archive_root = pathlib.Path(args.archive_root)
        require_external_archive_root(repo_root, archive_root)
        digest, path, created = put_immutable(archive_root.resolve(), record)
        result.update({"object_sha256": digest, "object_path": str(path), "created": created})
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
