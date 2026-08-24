#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

ROOT = pathlib.Path.cwd().resolve()
REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/" + REPO
OWNER = REPO.split("/", 1)[0]
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
POLICY_PATH = "config/root_epoch9_integrity_repair_seed_v25.json"
STATE_PATH = "state/CURRENT.json"
GEN11_VERIFICATION_PATH = "verification/CAL-BR-011-v25-27955ce6.json"


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
        return json.loads(raw) if raw else None


def run(cmd, cwd=ROOT):
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return proc.returncode, proc.stdout


def blob_at(ref: str, path: str):
    rc, out = run(["git", "rev-parse", f"{ref}:{path}"])
    return out.strip() if rc == 0 else None


def post(sha: str, context: str, state: str, description: str):
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    body = {"state": state, "context": context, "description": description[:140]}
    if run_id.isdigit():
        body["target_url"] = f"https://github.com/{REPO}/actions/runs/{run_id}"
    api("/statuses/" + sha, "POST", body)


def fail(sha, reason: str, policy: dict):
    if isinstance(sha, str) and HEX40.fullmatch(sha):
        post(sha, policy["seed_context"], "failure", "epoch9 integrity seed refused: " + reason)
    print("ROOT EPOCH9 INTEGRITY SEED REFUSED:", reason)
    return 1


def verifier_terminal(policy: dict):
    branch = "ps/verify/" + policy["required_active_cohort"]
    b = api("/branches/" + urllib.parse.quote(branch, safe=""))
    head = ((b or {}).get("commit") or {}).get("sha")
    if head != policy["required_verifier_head"]:
        return False, "verifier head does not match frozen terminal MM06 receipt"
    obj = api("/contents/" + urllib.parse.quote(GEN11_VERIFICATION_PATH, safe="/") + "?ref=" + head)
    if not isinstance(obj, dict) or obj.get("type") != "file":
        return False, "terminal MM06 receipt missing"
    try:
        receipt = strict_loads(base64.b64decode(obj["content"]).decode("utf-8"))
    except Exception as exc:
        return False, "terminal MM06 receipt is not strict JSON: " + repr(exc)
    expected = {
        "cohort_id": policy["required_active_cohort"],
        "generation_head_sha": policy["required_generation_head"],
        "verdict": policy["required_verifier_verdict"],
        "calibration_pass": policy["required_verifier_calibration_pass"],
        "partition_exhaustive_verified": True,
        "liveness_complete": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            return False, "terminal MM06 receipt mismatch " + key
    safe = receipt.get("safe_report_refs") or []
    if len(safe) != 12 or receipt.get("quarantined_report_refs") != [] or receipt.get("missing_workers") != []:
        return False, "terminal MM06 partition is not exact 12 SAFE / 0 quarantine / 0 missing"
    issue_text = json.dumps(receipt.get("issue_ledger") or [], sort_keys=True, allow_nan=False)
    for issue in (
        "GEN11-EXACT-G-LIVENESS-NONCLEAN",
        "O-T0-BRANCH-CONFIG-STRUCTURAL-WRITER-DRIFT",
        "PS-MF04-NONFINITEJSON-001",
        "MM03-RPT-TYPED-MISSING-006",
        "MM04-T0-MM04-ROLE-NONVACUITY-SCHEMA-001",
        "MM04-T0-PRIVILEGED-VALIDATOR-ENV-ASSERTION-001",
    ):
        if issue not in issue_text:
            return False, "terminal MM06 receipt missing confirmed issue " + issue
    return True, ""


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
        return fail(sha, "head prefix not root-epoch9 eligible", policy)

    state = load(ROOT, STATE_PATH)
    if state.get("active_cohort_id") != policy["required_active_cohort"] or state.get("generation_head_sha") != policy["required_generation_head"]:
        return fail(sha, "seed only applies while exact Gen11 is canonical", policy)
    if blob_at("HEAD", STATE_PATH) != "ad93b7d0a0a4fe329fea2f4855f8eb65a86ce7f9":
        return fail(sha, "canonical Gen11 state blob changed", policy)
    if state.get("calibration_streak") != 0 or state.get("fresh_allowed_globally") is not False:
        return fail(sha, "streak must be zero and fresh disabled", policy)
    current_epoch = load(ROOT, "config/root_tcb_epoch_v25.json")
    if current_epoch.get("epoch") != policy["required_current_root_epoch"]:
        return fail(sha, "one-shot seed is inert outside root epoch 8", policy)
    if (ROOT / policy["one_shot_marker_path"]).exists():
        return fail(sha, "root epoch9 repair marker already exists; seed is inert", policy)
    ok, reason = verifier_terminal(policy)
    if not ok:
        return fail(sha, reason, policy)

    run(["git", "fetch", "--no-tags", "origin", f"pull/{number}/head"])
    if run(["git", "merge-base", "--is-ancestor", trusted, sha])[0] != 0:
        return fail(sha, "candidate does not descend from exact accepted main", policy)
    rc, out = run(["git", "diff", "--name-only", trusted + "..." + sha])
    changed = [line for line in out.splitlines() if line]
    required = set(policy["required_root_candidate_paths"])
    if rc or set(changed) != required:
        return fail(sha, "root candidate diff is not exact required repair set", policy)
    if set(policy["seed_paths"]).intersection(changed):
        return fail(sha, "seed self-modification forbidden", policy)
    for prefix in policy["forbidden_candidate_prefixes"]:
        if any(path.startswith(prefix) for path in changed):
            return fail(sha, "forbidden evidence/runtime/scientific path changed", policy)
    for path in changed:
        rc, tree = run(["git", "ls-tree", sha, "--", path])
        if rc or (tree.strip() and tree.split(None, 1)[0] != "100644"):
            return fail(sha, "non-regular changed path " + path, policy)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-root-epoch9-integrity-seed-"))
    try:
        rc, _ = run(["git", "worktree", "add", "--detach", str(tmp), sha])
        if rc:
            return fail(sha, "cannot create candidate data worktree", policy)
        if load(tmp, STATE_PATH) != state:
            return fail(sha, "state changed in epoch9 repair candidate", policy)
        plan = load(tmp, "plan/PLAN.json")
        if plan.get("task_network_plan_id") != PLAN or plan.get("protocol_version") != "2.5" or plan.get("specification_revision") != 4:
            return fail(sha, "plan/protocol/revision drift", policy)

        epoch = load(tmp, "config/root_tcb_epoch_v25.json")
        if epoch.get("schema_version") != "PS-ROOT-TCB-EPOCH-2.5-9" or epoch.get("epoch") != 9:
            return fail(sha, "invalid target root epoch", policy)
        if epoch.get("previous_epoch_blob") != blob_at("HEAD", "config/root_tcb_epoch_v25.json"):
            return fail(sha, "epoch9 does not bind accepted epoch8 blob", policy)
        expected_seed = {
            "root_epoch9_integrity_repair_seed_install_commit_sha": trusted,
            "root_epoch9_integrity_repair_seed_policy_blob": blob_at("HEAD", policy["seed_paths"][0]),
            "root_epoch9_integrity_repair_seed_reconciler_blob": blob_at("HEAD", policy["seed_paths"][1]),
            "root_epoch9_integrity_repair_seed_workflow_blob": blob_at("HEAD", policy["seed_paths"][2]),
        }
        for key, value in expected_seed.items():
            if epoch.get(key) != value:
                return fail(sha, "epoch9 does not bind accepted seed " + key, policy)

        marker = load(tmp, policy["one_shot_marker_path"])
        marker_expected = {
            "schema_version": "PS-ROOT-EPOCH9-INTEGRITY-REPAIR-EPOCH-2.5-1",
            "protocol_version": "2.5",
            "task_network_plan_id": PLAN,
            "previous_root_epoch": 8,
            "new_root_epoch": 9,
            "source_cohort": policy["required_active_cohort"],
            "source_verifier_head": policy["required_verifier_head"],
            "calibration_credit_effect": 0,
            "fresh_science_effect": "NONE",
            "runtime_effect": "NONE",
        }
        for key, value in marker_expected.items():
            if marker.get(key) != value:
                return fail(sha, "invalid epoch9 marker " + key, policy)

        authority = load(tmp, "config/admission_authority.json")
        if authority.get("root_tcb_epoch") != 9 or authority.get("authoritative_structural_status_writer") != "scripts/reconcile_branch_statuses.py" or authority.get("structural_status_writer_cardinality") != 1:
            return fail(sha, "epoch9 admission authority invariant mismatch", policy)
        if policy["seed_paths"][2] not in set(authority.get("authoritative_status_workflows") or []):
            return fail(sha, "epoch9 seed workflow missing from authority inventory", policy)
        if policy["one_shot_marker_path"] not in set(authority.get("trusted_authority_helpers") or []):
            return fail(sha, "epoch9 marker missing from trusted helper inventory", policy)

        bootstrap = load(tmp, "config/authority_bootstrap_v25.json")
        if bootstrap.get("root_tcb_epoch_required") != 9:
            return fail(sha, "authority bootstrap policy did not migrate to epoch9", policy)
        checker = (tmp / "scripts/reconcile_authority_bootstrap.py").read_text(encoding="utf-8")
        if '"root_tcb_epoch": 9' not in checker or '"root_tcb_epoch_required": 9' not in checker:
            return fail(sha, "authority bootstrap checker did not migrate to epoch9", policy)

        strict = (tmp / "scripts/strict_json.py").read_text(encoding="utf-8")
        for needle in ("parse_constant", "object_pairs_hook", "allow_nan=False"):
            if needle not in strict:
                return fail(sha, "strict JSON boundary incomplete: " + needle, policy)
        for script in ("scripts/validate_bus.py", "scripts/validate_branch_bus_v251.py", "scripts/reconcile_open_prs.py", "scripts/reconcile_v25_admission.py", "scripts/reconcile_branch_statuses.py", "scripts/liveness_contract_guard.py", "scripts/check_lane_liveness.py"):
            if "strict_json" not in (tmp / script).read_text(encoding="utf-8"):
                return fail(sha, "active authority script does not use strict JSON: " + script, policy)

        cfg = load(tmp, "branch/CONFIG.json")
        sr = cfg.get("structural_reconciler") or {}
        if sr.get("authoritative") != "scripts/reconcile_branch_statuses.py via supernova-branch-reconciler.yml":
            return fail(sha, "branch config does not name sole structural authority", policy)
        if cfg.get("minimum_worker_liveness_window_minutes", 0) < 30:
            return fail(sha, "branch config liveness slack is below 30 minutes", policy)

        report_schema = load(tmp, "schemas/branch_report.schema.json")
        nz = (((report_schema.get("$defs") or {}).get("negative_zero_record") or {}).get("properties") or {})
        if "enum" not in (nz.get("quantity") or {}):
            return fail(sha, "negative_zero accounting quantities are not closed", policy)
        mm04 = load(tmp, "schemas/mastermind_mm04_replay_payload.schema.json")
        if "check_record" not in (mm04.get("$defs") or {}):
            return fail(sha, "MM04 replay schema lacks typed check_record", policy)

        for workflow in ("supernova-pr-target-admission.yml", "supernova-comment-admission.yml", "supernova-open-pr-reconciler.yml"):
            text = (tmp / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
            for needle in ("runs-on: ubuntu-24.04", "python-version: '3.13.15'", "assert_validator_environment.py"):
                if needle not in text:
                    return fail(sha, workflow + " missing privileged environment gate " + needle, policy)

        liveness = (tmp / "scripts/liveness_contract_guard.py").read_text(encoding="utf-8")
        if "minimum_worker_liveness_window_minutes" not in liveness:
            return fail(sha, "liveness guard does not enforce publication slack", policy)
        open_prs = (tmp / "scripts/reconcile_open_prs.py").read_text(encoding="utf-8")
        for needle in ("GEN11_COHORT", "GEN11_VERIFIER_HEAD", "exact_gen11_zero_credit_terminal_parent"):
            if needle not in open_prs:
                return fail(sha, "Gen11 zero-credit successor escape incomplete: " + needle, policy)

        control = load(tmp, "config/countable_control_set_v25.json")
        if control.get("schema_version") != "PS-COUNTABLE-CONTROL-SET-2.5-24":
            return fail(sha, "future countable control set is not v24", policy)
        required_frozen = set(policy["required_root_candidate_paths"]) | set(policy["seed_paths"])
        if not required_frozen.issubset(set(control.get("required_control_paths") or [])):
            return fail(sha, "v24 control set does not freeze full epoch9 repair surface", policy)
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)

    post(sha, policy["seed_context"], "success", "one-shot accepted-main root epoch9 integrity repair seed PASS")
    print("ROOT EPOCH9 INTEGRITY REPAIR SEED PASS", number, sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
