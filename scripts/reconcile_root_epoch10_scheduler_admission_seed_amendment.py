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
POLICY_PATH = "config/root_epoch10_scheduler_admission_seed_amendment_v25.json"
STATE_PATH = "state/CURRENT.json"
STATE_BLOB = "826fcdd01701eda04a177f86748878b3755badc0"
ACTIONS_CREATOR = "github-actions[bot]"
REQUIRED_IMPORT_TOKEN = "import strict_json"
WORKERS = {"MF01", "MF02", "MF03", "MF04", "MF05", "MM01", "MM02", "MM03", "MM04", "MM05", "MM07", "EXT01"}
FIRST_SEED_PATHS = {
    "config/root_epoch10_scheduler_admission_seed_v25.json",
    "scripts/reconcile_root_epoch10_scheduler_admission_seed.py",
    ".github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml",
    "tests/test_root_epoch10_scheduler_admission_seed.py",
}
AMENDMENT_PATHS = {
    "config/root_epoch10_scheduler_admission_seed_amendment_v25.json",
    "scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py",
    ".github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml",
    "tests/test_root_epoch10_scheduler_admission_seed_amendment.py",
}


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
        post(sha, policy["seed_context"], "failure", "root10 seed amendment refused: " + reason)
        for context in policy["required_status_contexts"]:
            post(sha, context, "failure", "root10 seed amendment refused: " + reason)
    print("ROOT EPOCH10 SCHEDULER-ADMISSION SEED AMENDMENT REFUSED:", reason)
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


def source_bound_status(sha: str, context: str, state: str = "success"):
    rows = api("/commits/" + sha + "/statuses?per_page=100") or []
    matches = [r for r in rows if r.get("context") == context]
    if not matches:
        return False
    row = matches[0]
    return row.get("state") == state and (row.get("creator") or {}).get("login") == ACTIONS_CREATOR


def exact_gen12_mm06_terminal(policy: dict):
    cohort = policy["required_active_cohort"]
    G = policy["required_generation_head"]
    vh = branch_head("ps/verify/" + cohort)
    if not vh or vh == G:
        return False, "terminal Gen12 verifier receipt missing"
    try:
        meta, receipt = content("verification/" + cohort + ".json", vh)
    except Exception as exc:
        return False, "terminal Gen12 verifier unreadable: " + repr(exc)
    if meta.get("sha") != policy["required_verifier_blob"]:
        return False, "terminal Gen12 verifier blob mismatch"
    if receipt.get("cohort_id") != cohort or receipt.get("generation_head_sha") != G:
        return False, "terminal Gen12 verifier identity mismatch"
    if receipt.get("verdict") != policy["required_verifier_verdict"] or receipt.get("calibration_pass") is not False:
        return False, "terminal Gen12 verifier is not zero-credit INCOMPLETE"
    if receipt.get("safe_report_refs") != [] or receipt.get("quarantined_report_refs") != []:
        return False, "terminal Gen12 verifier must preserve zero SAFE / zero quarantine"
    if set(receipt.get("missing_workers") or []) != WORKERS:
        return False, "terminal Gen12 verifier must preserve exact 12 MISSING"
    if receipt.get("liveness_complete") is not False or receipt.get("partition_exhaustive_verified") is not True:
        return False, "terminal Gen12 verifier liveness/partition mismatch"
    if not source_bound_status(vh, "supernova/branch-verify", "success"):
        return False, "terminal Gen12 branch-verify success not source-bound"
    return True, ""


def trusted_deadlock_present(root: pathlib.Path, policy: dict):
    wf = (root / policy["deadlock_proof"]["workflow_path"]).read_text(encoding="utf-8")
    reconciler = (root / policy["deadlock_proof"]["reconciler_path"]).read_text(encoding="utf-8")
    if policy["deadlock_proof"]["required_import_token"] != REQUIRED_IMPORT_TOKEN:
        return False, "trusted deadlock policy import token mismatch"
    if REQUIRED_IMPORT_TOKEN not in reconciler:
        return False, "trusted reconciler no longer imports strict_json"
    if "for name in ('reconcile_branch_rest.py','reconcile_v25_admission.py')" not in wf:
        return False, "trusted REST workflow no longer has the proven two-file /tmp loader"
    if "strict_json.py" in wf:
        return False, "trusted REST workflow already transports strict_json dependency"
    if "python3 /tmp/reconcile_v25_admission.py" not in wf:
        return False, "trusted REST workflow no longer executes reconciler from /tmp"
    return True, ""


def candidate_semantics(tmp: pathlib.Path, trusted: str, policy: dict):
    problems = []
    state = load(tmp, STATE_PATH)
    if blob_at("HEAD", STATE_PATH) != STATE_BLOB or state.get("active_cohort_id") != policy["required_active_cohort"]:
        problems.append("candidate mutated canonical Gen12 state")
    epoch = load(tmp, "config/root_tcb_epoch_v25.json")
    if epoch.get("epoch") != 10 or epoch.get("schema_version") != "PS-ROOT-TCB-EPOCH-2.5-10":
        problems.append("candidate root epoch did not migrate to 10")
    if epoch.get("previous_epoch_blob") != blob_at("HEAD", "config/root_tcb_epoch_v25.json"):
        problems.append("root10 does not bind accepted root9 blob")
    if epoch.get("root_epoch10_scheduler_admission_seed_install_commit_sha") != policy["first_seed_install_commit_sha"]:
        problems.append("root10 lost first scheduler seed binding")
    if epoch.get("root_epoch10_scheduler_admission_seed_amendment_install_commit_sha") != trusted:
        problems.append("root10 does not bind exact amendment install commit")
    for key, path in (
        ("root_epoch10_scheduler_admission_seed_amendment_policy_blob", "config/root_epoch10_scheduler_admission_seed_amendment_v25.json"),
        ("root_epoch10_scheduler_admission_seed_amendment_reconciler_blob", "scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py"),
        ("root_epoch10_scheduler_admission_seed_amendment_workflow_blob", ".github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml"),
    ):
        if epoch.get(key) != blob_at("HEAD", path):
            problems.append("root10 amendment blob binding mismatch " + key)
    rest = (tmp / ".github/workflows/supernova-rest-branch-reconciler.yml").read_text(encoding="utf-8")
    for token in (
        "actions/checkout@",
        "actions/setup-python@",
        "requirements-validation.lock",
        "scripts/assert_validator_environment.py",
        "python scripts/reconcile_branch_rest.py",
        "python scripts/reconcile_v25_admission.py",
    ):
        if token not in rest:
            problems.append("repaired REST admission workflow missing " + token)
    for forbidden in ("python3 /tmp/reconcile_v25_admission.py", "for name in ('reconcile_branch_rest.py','reconcile_v25_admission.py')"):
        if forbidden in rest:
            problems.append("repaired REST admission workflow retains broken /tmp loader")
    countable = load(tmp, "config/countable_control_set_v25.json")
    if countable.get("schema_version") != "PS-COUNTABLE-CONTROL-SET-2.5-25":
        problems.append("countable control did not migrate to v25")
    if countable.get("canonical_scheduled_task_count") != 15 or countable.get("replacement_scheduled_task") != "FORBIDDEN":
        problems.append("countable control does not preserve exact 15 canonical sessions")
    registry = load(tmp, "config/task_registry_v25.json")
    if registry.get("active_task_count") != 15 or registry.get("no_sixteenth_lane") is not True or registry.get("same_task_session_each_run") is not True:
        problems.append("task registry does not preserve exact 15 same sessions")
    for path in (
        "tests/test_root_epoch6_repair.py",
        "tests/test_gen9_reset_compat_root.py",
        "tests/test_gen10_zero_credit_terminal_transition.py",
        "tests/test_gen11_zero_credit_terminal_transition.py",
        "tests/test_root_epoch9_integrity_repair.py",
        "tests/test_structural_status_single_writer.py",
    ):
        text = (tmp / path).read_text(encoding="utf-8")
        if "root10" not in text.lower() and "epoch 10" not in text.lower():
            problems.append(path + " was not explicitly migrated while preserving historical assertions")
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
    if base.get("ref") != "main" or (head.get("repo") or {}).get("full_name") != REPO or (pr.get("user") or {}).get("login") != OWNER:
        return fail(sha, "same-repository owner PR to main required", policy)
    if not str(head.get("ref", "")).startswith(policy["head_prefix_required"]):
        return fail(sha, "head prefix not root10-amendment eligible", policy)
    state = load(ROOT, STATE_PATH)
    if state.get("active_cohort_id") != policy["required_active_cohort"] or state.get("generation_head_sha") != policy["required_generation_head"]:
        return fail(sha, "amendment only applies while exact Gen12 is canonical", policy)
    if blob_at("HEAD", STATE_PATH) != STATE_BLOB or state.get("calibration_streak") != 0 or state.get("fresh_allowed_globally") is not False:
        return fail(sha, "Gen12 state/streak/fresh binding changed", policy)
    current_epoch = load(ROOT, "config/root_tcb_epoch_v25.json")
    if current_epoch.get("epoch") != 9:
        return fail(sha, "amendment is inert outside root epoch9", policy)
    for path in FIRST_SEED_PATHS:
        if not (ROOT / path).is_file():
            return fail(sha, "first root10 seed installation incomplete: " + path, policy)
    ok, reason = exact_gen12_mm06_terminal(policy)
    if not ok:
        return fail(sha, reason, policy)
    ok, reason = trusted_deadlock_present(ROOT, policy)
    if not ok:
        return fail(sha, reason, policy)
    run(["git", "fetch", "--no-tags", "origin", f"pull/{number}/head"])
    if run(["git", "merge-base", "--is-ancestor", trusted, sha])[0] != 0:
        return fail(sha, "candidate does not descend from exact accepted main", policy)
    rc, out = run(["git", "diff", "--name-only", trusted + "..." + sha])
    changed = [line for line in out.splitlines() if line]
    required = set(policy["required_root_candidate_paths"])
    if rc or set(changed) != required:
        return fail(sha, "root10 candidate diff is not exact amended scheduler-admission repair set", policy)
    if (FIRST_SEED_PATHS | AMENDMENT_PATHS).intersection(changed):
        return fail(sha, "trusted seed or amendment self-modification forbidden", policy)
    for prefix in policy["forbidden_candidate_prefixes"]:
        if any(path.startswith(prefix) for path in changed):
            return fail(sha, "forbidden active evidence/runtime/scientific path changed", policy)
    for path in changed:
        rc, tree = run(["git", "ls-tree", sha, "--", path])
        if rc or (tree.strip() and tree.split(None, 1)[0] != "100644"):
            return fail(sha, "non-regular changed path " + path, policy)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-root10-amendment-"))
    try:
        rc, _ = run(["git", "worktree", "add", "--detach", str(tmp), sha])
        if rc:
            return fail(sha, "cannot create candidate data worktree", policy)
        if load(tmp, STATE_PATH) != state:
            return fail(sha, "candidate changes canonical state", policy)
        problems = candidate_semantics(tmp, trusted, policy)
        if problems:
            return fail(sha, problems[0], policy)
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = ""
        for cmd in (["python", "scripts/validate_bus.py"], ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]):
            rc, output = run(cmd, cwd=tmp, env=env)
            if rc:
                return fail(sha, "candidate diagnostics failed: " + output[-1400:], policy)
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)
    post(sha, policy["seed_context"], "success", "root10 scheduler-admission seed amendment PASS")
    for context in policy["required_status_contexts"]:
        post(sha, context, "success", "trusted root10 scheduler-admission amendment PASS")
    print("ROOT EPOCH10 SCHEDULER-ADMISSION SEED AMENDMENT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
