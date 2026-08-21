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
CONTEXTS = ("supernova/static-control", "supernova/report-admission", "supernova/transition-admission")
BOOTSTRAP_CONTEXT = "supernova/bootstrap-admission"
BOOTSTRAP_CREATOR = "github-actions[bot]"
BOOTSTRAP_WORKFLOW = ".github/workflows/supernova-authority-bootstrap.yml"
RUN_URL_RE = re.compile(r"^https://github\.com/" + re.escape(REPO) + r"/actions/runs/([0-9]+)$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
GEN6_BOOTSTRAP_COHORT = "CAL-BR-006-v251-433ad83a"
GEN6_BOOTSTRAP_STATE_BLOB = "b08c9ae01be715ad25059d3dfcb72febb4794c38"
GEN7_INVALIDATED_COHORT = "CAL-BR-007-v25-c13b6ee4"
GEN7_INVALIDATED_STATE_BLOB = "856481759722e23ff9a652ce140f304efe13b023"
GEN7_INVALIDATED_HEAD = "7c182fb7ce3a3941f86f7508bbb4a18152402bb8"
GEN7_INVALIDATED_DISPOSITION = "INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS"
AUTHORITY_PREFIXES = ("scripts/", "tests/", "schemas/", "config/", ".github/workflows/")
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
    api("/statuses/" + sha, "POST", {"state": state, "context": context, "description": description[:140]})


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
    return sorted(path for path in changed if path in AUTHORITY_PATHS or path.startswith(AUTHORITY_PREFIXES))


def expected_bootstrap_description(pr_number: int, head_sha: str, base_sha: str):
    return f"trusted-main bootstrap PASS pr={pr_number} head={head_sha} base={base_sha}"[:140]


def trusted_bootstrap_success(head_sha: str, base_sha: str | None = None, pr_number: int | None = None):
    """Require exactly one completed designated bootstrap workflow run."""
    if not (
        isinstance(base_sha, str)
        and HEX40.fullmatch(base_sha)
        and isinstance(pr_number, int)
        and pr_number > 0
    ):
        return False

    statuses = api("/commits/" + head_sha + "/statuses?per_page=100") or []
    expected_desc = expected_bootstrap_description(pr_number, head_sha, base_sha)
    valid_run_ids: list[str] = []
    for status in statuses:
        if status.get("context") != BOOTSTRAP_CONTEXT or status.get("state") != "success":
            continue
        if (status.get("creator") or {}).get("login") != BOOTSTRAP_CREATOR:
            continue
        if status.get("description") != expected_desc:
            continue
        match = RUN_URL_RE.fullmatch(str(status.get("target_url") or ""))
        if not match:
            continue
        run_id = match.group(1)
        try:
            run_obj = api("/actions/runs/" + run_id) or {}
        except Exception:
            continue
        if run_obj.get("id") != int(run_id):
            continue
        if run_obj.get("path") != BOOTSTRAP_WORKFLOW:
            continue
        if run_obj.get("event") != "pull_request_target":
            continue
        if run_obj.get("status") != "completed" or run_obj.get("conclusion") != "success":
            continue
        if (run_obj.get("repository") or {}).get("full_name") != REPO:
            continue
        if (run_obj.get("actor") or {}).get("login") != OWNER:
            continue
        valid_run_ids.append(run_id)
    return len(set(valid_run_ids)) == 1


# Backward source-regression marker retained intentionally: trusted_bootstrap_success(head_sha)

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
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = ""
    rc, out = run([sys.executable, "scripts/validate_bus.py"], trusted_root, env=env)
    return [] if rc == 0 else ["trusted main canonical validator failed: " + out[-1200:]]


def trusted_static_control(trusted_root: pathlib.Path, candidate_root: pathlib.Path):
    env = os.environ.copy()
    env["SUPERNOVA_VALIDATE_ROOT"] = str(candidate_root)
    rc, out = run(
        [sys.executable, str(trusted_root / "scripts/validate_bus.py")],
        trusted_root,
        env=env,
    )
    return [] if rc == 0 else ["trusted static validation failed: " + out[-1200:]]


def exact_noncountable_gen6_bootstrap_parent(candidate_root: pathlib.Path, base_sha: str, old: dict):
    rc, out = run(["git", "rev-parse", base_sha + ":state/CURRENT.json"], candidate_root)
    return (
        not rc
        and out.strip() == GEN6_BOOTSTRAP_STATE_BLOB
        and old.get("generation_seq") == 6
        and old.get("active_cohort_id") == GEN6_BOOTSTRAP_COHORT
        and old.get("calibration_countable_current") is False
        and old.get("calibration_streak") == 0
        and old.get("fresh_allowed_globally") is False
        and old.get("repo_policy_status") == "UNVERIFIED_BLOCKING"
        and old.get("generation_head_sha") == "c86c091c3be840559a46670218705be1277acd8f"
    )


def exact_invalidated_gen7_repair_parent(candidate_root: pathlib.Path, base_sha: str, old: dict, changed: list[str]):
    """One exact zero-credit escape hatch for the immutable invalidated Gen7 parent.

    This is not a generic waiver. The base state blob, old cohort/head, successor
    generation/streak/fresh flags, parent linkage, candidate diff and explicit
    supersession receipt must all match exactly. Any near miss falls back to the
    ordinary clean-history admission rule.
    """
    rc, out = run(["git", "rev-parse", base_sha + ":state/CURRENT.json"], candidate_root)
    if rc or out.strip() != GEN7_INVALIDATED_STATE_BLOB:
        return False
    if not (
        old.get("generation_seq") == 7
        and old.get("active_cohort_id") == GEN7_INVALIDATED_COHORT
        and old.get("generation_head_sha") == GEN7_INVALIDATED_HEAD
        and old.get("calibration_countable_current") is True
        and old.get("calibration_streak") == 0
        and old.get("fresh_allowed_globally") is False
        and old.get("repo_policy_status") == "VERIFIED_PROTECTED_SOURCE_BOUND"
    ):
        return False
    try:
        new = json.loads((candidate_root / "state/CURRENT.json").read_text(encoding="utf-8"))
        cohort = new["active_cohort_id"]
        control_path = new["active_control_manifest_path"]
        assignment_path = new["active_assignment_path"]
        liveness_path = f"liveness/{cohort}.json"
        superseded_path = "superseded/CAL-BR-007-v25-c13b6ee4.json"
        control = json.loads((candidate_root / control_path).read_text(encoding="utf-8"))
        assignment = json.loads((candidate_root / assignment_path).read_text(encoding="utf-8"))
        liveness = json.loads((candidate_root / liveness_path).read_text(encoding="utf-8"))
        superseded = json.loads((candidate_root / superseded_path).read_text(encoding="utf-8"))
    except Exception:
        return False

    exact_changed = {"state/CURRENT.json", control_path, assignment_path, liveness_path, superseded_path}
    if set(changed) != exact_changed:
        return False
    if not (
        new.get("generation_seq") == 8
        and new.get("active_parent_state_git_identity") == GEN7_INVALIDATED_STATE_BLOB
        and new.get("calibration_streak") == 0
        and new.get("calibration_countable_current") is True
        and new.get("fresh_allowed_globally") is False
        and new.get("repo_policy_status") == "VERIFIED_PROTECTED_SOURCE_BOUND"
        and cohort != GEN7_INVALIDATED_COHORT
        and GEN7_INVALIDATED_COHORT in set(new.get("superseded_cohorts", []))
        and new.get("expected_base_head") == base_sha
    ):
        return False
    for obj in (control, assignment):
        if not (
            obj.get("cohort_id") == cohort
            and obj.get("generation_seq") == 8
            and obj.get("parent_state_git_identity") == GEN7_INVALIDATED_STATE_BLOB
            and obj.get("calibration_countable") is True
            and obj.get("expected_base_head") == base_sha
        ):
            return False
    if not (
        liveness.get("cohort_id") == cohort
        and liveness.get("generation_seq") == 8
        and liveness.get("generation_root_sha") == base_sha
    ):
        return False
    if not (
        superseded.get("cohort_id") == GEN7_INVALIDATED_COHORT
        and superseded.get("generation_seq") == 7
        and superseded.get("generation_head_sha") == GEN7_INVALIDATED_HEAD
        and superseded.get("state_blob") == GEN7_INVALIDATED_STATE_BLOB
        and superseded.get("disposition") == GEN7_INVALIDATED_DISPOSITION
        and superseded.get("clean_cohort_credit") == 0
        and superseded.get("calibration_streak_credit") == 0
        and superseded.get("fresh_evidence_credit") == 0
    ):
        return False
    return True


def report_admission(candidate_root: pathlib.Path, base_sha: str, changed: list[str]):
    if "state/CURRENT.json" not in changed:
        return []
    errors = []
    rc, old_text = run(["git", "show", base_sha + ":state/CURRENT.json"], candidate_root)
    if rc:
        return ["cannot read base state: " + old_text[-800:]]
    try:
        old = json.loads(old_text)
        if exact_noncountable_gen6_bootstrap_parent(candidate_root, base_sha, old):
            return []
        if exact_invalidated_gen7_repair_parent(candidate_root, base_sha, old, changed):
            return []
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
    base = pr.get("base") or {}
    head_sha = head.get("sha")
    base_sha = base.get("sha")
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
    if authority_drift and not trusted_bootstrap_success(head_sha, base_sha, number):
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
        rc, _ = run(["git", "worktree", "add", "--detach", str(tmp), head_sha], repo_root)
        if rc:
            fail_contexts(head_sha, "trusted admission could not create candidate data worktree")
            return
        results = {
            "supernova/static-control": trusted_static_control(repo_root, tmp),
            "supernova/report-admission": report_admission(tmp, trusted, changed),
            "supernova/transition-admission": transition_admission(repo_root, tmp, trusted, head_sha, changed),
        }
        for ctx, errors in results.items():
            if errors:
                post_status(head_sha, ctx, "failure", "FAIL " + errors[0])
            else:
                label = "PASS" if "state/CURRENT.json" in changed else "PASS/N-A non-transition"
                prefix = "trusted-bootstrap-run" if authority_drift else "trusted-main"
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
