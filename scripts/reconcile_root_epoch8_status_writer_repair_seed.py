#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = pathlib.Path.cwd().resolve()
REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/" + REPO
OWNER = REPO.split("/", 1)[0]
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
POLICY_PATH = "config/root_epoch8_status_writer_repair_seed_v25.json"
GEN10_COHORT = "CAL-BR-010-v25-fe539297-r2"
GEN10_G = "25c7c4e4732a5635ae8f47a9194d59a3f5a58e8f"
GEN10_STATE_BLOB = "72d5aa0c0f9144bb0cb2faa19ad8300bd38c8ad6"
STRUCTURAL_WRITER = "scripts/reconcile_branch_statuses.py"
ADMISSION_HELPER = "scripts/reconcile_v25_admission.py"
STRUCTURAL_CONTEXT = "supernova/branch-integrate"


def api(path: str, method: str = "GET", data=None):
    req = urllib.request.Request(
        API + path,
        data=(json.dumps(data).encode("utf-8") if data is not None else None),
        method=method,
    )
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def run(cmd, cwd=ROOT):
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def load(root: pathlib.Path, path: str):
    return json.loads((root / path).read_text(encoding="utf-8"))


def blob_at(ref: str, path: str):
    rc, out = run(["git", "rev-parse", f"{ref}:{path}"])
    return out.strip() if rc == 0 else None


def post(sha: str, context: str, state: str, description: str):
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    target = f"https://github.com/{REPO}/actions/runs/{run_id}" if run_id.isdigit() else None
    body = {"state": state, "context": context, "description": description[:140]}
    if target:
        body["target_url"] = target
    api("/statuses/" + sha, "POST", body)


def fail(sha, reason: str, policy: dict):
    if isinstance(sha, str) and HEX40.fullmatch(sha):
        post(sha, policy["seed_context"], "failure", "epoch8 status-writer seed refused: " + reason)
    print("ROOT EPOCH8 STATUS-WRITER SEED REFUSED:", reason)
    return 1


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
    if base.get("ref") != "main" or (head.get("repo") or {}).get("full_name") != REPO or (pr.get("user") or {}).get("login") != OWNER:
        return fail(sha, "same-repository owner PR to main required", policy)
    if not str(head.get("ref", "")).startswith(policy["head_prefix_required"]):
        return fail(sha, "head prefix not root-epoch8 eligible", policy)

    state = load(ROOT, "state/CURRENT.json")
    if state.get("active_cohort_id") != GEN10_COHORT or state.get("generation_head_sha") != GEN10_G:
        return fail(sha, "seed only applies while exact Gen10 is canonical", policy)
    if blob_at("HEAD", "state/CURRENT.json") != GEN10_STATE_BLOB:
        return fail(sha, "canonical Gen10 state blob changed", policy)
    if state.get("calibration_streak") != policy["calibration_streak_required"] or state.get("fresh_allowed_globally") is not policy["fresh_allowed_globally_required"]:
        return fail(sha, "streak must be zero and fresh disabled", policy)
    current_epoch = load(ROOT, "config/root_tcb_epoch_v25.json")
    if current_epoch.get("epoch") != policy["required_current_root_epoch"]:
        return fail(sha, "one-shot seed is inert outside root epoch 7", policy)
    if (ROOT / policy["one_shot_marker_path"]).exists():
        return fail(sha, "root epoch8 status-writer repair marker already exists; seed is inert", policy)

    run(["git", "fetch", "--no-tags", "origin", f"pull/{number}/head"])
    if run(["git", "merge-base", "--is-ancestor", trusted, sha])[0] != 0:
        return fail(sha, "candidate does not descend from exact accepted main", policy)
    rc, out = run(["git", "diff", "--name-only", trusted + "..." + sha])
    changed = [line for line in out.splitlines() if line]
    if rc or not changed:
        return fail(sha, "cannot enumerate nonempty candidate diff", policy)

    allowed = set(policy["allowed_root_candidate_paths"])
    required = set(policy["required_root_candidate_paths"])
    seed = set(policy["seed_paths"])
    if seed.intersection(changed):
        return fail(sha, "seed self-modification forbidden", policy)
    if set(changed) != required:
        return fail(sha, "root candidate diff is not exact required repair set", policy)
    if any(path not in allowed for path in changed):
        return fail(sha, "candidate path outside epoch8 repair allowlist", policy)
    for prefix in policy["forbidden_candidate_prefixes"]:
        if any(path.startswith(prefix) for path in changed):
            return fail(sha, "forbidden runtime/scientific path changed", policy)
    for path in changed:
        rc, tree = run(["git", "ls-tree", sha, "--", path])
        if rc or (tree.strip() and tree.split(None, 1)[0] != "100644"):
            return fail(sha, "non-regular changed path " + path, policy)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-root-epoch8-status-writer-seed-"))
    try:
        rc, _ = run(["git", "worktree", "add", "--detach", str(tmp), sha])
        if rc:
            return fail(sha, "cannot create candidate data worktree", policy)
        if load(tmp, "state/CURRENT.json") != state:
            return fail(sha, "state changed in epoch8 repair candidate", policy)
        plan = load(tmp, "plan/PLAN.json")
        if plan.get("task_network_plan_id") != PLAN or plan.get("protocol_version") != "2.5" or plan.get("specification_revision") != 4:
            return fail(sha, "plan/protocol/revision drift", policy)

        epoch = load(tmp, "config/root_tcb_epoch_v25.json")
        if epoch.get("schema_version") != "PS-ROOT-TCB-EPOCH-2.5-8" or epoch.get("epoch") != 8:
            return fail(sha, "invalid target root epoch marker", policy)
        if epoch.get("previous_epoch_blob") != blob_at("HEAD", "config/root_tcb_epoch_v25.json"):
            return fail(sha, "epoch8 does not bind accepted epoch7 blob", policy)
        expected_seed = {
            "root_epoch8_status_writer_repair_seed_install_commit_sha": trusted,
            "root_epoch8_status_writer_repair_seed_policy_blob": blob_at("HEAD", policy["seed_paths"][0]),
            "root_epoch8_status_writer_repair_seed_reconciler_blob": blob_at("HEAD", policy["seed_paths"][1]),
            "root_epoch8_status_writer_repair_seed_workflow_blob": blob_at("HEAD", policy["seed_paths"][2]),
        }
        for key, value in expected_seed.items():
            if not isinstance(value, str) or epoch.get(key) != value:
                return fail(sha, "epoch8 does not bind accepted seed " + key, policy)
        if epoch.get("single_authoritative_structural_writer") != STRUCTURAL_WRITER:
            return fail(sha, "epoch8 single structural writer binding changed", policy)

        marker = load(tmp, policy["one_shot_marker_path"])
        expected_marker = {
            "schema_version": "PS-ROOT-EPOCH8-STATUS-WRITER-REPAIR-EPOCH-2.5-1",
            "protocol_version": "2.5",
            "task_network_plan_id": PLAN,
            "previous_root_epoch": 7,
            "new_root_epoch": 8,
            "stable_issue_id": "O-T0-GEN10-HISTORICAL-INTEGRATION-STATUS-DRIFT",
            "calibration_credit_effect": 0,
            "fresh_science_effect": "NONE",
            "runtime_effect": "NONE",
            "scientific_state_effect": "NONE",
        }
        for key, value in expected_marker.items():
            if marker.get(key) != value:
                return fail(sha, "invalid epoch8 status-writer repair marker " + key, policy)

        admission = load(tmp, "config/admission_authority.json")
        if admission.get("root_tcb_epoch") != 8 or admission.get("authoritative_structural_status_writer") != STRUCTURAL_WRITER or admission.get("structural_status_writer_cardinality") != 1:
            return fail(sha, "admission authority did not migrate exact single-writer epoch8 invariant", policy)
        helpers = set(admission.get("trusted_authority_helpers") or [])
        if not set(policy["seed_paths"][:3]).issubset(helpers) or policy["one_shot_marker_path"] not in helpers:
            return fail(sha, "epoch8 authority does not protect installed seed/marker", policy)
        workflows = set(admission.get("authoritative_status_workflows") or [])
        if policy["seed_paths"][2] not in workflows:
            return fail(sha, "epoch8 seed workflow missing from authority inventory", policy)

        bootstrap_policy = load(tmp, "config/authority_bootstrap_v25.json")
        if bootstrap_policy.get("root_tcb_epoch_required") != 8:
            return fail(sha, "authority bootstrap policy root epoch not 8", policy)
        bootstrap_checker = (tmp / "scripts/reconcile_authority_bootstrap.py").read_text(encoding="utf-8")
        if '"root_tcb_epoch": 8' not in bootstrap_checker or '"root_tcb_epoch_required": 8' not in bootstrap_checker:
            return fail(sha, "authority bootstrap checker did not migrate to root epoch 8", policy)

        v25 = (tmp / ADMISSION_HELPER).read_text(encoding="utf-8")
        if STRUCTURAL_CONTEXT in v25:
            return fail(sha, "admission helper still publishes structural branch-integrate context", policy)
        for needle in (
            "ih,ie=integration_check(state,vh)",
            "rs=result_state(ve+ie,ri_wait)",
            "supernova/report-admission",
            "integration_semantic_errors",
        ):
            if needle not in v25:
                return fail(sha, "admission semantic fan-in was weakened while removing duplicate writer: " + needle, policy)
        structural = (tmp / "tests/test_structural_status_single_writer.py").read_text(encoding="utf-8")
        for needle in ("reconcile_v25_admission.py", "supernova/branch-integrate", "structural_status_writer_cardinality"):
            if needle not in structural:
                return fail(sha, "single-writer regression incomplete: " + needle, policy)

        control_set = load(tmp, "config/countable_control_set_v25.json")
        if control_set.get("schema_version") != "PS-COUNTABLE-CONTROL-SET-2.5-23":
            return fail(sha, "future countable control set is not v23", policy)
        frozen = set(control_set.get("required_control_paths") or [])
        required_frozen = set(policy["seed_paths"]) | {
            policy["one_shot_marker_path"],
            ADMISSION_HELPER,
            "scripts/reconcile_authority_bootstrap.py",
            "tests/test_structural_status_single_writer.py",
            "tests/test_bootstrap_root_tcb_and_head_binding.py",
            "tests/test_gen10_zero_credit_terminal_transition.py",
            "tests/test_gen9_reset_compat_root.py",
            "tests/test_root_epoch6_repair.py",
        }
        if not required_frozen.issubset(frozen):
            return fail(sha, "epoch8/countable v23 does not freeze full status-writer repair surface", policy)
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)

    post(sha, policy["seed_context"], "success", "one-shot accepted-main root epoch8 status-writer repair seed PASS")
    print("ROOT EPOCH8 STATUS-WRITER REPAIR SEED PASS", number, sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
