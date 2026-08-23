#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import os
import pathlib
import re
import shutil
import tempfile


ROOT = pathlib.Path.cwd().resolve()
POLICY_PATH = "config/root_epoch11_readme_lineage_seed_v25.json"
ORIGINAL_POLICY_PATH = "config/root_epoch11_stageability_repair_seed_v25.json"
AMENDMENT_POLICY_PATH = "config/root_epoch11_stageability_repair_seed_amendment_v25.json"
ORIGINAL_SCRIPT_PATH = ROOT / "scripts/reconcile_root_epoch11_stageability_repair_seed.py"
AMENDMENT_SCRIPT_PATH = ROOT / "scripts/reconcile_root_epoch11_stageability_repair_seed_amendment.py"
STATE_PATH = "state/CURRENT.json"
ROOT_TCB_PATH = "config/root_tcb_epoch_v25.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("trusted module unavailable: " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy_errors(policy: dict) -> list[str]:
    expected = {
        "schema_version": "PS-ROOT-EPOCH11-README-LINEAGE-SEED-2.5-1",
        "protocol_version": "2.5",
        "task_network_plan_id": "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa",
        "trusted_source": "EXACT_ACCEPTED_MAIN_SEED_BYTES",
        "candidate_bytes_in_privileged_phase": "DATA_ONLY",
        "candidate_execution_with_write_token": "FORBIDDEN",
        "same_repository_required": True,
        "owner_authored_required": True,
        "base_branch_required": "main",
        "head_prefix_required": "root-rotation/",
        "required_seed_base_main_sha": "de897f6243707410694a81733a23de4828408693",
        "required_current_root_epoch": 10,
        "target_root_epoch": 11,
        "calibration_streak_required": 0,
        "fresh_allowed_globally_required": False,
        "candidate_path_count": 69,
        "failure_semantics": "FAIL_CLOSED",
        "seed_self_modification": "FORBIDDEN",
        "policy_self_hash": "FORBIDDEN_TO_AVOID_CIRCULAR_BINDING",
    }
    errors = ["lineage policy mismatch " + key for key, value in expected.items() if policy.get(key) != value]
    contexts = ["supernova/static-control", "supernova/report-admission", "supernova/transition-admission"]
    if policy.get("required_status_contexts") != contexts:
        errors.append("required status context contract mismatch")
    paths = policy.get("seed_paths")
    expected_paths = [
        POLICY_PATH,
        "scripts/reconcile_root_epoch11_readme_lineage_seed.py",
        ".github/workflows/supernova-root-epoch11-readme-lineage-seed.yml",
        "tests/test_root_epoch11_readme_lineage_seed.py",
    ]
    if paths != expected_paths or len(set(paths or [])) != 4:
        errors.append("seed path contract is not exact")
    pins = policy.get("installed_seed_blob_pins")
    if not isinstance(pins, dict) or set(pins) != set(expected_paths[1:]):
        errors.append("installed seed pin map is not exact")
    elif any(not isinstance(value, str) or not HEX40.fullmatch(value) for value in pins.values()):
        errors.append("installed seed pin is invalid")
    if policy.get("one_shot_marker_path") != "config/root_epoch11_stageability_repair_epoch_v25.json":
        errors.append("one-shot marker contract mismatch")
    if POLICY_PATH in (pins or {}):
        errors.append("policy self-hash is forbidden")
    required = policy.get("required_root_candidate_paths")
    candidate_pins = policy.get("expected_root_candidate_blobs")
    if not isinstance(required, list) or len(required) != 69 or len(set(required)) != 69 or ROOT_TCB_PATH not in required:
        errors.append("candidate path manifest is not exact")
    elif not isinstance(candidate_pins, dict) or set(candidate_pins) != set(required) - {ROOT_TCB_PATH} or len(candidate_pins) != 68:
        errors.append("candidate non-root blob manifest is not exact")
    elif any(not isinstance(value, str) or not HEX40.fullmatch(value) or value == "0" * 40 for value in candidate_pins.values()):
        errors.append("candidate non-root blob pin is invalid")
    expected_bindings = {
        "root_epoch11_readme_lineage_seed_install_commit_sha": "__ROOT11_README_LINEAGE_SEED_INSTALL_COMMIT__",
        "root_epoch11_readme_lineage_seed_policy_blob": "__ROOT11_README_LINEAGE_SEED_POLICY_BLOB__",
        "root_epoch11_readme_lineage_seed_reconciler_blob": "__ROOT11_README_LINEAGE_SEED_RECONCILER_BLOB__",
        "root_epoch11_readme_lineage_seed_workflow_blob": "__ROOT11_README_LINEAGE_SEED_WORKFLOW_BLOB__",
        "root_epoch11_readme_lineage_seed_test_blob": "__ROOT11_README_LINEAGE_SEED_TEST_BLOB__",
    }
    if policy.get("root_tcb_dynamic_lineage_bindings") != expected_bindings:
        errors.append("root TCB five-sentinel manifest is not exact")
    digest = policy.get("expected_normalized_root_tcb_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or digest == "0" * 64:
        errors.append("normalized root TCB digest is invalid")
    return errors


def actions_provenance_errors(run: dict, pr: dict, trusted: str, candidate: str, policy: dict, run_id: int, run_attempt: int) -> list[str]:
    contract = policy.get("actions_provenance") or {}
    expected = {
        "workflow_name": "Supernova Root Epoch11 README Lineage Seed",
        "workflow_path": ".github/workflows/supernova-root-epoch11-readme-lineage-seed.yml",
        "event": "pull_request_target",
        "head_branch": "main",
        "status": "in_progress",
        "repository": "Kitahl/Project-supernova-",
        "actor": "Kitahl",
    }
    errors = []
    if contract != expected:
        errors.append("Actions provenance policy mismatch")
        return errors
    checks = (
        (run.get("id") == run_id, "workflow run id mismatch"),
        (run.get("run_attempt") == run_attempt and run_attempt > 0, "workflow run attempt mismatch"),
        (run.get("name") == expected["workflow_name"], "workflow name mismatch"),
        (run.get("path") == expected["workflow_path"], "workflow path mismatch"),
        (run.get("event") == expected["event"], "workflow event is not pull_request_target"),
        (run.get("head_sha") == trusted, "workflow did not execute from exact accepted main"),
        (run.get("head_branch") == expected["head_branch"], "workflow head branch mismatch"),
        (run.get("status") == expected["status"], "workflow is not the live trusted writer run"),
        (((run.get("repository") or {}).get("full_name")) == expected["repository"], "workflow repository mismatch"),
        (((run.get("actor") or {}).get("login")) == expected["actor"], "workflow actor is not the repository owner"),
    )
    errors.extend(reason for ok, reason in checks if not ok)
    rows = run.get("pull_requests") or []
    if len(rows) != 1:
        errors.append("workflow provenance must bind exactly one pull request")
    else:
        row = rows[0]
        if row.get("number") != pr.get("number"):
            errors.append("workflow pull request number mismatch")
        if (row.get("head") or {}).get("sha") != candidate:
            errors.append("workflow pull request head mismatch")
        if (row.get("base") or {}).get("sha") != trusted:
            errors.append("workflow pull request base mismatch")
    return errors


def accepted_seed_installation(trusted: str, policy: dict, seed) -> tuple[bool, str]:
    base = policy["required_seed_base_main_sha"]
    if seed.run(["git", "rev-parse", base + "^{tree}"])[1].strip() != policy.get("required_seed_base_tree_sha"):
        return False, "audited seed base tree mismatch"
    if seed.run(["git", "merge-base", "--is-ancestor", base, trusted])[0] != 0:
        return False, "lineage seed does not descend from exact audited main"
    rc, parent = seed.run(["git", "rev-parse", trusted + "^1"])
    if rc or parent.strip() != base:
        return False, "lineage seed is not the immediate first-parent successor of audited main"
    rc, count = seed.run(["git", "rev-list", "--count", "--first-parent", base + ".." + trusted])
    if rc or count.strip() != "1":
        return False, "lineage seed is not the next accepted-main transaction"
    rc, delta = seed.run(["git", "diff", "--name-status", base + "..." + trusted])
    expected = {"A\t" + path for path in policy["seed_paths"]}
    if rc or set(delta.splitlines()) != expected:
        return False, "accepted lineage seed is not the exact four-new-path transaction"
    for path in policy["seed_paths"]:
        if seed.blob_at(base, path) is not None:
            return False, "lineage seed path already existed at audited main: " + path
        rc, tree = seed.run(["git", "ls-tree", trusted, "--", path])
        fields = tree.strip().split(None, 2)
        if rc or len(fields) < 2 or fields[0] != "100644" or fields[1] != "blob":
            return False, "installed lineage seed path is not a regular blob: " + path
    for path, expected_blob in policy["installed_seed_blob_pins"].items():
        if seed.blob_at(trusted, path) != expected_blob:
            return False, "installed lineage seed blob mismatch: " + path
    if seed.blob_at(trusted, ROOT_TCB_PATH) != policy["required_current_root_epoch_blob"]:
        return False, "accepted root10 blob changed during lineage seed installation"
    if seed.blob_at(trusted, STATE_PATH) != policy["required_state_blob"]:
        return False, "accepted Gen12 state changed during lineage seed installation"
    return True, ""


def exact_candidate(tmp: pathlib.Path, trusted: str, policy: dict, seed) -> tuple[bool, str]:
    required = set(policy["required_root_candidate_paths"])
    pins = policy.get("expected_root_candidate_blobs")
    if policy.get("candidate_path_count") != 69 or len(required) != 69:
        return False, "candidate path count is not exactly 69"
    if not isinstance(pins, dict) or set(pins) != required - {ROOT_TCB_PATH} or len(pins) != 68:
        return False, "lineage seed does not pin exact 68 non-root candidate blobs"
    for path, expected_blob in pins.items():
        if not isinstance(expected_blob, str) or not HEX40.fullmatch(expected_blob):
            return False, "candidate pin is invalid: " + path
        if seed.blob_at("HEAD", path, cwd=tmp) != expected_blob:
            return False, "candidate blob mismatch: " + path

    bindings = policy.get("root_tcb_dynamic_lineage_bindings")
    if not isinstance(bindings, dict) or len(bindings) != 5 or len(set(bindings.values())) != 5:
        return False, "root TCB five-sentinel contract is not exact"
    paths = policy["seed_paths"]
    actual = {
        "root_epoch11_readme_lineage_seed_install_commit_sha": trusted,
        "root_epoch11_readme_lineage_seed_policy_blob": seed.blob_at(trusted, paths[0]),
        "root_epoch11_readme_lineage_seed_reconciler_blob": seed.blob_at(trusted, paths[1]),
        "root_epoch11_readme_lineage_seed_workflow_blob": seed.blob_at(trusted, paths[2]),
        "root_epoch11_readme_lineage_seed_test_blob": seed.blob_at(trusted, paths[3]),
    }
    if set(bindings) != set(actual) or any(not isinstance(value, str) or not value for value in bindings.values()):
        return False, "root TCB dynamic lineage names or sentinels are not exact"
    root_tcb = seed.load(tmp, ROOT_TCB_PATH)
    for key, value in actual.items():
        if root_tcb.get(key) != value:
            return False, "root TCB lineage binding mismatch " + key
    normalized = dict(root_tcb)
    for key, sentinel in bindings.items():
        normalized[key] = sentinel
    expected_digest = policy.get("expected_normalized_root_tcb_sha256")
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        return False, "normalized root TCB digest pin is invalid"
    if seed.canonical_sha256(normalized) != expected_digest:
        return False, "root TCB differs outside its five exact lineage bindings"
    return True, ""


def lineage_semantic_errors(tmp: pathlib.Path, policy: dict, seed) -> list[str]:
    errors = []
    seed_paths = set(policy["seed_paths"])
    countable = set((seed.load(tmp, "config/countable_control_set_v25.json").get("required_control_paths") or []))
    if not seed_paths.issubset(countable):
        errors.append("countable control does not protect every lineage seed path")
    authority = seed.load(tmp, "config/admission_authority.json")
    inventory = set(authority.get("authoritative_status_workflows") or []) | set(authority.get("trusted_authority_helpers") or []) | set(authority.get("trusted_validator_entrypoints") or [])
    if not seed_paths.issubset(inventory):
        errors.append("admission authority does not protect every lineage seed path")
    bootstrap_path = tmp / "scripts/reconcile_authority_bootstrap.py"
    try:
        tree = ast.parse(bootstrap_path.read_text(encoding="utf-8"), filename=str(bootstrap_path))
        literals = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    except (OSError, SyntaxError) as exc:
        errors.append("authority bootstrap data is not parseable: " + repr(exc))
        literals = []
    for path in seed_paths:
        if literals.count(path) < 2:
            errors.append("authority bootstrap does not protect installed lineage path: " + path)
    registry = seed.load(tmp, "config/task_registry_v25.json")
    roles = [row.get("role_id") for row in registry.get("tasks", []) if isinstance(row, dict)]
    exact_roles = {"MF01", "MF02", "MF03", "MF04", "MF05", "MM01", "MM02", "MM03", "MM04", "MM05", "MM07", "EXT01", "MM06", "MF06", "BIL00"}
    if registry.get("active_task_count") != 15 or registry.get("no_sixteenth_lane") is not True or len(roles) != 15 or set(roles) != exact_roles or len(set(roles)) != 15:
        errors.append("candidate does not preserve exact 15 canonical roles and no sixteenth lane")
    return errors


def trusted_candidate_semantic_errors(tmp: pathlib.Path, policy: dict, seed, amendment, amendment_policy: dict, original_policy: dict) -> list[str]:
    ok, reason = amendment.corrected_candidate_semantics(tmp, amendment_policy, seed, original_policy)
    if not ok:
        return [reason or "trusted root11 semantic validation failed"]
    return lineage_semantic_errors(tmp, policy, seed)


def fail(seed, sha: str | None, reason: str, policy: dict) -> int:
    if isinstance(sha, str) and HEX40.fullmatch(sha):
        for context in policy.get("required_status_contexts", []):
            seed.post(sha, context, "failure", "root11 lineage seed refused: " + reason)
    print("ROOT EPOCH11 README LINEAGE SEED REFUSED:", reason)
    return 1


def main() -> int:
    seed = load_module("trusted_root11_seed", ORIGINAL_SCRIPT_PATH)
    amendment = load_module("trusted_root11_amendment", AMENDMENT_SCRIPT_PATH)
    policy = seed.load(ROOT, POLICY_PATH)
    errors = policy_errors(policy)
    if errors:
        return fail(seed, None, errors[0], policy)
    try:
        number = int(os.environ.get("PR_NUMBER", "0"))
        run_id = int(os.environ.get("GITHUB_RUN_ID", "0"))
        run_attempt = int(os.environ.get("GITHUB_RUN_ATTEMPT", "0"))
    except ValueError:
        return fail(seed, None, "invalid PR or Actions run binding", policy)
    if number <= 0 or run_id <= 0 or run_attempt <= 0:
        return fail(seed, None, "missing PR or Actions run binding", policy)
    pr = seed.api(f"/pulls/{number}")
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    sha = head.get("sha")
    if os.environ.get("CANDIDATE_DIAGNOSTICS_RESULT") != "success":
        return fail(seed, sha, "read-only candidate diagnostics did not succeed", policy)
    if sha != os.environ.get("DIAGNOSED_HEAD_SHA") or base.get("sha") != os.environ.get("DIAGNOSED_BASE_SHA"):
        return fail(seed, sha, "diagnosed head/base no longer match PR", policy)
    rc, out = seed.run(["git", "rev-parse", "HEAD"])
    trusted = out.strip()
    if rc or trusted != base.get("sha") or os.environ.get("DIAGNOSED_BASE_SHA") != trusted:
        return fail(seed, sha, "candidate base is not exact current accepted main", policy)
    if base.get("ref") != "main" or (head.get("repo") or {}).get("full_name") != seed.REPO or (pr.get("user") or {}).get("login") != seed.OWNER:
        return fail(seed, sha, "same-repository owner PR to main required", policy)
    if not str(head.get("ref", "")).startswith(policy["head_prefix_required"]):
        return fail(seed, sha, "head prefix not root-epoch11 eligible", policy)
    run = seed.api(f"/actions/runs/{run_id}")
    provenance = actions_provenance_errors(run, pr, trusted, sha, policy, run_id, run_attempt)
    if provenance:
        return fail(seed, sha, provenance[0], policy)
    ok, reason = accepted_seed_installation(trusted, policy, seed)
    if not ok:
        return fail(seed, sha, reason, policy)

    state = seed.load(ROOT, STATE_PATH)
    if state.get("active_cohort_id") != policy["required_active_cohort"] or state.get("generation_head_sha") != policy["required_generation_head"]:
        return fail(seed, sha, "lineage seed only applies while exact Gen12 is canonical", policy)
    if state.get("calibration_streak") != 0 or state.get("fresh_allowed_globally") is not False:
        return fail(seed, sha, "Gen12 must remain streak zero with fresh disabled", policy)
    epoch = seed.load(ROOT, ROOT_TCB_PATH)
    if epoch.get("epoch") != 10 or (ROOT / policy["one_shot_marker_path"]).exists():
        return fail(seed, sha, "one-shot lineage seed is inert after root epoch11 exists", policy)
    original_policy = seed.load(ROOT, ORIGINAL_POLICY_PATH)
    amendment_policy = seed.load(ROOT, AMENDMENT_POLICY_PATH)
    ok, reason = seed.exact_gen12_terminal_chain(original_policy)
    if not ok:
        return fail(seed, sha, reason, policy)

    if not isinstance(sha, str) or not HEX40.fullmatch(sha) or seed.run(["git", "cat-file", "-e", sha + "^{commit}"])[0] != 0:
        return fail(seed, sha, "exact candidate head is unavailable", policy)
    if seed.run(["git", "merge-base", "--is-ancestor", trusted, sha])[0] != 0:
        return fail(seed, sha, "candidate does not descend from exact accepted lineage seed", policy)
    rc, out = seed.run(["git", "diff", "--name-only", trusted + "..." + sha])
    changed = [line for line in out.splitlines() if line]
    required = set(policy["required_root_candidate_paths"])
    if rc or len(changed) != 69 or set(changed) != required:
        return fail(seed, sha, "root candidate diff is not the exact 69-path transaction", policy)
    if set(policy["seed_paths"]).intersection(changed):
        return fail(seed, sha, "lineage seed self-modification forbidden", policy)
    for prefix in policy["forbidden_candidate_prefixes"]:
        if any(path.startswith(prefix) for path in changed):
            return fail(seed, sha, "state/evidence/runtime/scientific candidate change forbidden", policy)
    for path in changed:
        rc, row = seed.run(["git", "ls-tree", sha, "--", path])
        fields = row.strip().split(None, 2)
        if rc or len(fields) < 2 or fields[0] != "100644" or fields[1] != "blob":
            return fail(seed, sha, "candidate changed path is not a regular blob: " + path, policy)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-root11-readme-lineage-seed-"))
    try:
        rc, output = seed.run(["git", "worktree", "add", "--detach", str(tmp), sha])
        if rc:
            return fail(seed, sha, "cannot materialize candidate as data: " + output[-500:], policy)
        if seed.blob_at("HEAD", STATE_PATH, cwd=tmp) != policy["required_state_blob"] or seed.load(tmp, STATE_PATH) != state:
            return fail(seed, sha, "canonical Gen12 state changed in root11 candidate", policy)
        for path in policy["seed_paths"]:
            if seed.blob_at("HEAD", path, cwd=tmp) != seed.blob_at(trusted, path):
                return fail(seed, sha, "candidate changed installed lineage seed path: " + path, policy)
        plan = seed.load(tmp, "plan/PLAN.json")
        if plan.get("task_network_plan_id") != seed.PLAN or plan.get("protocol_version") != "2.5" or plan.get("specification_revision") != 4:
            return fail(seed, sha, "plan/protocol/revision drift", policy)
        ok, reason = exact_candidate(tmp, trusted, policy, seed)
        if not ok:
            return fail(seed, sha, reason, policy)
        semantic_errors = trusted_candidate_semantic_errors(tmp, policy, seed, amendment, amendment_policy, original_policy)
        if semantic_errors:
            return fail(seed, sha, semantic_errors[0], policy)
    finally:
        seed.run(["git", "worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)

    for context in policy["required_status_contexts"]:
        seed.post(sha, context, "success", f"PASS pr={number} h={sha} b={trusted} r={run_id}")
    print("ROOT EPOCH11 README LINEAGE SEED PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
