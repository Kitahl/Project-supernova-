#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/" + REPO
OWNER = REPO.split("/", 1)[0]
ALLOWED_HEAD_PREFIXES = ("hardening/", "transition/", "ps/consolidate/", "rev4/")
CONTEXTS = (
    "supernova/static-control",
    "supernova/report-admission",
    "supernova/transition-admission",
)
BOOTSTRAP_CONTEXT = "supernova/bootstrap-admission"
BOOTSTRAP_CREATOR = "github-actions[bot]"
HEX40 = re.compile(r"^[0-9a-f]{40}$")

AUTHORITY_PREFIXES = (
    "scripts/",
    "tests/",
    "schemas/",
    "config/",
    ".github/workflows/",
)
AUTHORITY_PATHS = {
    "PROTOCOL.md",
    "BRANCH_PROTOCOL.md",
    "BRANCH_WORKER_PROTOCOL.md",
    "SESSION_STANDARD.md",
    "plan/PLAN.json",
    "requirements-validation.lock",
    "branch/CONFIG.json",
    "research/open_lanes.json",
    "benchmark/pool_disposition.json",
}


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
        {"state": state, "context": context, "description": description[:140]},
    )


def fail_contexts(sha: str, description: str):
    for ctx in CONTEXTS:
        post_status(sha, ctx, "failure", description)


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


def authority_path_changes(changed: list[str]):
    return sorted(
        path
        for path in changed
        if path in AUTHORITY_PATHS or path.startswith(AUTHORITY_PREFIXES)
    )


def trusted_bootstrap_success(head_sha: str):
    statuses = api("/commits/" + head_sha + "/statuses?per_page=100") or []
    for status in statuses:
        if status.get("context") != BOOTSTRAP_CONTEXT:
            continue
        creator = (status.get("creator") or {}).get("login")
        return status.get("state") == "success" and creator == BOOTSTRAP_CREATOR
    return False


def pr_metadata_errors(pr: dict):
    errors = []
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    head_ref = head.get("ref")
    head_sha = head.get("sha")
    head_repo = (head.get("repo") or {}).get("full_name")
    user = (pr.get("user") or {}).get("login")
    if base.get("ref") != "main":
        errors.append("PR base is not main")
    if head_repo != REPO:
        errors.append("PR head repository is not canonical repository")
    if user != OWNER:
        errors.append("PR author is not repository owner")
    if not isinstance(head_ref, str) or not head_ref.startswith(ALLOWED_HEAD_PREFIXES):
        errors.append("PR head prefix is not admitted")
    if not isinstance(head_sha, str) or not HEX40.fullmatch(head_sha):
        errors.append("PR head SHA is invalid")
    return errors


def trusted_main_sha(repo: pathlib.Path):
    rc, out = run(["git", "rev-parse", "HEAD"], repo)
    sha = out.strip()
    if rc or not HEX40.fullmatch(sha):
        raise RuntimeError("cannot resolve exact trusted main HEAD")
    return sha


def is_ancestor(repo: pathlib.Path, ancestor: str, descendant: str):
    rc, _ = run(["git", "merge-base", "--is-ancestor", ancestor, descendant], repo)
    return rc == 0


def changed_file_mode_errors(repo: pathlib.Path, head_sha: str, changed: list[str]):
    errors = []
    for path in changed:
        rc, out = run(["git", "ls-tree", head_sha, "--", path], repo)
        if rc:
            errors.append("cannot inspect git mode for " + path)
            continue
        if not out.strip():
            continue
        mode = out.split(None, 1)[0]
        if mode != "100644":
            errors.append(f"non-regular candidate path {path} mode={mode}")
    return errors


def trusted_self_check(trusted_root: pathlib.Path):
    errors = []
    for cmd in (
        [sys.executable, "scripts/validate_bus.py"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
    ):
        rc, out = run(cmd, trusted_root)
        if rc:
            errors.append("trusted main self-check failed: " + " ".join(cmd) + ": " + out[-1200:])
    return errors


def trusted_static_control(trusted_root: pathlib.Path, candidate_root: pathlib.Path):
    env = os.environ.copy()
    env["SUPERNOVA_VALIDATE_ROOT"] = str(candidate_root)
    rc, out = run([sys.executable, str(trusted_root / "scripts/validate_bus.py")], trusted_root, env=env)
    return [] if rc == 0 else ["trusted static validation failed: " + out[-1200:]]


def first_countable_bootstrap_report_errors(old: dict, new: dict):
    """Return None when normal prior-cohort report admission is required.

    A single fail-closed exception exists only for the transition from a
    deliberately non-countable bootstrap cohort into the first countable v2.5
    cohort. That historical bootstrap must never be retrofitted into a clean
    report envelope merely to start countable calibration.
    """
    if not (
        old.get("calibration_countable_current") is False
        and new.get("calibration_countable_current") is True
    ):
        return None

    errors = []
    if old.get("calibration_streak") != 0:
        errors.append("first-countable bootstrap old calibration streak is not zero")
    if new.get("calibration_streak") != 0:
        errors.append("first-countable bootstrap new calibration streak is not zero")
    if new.get("fresh_allowed_globally") is not False:
        errors.append("first-countable bootstrap fresh evidence must remain disabled")
    if new.get("repo_policy_status") != "VERIFIED_PROTECTED_SOURCE_BOUND":
        errors.append("first-countable bootstrap source-bound repository policy is not verified")
    if new.get("generation_seq") != old.get("generation_seq", -1) + 1:
        errors.append("first-countable bootstrap generation is not the exact successor")
    old_cohort = old.get("active_cohort_id")
    if not old_cohort or old_cohort not in (new.get("superseded_cohorts") or []):
        errors.append("first-countable bootstrap does not explicitly supersede old cohort")
    return errors


def report_admission(candidate_root: pathlib.Path, base_sha: str, changed: list[str]):
    if "state/CURRENT.json" not in changed:
        return []
    errors = []
    rc, old_text = run(["git", "show", base_sha + ":state/CURRENT.json"], candidate_root)
    if rc:
        return ["cannot read base state: " + old_text[-800:]]
    try:
        old = json.loads(old_text)
        new = json.loads((candidate_root / "state" / "CURRENT.json").read_text(encoding="utf-8"))
        bootstrap_errors = first_countable_bootstrap_report_errors(old, new)
        if bootstrap_errors is not None:
            return bootstrap_errors

        cohort = old["active_cohort_id"]
        root = candidate_root / "history" / cohort
        con = json.loads((root / "CONSOLIDATION.json").read_text(encoding="utf-8"))
        ver = json.loads((root / "verification.json").read_text(encoding="utf-8"))
        integ = json.loads((root / "integration.json").read_text(encoding="utf-8"))
        if ver.get("verdict") != "VERIFIED_COMPLETE":
            errors.append("verification verdict not complete")
        if ver.get("partition_exhaustive_verified") is not True:
            errors.append("verification partition not exhaustive")
        if ver.get("quarantined_report_refs") or ver.get("missing_workers"):
            errors.append("verification has quarantine/missing")
        if ver.get("liveness_complete") is not True:
            errors.append("verification liveness incomplete")
        if ver.get("required_post_write_ci_context") != "supernova/report-admission":
            errors.append("wrong post-write CI context")
        if integ.get("verification_head_sha") != con.get("verification_head_sha"):
            errors.append("integration/consolidation verifier head mismatch")
        if integ.get("verification_external_ci_context") != "supernova/report-admission":
            errors.append("integration wrong external CI context")
        if integ.get("verification_external_ci_status") != "PASS":
            errors.append("integration external CI not PASS")
        if integ.get("verification_external_ci_source") != "github-actions[bot]":
            errors.append("integration CI source not github-actions[bot]")
        if integ.get("verification_external_ci_observed_after_receipt") is not True:
            errors.append("integration CI not observed after receipt")
    except Exception as exc:
        errors.append("report admission: " + repr(exc))
    return errors


def transition_admission(
    trusted_root: pathlib.Path,
    candidate_root: pathlib.Path,
    base_sha: str,
    head_sha: str,
    changed: list[str],
):
    if "state/CURRENT.json" not in changed:
        return []
    env = os.environ.copy()
    env["SUPERNOVA_VALIDATE_ROOT"] = str(candidate_root)
    env["SUPERNOVA_BASE_SHA"] = base_sha
    env["SUPERNOVA_HEAD_SHA"] = head_sha
    errors = []
    for script in ("scripts/parent_lineage_guard.py", "scripts/transition_guard.py"):
        rc, out = run([sys.executable, str(trusted_root / script)], trusted_root, env=env)
        if rc:
            errors.append(script + " failed: " + out[-1200:])
    return errors


def validate_pr(repo_root: pathlib.Path, pr: dict, trusted_errors=None):
    head = pr.get("head") or {}
    head_sha = head.get("sha")
    metadata_errors = pr_metadata_errors(pr)
    if metadata_errors:
        if isinstance(head_sha, str) and HEX40.fullmatch(head_sha):
            fail_contexts(head_sha, "trusted admission refused: " + metadata_errors[0])
        return

    if trusted_errors:
        fail_contexts(head_sha, trusted_errors[0])
        return

    number = pr["number"]
    trusted = trusted_main_sha(repo_root)
    run(["git", "fetch", "--no-tags", "origin", f"pull/{number}/head"], repo_root)
    if not is_ancestor(repo_root, trusted, head_sha):
        fail_contexts(head_sha, "trusted admission refused: PR head does not descend from exact current main")
        return

    changed = changed_files(repo_root, trusted, head_sha)
    authority_drift = authority_path_changes(changed)
    if authority_drift and not trusted_bootstrap_success(head_sha):
        fail_contexts(
            head_sha,
            "trusted admission refused: authority bytes changed without source-verified bootstrap: " + authority_drift[0],
        )
        return

    mode_errors = changed_file_mode_errors(repo_root, head_sha, changed)
    if mode_errors:
        fail_contexts(head_sha, "trusted admission refused: " + mode_errors[0])
        return

    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"supernova-pr-{number}-"))
    try:
        rc, out = run(["git", "worktree", "add", "--detach", str(tmp), head_sha], repo_root)
        if rc:
            fail_contexts(head_sha, "trusted admission could not create candidate data worktree")
            return

        static_errors = trusted_static_control(repo_root, tmp)
        report_errors = report_admission(tmp, trusted, changed)
        transition_errors = transition_admission(repo_root, tmp, trusted, head_sha, changed)
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
                prefix = "trusted-bootstrap" if authority_drift else "trusted-main"
                post_status(head_sha, ctx, "success", prefix + " exact-head " + label)
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)], repo_root)
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    root = pathlib.Path.cwd().resolve()
    trusted_errors = trusted_self_check(root)
    prs = api("/pulls?state=open&base=main&per_page=50") or []
    for pr in prs:
        if pr.get("draft"):
            continue
        try:
            validate_pr(root, pr, trusted_errors=trusted_errors)
        except Exception as exc:
            sha = (pr.get("head") or {}).get("sha")
            if sha and HEX40.fullmatch(sha):
                fail_contexts(sha, "trusted admission exception: " + repr(exc))
    return 1 if trusted_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
