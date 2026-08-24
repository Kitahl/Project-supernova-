#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path.cwd().resolve()
REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/" + REPO
OWNER = REPO.split("/", 1)[0]
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
POLICY_PATH = "config/root_epoch11_stageability_repair_seed_v25.json"
RECEIPT_CONTEXT = "supernova/root-epoch11-stageability-repair-seed"
STATE_PATH = "state/CURRENT.json"
ROOT_TCB_PATH = "config/root_tcb_epoch_v25.json"
ACTIONS_CREATOR = "github-actions[bot]"
WORKERS = {"MF01", "MF02", "MF03", "MF04", "MF05", "MM01", "MM02", "MM03", "MM04", "MM05", "MM07", "EXT01"}
ROLES = WORKERS | {"MM06", "MF06", "BIL00"}


def _reject_constant(value: str):
    raise ValueError("non-finite JSON constant forbidden: " + value)


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON object key forbidden: " + key)
        out[key] = value
    return out


def strict_loads(text: str):
    return json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_unique_pairs)


def load(root: pathlib.Path, path: str):
    return strict_loads((root / path).read_text(encoding="utf-8"))


def api(path: str, method: str = "GET", data=None):
    payload = None if data is None else json.dumps(data, allow_nan=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(API + path, data=payload, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        return strict_loads(raw.decode("utf-8")) if raw else None


def run(cmd, cwd=ROOT, env=None, timeout=1200):
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        return 124, out + "\ncommand timed out"


def blob_at(ref: str, path: str, cwd=ROOT):
    rc, out = run(["git", "rev-parse", f"{ref}:{path}"], cwd=cwd)
    return out.strip() if rc == 0 else None


def canonical_sha256(value) -> str:
    raw = json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def exact_pinned_candidate(tmp: pathlib.Path, trusted: str, policy: dict):
    required = set(policy["required_root_candidate_paths"])
    pinned = policy.get("expected_root_candidate_blobs")
    if not isinstance(pinned, dict) or set(pinned) != required - {ROOT_TCB_PATH} or len(pinned) != len(required) - 1:
        return False, "seed does not pin every non-dynamic root candidate blob"
    for path, expected in pinned.items():
        if not isinstance(expected, str) or not HEX40.fullmatch(expected):
            return False, "invalid pinned candidate blob for " + path
        if blob_at("HEAD", path, cwd=tmp) != expected:
            return False, "candidate blob does not match accepted-main pin: " + path

    bindings = policy.get("root_tcb_dynamic_seed_bindings")
    if not isinstance(bindings, dict) or len(bindings) != 4 or len(set(bindings.values())) != 4:
        return False, "root TCB dynamic binding specification is not exact"
    actual_bindings = {
        "root_epoch11_stageability_repair_seed_install_commit_sha": trusted,
        "root_epoch11_stageability_repair_seed_policy_blob": blob_at("HEAD", policy["seed_paths"][0]),
        "root_epoch11_stageability_repair_seed_reconciler_blob": blob_at("HEAD", policy["seed_paths"][1]),
        "root_epoch11_stageability_repair_seed_workflow_blob": blob_at("HEAD", policy["seed_paths"][2]),
    }
    if set(bindings) != set(actual_bindings) or any(not isinstance(v, str) or not v for v in bindings.values()):
        return False, "root TCB dynamic binding names/sentinels are not exact"
    root_tcb = load(tmp, ROOT_TCB_PATH)
    for key, expected in actual_bindings.items():
        if root_tcb.get(key) != expected:
            return False, "root TCB trusted seed binding mismatch " + key
    normalized = dict(root_tcb)
    for key, sentinel in bindings.items():
        normalized[key] = sentinel
    expected_digest = policy.get("expected_normalized_root_tcb_sha256")
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        return False, "normalized root TCB digest pin is invalid"
    if canonical_sha256(normalized) != expected_digest:
        return False, "root TCB differs outside its four trusted seed bindings"
    return True, ""


def post(sha: str, context: str, state: str, description: str):
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    body = {"state": state, "context": context, "description": description[:140]}
    if run_id.isdigit():
        body["target_url"] = f"https://github.com/{REPO}/actions/runs/{run_id}"
    api("/statuses/" + sha, "POST", body)


def fail(sha, reason: str, policy: dict):
    if isinstance(sha, str) and HEX40.fullmatch(sha):
        post(sha, RECEIPT_CONTEXT, "failure", "epoch11 stageability seed refused: " + reason)
    print("ROOT EPOCH11 STAGEABILITY-REPAIR SEED REFUSED:", reason)
    return 1


def branch_head(branch: str):
    try:
        obj = api("/branches/" + urllib.parse.quote(branch, safe=""))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    return ((obj or {}).get("commit") or {}).get("sha")


def content(path: str, ref: str):
    obj = api("/contents/" + urllib.parse.quote(path, safe="/") + "?ref=" + urllib.parse.quote(ref, safe=""))
    if not isinstance(obj, dict) or obj.get("type") != "file":
        raise RuntimeError(path + " is not a file")
    raw = base64.b64decode(obj["content"]).decode("utf-8")
    return obj, strict_loads(raw)


def observed_actions_success(sha: str, context: str):
    rows = api("/commits/" + sha + "/statuses?per_page=100") or []
    matches = [row for row in rows if row.get("context") == context]
    if not matches:
        return False
    latest = matches[0]
    return (
        latest.get("state") == "success"
        and (latest.get("creator") or {}).get("login") == ACTIONS_CREATOR
        and latest.get("target_url") is None
    )


def exact_gen12_terminal_chain(policy: dict):
    cohort = policy["required_active_cohort"]
    generation = policy["required_generation_head"]
    verifier_head = branch_head("ps/verify/" + cohort)
    if verifier_head != policy["required_verifier_head"]:
        return False, "terminal Gen12 verifier head mismatch"
    try:
        verifier_meta, verifier = content("verification/" + cohort + ".json", verifier_head)
    except Exception as exc:
        return False, "terminal Gen12 verifier unreadable: " + repr(exc)
    if verifier_meta.get("sha") != policy["required_verifier_blob"]:
        return False, "terminal Gen12 verifier blob mismatch"
    expected_verifier = {
        "cohort_id": cohort,
        "generation_head_sha": generation,
        "verdict": "INCOMPLETE",
        "calibration_pass": False,
        "partition_exhaustive_verified": True,
        "liveness_complete": False,
    }
    for key, value in expected_verifier.items():
        if verifier.get(key) != value:
            return False, "terminal Gen12 verifier mismatch " + key
    if verifier.get("safe_report_refs") != [] or verifier.get("quarantined_report_refs") != []:
        return False, "terminal Gen12 verifier must preserve 0 SAFE / 0 quarantined"
    if set(verifier.get("missing_workers") or []) != WORKERS:
        return False, "terminal Gen12 verifier must preserve exact 12 MISSING"
    for context in policy["required_verifier_statuses"]:
        if not observed_actions_success(verifier_head, context):
            return False, "terminal Gen12 observed Actions status mismatch: " + context

    integration_head = branch_head("ps/integrate/" + cohort)
    if integration_head != policy["required_mf06_head"]:
        return False, "terminal Gen12 MF06 head mismatch"
    try:
        integration_meta, integration = content("integration/" + cohort + ".json", integration_head)
    except Exception as exc:
        return False, "terminal Gen12 MF06 receipt unreadable: " + repr(exc)
    if integration_meta.get("sha") != policy["required_mf06_blob"]:
        return False, "terminal Gen12 MF06 blob mismatch"
    expected_integration = {
        "cohort_id": cohort,
        "generation_head_sha": generation,
        "verification_head_sha": verifier_head,
        "verification_verdict": "INCOMPLETE",
        "verification_partition_exhaustive": True,
        "verification_liveness_complete": False,
        "calibration_pass": False,
    }
    for key, value in expected_integration.items():
        if integration.get(key) != value:
            return False, "terminal Gen12 MF06 mismatch " + key
    if integration.get("safe_report_refs") != [] or integration.get("quarantines") != []:
        return False, "terminal Gen12 MF06 must preserve 0 SAFE / 0 quarantined"
    if set(integration.get("missing_workers") or []) != WORKERS:
        return False, "terminal Gen12 MF06 must preserve exact 12 MISSING"
    effects = integration.get("costs_regressions_unknowns") or {}
    if effects.get("calibration_credit") != 0:
        return False, "terminal Gen12 MF06 calibration credit is not zero"
    if not observed_actions_success(integration_head, policy["required_mf06_status"]):
        return False, "terminal Gen12 observed branch-integrate status mismatch"
    return True, ""


def accepted_seed_installation(trusted: str, policy: dict):
    anchor = policy["required_seed_base_main_sha"]
    if run(["git", "merge-base", "--is-ancestor", anchor, trusted])[0] != 0:
        return False, "seed install does not descend from exact audited main"
    rc, out = run(["git", "diff", "--name-only", anchor + "..." + trusted])
    if rc or set(out.splitlines()) != set(policy["seed_paths"]):
        return False, "accepted main since audited anchor is not exact four-path seed installation"
    if blob_at("HEAD", "config/root_tcb_epoch_v25.json") != policy["required_current_root_epoch_blob"]:
        return False, "accepted root10 blob changed"
    if blob_at("HEAD", STATE_PATH) != policy["required_state_blob"]:
        return False, "accepted Gen12 state blob changed"
    for path, expected_blob in policy["frozen_root10_paths"].items():
        if blob_at("HEAD", path) != expected_blob:
            return False, "frozen root10 seed path changed: " + path
    return True, ""


def candidate_semantics(tmp: pathlib.Path, trusted: str, policy: dict):
    problems = []
    epoch = load(tmp, "config/root_tcb_epoch_v25.json")
    if epoch.get("epoch") != 11 or epoch.get("schema_version") != "PS-ROOT-TCB-EPOCH-2.5-11":
        problems.append("root epoch did not migrate to 11")
    if epoch.get("previous_epoch_blob") != policy["required_current_root_epoch_blob"]:
        problems.append("root11 does not bind exact accepted root10 blob")
    for key, value in policy["frozen_root10_anchors"].items():
        if epoch.get(key) != value:
            problems.append("root11 lost frozen root10 anchor " + key)
    seed_bindings = {
        "root_epoch11_stageability_repair_seed_install_commit_sha": trusted,
        "root_epoch11_stageability_repair_seed_policy_blob": blob_at("HEAD", policy["seed_paths"][0]),
        "root_epoch11_stageability_repair_seed_reconciler_blob": blob_at("HEAD", policy["seed_paths"][1]),
        "root_epoch11_stageability_repair_seed_workflow_blob": blob_at("HEAD", policy["seed_paths"][2]),
    }
    for key, value in seed_bindings.items():
        if epoch.get(key) != value:
            problems.append("root11 seed binding mismatch " + key)

    marker = load(tmp, policy["one_shot_marker_path"])
    marker_expected = {
        "schema_version": "PS-ROOT-EPOCH11-STAGEABILITY-REPAIR-EPOCH-2.5-1",
        "protocol_version": "2.5",
        "task_network_plan_id": PLAN,
        "previous_root_epoch": 10,
        "new_root_epoch": 11,
        "source_cohort": policy["required_active_cohort"],
        "source_generation_head": policy["required_generation_head"],
        "source_verifier_head": policy["required_verifier_head"],
        "source_mf06_head": policy["required_mf06_head"],
        "issue_ref": "#233",
        "calibration_credit_effect": 0,
        "fresh_science_effect": "NONE",
        "runtime_effect": "NONE",
    }
    for key, value in marker_expected.items():
        if marker.get(key) != value:
            problems.append("root11 marker mismatch " + key)

    delta = load(tmp, "config/generation_delta_policy_v25.json")
    countable = delta.get("countable") or {}
    order = policy["candidate_construction_order"]
    if countable.get("exact_cardinality") != 4 or countable.get("exact_path_templates") != order:
        problems.append("countable candidate is not exact ordered four-path C->A->L->S DAG")
    if countable.get("construction_order") != order:
        problems.append("countable policy does not machine-freeze construction order")

    assignment_schema = load(tmp, "schemas/assignment.schema.json")
    liveness_schema = load(tmp, "schemas/cohort_liveness_contract.schema.json")
    manifest_schema = load(tmp, "schemas/scheduler_manifest.schema.json")
    control_schema = load(tmp, "schemas/control.schema.json")
    for name, schema in (("assignment", assignment_schema), ("liveness", liveness_schema)):
        required = set(schema.get("required") or [])
        properties = set((schema.get("properties") or {}).keys())
        if "generation_root_sha" not in properties:
            problems.append(name + " schema does not define non-self-referential generation_root_sha")
        if "generation_root_sha" in required:
            problems.append(name + " schema globally requires root11 field and breaks frozen Gen12 compatibility")
        if "generation_head_sha" in required or "generation_head_sha" in properties:
            problems.append(name + " schema still embeds final generation head")
    manifest_required = set(manifest_schema.get("required") or [])
    manifest_properties = set((manifest_schema.get("properties") or {}).keys())
    for field in ("generation_root_sha", "candidate_nonce", "generation_branch", "control_manifest_git_identity", "assignment_git_identity", "liveness_git_identity"):
        if field not in manifest_required:
            problems.append("scheduler manifest does not require DAG binding " + field)
    if "generation_head_sha" in manifest_required or "generation_head_sha" in manifest_properties:
        problems.append("scheduler manifest still embeds final generation head")
    control_required = set(control_schema.get("required") or [])
    control_properties = set((control_schema.get("properties") or {}).keys())
    if "scheduler_manifest_path" not in control_required or "scheduler_admission_required" not in control_required:
        problems.append("control does not require scheduler path/admission")
    if "scheduler_manifest_git_identity" in control_required or "scheduler_manifest_git_identity" in control_properties:
        problems.append("control retains forbidden control-to-scheduler blob back-edge")

    staged_schema = load(tmp, "schemas/staged_candidate.schema.json")
    if staged_schema.get("title") != "PS-STAGED-CANDIDATE-2.5-1" or staged_schema.get("additionalProperties") is not False:
        problems.append("state/STAGED schema is not the closed root11 contract")
    staged_required = set(staged_schema.get("required") or [])
    for field in ("cohort_id", "generation_head_sha", "generation_branch", "scheduler_manifest_path", "scheduler_manifest_git_identity"):
        if field not in staged_required:
            problems.append("state/STAGED schema missing " + field)

    source_admission_schema = load(tmp, "schemas/scheduler_admission.schema.json")
    source_properties = set((source_admission_schema.get("properties") or {}).keys())
    for field in ("source_preactivation_admission_commit_sha", "source_preactivation_admission_blob_sha"):
        if field in source_properties or field in set(source_admission_schema.get("required") or []):
            problems.append("MM06 source admission receipt retains self-reference " + field)
    copy_schema = load(tmp, "schemas/scheduler_admission_copy.schema.json")
    if copy_schema.get("title") != "PS-SCHEDULER-ADMISSION-COPY-2.5-1" or copy_schema.get("additionalProperties") is not False:
        problems.append("scheduler admission main-copy envelope is not the closed root11 contract")
    copy_required = set(copy_schema.get("required") or [])
    for field in ("cohort_id", "generation_head_sha", "source_preactivation_admission_branch", "source_preactivation_admission_commit_sha", "source_preactivation_admission_blob_sha"):
        if field not in copy_required:
            problems.append("scheduler admission copy envelope missing " + field)

    guard = (tmp / "scripts/scheduler_admission_guard.py").read_text(encoding="utf-8")
    for token in ("generation_root_sha", "candidate_nonce", "actual_candidate_head", "validate_scheduler_admission", "PREACTIVATION_WAIT"):
        if token not in guard:
            problems.append("scheduler admission guard missing " + token)
    for forbidden in (
        'manifest.get("generation_head_sha") != assignment.get',
        'manifest.get("generation_head_sha") != liveness.get',
    ):
        if forbidden in guard:
            problems.append("scheduler pre-stage guard retains final-G self-reference")

    required_pointer_consumers = (
        "branch/CONFIG.json",
        "scripts/reconcile_branch_statuses.py",
        "scripts/reconcile_open_prs.py",
        "scripts/reconcile_v25_admission.py",
        "scripts/transition_guard.py",
    )
    for path in required_pointer_consumers:
        if "state/STAGED.json" not in (tmp / path).read_text(encoding="utf-8"):
            problems.append(path + " does not consume fixed main-readable state/STAGED.json")
    transition = (tmp / "scripts/transition_guard.py").read_text(encoding="utf-8")
    for token in ("validate_scheduler_admission", "generation_head_sha", "STAGED"):
        if token not in transition:
            problems.append("transition guard missing post-G admission token " + token)
    for token in ("scheduler_admission/", "promotion", "expected_base_head"):
        if token.lower() not in transition.lower():
            problems.append("transition guard missing create-once/later-main promotion invariant " + token)
    admission_reconciler = (tmp / "scripts/reconcile_v25_admission.py").read_text(encoding="utf-8")
    for token in ("scheduler_admission_copy.schema.json", "source_preactivation_admission_commit_sha", "source_preactivation_admission_blob_sha", "supernova/report-admission"):
        if token not in admission_reconciler:
            problems.append("trusted admission reconciler missing source/copy binding token " + token)
    for forbidden in ("byte_identical", "source_bytes == copy_bytes", "source_raw == copy_raw"):
        if forbidden in admission_reconciler.lower():
            problems.append("trusted admission reconciler incorrectly requires byte-identical source/copy")

    branch_workflow = (tmp / ".github/workflows/supernova-branch-reconciler.yml").read_text(encoding="utf-8")
    reconciler = (tmp / "scripts/reconcile_branch_statuses.py").read_text(encoding="utf-8")
    branch_validator = (tmp / "scripts/validate_branch_bus_v251.py").read_text(encoding="utf-8")
    for token in ("statuses: write", "persist-credentials: false", "scripts/reconcile_branch_statuses.py"):
        if token not in branch_workflow:
            problems.append("authoritative branch reconciler workflow missing " + token)
    for token in ("TRUSTED_ROOT", "state/STAGED.json", "supernova/branch-generation", "validate_branch_bus_v251.py"):
        if token not in reconciler:
            problems.append("accepted-main structural reconciler missing " + token)
    if "SUPERNOVA_VALIDATE_ROOT" not in reconciler or "SUPERNOVA_VALIDATE_ROOT" not in branch_validator:
        problems.append("accepted-main branch validator cannot operate on a separate candidate data root")
    if "GITHUB_TOKEN" in branch_validator:
        problems.append("candidate data validator must not consume the status-write token")

    registry = load(tmp, "config/task_registry_v25.json")
    role_ids = [row.get("role_id") for row in registry.get("tasks", []) if isinstance(row, dict)]
    if registry.get("active_task_count") != 15 or registry.get("no_sixteenth_lane") is not True:
        problems.append("task registry does not preserve exact 15/no-16th-lane")
    if len(role_ids) != 15 or set(role_ids) != ROLES or len(set(role_ids)) != 15:
        problems.append("task registry role partition is not exact canonical 15")
    semantics = json.dumps(load(tmp, "config/task_registry_semantics_v25.json"), sort_keys=True, allow_nan=False)
    for token in ("PREACTIVATION", "MM06", "LATER_PROMOTE", "SAME_TASK_SESSION"):
        if token not in semantics:
            problems.append("task registry semantics missing " + token)

    construction_test = (tmp / "tests/test_scheduler_admission_construction.py").read_text(encoding="utf-8")
    for token in ("git", "--no-admission", "generation_root_sha", "generation_head_sha"):
        if token not in construction_test:
            problems.append("construction regression missing executable token " + token)
    negative_test = (tmp / "tests/test_scheduler_admission_negative.py").read_text(encoding="utf-8")
    for token in ("wrong", "generation_head_sha", "placeholder"):
        if token.lower() not in negative_test.lower():
            problems.append("scheduler negative tests missing " + token)
    staged_test = (tmp / "tests/test_staged_candidate_admission.py").read_text(encoding="utf-8")
    for token in ("source_preactivation_admission_commit_sha", "source_preactivation_admission_blob_sha", "not byte", "semantic"):
        if token.lower() not in staged_test.lower():
            problems.append("staged admission tests missing source/copy regression " + token)

    authority = load(tmp, "config/admission_authority.json")
    if authority.get("root_tcb_epoch") != 11:
        problems.append("admission authority root epoch != 11")
    inventory = set(authority.get("authoritative_status_workflows") or []) | set(authority.get("trusted_authority_helpers") or []) | set(authority.get("trusted_validator_entrypoints") or [])
    for path in (policy["seed_paths"][0], policy["seed_paths"][1], policy["seed_paths"][2], policy["one_shot_marker_path"], "schemas/staged_candidate.schema.json", "schemas/scheduler_admission_copy.schema.json"):
        if path not in inventory:
            problems.append("admission authority inventory missing " + path)
    bootstrap = load(tmp, "config/authority_bootstrap_v25.json")
    if bootstrap.get("root_tcb_epoch_required") != 11:
        problems.append("authority bootstrap did not migrate to root epoch11")
    return problems


def main():
    policy = load(ROOT, POLICY_PATH)
    try:
        number = int(os.environ.get("PR_NUMBER", "0"))
    except ValueError:
        number = 0
    if number <= 0:
        return 1
    pr = api(f"/pulls/{number}")
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    sha = head.get("sha")
    if os.environ.get("CANDIDATE_DIAGNOSTICS_RESULT") != "success":
        return fail(sha, "read-only candidate diagnostics did not succeed", policy)
    if sha != os.environ.get("DIAGNOSED_HEAD_SHA") or base.get("sha") != os.environ.get("DIAGNOSED_BASE_SHA"):
        return fail(sha, "diagnosed head/base no longer match PR", policy)
    rc, out = run(["git", "rev-parse", "HEAD"])
    trusted = out.strip()
    if rc or trusted != base.get("sha"):
        return fail(sha, "diagnosed base is not exact accepted main", policy)
    if base.get("ref") != policy["base_branch_required"] or (head.get("repo") or {}).get("full_name") != REPO or (pr.get("user") or {}).get("login") != OWNER:
        return fail(sha, "same-repository owner PR to main required", policy)
    if not str(head.get("ref", "")).startswith(policy["head_prefix_required"]):
        return fail(sha, "head prefix not root-epoch11 eligible", policy)

    ok, reason = accepted_seed_installation(trusted, policy)
    if not ok:
        return fail(sha, reason, policy)
    state = load(ROOT, STATE_PATH)
    if state.get("active_cohort_id") != policy["required_active_cohort"] or state.get("generation_head_sha") != policy["required_generation_head"]:
        return fail(sha, "seed only applies while exact Gen12 is canonical", policy)
    if state.get("calibration_streak") != 0 or state.get("fresh_allowed_globally") is not False:
        return fail(sha, "Gen12 streak must remain zero and fresh disabled", policy)
    current_epoch = load(ROOT, "config/root_tcb_epoch_v25.json")
    if current_epoch.get("epoch") != policy["required_current_root_epoch"]:
        return fail(sha, "one-shot seed is inert outside root epoch10", policy)
    for key, value in policy["frozen_root10_anchors"].items():
        if current_epoch.get(key) != value:
            return fail(sha, "accepted root10 anchor mismatch " + key, policy)
    if (ROOT / policy["one_shot_marker_path"]).exists():
        return fail(sha, "root epoch11 stageability marker already exists", policy)
    ok, reason = exact_gen12_terminal_chain(policy)
    if not ok:
        return fail(sha, reason, policy)

    if run(["git", "cat-file", "-e", str(sha) + "^{commit}"])[0] != 0:
        return fail(sha, "exact candidate head was not fetched by trusted workflow", policy)
    if run(["git", "merge-base", "--is-ancestor", trusted, sha])[0] != 0:
        return fail(sha, "candidate does not descend from exact accepted main", policy)
    rc, out = run(["git", "diff", "--name-only", trusted + "..." + sha])
    changed = [line for line in out.splitlines() if line]
    required = set(policy["required_root_candidate_paths"])
    if rc or set(changed) != required:
        return fail(sha, "root candidate diff is not exact required stageability repair set", policy)
    if set(policy["seed_paths"]).intersection(changed):
        return fail(sha, "seed self-modification forbidden", policy)
    for prefix in policy["forbidden_candidate_prefixes"]:
        if any(path.startswith(prefix) for path in changed):
            return fail(sha, "forbidden state/evidence/runtime/scientific path changed", policy)
    for path in changed:
        rc, tree = run(["git", "ls-tree", sha, "--", path])
        fields = tree.strip().split(None, 2)
        if rc or len(fields) < 2 or fields[0] != "100644" or fields[1] != "blob":
            return fail(sha, "non-regular or missing changed path " + path, policy)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-root-epoch11-stageability-seed-"))
    try:
        rc, output = run(["git", "worktree", "add", "--detach", str(tmp), sha])
        if rc:
            return fail(sha, "cannot create candidate data worktree: " + output[-500:], policy)
        if blob_at("HEAD", STATE_PATH, cwd=tmp) != policy["required_state_blob"] or load(tmp, STATE_PATH) != state:
            return fail(sha, "canonical Gen12 state changed in root11 candidate", policy)
        for path, expected_blob in policy["frozen_root10_paths"].items():
            if blob_at("HEAD", path, cwd=tmp) != expected_blob:
                return fail(sha, "candidate changed frozen root10 seed path " + path, policy)
        plan = load(tmp, "plan/PLAN.json")
        if plan.get("task_network_plan_id") != PLAN or plan.get("protocol_version") != "2.5" or plan.get("specification_revision") != 4:
            return fail(sha, "plan/protocol/revision drift", policy)
        ok, reason = exact_pinned_candidate(tmp, trusted, policy)
        if not ok:
            return fail(sha, reason, policy)
        problems = candidate_semantics(tmp, trusted, policy)
        if problems:
            return fail(sha, problems[0], policy)
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = ""
        commands = (
            ["python", "scripts/validate_bus.py"],
            ["python", "-m", "unittest", "tests.test_scheduler_admission_construction"],
            ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        )
        for cmd in commands:
            rc, output = run(cmd, cwd=tmp, env=env)
            if rc:
                return fail(sha, "candidate diagnostics failed: " + output[-1000:], policy)
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)

    post(sha, RECEIPT_CONTEXT, "success", "trusted root epoch11 stageability seed PASS")
    print("ROOT EPOCH11 STAGEABILITY-REPAIR SEED PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
