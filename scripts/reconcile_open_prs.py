#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/" + REPO
ALLOWED_HEAD_PREFIXES = ("hardening/", "transition/", "ps/consolidate/", "rev4/")
CONTEXTS = (
    "supernova/static-control",
    "supernova/report-admission",
    "supernova/transition-admission",
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")


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


def post_status(sha: str, context: str, state: str, description: str):
    api(
        "/statuses/" + sha,
        "POST",
        {
            "state": state,
            "context": context,
            "description": description[:140],
        },
    )


def run(cmd, cwd: pathlib.Path, env=None):
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return p.returncode, p.stdout


def changed_files(repo: pathlib.Path, base: str, head: str):
    rc, out = run(["git", "diff", "--name-only", base + "..." + head], repo)
    if rc:
        raise RuntimeError("git diff failed: " + out[-1000:])
    return [x for x in out.splitlines() if x]


def static_control(worktree: pathlib.Path):
    errors = []
    commands = [
        ["python", "scripts/validate_bus.py"],
        ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
    ]
    for cmd in commands:
        rc, out = run(cmd, worktree)
        if rc:
            errors.append(" ".join(cmd) + " failed: " + out[-1200:])
    try:
        auth = json.loads((worktree / "config/worker_auth.json").read_text(encoding="utf-8"))
        freeze = json.loads((worktree / "config/protocol_freeze.json").read_text(encoding="utf-8"))
        if auth.get("scheme") != "PS-HMAC-SHA256-CANONICAL-REPORT-2":
            errors.append("worker_auth scheme is not HMAC-2")
        if freeze.get("frozen_protocol_version") != "2.5":
            errors.append("protocol freeze is not 2.5")
        for wf in (worktree / ".github/workflows").glob("*.yml"):
            for line in wf.read_text(encoding="utf-8").splitlines():
                if re.search(r"^\s*-\s+uses:", line):
                    ref = line.split("@", 1)[1].split()[0] if "@" in line else ""
                    if not re.fullmatch(r"[0-9a-f]{40}", ref):
                        errors.append(f"unpinned action in {wf.name}: {line.strip()}")
    except Exception as exc:
        errors.append("static metadata check failed: " + repr(exc))
    return errors


def report_admission(worktree: pathlib.Path, base_sha: str, changed: list[str]):
    if "state/CURRENT.json" not in changed:
        return []
    errors = []
    rc, old_text = run(["git", "show", base_sha + ":state/CURRENT.json"], worktree)
    if rc:
        return ["cannot read base state: " + old_text[-800:]]
    try:
        old = json.loads(old_text)
        cohort = old["active_cohort_id"]
        root = worktree / "history" / cohort
        con = json.loads((root / "CONSOLIDATION.json").read_text(encoding="utf-8"))
        ver = json.loads((root / "verification.json").read_text(encoding="utf-8"))
        integ = json.loads((root / "integration.json").read_text(encoding="utf-8"))
        if ver.get("verdict") != "VERIFIED_COMPLETE": errors.append("verification verdict not complete")
        if ver.get("partition_exhaustive_verified") is not True: errors.append("verification partition not exhaustive")
        if ver.get("quarantined_report_refs") or ver.get("missing_workers"): errors.append("verification has quarantine/missing")
        if ver.get("liveness_complete") is not True: errors.append("verification liveness incomplete")
        if ver.get("required_post_write_ci_context") != "supernova/report-admission": errors.append("wrong post-write CI context")
        if integ.get("verification_head_sha") != con.get("verification_head_sha"): errors.append("integration/consolidation verifier head mismatch")
        if integ.get("verification_external_ci_context") != "supernova/report-admission": errors.append("integration wrong external CI context")
        if integ.get("verification_external_ci_status") != "PASS": errors.append("integration external CI not PASS")
        if integ.get("verification_external_ci_source") != "github-actions[bot]": errors.append("integration CI source not github-actions[bot]")
        if integ.get("verification_external_ci_observed_after_receipt") is not True: errors.append("integration CI not observed after receipt")
    except Exception as exc:
        errors.append("report admission: " + repr(exc))
    return errors


def transition_admission(worktree: pathlib.Path, base_sha: str, head_sha: str, changed: list[str]):
    if "state/CURRENT.json" not in changed:
        return []
    env = os.environ.copy()
    env["SUPERNOVA_BASE_SHA"] = base_sha
    env["SUPERNOVA_HEAD_SHA"] = head_sha
    errors = []
    for script in ("scripts/parent_lineage_guard.py", "scripts/transition_guard.py"):
        rc, out = run(["python", script], worktree, env=env)
        if rc:
            errors.append(script + " failed: " + out[-1200:])
    return errors


def validate_pr(repo_root: pathlib.Path, pr: dict):
    number = pr["number"]
    head_ref = pr["head"]["ref"]
    head_sha = pr["head"]["sha"]
    base_sha = pr["base"]["sha"]
    if not head_ref.startswith(ALLOWED_HEAD_PREFIXES):
        return
    if not HEX40.fullmatch(head_sha) or not HEX40.fullmatch(base_sha):
        return
    run(["git", "fetch", "--no-tags", "origin", f"pull/{number}/head"], repo_root)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"supernova-pr-{number}-"))
    try:
        rc, out = run(["git", "worktree", "add", "--detach", str(tmp), head_sha], repo_root)
        if rc:
            for ctx in CONTEXTS:
                post_status(head_sha, ctx, "failure", "scheduled PR reconciler could not create worktree")
            return
        changed = changed_files(repo_root, base_sha, head_sha)
        static_errors = static_control(tmp)
        report_errors = report_admission(tmp, base_sha, changed)
        transition_errors = transition_admission(tmp, base_sha, head_sha, changed)
        results = {
            "supernova/static-control": static_errors,
            "supernova/report-admission": report_errors,
            "supernova/transition-admission": transition_errors,
        }
        for ctx, errors in results.items():
            if errors:
                post_status(head_sha, ctx, "failure", "FAIL " + errors[0])
            else:
                label = "PASS" if "state/CURRENT.json" in changed else "PASS/N-A non-transition"
                post_status(head_sha, ctx, "success", "scheduled GitHub Actions exact-head " + label)
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)], repo_root)
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    root = pathlib.Path.cwd()
    prs = api("/pulls?state=open&base=main&per_page=50") or []
    for pr in prs:
        if pr.get("draft"):
            continue
        try:
            validate_pr(root, pr)
        except Exception as exc:
            sha = (pr.get("head") or {}).get("sha")
            if sha and HEX40.fullmatch(sha):
                for ctx in CONTEXTS:
                    post_status(sha, ctx, "failure", "scheduled PR reconciler exception: " + repr(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
