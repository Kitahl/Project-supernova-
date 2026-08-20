#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import shutil
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/" + REPO
OWNER = REPO.split("/", 1)[0]
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
BOOTSTRAP_CONTEXT = "supernova/bootstrap-admission"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_HEAD_PREFIXES = ("hardening/", "rev4/")
ALLOWED_PREFIXES = ("config/", "schemas/", "scripts/", "tests/", ".github/workflows/", "docs/")
ALLOWED_EXACT = {
    "PROTOCOL.md",
    "WORKER_PROTOCOL.md",
    "BRANCH_PROTOCOL.md",
    "BRANCH_WORKER_PROTOCOL.md",
    "SESSION_STANDARD.md",
    "plan/PLAN.json",
    "requirements-validation.lock",
    "branch/CONFIG.json",
}
FORBIDDEN_EXACT = {
    "state/CURRENT.json",
    "config/worker_auth.json",
    "config/task_registry_v25.json",
    "benchmark/registry.json",
    "benchmark/pool_disposition.json",
    "research/open_lanes.json",
}
FORBIDDEN_PREFIXES = (
    "state/",
    "control/",
    "assignments/",
    "reports/",
    "verification/",
    "integration/",
    "history/",
    "transitions/",
    "superseded/",
    "benchmark/",
    "research/",
)


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
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def post(state: str, sha: str, description: str):
    api(
        "/statuses/" + sha,
        "POST",
        {"state": state, "context": BOOTSTRAP_CONTEXT, "description": description[:140]},
    )


def run(cmd, cwd: pathlib.Path):
    p = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return p.returncode, p.stdout


def load_json(root: pathlib.Path, path: str):
    return json.loads((root / path).read_text(encoding="utf-8"))


def fail(sha: str | None, reason: str):
    if sha and HEX40.fullmatch(sha):
        post("failure", sha, "trusted bootstrap refused: " + reason)
    print("BOOTSTRAP REFUSED:", reason)
    return 1


def main():
    root = pathlib.Path.cwd().resolve()
    try:
        number = int(os.environ.get("PR_NUMBER", "0"))
    except ValueError:
        number = 0
    if number <= 0:
        print("BOOTSTRAP REFUSED: missing PR number")
        return 1

    pr = api(f"/pulls/{number}")
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    head_sha = head.get("sha")
    head_ref = head.get("ref")
    head_repo = (head.get("repo") or {}).get("full_name")
    author = (pr.get("user") or {}).get("login")

    if os.environ.get("CANDIDATE_DIAGNOSTICS_RESULT") != "success":
        return fail(head_sha, "read-only candidate diagnostics did not succeed")
    if base.get("ref") != "main":
        return fail(head_sha, "base is not main")
    if head_repo != REPO or author != OWNER:
        return fail(head_sha, "same-repository owner-authored PR required")
    if not isinstance(head_ref, str) or not head_ref.startswith(ALLOWED_HEAD_PREFIXES):
        return fail(head_sha, "head prefix not bootstrap-eligible")
    if not isinstance(head_sha, str) or not HEX40.fullmatch(head_sha):
        return fail(None, "invalid head SHA")

    state = load_json(root, "state/CURRENT.json")
    if state.get("calibration_streak") != 0:
        return fail(head_sha, "calibration streak must be zero before authority bootstrap")
    if state.get("fresh_allowed_globally") is not False:
        return fail(head_sha, "fresh work must be disabled before authority bootstrap")

    rc, out = run(["git", "rev-parse", "HEAD"], root)
    trusted = out.strip()
    if rc or not HEX40.fullmatch(trusted):
        return fail(head_sha, "cannot resolve exact accepted main")
    run(["git", "fetch", "--no-tags", "origin", f"pull/{number}/head"], root)
    rc, _ = run(["git", "merge-base", "--is-ancestor", trusted, head_sha], root)
    if rc:
        return fail(head_sha, "PR head does not descend from exact accepted main")
    rc, out = run(["git", "diff", "--name-only", trusted + "..." + head_sha], root)
    if rc:
        return fail(head_sha, "cannot enumerate candidate changes")
    changed = [x for x in out.splitlines() if x]
    if not changed:
        return fail(head_sha, "empty authority change")
    for path in changed:
        if path in FORBIDDEN_EXACT or path.startswith(FORBIDDEN_PREFIXES):
            return fail(head_sha, "state/scientific/runtime-sensitive path changed: " + path)
        if path not in ALLOWED_EXACT and not path.startswith(ALLOWED_PREFIXES):
            return fail(head_sha, "path outside automated bootstrap allowlist: " + path)
        rc, tree = run(["git", "ls-tree", head_sha, "--", path], root)
        if rc:
            return fail(head_sha, "cannot inspect candidate git mode: " + path)
        if tree.strip() and tree.split(None, 1)[0] != "100644":
            return fail(head_sha, "non-regular candidate path: " + path)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"supernova-bootstrap-{number}-"))
    try:
        rc, out = run(["git", "worktree", "add", "--detach", str(tmp), head_sha], root)
        if rc:
            return fail(head_sha, "cannot create candidate data worktree")
        plan = load_json(tmp, "plan/PLAN.json")
        freeze = load_json(tmp, "config/protocol_freeze.json")
        admission = load_json(tmp, "config/admission_authority.json")
        bootstrap = load_json(tmp, "config/authority_bootstrap_v25.json")
        policy = load_json(tmp, "config/repo_policy.json")
        if plan.get("task_network_plan_id") != PLAN or plan.get("protocol_version") != "2.5":
            return fail(head_sha, "plan identity/protocol drift")
        if plan.get("specification_revision") != 4:
            return fail(head_sha, "Revision 4 freeze violated")
        if freeze.get("frozen_protocol_version") != "2.5" or freeze.get("frozen_specification_revision") != 4:
            return fail(head_sha, "protocol freeze weakened")
        if admission.get("required_status_creator") != "github-actions[bot]":
            return fail(head_sha, "admission status source weakened")
        if admission.get("candidate_code_execution_with_status_write_token") != "FORBIDDEN":
            return fail(head_sha, "candidate-code privilege boundary weakened")
        if admission.get("ref_selectable_dispatch_with_status_write_token") != "FORBIDDEN":
            return fail(head_sha, "ref-selectable privileged dispatch enabled")
        if bootstrap.get("trusted_executable_source") != "EXACT_ACCEPTED_MAIN":
            return fail(head_sha, "bootstrap trusted-source invariant weakened")
        if bootstrap.get("candidate_diagnostics") != "READ_ONLY_SEPARATE_JOB_REQUIRED":
            return fail(head_sha, "bootstrap candidate isolation weakened")
        if bootstrap.get("state_or_scientific_change") != "FORBIDDEN_IN_AUTOMATED_BOOTSTRAP":
            return fail(head_sha, "bootstrap state/science exclusion weakened")
        if policy.get("fresh_gate") != "BLOCK":
            return fail(head_sha, "fresh gate weakened")
    except Exception as exc:
        return fail(head_sha, "candidate policy parse/check failed: " + repr(exc))
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)], root)
        shutil.rmtree(tmp, ignore_errors=True)

    post("success", head_sha, "trusted-main authority bootstrap PASS; candidate diagnostics were read-only")
    print("AUTHORITY BOOTSTRAP PASS", number, head_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
