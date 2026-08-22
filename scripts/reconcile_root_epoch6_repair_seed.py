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
POLICY_PATH = "config/root_epoch6_repair_seed_v25.json"
DURABLE_BOOTSTRAP_PROVENANCE = "PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED"


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
        post(sha, policy["seed_context"], "failure", "epoch6 seed refused: " + reason)
        for context in policy["required_status_contexts"]:
            post(sha, context, "failure", "epoch6 seed refused: " + reason)
    print("ROOT EPOCH6 SEED REFUSED:", reason)
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
        return fail(sha, "head prefix not root-epoch6 eligible", policy)

    state = load(ROOT, "state/CURRENT.json")
    if state.get("calibration_streak") != policy["calibration_streak_required"] or state.get("fresh_allowed_globally") is not policy["fresh_allowed_globally_required"]:
        return fail(sha, "streak must be zero and fresh disabled", policy)
    current_epoch = load(ROOT, "config/root_tcb_epoch_v25.json")
    if current_epoch.get("epoch") != policy["required_current_root_epoch"]:
        return fail(sha, "one-shot seed is inert outside root epoch 5", policy)
    if (ROOT / policy["one_shot_marker_path"]).exists():
        return fail(sha, "root epoch6 repair marker already exists; seed is inert", policy)

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
        return fail(sha, "candidate path outside epoch6 repair allowlist", policy)
    for prefix in policy["forbidden_candidate_prefixes"]:
        if any(path.startswith(prefix) for path in changed):
            return fail(sha, "forbidden runtime/scientific path changed", policy)
    for path in changed:
        rc, tree = run(["git", "ls-tree", sha, "--", path])
        if rc or (tree.strip() and tree.split(None, 1)[0] != "100644"):
            return fail(sha, "non-regular changed path " + path, policy)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-root-epoch6-seed-"))
    try:
        rc, _ = run(["git", "worktree", "add", "--detach", str(tmp), sha])
        if rc:
            return fail(sha, "cannot create candidate data worktree", policy)
        if load(tmp, "state/CURRENT.json") != state:
            return fail(sha, "state changed in epoch6 repair candidate", policy)
        plan = load(tmp, "plan/PLAN.json")
        if plan.get("task_network_plan_id") != PLAN or plan.get("protocol_version") != "2.5" or plan.get("specification_revision") != 4:
            return fail(sha, "plan/protocol/revision drift", policy)

        epoch = load(tmp, "config/root_tcb_epoch_v25.json")
        if epoch.get("schema_version") != "PS-ROOT-TCB-EPOCH-2.5-6" or epoch.get("epoch") != policy["target_root_epoch"]:
            return fail(sha, "invalid target root epoch marker", policy)
        if epoch.get("previous_epoch_blob") != blob_at("HEAD", "config/root_tcb_epoch_v25.json"):
            return fail(sha, "epoch6 does not bind accepted epoch5 blob", policy)
        expected_seed = {
            "root_epoch6_repair_seed_install_commit_sha": trusted,
            "root_epoch6_repair_seed_policy_blob": blob_at("HEAD", policy["seed_paths"][0]),
            "root_epoch6_repair_seed_reconciler_blob": blob_at("HEAD", policy["seed_paths"][1]),
            "root_epoch6_repair_seed_workflow_blob": blob_at("HEAD", policy["seed_paths"][2]),
        }
        for key, value in expected_seed.items():
            if not isinstance(value, str) or epoch.get(key) != value:
                return fail(sha, "epoch6 does not bind accepted seed " + key, policy)

        marker = load(tmp, policy["one_shot_marker_path"])
        expected_marker = {
            "schema_version": "PS-ROOT-EPOCH6-REPAIR-EPOCH-2.5-1",
            "protocol_version": "2.5",
            "task_network_plan_id": PLAN,
            "previous_root_epoch": 5,
            "new_root_epoch": 6,
            "calibration_credit_effect": 0,
            "fresh_science_effect": "NONE",
        }
        for key, value in expected_marker.items():
            if marker.get(key) != value:
                return fail(sha, "invalid epoch6 repair marker " + key, policy)

        admission = load(tmp, "config/admission_authority.json")
        if admission.get("root_tcb_epoch") != 6:
            return fail(sha, "admission authority root epoch not 6", policy)
        if admission.get("bootstrap_status_provenance") != DURABLE_BOOTSTRAP_PROVENANCE:
            return fail(sha, "durable bootstrap provenance rule missing", policy)
        helpers = set(admission.get("trusted_authority_helpers") or [])
        if not set(policy["seed_paths"][:3]).issubset(helpers):
            return fail(sha, "epoch6 authority does not protect installed seed", policy)
        if policy["one_shot_marker_path"] not in helpers:
            return fail(sha, "epoch6 authority does not protect repair marker", policy)

        bootstrap = load(tmp, "config/authority_bootstrap_v25.json")
        if bootstrap.get("bootstrap_success_consumption") != DURABLE_BOOTSTRAP_PROVENANCE:
            return fail(sha, "bootstrap policy does not require durable provenance re-derivation", policy)

        open_prs = (tmp / "scripts/reconcile_open_prs.py").read_text(encoding="utf-8")
        if "PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION" not in open_prs or "/actions/runs" not in open_prs:
            return fail(sha, "open-PR reconciler lacks persistent workflow-run provenance re-derivation", policy)
        diagnostic = (tmp / "scripts/diagnose_authority_bootstrap.py").read_text(encoding="utf-8")
        if "DIAGNOSED_HEAD_SHA" not in diagnostic or "DIAGNOSED_BASE_SHA" not in diagnostic:
            return fail(sha, "bootstrap diagnostic does not bind diagnosed head/base", policy)
        bootstrap_checker = (tmp / "scripts/reconcile_authority_bootstrap.py").read_text(encoding="utf-8")
        if DURABLE_BOOTSTRAP_PROVENANCE not in bootstrap_checker:
            return fail(sha, "bootstrap invariant checker does not accept durable provenance rule", policy)

        verifier_schema = load(tmp, "schemas/branch_verification.schema.json")
        integration_schema = load(tmp, "schemas/branch_integration.schema.json")
        if "VERIFIED_WITH_QUARANTINES" not in json.dumps(verifier_schema, sort_keys=True):
            return fail(sha, "verification schema lost terminal quarantine verdict", policy)
        if "VERIFIED_WITH_QUARANTINES" not in json.dumps(integration_schema, sort_keys=True):
            return fail(sha, "integration schema cannot preserve terminal quarantine verdict", policy)
        admission_code = (tmp / "scripts/reconcile_v25_admission.py").read_text(encoding="utf-8")
        for needle in ("TERMINAL_VERDICTS", "VERIFIED_WITH_QUARANTINES", "calibration_pass"):
            if needle not in admission_code:
                return fail(sha, "terminal quarantine admission repair incomplete: " + needle, policy)
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)

    post(sha, policy["seed_context"], "success", "one-shot accepted-main root epoch6 repair seed PASS")
    for context in policy["required_status_contexts"]:
        post(sha, context, "success", "one-shot root epoch6 seed exact-head PASS/N-A non-state transition")
    print("ROOT EPOCH6 REPAIR SEED PASS", number, sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
