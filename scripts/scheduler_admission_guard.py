#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import strict_json

PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
WORKERS = ("MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01")
PREACTIVATION_ROLES = WORKERS + ("MF06",)
ROLES = WORKERS + ("MM06","MF06","BIL00")
TZID_TOKEN = "TZID=America/Vancouver"
CANONICAL_HOURLY_SCHEDULE_RE = re.compile(r"^TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE=([0-5][0-9])$")
PREACTIVATION_WAIT = "PREACTIVATION_WAIT"
APPROVED_MAX_ATTEMPT_DURATION_SECONDS = 600
APPROVED_SCHEDULER_JITTER_BUDGET_SECONDS = 60
BEHAVIORAL_PROJECTION = ("task_id","title","prompt_sha256","normalized_schedule","timing_mode","default_timezone","enabled","execution_mode","preactivation_inactive_result")
MUTABLE_RUNTIME_FIELDS = {"last_run_time","updated_at","next_run_time","last_error","last_result"}
FORBIDDEN_PUBLIC_KEY_NAMES = {"worker_auth_secret","worker_auth_secret_hex","raw_auth_material","private_key","raw_key","api_key","access_token","password"}


def candidate_fresh_gate_errors(control: dict, assignment: dict) -> list[str]:
    errors: list[str] = []
    if control.get("calibration_countable") is not True or control.get("fresh_allowed") is not False:
        errors.append("candidate control must be countable and fresh-disabled")
    if assignment.get("calibration_countable") is not True or assignment.get("network_mode") != "GITHUB_BRANCH_CALIBRATION":
        errors.append("candidate assignment must be countable branch calibration")
    if assignment.get("benchmark_program") is not None or assignment.get("benchmark_suite_id") is not None:
        errors.append("candidate assignment must not bind a benchmark before two clean cohorts")
    workers = assignment.get("workers") or {}
    if not isinstance(workers, dict) or set(workers) != set(WORKERS):
        errors.append("candidate assignment worker partition is not exact 12")
        return errors
    for role, row in workers.items():
        if not isinstance(row, dict):
            errors.append(role + " assignment is not an object")
            continue
        if row.get("fresh_allowed") is not False:
            errors.append(role + " assignment authorizes fresh execution")
        for field in ("fresh_scope","private_manifest_id","private_manifest_git_identity","benchmark_program","benchmark_suite_id"):
            if row.get(field) is not None:
                errors.append(role + " assignment must leave " + field + " null/absent")
    return errors


def load(root: pathlib.Path, path: str) -> Any:
    return strict_json.loads((root / path).read_text(encoding="utf-8"))


def scheduler_retry_budget_errors(root: pathlib.Path, manifest: dict) -> list[str]:
    """Bind freshness-window inputs to exact accepted-main values outside C/A/L/S."""
    errors: list[str] = []
    try:
        authority = load(root, "config/scheduler_attestation_authority_v25.json")
    except Exception as exc:
        return ["scheduler retry budget authority unavailable: " + str(exc)]
    approved = {
        "max_attempt_duration_seconds": APPROVED_MAX_ATTEMPT_DURATION_SECONDS,
        "scheduler_jitter_budget_seconds": APPROVED_SCHEDULER_JITTER_BUDGET_SECONDS,
    }
    if authority.get("retry_budget_authority") != "ACCEPTED_MAIN_EXACT_VALUES_CANDIDATE_OVERRIDE_FORBIDDEN":
        errors.append("scheduler retry budget authority mode mismatch")
    for field, exact in approved.items():
        if type(authority.get(field)) is not int or authority.get(field) != exact:
            errors.append("accepted-main scheduler retry budget authority mismatch: " + field)
        if type(manifest.get(field)) is not int or manifest.get(field) != exact:
            errors.append("scheduler manifest retry budget differs from accepted-main exact value: " + field)
    return errors


def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def staged_pointer_blob(root: pathlib.Path, staged: dict | None) -> str | None:
    if not staged:
        return None
    cohort = staged.get("candidate_cohort_id")
    candidates = [root / f"staging/{cohort}.json", root / "state/STAGED.json"]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            if strict_json.loads(path.read_text(encoding="utf-8")) == staged:
                return git_blob_sha(path)
        except Exception:
            continue
    return None


def _git(root: pathlib.Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


def load_scheduler_admission_source(root: pathlib.Path, admission: dict) -> tuple[dict | None, list[str]]:
    """Resolve the declared MM06 source from fetched Git objects, never from copy assertions."""
    errors: list[str] = []
    branch = admission.get("source_preactivation_admission_branch")
    path = admission.get("source_preactivation_admission_path")
    commit = admission.get("source_preactivation_admission_commit_sha")
    blob = admission.get("source_preactivation_admission_blob_sha")
    cohort = admission.get("cohort_id")
    generation_head = admission.get("generation_head_sha")
    if branch != f"ps/preactivate/{cohort}/MM06" or path != f"preactivation/{cohort}/MM06.json":
        return None, ["scheduler admission source branch/path is not canonical"]
    remote_ref = f"refs/remotes/origin/{branch}"
    local_ref = f"refs/heads/{branch}"
    rc_remote, remote_head = _git(root, "rev-parse", "--verify", remote_ref)
    rc_local, local_head = _git(root, "rev-parse", "--verify", local_ref)
    if not ((rc_remote == 0 and remote_head == commit) or (rc_local == 0 and local_head == commit)):
        errors.append("scheduler admission source branch is absent or moved from declared commit")
    rc_commit, resolved_commit = _git(root, "rev-parse", "--verify", f"{commit}^{{commit}}")
    if rc_commit or resolved_commit != commit:
        errors.append("scheduler admission source commit is unavailable")
        return None, errors
    rc_parents, parents = _git(root, "show", "-s", "--format=%P", commit)
    if rc_parents or parents.split() != [generation_head]:
        errors.append("scheduler admission source must be exactly one commit child of generation head")
    rc_paths, changed = _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", f"{commit}^", commit)
    if rc_paths or [row for row in changed.splitlines() if row] != [path]:
        errors.append("scheduler admission source commit must change exactly its declared receipt path")
    rc_blob, observed_blob = _git(root, "rev-parse", f"{commit}:{path}")
    if rc_blob or observed_blob != blob:
        errors.append("scheduler admission source blob does not match declared commit/path")
        return None, errors
    rc_source, raw = _git(root, "show", f"{commit}:{path}")
    if rc_source:
        errors.append("scheduler admission source content is unavailable")
        return None, errors
    try:
        source = strict_json.loads(raw)
    except Exception as exc:
        errors.append("scheduler admission source is not strict JSON: " + str(exc))
        return None, errors
    return source, errors


def validate_preactivation_sources(root: pathlib.Path, manifest: dict, admission: dict, staged: dict | None) -> list[str]:
    """Re-derive the 12 worker plus MF06 receipts from immutable commits and blobs."""
    errors: list[str] = []
    tasks = {row.get("role_id"): row for row in manifest.get("tasks", []) if isinstance(row, dict)}
    pointer_blob = staged_pointer_blob(root, staged)
    authority = load(root, "config/scheduler_attestation_authority_v25.json")
    for row in admission.get("preactivation_results") or []:
        if not isinstance(row, dict):
            continue
        role = row.get("role_id")
        branch = row.get("preactivation_branch")
        path = row.get("preactivation_path")
        commit = row.get("receipt_creation_commit_sha")
        blob = row.get("receipt_blob_sha")
        expected_branch = f"ps/preactivate/{admission.get('cohort_id')}/{role}"
        expected_path = f"preactivation/{admission.get('cohort_id')}/{role}.json"
        if branch != expected_branch or path != expected_path:
            errors.append(f"{role} preactivation source branch/path is not canonical")
            continue
        rc_remote, remote_head = _git(root, "rev-parse", "--verify", f"refs/remotes/origin/{branch}")
        rc_local, local_head = _git(root, "rev-parse", "--verify", f"refs/heads/{branch}")
        if not ((rc_remote == 0 and remote_head == commit) or (rc_local == 0 and local_head == commit)):
            errors.append(f"{role} preactivation source branch is absent or moved")
        rc_parents, parents = _git(root, "show", "-s", "--format=%P", str(commit))
        if rc_parents or parents.split() != [admission.get("generation_head_sha")]:
            errors.append(f"{role} preactivation source is not a sole child of generation head")
        rc_paths, changed = _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", f"{commit}^", str(commit))
        if rc_paths or [item for item in changed.splitlines() if item] != [path]:
            errors.append(f"{role} preactivation source does not add exactly its declared path")
        rc_blob, observed_blob = _git(root, "rev-parse", f"{commit}:{path}")
        if rc_blob or observed_blob != blob:
            errors.append(f"{role} preactivation receipt blob mismatch")
            continue
        rc_receipt, raw = _git(root, "show", f"{commit}:{path}")
        if rc_receipt:
            errors.append(f"{role} preactivation receipt unavailable")
            continue
        try:
            receipt = strict_json.loads(raw)
        except Exception as exc:
            errors.append(f"{role} preactivation receipt is not strict JSON: {exc}")
            continue
        errors.extend(f"{role} preactivation receipt: {message}" for message in schema_errors(root, "schemas/preactivation_receipt.schema.json", receipt))
        task = tasks.get(role) or {}
        expected = {
            "protocol_version": admission.get("protocol_version"),
            "task_network_plan_id": admission.get("task_network_plan_id"),
            "candidate_nonce": admission.get("candidate_nonce"),
            "cohort_id": admission.get("cohort_id"),
            "generation_root_sha": admission.get("generation_root_sha"),
            "generation_head_sha": admission.get("generation_head_sha"),
            "staged_candidate_git_identity": pointer_blob,
            "scheduler_manifest_git_identity": admission.get("scheduler_manifest_git_identity"),
            "role_id": role,
            "scheduler_task_id": task.get("scheduler_task_id"),
            "behavioral_config_sha256": task.get("behavioral_config_sha256"),
            "runtime_state_id": manifest.get("runtime_state_id"),
            "role_auth_scheme": "PS-HMAC-SHA256-PREACTIVATION-RECEIPT-1",
            "role_auth_commitment": (
                task.get("worker_auth_commitment") if role in WORKERS
                else authority.get("mf06_preactivation_key_commitment_sha256")
            ),
            "production_not_before_utc": manifest.get("production_not_before_utc"),
            "normalized_first_production_utc": task.get("normalized_first_production_utc"),
            "production_branch": task.get("production_branch"),
            "production_path": task.get("production_path"),
            "preactivation_branch": branch,
            "preactivation_path": path,
        }
        for key, value in expected.items():
            if receipt.get(key) != value:
                errors.append(f"{role} preactivation receipt semantic mismatch: {key}")
        if receipt.get("challenge_occurrence_utc") not in set(task.get("challenge_occurrences_utc") or []):
            errors.append(f"{role} preactivation receipt challenge is not a frozen scheduled occurrence")
    return errors


def parse_time(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("scheduler/liveness time is not offset-aware")
    return dt.astimezone(timezone.utc)


def parse_utc_occurrence(value: str) -> datetime:
    """Accept only an explicit UTC instant; local wall times are never schedule evidence."""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("scheduler occurrence must be an explicit UTC Z instant")
    return parse_time(value)


def canonical_hourly_minute(schedule: object, registry_minute: object) -> int:
    """Parse the sole normalized schedule grammar and bind it to frozen registry minute."""
    match = CANONICAL_HOURLY_SCHEDULE_RE.fullmatch(str(schedule))
    if match is None:
        raise ValueError("normalized_schedule must equal TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE=MM")
    minute = int(match.group(1))
    if not isinstance(registry_minute, int) or registry_minute != minute:
        raise ValueError("normalized_schedule minute does not equal frozen task registry minute")
    return minute


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> int:
    first = datetime(year, month, 1).weekday()
    return 1 + ((weekday - first) % 7) + 7 * (occurrence - 1)


def _vancouver_transition_utc(year: int) -> tuple[datetime, datetime]:
    """Frozen post-2007 Canada Pacific rule, independent of host tzdata."""
    start_day = _nth_weekday(year, 3, 6, 2)  # second Sunday, 02:00 PST = 10:00Z
    end_day = _nth_weekday(year, 11, 6, 1)   # first Sunday, 02:00 PDT = 09:00Z
    return (
        datetime(year, 3, start_day, 10, tzinfo=timezone.utc),
        datetime(year, 11, end_day, 9, tzinfo=timezone.utc),
    )


def _vancouver_local(instant: datetime) -> tuple[datetime, timedelta]:
    utc = instant.astimezone(timezone.utc)
    start, end = _vancouver_transition_utc(utc.year)
    offset = timedelta(hours=-7 if start <= utc < end else -8)
    return (utc + offset).replace(tzinfo=None), offset


def _ambiguous_vancouver_wall_time(instant: datetime) -> bool:
    local, _ = _vancouver_local(instant)
    return local.month == 11 and local.day == _nth_weekday(local.year, 11, 6, 1) and local.hour == 1


def derive_hourly_occurrences(schedule: object, registry_minute: object, production_not_before: object) -> tuple[datetime, datetime]:
    """Derive the first two UTC occurrences from canonical schedule data, fail-closed at DST ambiguity."""
    minute = canonical_hourly_minute(schedule, registry_minute)
    not_before = parse_utc_occurrence(production_not_before)
    candidate = not_before.replace(second=0, microsecond=0)
    if candidate < not_before:
        candidate += timedelta(minutes=1)
    first = None
    for _ in range(121):
        local, _ = _vancouver_local(candidate)
        if local.minute == minute and local.second == 0 and local.microsecond == 0:
            first = candidate
            break
        candidate += timedelta(minutes=1)
    if first is None:
        raise ValueError("canonical hourly schedule has no next occurrence")
    second = first + timedelta(hours=1)
    second_local, second_offset = _vancouver_local(second)
    first_local, first_offset = _vancouver_local(first)
    if second_local.minute != minute:
        raise ValueError("canonical hourly schedule does not preserve frozen local minute")
    if _ambiguous_vancouver_wall_time(first) or _ambiguous_vancouver_wall_time(second):
        raise ValueError("canonical hourly schedule intersects ambiguous Vancouver DST wall time")
    if first_offset != second_offset:
        raise ValueError("canonical hourly schedule crosses Vancouver DST offset transition")
    return first, second


def _utc_z(instant: datetime) -> str:
    return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def derive_countable_occurrences(
    task_by_role: dict,
    registry_rows: dict,
    lane_rows: dict,
    production_not_before: object,
) -> tuple[dict[str, tuple[datetime, datetime]], dict[str, str]]:
    """Derive worker starts from activation and fan-in starts from causal closure.

    All native tasks remain hourly. Early MM06/MF06/BIL00 wakes are
    heartbeat-only; the first countable occurrence is the first native
    occurrence strictly after its predecessor frontier.
    """
    if set(lane_rows) != set(WORKERS):
        raise ValueError("liveness lane inventory is not exact canonical 12")
    occurrences: dict[str, tuple[datetime, datetime]] = {}
    floors: dict[str, str] = {}
    for role in WORKERS:
        row = task_by_role[role]
        expected = registry_rows[role]
        floors[role] = str(production_not_before)
        occurrences[role] = derive_hourly_occurrences(
            row.get("normalized_schedule"), expected.get("minute"), production_not_before
        )

    predecessor_frontier = max(parse_time(row["deadline_utc"]) for row in lane_rows.values())
    for role in ("MM06", "MF06", "BIL00"):
        # Strictness matters when a deadline lands exactly on a role's minute.
        floor = _utc_z(predecessor_frontier + timedelta(microseconds=1))
        floors[role] = floor
        row = task_by_role[role]
        expected = registry_rows[role]
        occurrences[role] = derive_hourly_occurrences(
            row.get("normalized_schedule"), expected.get("minute"), floor
        )
        predecessor_frontier = occurrences[role][0]
    return occurrences, floors


def validate_canonical_hourly_timing(
    schedule: object,
    registry_minute: object,
    cadence_seconds: object,
    first_value: object,
    second_value: object,
    challenges: object,
    production_not_before: object,
    admission_cutoff: object,
    occurrence_not_before: object | None = None,
) -> list[str]:
    """Validate all timing fields as derived consequences of one unambiguous hourly schedule."""
    errors: list[str] = []
    if cadence_seconds != 3600:
        return ["scheduler cadence must equal exactly 3600 seconds"]
    try:
        not_before = parse_utc_occurrence(production_not_before)
        cutoff = parse_utc_occurrence(admission_cutoff)
        if cutoff >= not_before:
            return ["scheduler admission cutoff must precede production_not_before"]
        first, second = derive_hourly_occurrences(
            schedule,
            registry_minute,
            production_not_before if occurrence_not_before is None else occurrence_not_before,
        )
    except Exception as exc:
        return ["canonical scheduler timing invalid: " + str(exc)]
    try:
        observed_first = parse_utc_occurrence(first_value)
        observed_second = parse_utc_occurrence(second_value)
    except Exception as exc:
        return ["normalized production time invalid: " + str(exc)]
    if observed_first < not_before:
        errors.append("normalized first production occurrence precedes production_not_before")
    if observed_first != first:
        errors.append("normalized first production occurrence differs from canonical schedule derivation")
    if observed_second != second:
        errors.append("normalized second production occurrence differs from canonical schedule derivation")
    if observed_second - observed_first != timedelta(seconds=3600):
        errors.append("normalized retry occurrence does not equal first+3600 seconds")
    if not isinstance(challenges, list) or not challenges:
        errors.append("canonical scheduler requires one or more challenge occurrences")
        return errors
    for challenge_value in challenges:
        try:
            challenge = parse_utc_occurrence(challenge_value)
        except Exception as exc:
            errors.append("invalid challenge occurrence: " + str(exc))
            continue
        if challenge > cutoff:
            errors.append("preactivation challenge occurs after admission_cutoff")
        if challenge >= not_before:
            errors.append("preactivation challenge is not strictly before production_not_before")
        if _ambiguous_vancouver_wall_time(challenge):
            errors.append("preactivation challenge intersects ambiguous Vancouver DST wall time")
            continue
        local, _ = _vancouver_local(challenge)
        first_local, _ = _vancouver_local(first)
        if local.minute != first_local.minute or local.second or local.microsecond:
            errors.append("preactivation challenge does not align with canonical hourly schedule")
            continue
        delta_seconds = (first - challenge).total_seconds()
        if delta_seconds < 0 or delta_seconds % 3600 != 0:
            errors.append("preactivation challenge does not align with canonical hourly schedule")
    return errors


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


def production_allowed(
    current_state: dict,
    manifest: dict,
    now: datetime,
    staged: dict | None = None,
    role_id: str | None = None,
) -> bool:
    """Require exact activation and the role's countable occurrence gate."""
    try:
        expected_g = staged.get("generation_head_sha") if staged else manifest.get("generation_head_sha")
        staged_ok = True if staged is None else (
            staged.get("candidate_cohort_id") == manifest.get("cohort_id")
            and staged.get("candidate_nonce") == manifest.get("candidate_nonce")
            and staged.get("generation_root_sha") == manifest.get("generation_root_sha")
        )
        not_before = manifest["production_not_before_utc"]
        if role_id is not None:
            task = next(
                (
                    row
                    for row in manifest.get("tasks") or []
                    if isinstance(row, dict) and row.get("role_id") == role_id
                ),
                None,
            )
            if task is None:
                return False
            not_before = task["normalized_first_production_utc"]
        return (
            current_state.get("active_cohort_id") == manifest.get("cohort_id")
            and current_state.get("generation_head_sha") == expected_g
            and staged_ok
            and now.astimezone(timezone.utc) >= parse_time(not_before)
        )
    except Exception:
        return False


def validate_production_ref_fence(root: pathlib.Path, manifest: dict, generation_head: str, callback) -> list[str]:
    """Fence source validation between independent reads of all 15 production refs."""
    errors: list[str] = []
    cohort = manifest.get("cohort_id")
    tasks = {row.get("role_id"): row for row in manifest.get("tasks") or [] if isinstance(row, dict)}
    if set(tasks) != set(ROLES) or len(tasks) != 15:
        return ["production ref inventory is not exact canonical 15"]
    branches: list[str] = []
    for role in ROLES:
        if role in WORKERS:
            expected = f"ps/work/{cohort}/{role}"
        elif role == "MM06":
            expected = f"ps/verify/{cohort}"
        elif role == "MF06":
            expected = f"ps/integrate/{cohort}"
        else:
            expected = f"ps/consolidate/{cohort}"
        if (tasks.get(role) or {}).get("production_branch") != expected:
            errors.append("noncanonical production ref: " + role)
        branches.append(expected)
    if len(set(branches)) != 15:
        errors.append("production ref inventory is not one branch per canonical role")

    def refresh() -> None:
        # Real worktrees must refresh immediately before both snapshots; the
        # local-test/data-only roots without Git metadata use their injected
        # resolver and cannot silently stand in for the live production path.
        if not (root / ".git").exists():
            return
        refspecs = [f"+refs/heads/{branch}:refs/remotes/origin/{branch}" for branch in sorted(set(branches))]
        rc, output = _git(root, "fetch", "--no-tags", "origin", *refspecs)
        if rc:
            errors.append("live production ref refresh failed: " + output[-400:])

    refresh()
    before: dict[str, str | None] = {}
    for branch in sorted(set(branches)):
        rc, head = _git(root, "rev-parse", "--verify", f"refs/remotes/origin/{branch}")
        before[branch] = head if rc == 0 else None
        if rc or head != generation_head:
            errors.append("production ref is not generation head: " + branch)

    try:
        callback_errors = callback()
        if callback_errors:
            errors.extend(callback_errors)
    except Exception as exc:
        errors.append("preactivation source rederivation failed: " + str(exc))

    refresh()
    for branch in sorted(set(branches)):
        rc, head = _git(root, "rev-parse", "--verify", f"refs/remotes/origin/{branch}")
        observed = head if rc == 0 else None
        if observed != before.get(branch):
            errors.append("production ref moved during preactivation admission: " + branch)
        elif rc or observed != generation_head:
            # Preserve the initial exact-G failure without mislabelling an
            # already-moved ref as a between-read race.
            continue
    return errors


def validate_scheduler_manifest(root: pathlib.Path, control: dict, assignment: dict, liveness: dict, manifest: dict) -> list[str]:
    errors = schema_errors(root, "schemas/scheduler_manifest.schema.json", manifest)
    errors.extend(candidate_fresh_gate_errors(control, assignment))
    _scan_public(manifest, errors)
    cohort = control.get("cohort_id")
    if manifest.get("protocol_version") != "2.5" or manifest.get("task_network_plan_id") != PLAN:
        errors.append("scheduler manifest protocol/plan mismatch")
    if manifest.get("cohort_id") != cohort or manifest.get("cohort_id") != assignment.get("cohort_id") or manifest.get("cohort_id") != liveness.get("cohort_id"):
        errors.append("scheduler manifest cohort mismatch")
    nonce = manifest.get("candidate_nonce")
    root_sha = manifest.get("generation_root_sha")
    if not nonce or control.get("candidate_nonce") != nonce or assignment.get("candidate_nonce") != nonce or liveness.get("candidate_nonce") != nonce:
        errors.append("root11 candidate nonce chain mismatch")
    if not root_sha or any(value != root_sha for value in (control.get("generation_root_sha"), control.get("control_release_commit_sha"), assignment.get("generation_root_sha"), liveness.get("generation_root_sha"))):
        errors.append("root11 generation root chain mismatch")
    if manifest.get("generation_branch") != assignment.get("generation_branch") or manifest.get("generation_branch") != f"ps/gen/{cohort}":
        errors.append("scheduler manifest generation branch mismatch")
    if "generation_head_sha" in manifest:
        errors.append("scheduler manifest must not contain self-referential generation_head_sha")
    if "scheduler_manifest_git_identity" in control:
        errors.append("root11 control must not contain future scheduler manifest blob")
    if manifest.get("control_manifest_id") != control.get("control_manifest_id"):
        errors.append("scheduler manifest control id mismatch")
    if manifest.get("assignment_id") != assignment.get("assignment_id"):
        errors.append("scheduler manifest assignment id mismatch")
    if manifest.get("control_manifest_git_identity") != git_blob_sha(root / f"control/{cohort}.json"):
        errors.append("scheduler manifest control blob mismatch")
    if assignment.get("control_manifest_git_identity") != manifest.get("control_manifest_git_identity"):
        errors.append("assignment/control blob chain mismatch")
    if manifest.get("assignment_git_identity") != git_blob_sha(root / f"assignments/{cohort}.json") or manifest.get("assignment_git_identity") != liveness.get("assignment_git_identity"):
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

    raw_cadence = manifest.get("scheduler_cadence_seconds")
    raw_attempt = manifest.get("max_attempt_duration_seconds")
    raw_jitter = manifest.get("scheduler_jitter_budget_seconds")
    cadence = raw_cadence if type(raw_cadence) is int else 0
    attempt = raw_attempt if type(raw_attempt) is int else 0
    jitter = raw_jitter if type(raw_jitter) is int else 0
    if cadence != 3600:
        errors.append("scheduler cadence must equal exactly 3600 seconds")
    errors.extend(scheduler_retry_budget_errors(root, manifest))
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
    countable_occurrences: dict[str, tuple[datetime, datetime]] = {}
    occurrence_floors: dict[str, str] = {}
    try:
        countable_occurrences, occurrence_floors = derive_countable_occurrences(
            task_by_role, registry_rows, lane_rows, manifest.get("production_not_before_utc")
        )
    except Exception as exc:
        errors.append("countable scheduler occurrence derivation failed: " + str(exc))
    for role in ROLES:
        row = task_by_role.get(role) or {}
        expected = registry_rows.get(role) or {}
        if row.get("scheduler_task_id") != expected.get("scheduler_task_id"):
            errors.append(role + " canonical scheduler task id mismatch")
        if row.get("canonical_title") != expected.get("title"):
            errors.append(role + " canonical title/task session mismatch")
        if row.get("default_timezone") != "America/Vancouver":
            errors.append(role + " normalized scheduler timezone is not explicit Vancouver TZID")
        if row.get("timing_mode") != "exact_schedule" or row.get("enabled") is not True:
            errors.append(role + " scheduler task is not enabled exact_schedule")
        if row.get("execution_mode") != "SAFE_REPLAY_ONLY":
            errors.append(role + " countable scheduler execution mode is not SAFE_REPLAY_ONLY")
        if row.get("preactivation_inactive_result") != PREACTIVATION_WAIT:
            errors.append(role + " preactivation inactive result is not PREACTIVATION_WAIT")
        if row.get("preactivation_branch") != f"ps/preactivate/{cohort}/{role}":
            errors.append(role + " preactivation branch mismatch")
        if row.get("preactivation_path") != f"preactivation/{cohort}/{role}.json":
            errors.append(role + " preactivation path mismatch")
        timing_errors = validate_canonical_hourly_timing(
            row.get("normalized_schedule"), expected.get("minute"), cadence,
            row.get("normalized_first_production_utc"), row.get("normalized_second_production_utc"),
            row.get("challenge_occurrences_utc"), manifest.get("production_not_before_utc"),
            manifest.get("admission_cutoff_utc"),
            occurrence_floors.get(role, manifest.get("production_not_before_utc")),
        )
        errors.extend(role + " " + message for message in timing_errors)
        try:
            if role in countable_occurrences:
                first, second = countable_occurrences[role]
            else:
                first, second = derive_hourly_occurrences(
                    row.get("normalized_schedule"),
                    expected.get("minute"),
                    manifest.get("production_not_before_utc"),
                )
        except Exception as exc:
            errors.append(role + " canonical scheduler timing invalid: " + str(exc))
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


def validate_mm06_scheduler_admission(
    root: pathlib.Path,
    manifest: dict,
    admission: dict,
    staged: dict | None = None,
    observed_manifest_blob: str | None = None,
    require_inactive_production_fence: bool = False,
    expected_generation_head: str | None = None,
) -> list[str]:
    errors = schema_errors(root, "schemas/scheduler_admission.schema.json", admission)
    actual_candidate_head = expected_generation_head
    if actual_candidate_head is None or admission.get("generation_head_sha") != actual_candidate_head:
        errors.append("MM06 scheduler admission generation head does not match independently supplied expected generation head")
    _scan_public(admission, errors)
    for key in ("protocol_version","task_network_plan_id","candidate_nonce","cohort_id","generation_root_sha"):
        if admission.get(key) != manifest.get(key):errors.append("MM06 scheduler admission/manifest mismatch: " + key)
    if observed_manifest_blob is None:
        manifest_path = root / f"scheduler/{manifest['cohort_id']}.json"
        observed_manifest_blob = git_blob_sha(manifest_path) if manifest_path.is_file() else None
    manifest_blob = observed_manifest_blob
    if manifest_blob is None:
        errors.append("independently observed scheduler manifest blob is unavailable")
    if admission.get("scheduler_manifest_git_identity") != manifest_blob:errors.append("MM06 scheduler admission is not bound to exact scheduler manifest blob")
    if staged:
        for source_key, pointer_key in (("candidate_nonce","candidate_nonce"),("cohort_id","candidate_cohort_id"),("generation_root_sha","generation_root_sha"),("generation_head_sha","generation_head_sha"),("scheduler_manifest_git_identity","scheduler_manifest_git_identity")):
            if admission.get(source_key) != staged.get(pointer_key):errors.append("MM06 scheduler admission/staged pointer mismatch: " + source_key)
        if admission.get("staged_candidate_git_identity") != staged_pointer_blob(root, staged):errors.append("MM06 scheduler admission staged pointer blob mismatch")
    results = admission.get("preactivation_results") or []
    roles = [row.get("role_id") for row in results if isinstance(row, dict)]
    if len(results) != 13 or set(roles) != set(PREACTIVATION_ROLES) or len(roles) != len(set(roles)):
        errors.append("scheduler admission preactivation partition is not exact 12 workers plus MF06")
    if admission.get("partition_exhaustive_verified") is not True or admission.get("admission_verdict") != "SCHEDULER_ADMISSION_PASS":
        errors.append("scheduler admission is not a terminal PASS")
    tasks = {row.get("role_id"): row for row in manifest.get("tasks") or [] if isinstance(row, dict)}
    if admission.get("mm06_challenge_occurrence_utc") not in set((tasks.get("MM06") or {}).get("challenge_occurrences_utc") or []):
        errors.append("MM06 scheduler admission challenge is not a frozen scheduled occurrence")
    if require_inactive_production_fence:
        errors.extend(validate_production_ref_fence(
            root,
            manifest,
            admission.get("generation_head_sha"),
            lambda: validate_preactivation_sources(root, manifest, admission, staged),
        ))
    else:
        # The exact-G production fence is a transition invariant, not a durable
        # active-state invariant.  Once promoted, workers are expected to
        # advance their production refs.  The immutable preactivation sources
        # and their HMAC/schema bindings remain mandatory in both phases.
        errors.extend(validate_preactivation_sources(root, manifest, admission, staged))
    return errors


def validate_scheduler_admission(
    root: pathlib.Path,
    manifest: dict,
    admission: dict,
    staged: dict | None = None,
    source: dict | None = None,
    observed_manifest_blob: str | None = None,
    require_inactive_production_fence: bool = False,
    expected_generation_head: str | None = None,
) -> list[str]:
    """Validate the create-once main envelope; it is intentionally not the MM06 source bytes."""
    errors = schema_errors(root, "schemas/scheduler_admission_copy.schema.json", admission)
    actual_candidate_head = expected_generation_head
    if actual_candidate_head is None or admission.get("generation_head_sha") != actual_candidate_head:
        errors.append("scheduler admission copy generation head does not match independently supplied expected generation head")
    _scan_public(admission, errors)
    for key in ("protocol_version","task_network_plan_id","candidate_nonce","cohort_id","generation_root_sha"):
        if admission.get(key) != manifest.get(key):errors.append("scheduler admission copy/manifest mismatch: " + key)
    if observed_manifest_blob is None:
        manifest_path = root / f"scheduler/{manifest.get('cohort_id')}.json"
        observed_manifest_blob = git_blob_sha(manifest_path) if manifest_path.is_file() else None
    if observed_manifest_blob is None:
        errors.append("independently observed scheduler manifest blob is unavailable")
    elif admission.get("scheduler_manifest_git_identity") != observed_manifest_blob:
        errors.append("scheduler admission copy is not bound to independently observed scheduler manifest blob")
    if staged:
        for copy_key, pointer_key in (("candidate_nonce","candidate_nonce"),("cohort_id","candidate_cohort_id"),("generation_root_sha","generation_root_sha"),("generation_head_sha","generation_head_sha"),("scheduler_manifest_git_identity","scheduler_manifest_git_identity")):
            if admission.get(copy_key) != staged.get(pointer_key):errors.append("scheduler admission copy/staged pointer mismatch: " + copy_key)
        if admission.get("staged_candidate_git_identity") != staged_pointer_blob(root, staged):errors.append("scheduler admission copy staged pointer blob mismatch")
    if source is not None:
        errors.extend(validate_mm06_scheduler_admission(
            root,
            manifest,
            source,
            staged,
            observed_manifest_blob=observed_manifest_blob,
            require_inactive_production_fence=require_inactive_production_fence,
            expected_generation_head=expected_generation_head,
        ))
        for key in ("protocol_version","task_network_plan_id","candidate_nonce","cohort_id","generation_root_sha","generation_head_sha","staged_candidate_git_identity","scheduler_manifest_git_identity","admission_verdict"):
            if admission.get(key) != source.get(key):errors.append("scheduler admission copy/MM06 source semantic mismatch: " + key)
        if admission.get("source_schema_version") != source.get("schema_version"):errors.append("scheduler admission copy source schema mismatch")
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
    root11 = bool(control.get("candidate_nonce") or control.get("generation_root_sha"))
    if root11 and "scheduler_manifest_git_identity" in control:errors.append("root11 control contains forbidden future scheduler blob")
    elif not root11 and control.get("scheduler_manifest_git_identity") != git_blob_sha(path):errors.append("control scheduler manifest blob mismatch")
    errors.extend(validate_scheduler_manifest(root, control, assignment, liveness, manifest))
    if require_admission:
        admission_path = root / f"scheduler_admission/{cohort}.json"
        if not admission_path.is_file():
            errors.append("scheduler admission receipt missing; stage and promote must be distinct transactions")
        else:
            staged_rel = "state/STAGED.json"
            state_path = root / "state/CURRENT.json"
            if state_path.is_file():
                current = load(root, "state/CURRENT.json")
                archived = current.get("active_staged_candidate_path")
                if archived and current.get("active_cohort_id") == cohort:
                    staged_rel = archived
            staged_path = root / staged_rel
            staged = load(root, staged_rel) if staged_path.is_file() else None
            admission = load(root, f"scheduler_admission/{cohort}.json")
            source, source_errors = load_scheduler_admission_source(root, admission)
            errors.extend(source_errors)
            errors.extend(validate_scheduler_admission(root, manifest, admission, staged=staged, source=source, observed_manifest_blob=git_blob_sha(path), expected_generation_head=staged.get("generation_head_sha") if staged else None))
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
