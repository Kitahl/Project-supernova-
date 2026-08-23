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
POLICY_PATH = "config/root_epoch10_scheduler_admission_seed_v25.json"
STATE_PATH = "state/CURRENT.json"
STATE_BLOB = "826fcdd01701eda04a177f86748878b3755badc0"
ACTIONS_CREATOR = "github-actions[bot]"
WORKERS = {"MF01", "MF02", "MF03", "MF04", "MF05", "MM01", "MM02", "MM03", "MM04", "MM05", "MM07", "EXT01"}


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


def run(cmd, cwd=ROOT, env=None):
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
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
        post(sha, policy["seed_context"], "failure", "epoch10 scheduler seed refused: " + reason)
        for context in policy["required_status_contexts"]:
            post(sha, context, "failure", "epoch10 scheduler seed refused: " + reason)
    print("ROOT EPOCH10 SCHEDULER-ADMISSION SEED REFUSED:", reason)
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


def source_bound_success(sha: str, context: str):
    rows = api("/commits/" + sha + "/statuses?per_page=100") or []
    matches = [r for r in rows if r.get("context") == context]
    if not matches:
        return False
    row = matches[0]
    return row.get("state") == "success" and (row.get("creator") or {}).get("login") == ACTIONS_CREATOR


def exact_gen12_terminal_chain(policy: dict):
    cohort = policy["required_active_cohort"]
    G = policy["required_generation_head"]
    vb = "ps/verify/" + cohort
    vh = branch_head(vb)
    if not vh or vh == G:
        return False, "terminal Gen12 verifier receipt missing"
    try:
        meta, receipt = content("verification/" + cohort + ".json", vh)
    except Exception as exc:
        return False, "terminal Gen12 verifier receipt unreadable: " + repr(exc)
    if meta.get("sha") != policy["required_verifier_blob"]:
        return False, "terminal Gen12 verifier blob mismatch"
    expected = {
        "cohort_id": cohort,
        "generation_head_sha": G,
        "verdict": policy["required_verifier_verdict"],
        "calibration_pass": policy["required_verifier_calibration_pass"],
        "partition_exhaustive_verified": True,
        "liveness_complete": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            return False, "terminal Gen12 verifier mismatch " + key
    if receipt.get("safe_report_refs") != [] or receipt.get("quarantined_report_refs") != []:
        return False, "terminal Gen12 verifier must preserve zero SAFE / zero quarantine"
    if set(receipt.get("missing_workers") or []) != set(policy["required_missing_workers"]) or set(receipt.get("missing_workers") or []) != WORKERS:
        return False, "terminal Gen12 verifier partition is not exact 12 MISSING"
    if not source_bound_success(vh, "supernova/branch-verify"):
        return False, "terminal Gen12 branch-verify success not source-bound"
    if not source_bound_success(vh, "supernova/report-admission"):
        return False, "terminal Gen12 report-admission success not source-bound"

    ib = "ps/integrate/" + cohort
    ih = branch_head(ib)
    if not ih or ih == G:
        return False, "terminal Gen12 MF06 receipt missing"
    try:
        _, integ = content("integration/" + cohort + ".json", ih)
    except Exception as exc:
        return False, "terminal Gen12 MF06 receipt unreadable: " + repr(exc)
    if integ.get("cohort_id") != cohort or integ.get("generation_head_sha") != G:
        return False, "terminal Gen12 MF06 identity mismatch"
    if integ.get("verification_verdict") != "INCOMPLETE" or integ.get("calibration_pass") is not False:
        return False, "terminal Gen12 MF06 must preserve zero-credit INCOMPLETE disposition"
    if integ.get("safe_report_refs") != [] or integ.get("quarantines") != [] or set(integ.get("missing_workers") or []) != WORKERS:
        return False, "terminal Gen12 MF06 partition must be exact 0 SAFE / 0 quarantine / 12 missing"
    if not source_bound_success(ih, "supernova/branch-integrate"):
        return False, "terminal Gen12 branch-integrate success not source-bound"
    return True, ""


def candidate_semantics(tmp: pathlib.Path, trusted: str, policy: dict):
    problems = []
    epoch = load(tmp, "config/root_tcb_epoch_v25.json")
    if epoch.get("epoch") != 10 or epoch.get("schema_version") != "PS-ROOT-TCB-EPOCH-2.5-10":
        problems.append("root epoch did not migrate to 10")
    if epoch.get("previous_epoch_blob") != blob_at("HEAD", "config/root_tcb_epoch_v25.json"):
        problems.append("root epoch10 does not bind accepted epoch9 blob")
    seed_expected = {
        "root_epoch10_scheduler_admission_seed_install_commit_sha": trusted,
        "root_epoch10_scheduler_admission_seed_policy_blob": blob_at("HEAD", policy["seed_paths"][0]),
        "root_epoch10_scheduler_admission_seed_reconciler_blob": blob_at("HEAD", policy["seed_paths"][1]),
        "root_epoch10_scheduler_admission_seed_workflow_blob": blob_at("HEAD", policy["seed_paths"][2]),
    }
    for key, value in seed_expected.items():
        if epoch.get(key) != value:
            problems.append("root epoch10 seed binding mismatch " + key)

    marker = load(tmp, policy["one_shot_marker_path"])
    marker_expected = {
        "schema_version": "PS-ROOT-EPOCH10-SCHEDULER-ADMISSION-EPOCH-2.5-1",
        "protocol_version": "2.5",
        "task_network_plan_id": PLAN,
        "previous_root_epoch": 9,
        "new_root_epoch": 10,
        "source_cohort": policy["required_active_cohort"],
        "source_generation_head": policy["required_generation_head"],
        "calibration_credit_effect": 0,
        "fresh_science_effect": "NONE",
        "runtime_effect": "NONE",
    }
    for key, value in marker_expected.items():
        if marker.get(key) != value:
            problems.append("root epoch10 marker mismatch " + key)

    authority = load(tmp, "config/admission_authority.json")
    if authority.get("root_tcb_epoch") != 10:
        problems.append("admission authority root epoch != 10")
    for path in (policy["seed_paths"][2], policy["one_shot_marker_path"], "scripts/scheduler_admission_guard.py", "schemas/scheduler_manifest.schema.json", "schemas/preactivation_receipt.schema.json", "schemas/scheduler_admission.schema.json"):
        inventory = set(authority.get("authoritative_status_workflows") or []) | set(authority.get("trusted_authority_helpers") or []) | set(authority.get("trusted_validator_entrypoints") or [])
        if path not in inventory:
            problems.append("admission authority inventory missing " + path)

    bootstrap = load(tmp, "config/authority_bootstrap_v25.json")
    if bootstrap.get("root_tcb_epoch_required") != 10:
        problems.append("authority bootstrap did not migrate to root epoch10")
    checker = (tmp / "scripts/reconcile_authority_bootstrap.py").read_text(encoding="utf-8")
    if '"root_tcb_epoch": 10' not in checker or '"root_tcb_epoch_required": 10' not in checker:
        problems.append("authority bootstrap checker did not migrate to root epoch10")

    policy_delta = load(tmp, "config/generation_delta_policy_v25.json")
    countable = policy_delta.get("countable") or {}
    if countable.get("exact_cardinality") != 4 or "scheduler/{cohort}.json" not in set(countable.get("exact_path_templates") or []):
        problems.append("countable generation delta does not freeze scheduler manifest as fourth path")

    control_schema = load(tmp, "schemas/control.schema.json")
    required = set(control_schema.get("required") or [])
    for field in ("scheduler_manifest_path", "scheduler_manifest_git_identity", "scheduler_admission_required"):
        if field not in required:
            problems.append("control schema does not require " + field)

    for schema_path, schema_id in (
        ("schemas/scheduler_manifest.schema.json", "PS-SCHEDULER-MANIFEST-2.5-1"),
        ("schemas/preactivation_receipt.schema.json", "PS-PREACTIVATION-RECEIPT-2.5-1"),
        ("schemas/scheduler_admission.schema.json", "PS-SCHEDULER-ADMISSION-2.5-1"),
    ):
        schema = load(tmp, schema_path)
        if schema.get("title") is None or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            problems.append(schema_path + " is not a closed Draft-2020-12 contract")
        if schema_id not in json.dumps(schema, sort_keys=True, allow_nan=False):
            problems.append(schema_path + " missing schema identity " + schema_id)

    guard = (tmp / "scripts/scheduler_admission_guard.py").read_text(encoding="utf-8")
    for needle in (
        "PREACTIVATION_WAIT",
        "production_not_before",
        "scheduler_cadence_seconds",
        "max_attempt_duration_seconds",
        "scheduler_jitter_budget_seconds",
        "behavioral_config_sha256",
        "normalized_first_production_utc",
        "raw auth material",
        "stage and promote",
    ):
        if needle not in guard:
            problems.append("scheduler admission guard missing invariant token " + needle)
    transition = (tmp / "scripts/transition_guard.py").read_text(encoding="utf-8")
    if "scheduler_admission_guard" not in transition or "validate_scheduler_admission" not in transition:
        problems.append("transition guard does not mechanically invoke scheduler admission")

    registry = load(tmp, "config/task_registry_v25.json")
    if registry.get("active_task_count") != 15 or registry.get("no_sixteenth_lane") is not True:
        problems.append("task registry does not preserve exact 15-lane network")
    semantics = load(tmp, "config/task_registry_semantics_v25.json")
    text = json.dumps(semantics, sort_keys=True, allow_nan=False)
    for needle in ("SAME_TASK_SESSION", "PREACTIVATION", "NORMALIZED_SCHEDULER_READBACK", "NO_POST_ACTIVATION_CONSTRUCTIVE_REPAIR"):
        if needle not in text:
            problems.append("task registry semantics missing " + needle)

    countable_control = load(tmp, "config/countable_control_set_v25.json")
    required_paths = set(countable_control.get("required_control_paths") or [])
    for path in (
        "config/root_epoch10_scheduler_admission_seed_v25.json",
        "config/root_epoch10_scheduler_admission_epoch_v25.json",
        "scripts/reconcile_root_epoch10_scheduler_admission_seed.py",
        ".github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml",
        "scripts/scheduler_admission_guard.py",
        "schemas/scheduler_manifest.schema.json",
        "schemas/preactivation_receipt.schema.json",
        "schemas/scheduler_admission.schema.json",
        "tests/test_scheduler_admission_negative.py",
        "tests/test_root_epoch10_scheduler_admission.py",
    ):
        if path not in required_paths:
            problems.append("countable control surface missing " + path)
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
        return fail(sha, "head prefix not root-epoch10 eligible", policy)

    state = load(ROOT, STATE_PATH)
    if state.get("active_cohort_id") != policy["required_active_cohort"] or state.get("generation_head_sha") != policy["required_generation_head"]:
        return fail(sha, "seed only applies while exact Gen12 is canonical", policy)
    if blob_at("HEAD", STATE_PATH) != STATE_BLOB:
        return fail(sha, "canonical Gen12 state blob changed", policy)
    if state.get("calibration_streak") != 0 or state.get("fresh_allowed_globally") is not False:
        return fail(sha, "streak must be zero and fresh disabled", policy)
    current_epoch = load(ROOT, "config/root_tcb_epoch_v25.json")
    if current_epoch.get("epoch") != policy["required_current_root_epoch"]:
        return fail(sha, "one-shot seed is inert outside root epoch9", policy)
    if (ROOT / policy["one_shot_marker_path"]).exists():
        return fail(sha, "root epoch10 scheduler-admission marker already exists", policy)
    ok, reason = exact_gen12_terminal_chain(policy)
    if not ok:
        return fail(sha, reason, policy)

    run(["git", "fetch", "--no-tags", "origin", f"pull/{number}/head"])
    if run(["git", "merge-base", "--is-ancestor", trusted, sha])[0] != 0:
        return fail(sha, "candidate does not descend from exact accepted main", policy)
    rc, out = run(["git", "diff", "--name-only", trusted + "..." + sha])
    changed = [line for line in out.splitlines() if line]
    required = set(policy["required_root_candidate_paths"])
    if rc or set(changed) != required:
        return fail(sha, "root candidate diff is not exact required scheduler-admission repair set", policy)
    if set(policy["seed_paths"]).intersection(changed):
        return fail(sha, "seed self-modification forbidden", policy)
    for prefix in policy["forbidden_candidate_prefixes"]:
        if any(path.startswith(prefix) for path in changed):
            return fail(sha, "forbidden active evidence/runtime/scientific path changed", policy)
    for path in changed:
        rc, tree = run(["git", "ls-tree", sha, "--", path])
        if rc or (tree.strip() and tree.split(None, 1)[0] != "100644"):
            return fail(sha, "non-regular changed path " + path, policy)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-root-epoch10-scheduler-seed-"))
    try:
        rc, _ = run(["git", "worktree", "add", "--detach", str(tmp), sha])
        if rc:
            return fail(sha, "cannot create candidate data worktree", policy)
        if load(tmp, STATE_PATH) != state:
            return fail(sha, "state changed in root epoch10 candidate", policy)
        plan = load(tmp, "plan/PLAN.json")
        if plan.get("task_network_plan_id") != PLAN or plan.get("protocol_version") != "2.5" or plan.get("specification_revision") != 4:
            return fail(sha, "plan/protocol/revision drift", policy)
        problems = candidate_semantics(tmp, trusted, policy)
        if problems:
            return fail(sha, problems[0], policy)
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = ""
        for cmd in (["python", "scripts/validate_bus.py"], ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]):
            rc, output = run(cmd, cwd=tmp, env=env)
            if rc:
                return fail(sha, "candidate diagnostics failed: " + output[-1000:], policy)
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)

    post(sha, policy["seed_context"], "success", "epoch10 scheduler-admission root seed PASS")
    for context in policy["required_status_contexts"]:
        post(sha, context, "success", "trusted root epoch10 scheduler-admission seed PASS")
    print("ROOT EPOCH10 SCHEDULER-ADMISSION SEED PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
