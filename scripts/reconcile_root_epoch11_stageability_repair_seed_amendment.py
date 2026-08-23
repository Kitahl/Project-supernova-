#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import collections
import datetime
import os
import pathlib
import re
import shutil
import tempfile
import time


ROOT = pathlib.Path.cwd().resolve()
POLICY_PATH = "config/root_epoch11_stageability_repair_seed_amendment_v25.json"
ORIGINAL_POLICY_PATH = "config/root_epoch11_stageability_repair_seed_v25.json"
ORIGINAL_SCRIPT_PATH = ROOT / "scripts" / "reconcile_root_epoch11_stageability_repair_seed.py"
GITHUB_UTC_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)


def load_original_seed():
    spec = importlib.util.spec_from_file_location("trusted_root11_stageability_seed", ORIGINAL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("accepted root11 seed module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_run_binding_errors(source_run: dict, jobs: dict, pr: dict, trusted: str, policy: dict, source_attempt: int) -> list[str]:
    expected = policy["source_workflow"]
    errors: list[str] = []
    if source_run.get("name") != expected["name"]:
        errors.append("source workflow name mismatch")
    if source_run.get("path") != expected["path"]:
        errors.append("source workflow path mismatch")
    if source_run.get("event") != expected["event"]:
        errors.append("source workflow event mismatch")
    if source_run.get("status") != expected["status"] or source_run.get("conclusion") != expected["conclusion"]:
        errors.append("source workflow did not complete with the expected fail-closed result")
    if source_attempt <= 0 or source_run.get("run_attempt") != source_attempt:
        errors.append("source workflow run attempt mismatch")
    if expected.get("run_attempt_required_from_event") is not True:
        errors.append("source workflow policy does not require event-bound run attempt")
    pr_head = pr.get("head") or {}
    if source_run.get("head_sha") != pr_head.get("sha") or source_run.get("head_branch") != pr_head.get("ref"):
        errors.append("source workflow top-level head is not bound to the exact PR candidate")

    run_prs = source_run.get("pull_requests") or []
    if len(run_prs) != 1:
        errors.append("source workflow must identify exactly one pull request")
    else:
        run_pr = run_prs[0]
        if run_pr.get("number") != pr.get("number"):
            errors.append("source workflow pull request number mismatch")
        if (run_pr.get("head") or {}).get("sha") != (pr.get("head") or {}).get("sha"):
            errors.append("source workflow candidate head moved")
        if (run_pr.get("base") or {}).get("sha") != trusted or (pr.get("base") or {}).get("sha") != trusted:
            errors.append("source workflow candidate base moved")

    rows = jobs.get("jobs") or []
    by_name = {row.get("name"): row for row in rows if isinstance(row, dict)}
    candidate = by_name.get(expected["candidate_job"])
    writer = by_name.get(expected["trusted_job"])
    if not candidate or candidate.get("conclusion") != expected["candidate_job_conclusion"]:
        errors.append("source candidate diagnostics were not successful")
    if not writer or writer.get("conclusion") != expected["trusted_job_conclusion"]:
        errors.append("source trusted seed did not fail closed")
    return errors


def source_attempt_jobs(seed, source_run_id: int, source_attempt: int, policy: dict) -> dict:
    endpoint = policy["source_workflow"]["attempt_jobs_endpoint"].format(
        run_id=source_run_id,
        run_attempt=source_attempt,
    )
    return seed.api(endpoint + "?per_page=100")


def parse_github_utc_timestamp(value: object) -> datetime.datetime | None:
    if not isinstance(value, str) or not GITHUB_UTC_TIMESTAMP.fullmatch(value):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != datetime.timedelta(0):
        return None
    return parsed.astimezone(datetime.timezone.utc)


def incomplete_earlier_same_head_runs(workflow_runs: list[dict], candidate_head: str, amendment_created_at: str) -> list[int]:
    cutoff = parse_github_utc_timestamp(amendment_created_at)
    if cutoff is None:
        raise ValueError("amendment run created_at is not a valid GitHub UTC timestamp")
    pending: list[int] = []
    for run in workflow_runs:
        if not isinstance(run, dict) or run.get("event") != "pull_request_target":
            continue
        if run.get("head_sha") != candidate_head:
            continue
        created_at = parse_github_utc_timestamp(run.get("created_at"))
        if created_at is None:
            raise ValueError("inventory run created_at is not a valid GitHub UTC timestamp")
        if created_at > cutoff:
            continue
        if run.get("status") != "completed" and isinstance(run.get("id"), int):
            pending.append(run["id"])
    return sorted(pending)


def exact_head_pull_request_target_inventory(seed, candidate_head: str, policy: dict) -> tuple[bool, list[dict], str]:
    expected_contract = {
        "event": "pull_request_target",
        "head_sha_filter_required": True,
        "per_page": 100,
        "maximum_exact_head_results": 1000,
        "completeness_rule": "FULLY_PAGINATE_EXACT_HEAD_RESULTS_OR_FAIL_CLOSED",
    }
    if policy.get("earlier_run_inventory") != expected_contract:
        return False, [], "exact-head pull_request_target inventory policy mismatch"
    if not isinstance(candidate_head, str) or not seed.HEX40.fullmatch(candidate_head):
        return False, [], "exact-head pull_request_target inventory requires a 40-hex candidate head"

    per_page = expected_contract["per_page"]
    maximum = expected_contract["maximum_exact_head_results"]
    rows: list[dict] = []
    seen_ids: set[int] = set()
    expected_total: int | None = None
    for page in range(1, maximum // per_page + 1):
        payload = seed.api(
            f"/actions/runs?event=pull_request_target&head_sha={candidate_head}&per_page={per_page}&page={page}"
        )
        if not isinstance(payload, dict):
            return False, [], "exact-head pull_request_target inventory response is malformed"
        total = payload.get("total_count")
        batch = payload.get("workflow_runs")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0 or not isinstance(batch, list) or len(batch) > per_page:
            return False, [], "exact-head pull_request_target inventory response is malformed"
        if total >= maximum:
            return False, [], "exact-head pull_request_target run inventory reached fail-closed 1000-result bound"
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            return False, [], "exact-head pull_request_target run inventory changed during pagination"
        for run in batch:
            if not isinstance(run, dict):
                return False, [], "exact-head pull_request_target inventory contains a malformed run"
            if run.get("event") != expected_contract["event"] or run.get("head_sha") != candidate_head:
                return False, [], "server-filtered pull_request_target inventory returned a wrong-event or wrong-head run"
            if parse_github_utc_timestamp(run.get("created_at")) is None or not isinstance(run.get("status"), str):
                return False, [], "exact-head pull_request_target inventory run lacks ordering or status evidence"
            run_id = run.get("id")
            if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id in seen_ids:
                return False, [], "exact-head pull_request_target inventory contains a missing or duplicate run id"
            seen_ids.add(run_id)
            rows.append(run)
        if len(batch) < per_page:
            if len(rows) != expected_total:
                return False, [], "exact-head pull_request_target run inventory is incomplete"
            return True, rows, ""
    return False, [], "exact-head pull_request_target run inventory exceeded fail-closed pagination bound"


def wait_for_earlier_same_head_runs(seed, candidate_head: str, amendment_run_id: int, policy: dict) -> tuple[bool, str]:
    amendment_run = seed.api(f"/actions/runs/{amendment_run_id}")
    cutoff = amendment_run.get("created_at")
    if amendment_run.get("event") != "workflow_run" or parse_github_utc_timestamp(cutoff) is None:
        return False, "current amendment workflow provenance is unavailable"
    for _ in range(60):
        ok, rows, reason = exact_head_pull_request_target_inventory(seed, candidate_head, policy)
        if not ok:
            return False, reason
        try:
            pending = incomplete_earlier_same_head_runs(rows, candidate_head, cutoff)
        except ValueError as exc:
            return False, str(exc)
        if not pending:
            return True, ""
        time.sleep(5)
    return False, "earlier same-head pull_request_target writers did not complete before timeout"


def accepted_amendment_installation(trusted: str, policy: dict, seed, original_policy: dict) -> tuple[bool, str]:
    seed_install = policy["required_amendment_base_main_sha"]
    amendment_install = policy.get("original_amendment_install_commit_sha")
    if not isinstance(amendment_install, str) or not seed.HEX40.fullmatch(amendment_install):
        return False, "original amendment install commit binding is invalid"
    expected_followup_paths = [
        POLICY_PATH,
        "scripts/reconcile_root_epoch11_stageability_repair_seed_amendment.py",
        "tests/test_root_epoch11_stageability_repair_seed_amendment.py",
    ]
    if policy.get("followup_paths") != expected_followup_paths:
        return False, "pagination follow-up path contract is not exact"
    if set(policy.get("original_amendment_paths", {})) != set(policy.get("amendment_paths", [])):
        return False, "original amendment installation blob map is not exact"

    if seed.run(["git", "merge-base", "--is-ancestor", seed_install, amendment_install])[0] != 0:
        return False, "original amendment does not descend from exact accepted root11 seed commit"
    rc, first_parent = seed.run(["git", "rev-parse", amendment_install + "^1"])
    if rc or first_parent.strip() != seed_install:
        return False, "original amendment was not the immediate next first-parent transaction"
    rc, count = seed.run(["git", "rev-list", "--count", "--first-parent", seed_install + ".." + amendment_install])
    if rc or count.strip() != "1":
        return False, "original amendment was not the next accepted-main transaction"
    rc, changed = seed.run(["git", "diff", "--name-only", seed_install + "..." + amendment_install])
    if rc or set(changed.splitlines()) != set(policy["amendment_paths"]):
        return False, "accepted original amendment was not the exact four-path transaction"
    for path, expected_blob in policy["original_amendment_paths"].items():
        if seed.blob_at(amendment_install, path) != expected_blob:
            return False, "original amendment install blob mismatch: " + path

    if seed.run(["git", "merge-base", "--is-ancestor", amendment_install, trusted])[0] != 0:
        return False, "pagination follow-up does not descend from exact original amendment install"
    rc, first_parent = seed.run(["git", "rev-parse", trusted + "^1"])
    if rc or first_parent.strip() != amendment_install:
        return False, "pagination follow-up is not the immediate next first-parent transaction"
    rc, count = seed.run(["git", "rev-list", "--count", "--first-parent", amendment_install + ".." + trusted])
    if rc or count.strip() != "1":
        return False, "pagination follow-up is not the next accepted-main transaction"
    rc, changed = seed.run(["git", "diff", "--name-only", amendment_install + "..." + trusted])
    if rc or set(changed.splitlines()) != set(expected_followup_paths):
        return False, "accepted main since original amendment is not the exact three-path pagination follow-up"
    for path, expected_blob in policy["original_amendment_paths"].items():
        if path not in expected_followup_paths and seed.blob_at("HEAD", path) != expected_blob:
            return False, "preserved original amendment path changed: " + path

    checkpoints = [seed_install, amendment_install, "HEAD"]
    for path, expected_blob in policy["original_seed_paths"].items():
        if any(seed.blob_at(ref, path) != expected_blob for ref in checkpoints):
            return False, "original root11 seed path changed across protected transactions: " + path
    if any(seed.blob_at(ref, seed.ROOT_TCB_PATH) != policy["required_current_root_epoch_blob"] for ref in checkpoints):
        return False, "accepted root10 blob changed across protected transactions"
    if any(seed.blob_at(ref, seed.STATE_PATH) != policy["required_state_blob"] for ref in checkpoints):
        return False, "accepted Gen12 state changed across protected transactions"
    for path, expected_blob in original_policy["frozen_root10_paths"].items():
        if any(seed.blob_at(ref, path) != expected_blob for ref in checkpoints):
            return False, "frozen root10 path changed during pagination follow-up: " + path
    original_reconciler = (ROOT / "scripts" / "reconcile_root_epoch11_stageability_repair_seed.py").read_text(encoding="utf-8")
    defect = policy["known_defect"]
    if defect["corrected_marker_schema_version"] not in original_reconciler:
        return False, "accepted original seed no longer contains the exact diagnosed schema expectation"
    return True, ""


def exact_amended_nonroot_candidate(tmp: pathlib.Path, policy: dict, seed, original_policy: dict) -> tuple[bool, str]:
    root_tcb_path = seed.ROOT_TCB_PATH
    required = set(original_policy["required_root_candidate_paths"])
    pinned = policy.get("expected_root_candidate_blobs")
    if (
        policy.get("candidate_path_count") != len(required)
        or not isinstance(pinned, dict)
        or set(pinned) != required - {root_tcb_path}
        or len(pinned) != len(required) - 1
    ):
        return False, "amendment policy does not explicitly pin the exact 68 non-root candidate blobs"
    for path, expected_blob in pinned.items():
        if not isinstance(expected_blob, str) or not seed.HEX40.fullmatch(expected_blob):
            return False, "amendment policy contains an invalid candidate blob pin: " + path
        if seed.blob_at("HEAD", path, cwd=tmp) != expected_blob:
            return False, "candidate blob does not match amended accepted-main pin: " + path
    return True, ""


def exact_amended_candidate(tmp: pathlib.Path, trusted: str, policy: dict, seed, original_policy: dict) -> tuple[bool, str]:
    ok, reason = exact_amended_nonroot_candidate(tmp, policy, seed, original_policy)
    if not ok:
        return ok, reason

    root_tcb_path = seed.ROOT_TCB_PATH
    root_tcb = seed.load(tmp, root_tcb_path)
    original_seed_bindings = {
        "root_epoch11_stageability_repair_seed_install_commit_sha": policy["original_seed_install_commit_sha"],
        "root_epoch11_stageability_repair_seed_policy_blob": policy["original_seed_paths"][ORIGINAL_POLICY_PATH],
        "root_epoch11_stageability_repair_seed_reconciler_blob": policy["original_seed_paths"]["scripts/reconcile_root_epoch11_stageability_repair_seed.py"],
        "root_epoch11_stageability_repair_seed_workflow_blob": policy["original_seed_paths"][".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml"],
    }
    for key, expected in original_seed_bindings.items():
        if root_tcb.get(key) != expected:
            return False, "candidate changed literal first-seed provenance " + key
    dynamic = policy["root_tcb_dynamic_amendment_bindings"]
    actual_dynamic = {
        "root_epoch11_stageability_repair_seed_amendment_install_commit_sha": policy["original_amendment_install_commit_sha"],
        "root_epoch11_stageability_repair_seed_amendment_policy_blob": seed.blob_at("HEAD", policy["amendment_paths"][0]),
        "root_epoch11_stageability_repair_seed_amendment_reconciler_blob": seed.blob_at("HEAD", policy["amendment_paths"][1]),
        "root_epoch11_stageability_repair_seed_amendment_workflow_blob": seed.blob_at("HEAD", policy["amendment_paths"][2]),
    }
    if set(dynamic) != set(actual_dynamic) or len(set(dynamic.values())) != 4:
        return False, "amendment dynamic root-TCB binding specification is not exact"
    for key, expected in actual_dynamic.items():
        if not isinstance(root_tcb.get(key), str) or not seed.HEX40.fullmatch(root_tcb[key]) or root_tcb.get(key) != expected:
            return False, "candidate root-TCB amendment binding mismatch " + key
    normalized = dict(root_tcb)
    for key, sentinel in dynamic.items():
        normalized[key] = sentinel
    if seed.canonical_sha256(normalized) != policy["expected_normalized_root_tcb_sha256"]:
        return False, "candidate root TCB differs outside the four amendment install bindings"
    return True, ""


def _candidate_nonce_condition(schema: dict, required: set[str], forbidden: set[str] | None = None) -> bool:
    branches = schema.get("allOf")
    if not isinstance(branches, list) or len(branches) != 1 or not isinstance(branches[0], dict):
        return False
    branch = branches[0]
    condition = branch.get("if") or {}
    then = branch.get("then") or {}
    if condition.get("required") != ["candidate_nonce"] or set(then.get("required") or []) != required:
        return False
    if forbidden is None:
        return "not" not in then
    return set((then.get("not") or {}).get("required") or []) == forbidden


def stronger_rederived_contract_errors(tmp: pathlib.Path, policy: dict, seed, original_policy: dict) -> list[str]:
    """Prove the exact stronger contracts replacing the frozen seed's stale literal predicates."""
    errors: list[str] = []
    marker = seed.load(tmp, policy["known_defect"]["marker_path"])
    marker_expected = {
        "schema_version": policy["known_defect"]["corrected_marker_schema_version"],
        "active_source_cohort": policy["required_active_cohort"],
        "active_source_generation_head": policy["required_generation_head"],
        "active_source_state_blob": policy["required_state_blob"],
        "active_source_partition": policy["required_active_source_partition"],
        "active_source_immutable": True,
        "calibration_credit_effect": 0,
        "calibration_streak_effect": 0,
        "fresh_allowed": False,
    }
    if any(marker.get(key) != value for key, value in marker_expected.items()):
        errors.append("root11 marker does not bind the exact immutable active-source zero-credit state")
    if any(key in marker for key in ("source_cohort", "source_generation_head", "source_verifier_head", "source_mf06_head", "fresh_science_effect", "runtime_effect")):
        errors.append("root11 marker introduces redundant stale aliases instead of binding the active source")

    countable = (seed.load(tmp, "config/generation_delta_policy_v25.json").get("countable") or {})
    if not (
        countable.get("exact_path_templates") == original_policy["candidate_construction_order"]
        and countable.get("exact_cardinality") == 4
        and countable.get("commit_shape") == "EXACTLY_ONE_COMMIT_WITH_SOLE_PARENT_GENERATION_ROOT"
        and countable.get("artifact_identity_dag") == "CONTROL_TO_ASSIGNMENT_TO_LIVENESS_TO_SCHEDULER"
        and "construction_order" not in countable
    ):
        errors.append("generation delta does not freeze the exact ordered single-commit C/A/L/S DAG")

    control = seed.load(tmp, "schemas/control.schema.json")
    properties = set((control.get("properties") or {}).keys())
    globally_required = set(control.get("required") or [])
    root11_required = {
        "candidate_nonce", "generation_root_sha", "expected_base_head",
        "scheduler_manifest_path", "scheduler_admission_required",
    }
    if not (
        root11_required | {"scheduler_manifest_git_identity"} <= properties
        and globally_required.isdisjoint({"candidate_nonce", "generation_root_sha", "scheduler_manifest_path", "scheduler_admission_required", "scheduler_manifest_git_identity"})
        and _candidate_nonce_condition(control, root11_required, {"scheduler_manifest_git_identity"})
    ):
        errors.append("control schema does not preserve legacy fields while enforcing the exact root11 no-back-edge conditional")

    staged = seed.load(tmp, "schemas/staged_candidate.schema.json")
    staged_required = set(staged.get("required") or [])
    staged_properties = set((staged.get("properties") or {}).keys())
    if not ("candidate_cohort_id" in staged_required and "candidate_cohort_id" in staged_properties and "cohort_id" not in staged_required and "cohort_id" not in staged_properties):
        errors.append("staged pointer does not use the unambiguous candidate_cohort_id contract")

    semantics = seed.load(tmp, "config/task_registry_semantics_v25.json")
    if semantics.get("stage_admit_promote_rule") != "POINTER_ONLY_STAGE_THEN_CREATE_ONCE_ADMISSION_THEN_LATER_BIL00_PROMOTION_WITH_ADMISSION_ALREADY_IN_BASE_UNCHANGED":
        errors.append("task semantics do not freeze the stronger later BIL00 promotion lifecycle")

    reconciler = (tmp / "scripts/reconcile_branch_statuses.py").read_text(encoding="utf-8")
    generation_proofs = (
        'remote_head(repo, str(branch)) != generation_head',
        'one_commit_child(repo, str(generation_head), str(generation_root))',
        'changed_name_status(repo, str(generation_root), str(generation_head))',
        '"worktree", "add", "--detach", str(tmp), generation_head',
        'TRUSTED_ROOT / "scripts/scheduler_admission_guard.py"',
        '"--no-admission"',
    )
    if any(token not in reconciler for token in generation_proofs):
        errors.append("trusted branch generation writer lacks an independently derived exact-G construction fence")

    guard = (tmp / "scripts/scheduler_admission_guard.py").read_text(encoding="utf-8").lower()
    open_prs = (tmp / "scripts/reconcile_open_prs.py").read_text(encoding="utf-8")
    expected_head_proofs = (
        "actual_candidate_head = expected_generation_head",
        'admission.get("generation_head_sha") != actual_candidate_head',
        'expected_generation_head=staged.get("generation_head_sha") if staged else none',
    )
    if (
        any(token not in guard for token in expected_head_proofs)
        or guard.count('admission.get("generation_head_sha") != actual_candidate_head') != 2
        or open_prs.count("expected_generation_head=") != 3
        or 'expected_generation_head=pointer.get("generation_head_sha")' not in open_prs
        or 'expected_generation_head=archived.get("generation_head_sha")' not in open_prs
        or any('expected_generation_head=' + owner + '.get' in open_prs for owner in ("admission", "copy", "source"))
    ):
        errors.append("scheduler admission source/copy G is not fenced by independently supplied pointer/state generation G at every production caller")

    source_schema = seed.load(tmp, "schemas/scheduler_admission.schema.json")
    copy_schema = seed.load(tmp, "schemas/scheduler_admission_copy.schema.json")
    source_properties = set((source_schema.get("properties") or {}).keys())
    copy_required = set(copy_schema.get("required") or [])
    source_fields = {"source_preactivation_admission_commit_sha", "source_preactivation_admission_blob_sha"}
    sha_patterns = {
        (source_schema.get("properties") or {}).get("generation_head_sha", {}).get("pattern"),
        (copy_schema.get("properties") or {}).get("source_preactivation_admission_blob_sha", {}).get("pattern"),
    }
    if not (
        source_fields.isdisjoint(source_properties)
        and source_fields <= copy_required
        and source_schema.get("title") != copy_schema.get("title")
        and copy_schema.get("additionalProperties") is False
        and "scheduler admission copy/mm06 source semantic mismatch" in guard
        and not any(token in guard for token in ("byte_identical", "source_bytes == copy_bytes", "source_raw == copy_raw"))
        and sha_patterns == {"^[0-9a-f]{40}$"}
    ):
        errors.append("scheduler source/copy schemas or guard do not enforce distinct semantic envelopes with exact Git identities")
    return errors


def root11_schema_condition_errors(tmp: pathlib.Path, seed) -> list[str]:
    errors: list[str] = []
    for path in ("schemas/assignment.schema.json", "schemas/cohort_liveness_contract.schema.json"):
        schema = seed.load(tmp, path)
        if "generation_root_sha" in set(schema.get("required") or []):
            errors.append(path + " globally requires generation_root_sha")
        if not _candidate_nonce_condition(schema, {"generation_root_sha"}):
            errors.append(path + " does not conditionally require generation_root_sha when candidate_nonce is present")
    return errors


def corrected_candidate_semantics(tmp: pathlib.Path, policy: dict, seed, original_policy: dict) -> tuple[bool, str]:
    original_problems = seed.candidate_semantics(tmp, policy["original_seed_install_commit_sha"], original_policy)
    expected_conflicts = policy.get("expected_frozen_semantic_conflicts")
    if not isinstance(expected_conflicts, list) or collections.Counter(original_problems) != collections.Counter(expected_conflicts):
        return False, "candidate frozen-semantic conflict multiset differs from the exact reviewed contradiction set: " + repr(original_problems[:2])
    problems = stronger_rederived_contract_errors(tmp, policy, seed, original_policy)
    problems.extend(root11_schema_condition_errors(tmp, seed))
    if problems:
        return False, "corrected candidate still fails frozen/rederived seed semantics: " + repr(problems[:2])
    marker_path = policy["known_defect"]["marker_path"]
    if seed.blob_at("HEAD", marker_path, cwd=tmp) != policy["known_defect"]["corrected_marker_blob"]:
        return False, "candidate marker is not the exact corrected blob pinned by the amendment"
    marker = seed.load(tmp, marker_path)
    if marker.get("schema_version") != policy["known_defect"]["corrected_marker_schema_version"]:
        return False, "candidate marker does not carry the original seed's exact required schema version"
    amendment_paths = set(policy["amendment_paths"])
    countable = set(seed.load(tmp, "config/countable_control_set_v25.json").get("required_control_paths") or [])
    if not amendment_paths.issubset(countable):
        return False, "candidate countable control does not durably freeze all four amendment paths"
    authority = seed.load(tmp, "config/admission_authority.json")
    authority_paths = set()
    for key in ("trusted_validator_entrypoints", "authoritative_status_workflows", "trusted_authority_helpers"):
        authority_paths.update(authority.get(key) or [])
    if not amendment_paths.issubset(authority_paths):
        return False, "candidate admission authority does not inventory all four amendment paths"
    bootstrap_text = (tmp / "scripts/reconcile_authority_bootstrap.py").read_text(encoding="utf-8")
    if any(bootstrap_text.count(repr(path)) < 2 and bootstrap_text.count('"' + path + '"') < 2 for path in amendment_paths):
        return False, "candidate bootstrap does not freeze each amendment path as static and required installed"
    return True, ""


def decline(reason: str) -> int:
    print("ROOT EPOCH11 SEED AMENDMENT DECLINED: " + reason)
    return 1


def fail_bound(seed, sha: str, reason: str, policy: dict) -> int:
    if isinstance(sha, str) and seed.HEX40.fullmatch(sha):
        for context in [policy["seed_context"], *policy["required_status_contexts"]]:
            seed.post(sha, context, "failure", "root11 seed amendment refused: " + reason)
    print("ROOT EPOCH11 SEED AMENDMENT REFUSED: " + reason)
    return 1


def main():
    seed = load_original_seed()
    policy = seed.load(ROOT, POLICY_PATH)
    original_policy = seed.load(ROOT, ORIGINAL_POLICY_PATH)
    try:
        source_run_id = int(os.environ.get("SOURCE_WORKFLOW_RUN_ID", "0"))
        source_attempt = int(os.environ.get("SOURCE_WORKFLOW_RUN_ATTEMPT", "0"))
        amendment_run_id = int(os.environ.get("GITHUB_RUN_ID", "0"))
        diagnosed_pr_number = int(os.environ.get("DIAGNOSED_PR_NUMBER", "0"))
    except ValueError:
        return decline("workflow run or PR identity is malformed")
    diagnosed_head = os.environ.get("DIAGNOSED_HEAD_SHA")
    diagnosed_base = os.environ.get("DIAGNOSED_BASE_SHA")
    if source_run_id <= 0 or source_attempt <= 0 or amendment_run_id <= 0 or diagnosed_pr_number <= 0:
        return decline("workflow run or PR identity is unavailable")
    diagnostics_result = os.environ.get("CANDIDATE_DIAGNOSTICS_RESULT")

    source_run = seed.api(f"/actions/runs/{source_run_id}")
    jobs = source_attempt_jobs(seed, source_run_id, source_attempt, policy)
    run_prs = source_run.get("pull_requests") or []
    if len(run_prs) != 1 or run_prs[0].get("number") != diagnosed_pr_number:
        return decline("stale source workflow PR identity")
    pr = seed.api(f"/pulls/{diagnosed_pr_number}")
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    sha = head.get("sha")
    if sha != diagnosed_head or base.get("sha") != diagnosed_base:
        return decline("candidate head or base moved after read-only diagnostics")

    rc, out = seed.run(["git", "rev-parse", "HEAD"])
    trusted = out.strip()
    if rc or not seed.HEX40.fullmatch(trusted):
        return decline("trusted accepted-main head is unavailable")
    source_errors = source_run_binding_errors(source_run, jobs, pr, trusted, policy, source_attempt)
    if source_errors:
        return decline(source_errors[0])
    live_main = seed.api("/git/ref/heads/main")
    if (live_main.get("object") or {}).get("sha") != trusted:
        return decline("accepted main moved after source workflow completion")
    if diagnostics_result != "success":
        return fail_bound(seed, sha, "read-only candidate diagnostics did not succeed", policy)
    if base.get("ref") != policy["base_branch_required"] or (head.get("repo") or {}).get("full_name") != seed.REPO or (pr.get("user") or {}).get("login") != seed.OWNER:
        return fail_bound(seed, sha, "same-repository owner PR to main required", policy)
    if not str(head.get("ref", "")).startswith(policy["head_prefix_required"]):
        return fail_bound(seed, sha, "head prefix not root-epoch11 eligible", policy)

    ok, reason = accepted_amendment_installation(trusted, policy, seed, original_policy)
    if not ok:
        return fail_bound(seed, sha, reason, policy)
    if seed.blob_at("HEAD", ORIGINAL_POLICY_PATH) != policy["original_seed_paths"][ORIGINAL_POLICY_PATH]:
        return fail_bound(seed, sha, "accepted original root11 policy blob mismatch", policy)
    if original_policy.get("required_status_contexts") != policy["required_status_contexts"]:
        return fail_bound(seed, sha, "amendment does not preserve the original required contexts", policy)

    state = seed.load(ROOT, seed.STATE_PATH)
    if state.get("active_cohort_id") != policy["required_active_cohort"] or state.get("generation_head_sha") != policy["required_generation_head"]:
        return fail_bound(seed, sha, "amendment only applies while exact Gen12 is canonical", policy)
    if state.get("calibration_streak") != policy["calibration_streak_required"] or state.get("fresh_allowed_globally") is not policy["fresh_allowed_globally_required"]:
        return fail_bound(seed, sha, "Gen12 streak/fresh binding changed", policy)
    current_epoch = seed.load(ROOT, seed.ROOT_TCB_PATH)
    if current_epoch.get("epoch") != policy["required_current_root_epoch"]:
        return fail_bound(seed, sha, "one-shot amendment is inert outside root epoch10", policy)
    if (ROOT / policy["one_shot_marker_path"]).exists():
        return fail_bound(seed, sha, "root epoch11 stageability marker already exists", policy)
    ok, reason = seed.exact_gen12_terminal_chain(original_policy)
    if not ok:
        return fail_bound(seed, sha, reason, policy)

    if seed.run(["git", "cat-file", "-e", str(sha) + "^{commit}"])[0] != 0:
        return fail_bound(seed, sha, "exact candidate head was not fetched by trusted workflow", policy)
    if seed.run(["git", "merge-base", "--is-ancestor", trusted, sha])[0] != 0:
        return fail_bound(seed, sha, "candidate does not descend from exact amendment install head", policy)
    rc, changed_text = seed.run(["git", "diff", "--name-only", trusted + "..." + sha])
    changed = [line for line in changed_text.splitlines() if line]
    required = set(original_policy["required_root_candidate_paths"])
    if rc or set(changed) != required:
        return fail_bound(seed, sha, "root candidate diff is not the exact original pinned 69-path repair", policy)
    protected_seed_paths = set(policy["original_seed_paths"]) | set(policy["amendment_paths"])
    if protected_seed_paths.intersection(changed):
        return fail_bound(seed, sha, "original seed or amendment self-modification forbidden", policy)
    for prefix in original_policy["forbidden_candidate_prefixes"]:
        if any(path.startswith(prefix) for path in changed):
            return fail_bound(seed, sha, "forbidden state/evidence/runtime/scientific path changed", policy)
    for path in changed:
        rc, tree = seed.run(["git", "ls-tree", sha, "--", path])
        fields = tree.strip().split(None, 2)
        if rc or len(fields) < 2 or fields[0] != "100644" or fields[1] != "blob":
            return fail_bound(seed, sha, "non-regular or missing changed path " + path, policy)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-root11-seed-amendment-"))
    try:
        rc, output = seed.run(["git", "worktree", "add", "--detach", str(tmp), sha])
        if rc:
            return fail_bound(seed, sha, "cannot create candidate data worktree: " + output[-500:], policy)
        if seed.blob_at("HEAD", seed.STATE_PATH, cwd=tmp) != policy["required_state_blob"] or seed.load(tmp, seed.STATE_PATH) != state:
            return fail_bound(seed, sha, "canonical Gen12 state changed in root11 candidate", policy)
        for path, expected_blob in original_policy["frozen_root10_paths"].items():
            if seed.blob_at("HEAD", path, cwd=tmp) != expected_blob:
                return fail_bound(seed, sha, "candidate changed frozen root10 seed path " + path, policy)
        plan = seed.load(tmp, "plan/PLAN.json")
        if plan.get("task_network_plan_id") != seed.PLAN or plan.get("protocol_version") != "2.5" or plan.get("specification_revision") != 4:
            return fail_bound(seed, sha, "plan/protocol/revision drift", policy)
        ok, reason = exact_amended_candidate(tmp, trusted, policy, seed, original_policy)
        if not ok:
            return fail_bound(seed, sha, reason, policy)
        ok, reason = corrected_candidate_semantics(tmp, policy, seed, original_policy)
        if not ok:
            return fail_bound(seed, sha, reason, policy)
    finally:
        seed.run(["git", "worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)

    ok, reason = wait_for_earlier_same_head_runs(seed, sha, amendment_run_id, policy)
    if not ok:
        return fail_bound(seed, sha, reason, policy)
    final_pr = seed.api(f"/pulls/{diagnosed_pr_number}")
    final_main = seed.api("/git/ref/heads/main")
    if (final_pr.get("head") or {}).get("sha") != sha or (final_pr.get("base") or {}).get("sha") != trusted:
        return decline("candidate moved during trusted amendment validation")
    if (final_main.get("object") or {}).get("sha") != trusted:
        return decline("accepted main moved during trusted amendment validation")
    final_source = seed.api(f"/actions/runs/{source_run_id}")
    final_jobs = source_attempt_jobs(seed, source_run_id, source_attempt, policy)
    if source_run_binding_errors(final_source, final_jobs, final_pr, trusted, policy, source_attempt):
        return decline("source workflow provenance changed during amendment validation")
    for context in [policy["seed_context"], *policy["required_status_contexts"]]:
        seed.post(sha, context, "success", "trusted root11 seed-completeness amendment PASS")
    print("ROOT EPOCH11 STAGEABILITY-REPAIR SEED-COMPLETENESS AMENDMENT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
