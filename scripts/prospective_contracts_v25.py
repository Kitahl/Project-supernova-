#!/usr/bin/env python3
"""Prospective Protocol-2.5 contract overlays.

The active historical generation is never retrofitted. An overlay becomes
admission-authoritative only when its path is frozen in that cohort's
``required_control_paths``. This lets accepted hardening invalidate an old cohort
without rewriting its immutable control, while ensuring the replacement cohort
uses the stricter contracts.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

from jsonschema import Draft202012Validator

STRICT_ISSUE = "schemas/strict_issue_record_v25.schema.json"
MM03_PAYLOAD = "schemas/mastermind_mm03_payload_v25.schema.json"
MM07_REPLAY = "schemas/mastermind_mm07_replay_payload_v25.schema.json"
MM07_FRESH = "schemas/mastermind_mm07_fresh_payload_v25.schema.json"
MM01_REACT_V2 = "schemas/mastermind_react_proposal_v25_2.schema.json"
VERIFICATION_ASSURANCE = "schemas/verification_assurance_disposition_v25.schema.json"
POOL_DISPOSITION = "benchmark/pool_disposition.json"


def _load(root: pathlib.Path, path: str) -> dict:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _is_frozen(control: dict, path: str) -> bool:
    return path in set(control.get("required_control_paths") or [])


def _schema_errors(root: pathlib.Path, path: str, value: Any, prefix: str) -> list[str]:
    try:
        schema = _load(root, path)
        Draft202012Validator.check_schema(schema)
        return [f"{prefix}: {error.message}" for error in Draft202012Validator(schema).iter_errors(value)]
    except Exception as exc:
        return [f"{prefix} execution failed: {exc!r}"]


def _strict_issue_errors(report: dict, control: dict, root: pathlib.Path) -> list[str]:
    if not _is_frozen(control, STRICT_ISSUE):
        return []
    errors: list[str] = []
    ledger = report.get("issue_ledger")
    if not isinstance(ledger, list):
        return ["strict issue ledger is not an array"]
    for index, record in enumerate(ledger):
        errors.extend(_schema_errors(root, STRICT_ISSUE, record, f"issue_ledger[{index}]"))
    return errors


def _fresh_assignment_errors(report: dict, assignment: dict, worker_id: str) -> list[str]:
    if report.get("mode") != "FRESH_EXECUTION":
        return []
    errors: list[str] = []
    worker = (assignment.get("workers") or {}).get(worker_id) or {}
    if assignment.get("network_mode") != "FRESH_ENABLED":
        errors.append("FRESH_EXECUTION requires assignment.network_mode=FRESH_ENABLED")
    if worker.get("fresh_allowed") is not True:
        errors.append("FRESH_EXECUTION requires frozen worker fresh_allowed=true")

    manifest_id = worker.get("private_manifest_id")
    manifest_blob = worker.get("private_manifest_git_identity")
    if not isinstance(manifest_id, str) or not manifest_id:
        errors.append("FRESH_EXECUTION requires frozen worker private_manifest_id")
    if not isinstance(manifest_blob, str) or len(manifest_blob) != 40:
        errors.append("FRESH_EXECUTION requires frozen worker private_manifest_git_identity")
    if report.get("private_manifest_id") != manifest_id:
        errors.append("report private_manifest_id is not cross-bound to frozen assignment")
    if report.get("private_manifest_git_identity") != manifest_blob:
        errors.append("report private_manifest_git_identity is not cross-bound to frozen assignment")
    return errors


def _mm01_errors(report: dict, assignment: dict, control: dict, root: pathlib.Path) -> list[str]:
    if report.get("worker_id") != "MM01" or report.get("mode") != "FRESH_EXECUTION":
        return []
    if not _is_frozen(control, MM01_REACT_V2):
        return []

    payload = report.get("role_payload")
    errors = _schema_errors(root, MM01_REACT_V2, payload, "MM01 React payload")
    errors.extend(_fresh_assignment_errors(report, assignment, "MM01"))
    if not isinstance(payload, dict):
        return errors

    evidence = payload.get("assignment_evidence") or {}
    expected = {
        "assignment_id": assignment.get("assignment_id"),
        "cohort_id": assignment.get("cohort_id"),
        "phase": assignment.get("phase"),
        "private_manifest_id": report.get("private_manifest_id"),
        "private_manifest_git_identity": report.get("private_manifest_git_identity"),
    }
    for key, value in expected.items():
        if evidence.get(key) != value:
            errors.append(f"MM01 assignment_evidence.{key} is not cross-bound to frozen assignment/report")

    if assignment.get("phase") != "STAGE0_LOOP":
        errors.append("fresh MM01 React work requires exact frozen phase STAGE0_LOOP")
    if evidence.get("pool_class") != "TRAIN_TUNING":
        errors.append("fresh MM01 React work requires TRAIN_TUNING pool")

    suite_id = assignment.get("benchmark_suite_id")
    try:
        disposition = _load(root, POOL_DISPOSITION)
        suite = ((disposition.get("programs") or {}).get("MASTERMIND") or {}).get(suite_id)
        if not isinstance(suite, dict) or suite.get("pool") != "TRAIN_TUNING":
            errors.append("frozen MM01 benchmark suite is not admitted as TRAIN_TUNING")
        if suite and suite.get("promotion_eligible_for_supernova") is not False:
            errors.append("MM01 Stage0 TRAIN suite may not be promotion-eligible")
    except Exception as exc:
        errors.append(f"MM01 pool-disposition check failed: {exc!r}")
    return errors


def role_contract_errors(report: dict, assignment: dict, control: dict, root: pathlib.Path) -> list[str]:
    """Return strict prospective worker-report contract errors."""
    errors = _strict_issue_errors(report, control, root)
    worker_id = report.get("worker_id")
    mode = report.get("mode")

    if worker_id == "MM03" and _is_frozen(control, MM03_PAYLOAD):
        errors.extend(_schema_errors(root, MM03_PAYLOAD, report.get("role_payload"), "MM03 payload"))

    if worker_id == "MM07":
        if mode == "SAFE_REPLAY_ONLY" and _is_frozen(control, MM07_REPLAY):
            errors.extend(_schema_errors(root, MM07_REPLAY, report.get("role_payload"), "MM07 replay payload"))
        elif mode == "FRESH_EXECUTION" and _is_frozen(control, MM07_FRESH):
            errors.extend(_schema_errors(root, MM07_FRESH, report.get("role_payload"), "MM07 fresh payload"))
            errors.extend(_fresh_assignment_errors(report, assignment, "MM07"))

    errors.extend(_mm01_errors(report, assignment, control, root))

    if mode == "FRESH_EXECUTION" and worker_id not in {"MM01", "MM07"}:
        # The public control plane can prove frozen ownership and manifest identity.
        # Private payload validity is checked independently in the private vault.
        errors.extend(_fresh_assignment_errors(report, assignment, str(worker_id)))
    return errors


def verification_contract_errors(obj: dict, control: dict, root: pathlib.Path) -> list[str]:
    if not _is_frozen(control, VERIFICATION_ASSURANCE):
        return []
    return _schema_errors(root, VERIFICATION_ASSURANCE, obj, "verification assurance disposition")
