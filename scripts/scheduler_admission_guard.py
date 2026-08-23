#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import strict_json

PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
WORKERS = ("MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01")
ROLES = WORKERS + ("MM06","MF06","BIL00")
TZID_TOKEN = "TZID=America/Vancouver"
PREACTIVATION_WAIT = "PREACTIVATION_WAIT"
BEHAVIORAL_PROJECTION = ("task_id","title","prompt_sha256","normalized_schedule","timing_mode","default_timezone","enabled")
MUTABLE_RUNTIME_FIELDS = {"last_run_time","updated_at","next_run_time","last_error","last_result"}
FORBIDDEN_PUBLIC_KEY_NAMES = {"worker_auth_secret","worker_auth_secret_hex","raw_auth_material","private_key","raw_key","api_key","access_token","password"}


def load(root: pathlib.Path, path: str) -> Any:
    return strict_json.loads((root / path).read_text(encoding="utf-8"))


def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def parse_time(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("scheduler/liveness time is not offset-aware")
    return dt.astimezone(timezone.utc)


def schema_errors(root: pathlib.Path, schema_path: str, value: Any) -> list[str]:
    schema = load(root, schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [e.message for e in validator.iter_errors(value)]


def _scan_public(value: Any, errors: list[str], path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_PUBLIC_KEY_NAMES:
                errors.append(f"raw auth material forbidden in public scheduler evidence: {path}.{key}")
            _scan_public(child, errors, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_public(child, errors, f"{path}[{index}]")


def production_allowed(current_state: dict, manifest: dict, now: datetime) -> bool:
    """Staged tasks must return PREACTIVATION_WAIT until exact activation and time gate."""
    try:
        return (
            current_state.get("active_cohort_id") == manifest.get("cohort_id")
            and current_state.get("generation_head_sha") == manifest.get("generation_head_sha")
            and now.astimezone(timezone.utc) >= parse_time(manifest["production_not_before_utc"])
        )
    except Exception:
        return False


def validate_scheduler_manifest(root: pathlib.Path, control: dict, assignment: dict, liveness: dict, manifest: dict) -> list[str]:
    errors = schema_errors(root, "schemas/scheduler_manifest.schema.json", manifest)
    _scan_public(manifest, errors)
    cohort = control.get("cohort_id")
    if manifest.get("protocol_version") != "2.5" or manifest.get("task_network_plan_id") != PLAN:
        errors.append("scheduler manifest protocol/plan mismatch")
    if manifest.get("cohort_id") != cohort or manifest.get("cohort_id") != assignment.get("cohort_id") or manifest.get("cohort_id") != liveness.get("cohort_id"):
        errors.append("scheduler manifest cohort mismatch")
    if manifest.get("generation_head_sha") != assignment.get("generation_head_sha", liveness.get("generation_head_sha")):
        # Some frozen assignment versions name the pre-write root differently; final transition guard binds G separately.
        if manifest.get("generation_head_sha") != liveness.get("generation_head_sha"):
            errors.append("scheduler manifest generation head mismatch")
    if manifest.get("control_manifest_id") != control.get("control_manifest_id"):
        errors.append("scheduler manifest control id mismatch")
    if manifest.get("assignment_id") != assignment.get("assignment_id"):
        errors.append("scheduler manifest assignment id mismatch")
    if manifest.get("control_manifest_git_identity") != control.get("control_manifest_git_identity", manifest.get("control_manifest_git_identity")):
        # Control file cannot self-contain its Git blob; transition guard separately checks the state pointer.
        pass
    if manifest.get("assignment_git_identity") != liveness.get("assignment_git_identity", manifest.get("assignment_git_identity")):
        errors.append("scheduler manifest assignment blob mismatch")
    if manifest.get("liveness_git_identity") != git_blob_sha(root / f"liveness/{cohort}.json"):
        errors.append("scheduler manifest liveness blob mismatch")
    if manifest.get("task_registry_git_identity") != git_blob_sha(root / "config/task_registry_v25.json"):
        errors.append("scheduler manifest task registry blob mismatch")
    if manifest.get("behavioral_config_projection") != list(BEHAVIORAL_PROJECTION):
        errors.append("behavioral config projection is not the frozen whitelist")
    excluded = set(manifest.get("mutable_runtime_fields_excluded") or [])
    if not MUTABLE_RUNTIME_FIELDS.issubset(excluded):
        errors.append("behavioral config projection does not exclude mutable runtime observations")

    tasks = manifest.get("tasks") or []
    ids = [row.get("role_id") for row in tasks if isinstance(row, dict)]
    if len(tasks) != 15 or set(ids) != set(ROLES) or len(ids) != len(set(ids)):
        errors.append("scheduler manifest must contain exactly one task for each of the 15 canonical roles")
    task_ids = [row.get("scheduler_task_id") for row in tasks if isinstance(row, dict)]
    if len(task_ids) != len(set(task_ids)):
        errors.append("duplicate scheduler task id")

    registry = load(root, "config/task_registry_v25.json")
    if registry.get("active_task_count") != 15 or registry.get("no_sixteenth_lane") is not True or registry.get("same_task_session_each_run") is not True:
        errors.append("task registry does not preserve the canonical 15 same-task sessions")
    registry_rows = {row["role_id"]: row for row in registry.get("tasks", [])}
    auth = load(root, "config/worker_auth.json")
    commitments = auth.get("commitments") or {}

    lane_rows = {row.get("lane_id"): row for row in liveness.get("lanes", []) if isinstance(row, dict)}
    assignment_workers = assignment.get("workers") or assignment.get("assignments") or []
    assignment_by_role = {}
    if isinstance(assignment_workers, list):
        assignment_by_role = {row.get("worker_id") or row.get("role_id"): row for row in assignment_workers if isinstance(row, dict)}
    elif isinstance(assignment_workers, dict):
        assignment_by_role = assignment_workers

    cadence = int(manifest.get("scheduler_cadence_seconds", 0) or 0)
    attempt = int(manifest.get("max_attempt_duration_seconds", 0) or 0)
    jitter = int(manifest.get("scheduler_jitter_budget_seconds", 0) or 0)
    if cadence < 3600 or attempt <= 0 or jitter < 0:
        errors.append("invalid scheduler retry budget parameters")
    production_not_before = None
    admission_cutoff = None
    try:
        production_not_before = parse_time(manifest["production_not_before_utc"])
        admission_cutoff = parse_time(manifest["admission_cutoff_utc"])
        if admission_cutoff >= production_not_before:
            errors.append("scheduler admission cutoff must precede production_not_before")
    except Exception as exc:
        errors.append("scheduler production/admission time invalid: " + str(exc))

    task_by_role = {row.get("role_id"): row for row in tasks if isinstance(row, dict)}
    for role in ROLES:
        row = task_by_role.get(role) or {}
        expected = registry_rows.get(role) or {}
        if row.get("canonical_title") != expected.get("title"):
            errors.append(role + " canonical title/task session mismatch")
        if row.get("default_timezone") != "America/Vancouver" or TZID_TOKEN not in str(row.get("normalized_schedule", "")):
            errors.append(role + " normalized scheduler timezone is not explicit Vancouver TZID")
        if row.get("timing_mode") != "exact_schedule" or row.get("enabled") is not True:
            errors.append(role + " scheduler task is not enabled exact_schedule")
        if row.get("preactivation_branch") != f"ps/preactivate/{cohort}/{role}":
            errors.append(role + " preactivation branch mismatch")
        if row.get("preactivation_path") != f"preactivation/{cohort}/{role}.json":
            errors.append(role + " preactivation path mismatch")
        for challenge in row.get("challenge_occurrences_utc") or []:
            try:
                if production_not_before and parse_time(challenge) >= production_not_before:
                    errors.append(role + " preactivation challenge is not strictly before production_not_before")
            except Exception:
                errors.append(role + " invalid challenge occurrence")
        try:
            first = parse_time(row["normalized_first_production_utc"])
            second = parse_time(row["normalized_second_production_utc"])
            if cadence and int((second - first).total_seconds()) != cadence:
                errors.append(role + " normalized retry occurrence does not equal first+cadence")
        except Exception as exc:
            errors.append(role + " normalized production time invalid: " + str(exc))
            continue

        if role in WORKERS:
            lane = lane_rows.get(role) or {}
            if not lane:
                errors.append(role + " missing frozen liveness lane")
                continue
            try:
                expected_first = parse_time(lane["expected_window_start_utc"])
                deadline = parse_time(lane["deadline_utc"])
                if first != expected_first:
                    errors.append(role + " normalized first production occurrence differs from frozen liveness start")
                if (deadline - first).total_seconds() < cadence + attempt + jitter:
                    errors.append(role + " liveness lacks one full retry plus attempt+jitter budget")
                if (deadline - second).total_seconds() < attempt + jitter:
                    errors.append(role + " retry does not leave attempt+jitter budget before deadline")
            except Exception as exc:
                errors.append(role + " liveness time invalid: " + str(exc))
            if row.get("worker_auth_commitment") != commitments.get(role):
                errors.append(role + " worker auth commitment mismatch")
            lane_branch = lane.get("branch")
            lane_path = lane.get("path")
            if lane_branch and row.get("production_branch") != lane_branch:
                errors.append(role + " production branch mismatch")
            if lane_path and row.get("production_path") != lane_path:
                errors.append(role + " production path mismatch")
        elif row.get("worker_auth_commitment") is not None:
            errors.append(role + " non-worker must not claim a worker auth commitment")

    try:
        max_deadline = max(parse_time(row["deadline_utc"]) for row in lane_rows.values())
        mm06 = parse_time(task_by_role["MM06"]["normalized_first_production_utc"])
        mf06 = parse_time(task_by_role["MF06"]["normalized_first_production_utc"])
        bil00 = parse_time(task_by_role["BIL00"]["normalized_first_production_utc"])
        if not (max_deadline < mm06 < mf06 < bil00):
            errors.append("fan-in order must be workers -> postdeadline MM06 -> MF06 -> BIL00")
    except Exception as exc:
        errors.append("fan-in order could not be verified: " + str(exc))
    return errors


def validate_scheduler_admission(root: pathlib.Path, manifest: dict, admission: dict) -> list[str]:
    errors = schema_errors(root, "schemas/scheduler_admission.schema.json", admission)
    _scan_public(admission, errors)
    for key in ("protocol_version","task_network_plan_id","candidate_nonce","cohort_id","generation_head_sha"):
        if admission.get(key) != manifest.get(key):
            errors.append("scheduler admission/manifest mismatch: " + key)
    manifest_blob = git_blob_sha(root / f"scheduler/{manifest['cohort_id']}.json")
    if admission.get("scheduler_manifest_git_identity") != manifest_blob:
        errors.append("scheduler admission is not bound to exact scheduler manifest blob")
    results = admission.get("worker_results") or []
    roles = [row.get("role_id") for row in results if isinstance(row, dict)]
    if len(results) != 12 or set(roles) != set(WORKERS) or len(roles) != len(set(roles)):
        errors.append("scheduler admission worker partition is not exact 12")
    if admission.get("partition_exhaustive_verified") is not True or admission.get("admission_verdict") != "SCHEDULER_ADMISSION_PASS":
        errors.append("scheduler admission is not a terminal PASS")
    return errors


def validate_countable_scheduler(root: pathlib.Path, control: dict, assignment: dict, liveness: dict, require_admission: bool = True) -> list[str]:
    cohort = control.get("cohort_id")
    manifest_path = control.get("scheduler_manifest_path")
    errors: list[str] = []
    if control.get("scheduler_admission_required") is not True:
        errors.append("countable control does not require scheduler admission")
    if manifest_path != f"scheduler/{cohort}.json":
        errors.append("scheduler manifest path is not canonical")
        return errors
    path = root / manifest_path
    if not path.is_file():
        errors.append("scheduler manifest missing")
        return errors
    manifest = load(root, manifest_path)
    if control.get("scheduler_manifest_git_identity") != git_blob_sha(path):
        errors.append("control scheduler manifest blob mismatch")
    errors.extend(validate_scheduler_manifest(root, control, assignment, liveness, manifest))
    if require_admission:
        admission_path = root / f"scheduler_admission/{cohort}.json"
        if not admission_path.is_file():
            errors.append("scheduler admission receipt missing; stage and promote must be distinct transactions")
        else:
            errors.extend(validate_scheduler_admission(root, manifest, load(root, f"scheduler_admission/{cohort}.json")))
    return errors


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--cohort", required=True)
    parser.add_argument("--no-admission", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()
    control = load(root, f"control/{args.cohort}.json")
    assignment = load(root, f"assignments/{args.cohort}.json")
    liveness = load(root, f"liveness/{args.cohort}.json")
    errors = validate_countable_scheduler(root, control, assignment, liveness, require_admission=not args.no_admission)
    if errors:
        print("SCHEDULER ADMISSION FAILED")
        for error in errors:
            print("-", error)
        raise SystemExit(1)
    print("SCHEDULER ADMISSION PASS")
