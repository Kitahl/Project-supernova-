#!/usr/bin/env python3
from __future__ import annotations

import base64
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

from jsonschema import Draft202012Validator, FormatChecker

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import strict_json
from scheduler_admission_guard import WORKERS as SCHEDULER_WORKERS
from scheduler_admission_guard import validate_mm06_scheduler_admission

TRUSTED_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
OWNER = REPO.split("/", 1)[0]
API = "https://api.github.com/repos/" + REPO
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
GEN12_COHORT = "CAL-BR-012-v25-4ca0dec6"
GEN12_G = "b366cf01e64e1a00a2e566e14e25cc7c15ce523f"
GEN12_STATE_BLOB = "826fcdd01701eda04a177f86748878b3755badc0"
BRANCH_RECONCILER_WORKFLOW = ".github/workflows/supernova-branch-reconciler.yml"
RUN_URL_RE = re.compile(r"https://github\.com/[^/]+/[^/]+/actions/runs/(\d+)")
PREACTIVATION_WORKERS = set(SCHEDULER_WORKERS)
STATUS_INTEGRATION_ID = 15368
STATUS_EVENTS = {"schedule", "push", "repository_dispatch"}


def git(repo: pathlib.Path, *args: str) -> tuple[int, str, str]:
    p = subprocess.run(["git", "-C", str(repo), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def run(cmd: list[str], cwd: pathlib.Path, env: dict | None = None) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return p.returncode, p.stdout


def api(path: str):
    req = urllib.request.Request(API + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as response:
        return strict_json.loads(response.read().decode("utf-8"))


def load(path: pathlib.Path):
    return strict_json.loads(path.read_text(encoding="utf-8"))


def load_ref(repo: pathlib.Path, ref: str, path: str):
    rc, out, err = git(repo, "show", f"{ref}:{path}")
    if rc:
        raise ValueError(f"cannot read {path}@{ref}: {err}")
    return strict_json.loads(out)


def blob_at(repo: pathlib.Path, ref: str, path: str) -> str | None:
    rc, out, _ = git(repo, "rev-parse", f"{ref}:{path}")
    return out if rc == 0 and len(out) == 40 else None


def remote_head(repo: pathlib.Path, branch: str) -> str | None:
    rc, out, _ = git(repo, "rev-parse", f"refs/remotes/origin/{branch}")
    return out if rc == 0 else None


def changed(repo: pathlib.Path, base: str, head: str) -> list[str]:
    rc, out, err = git(repo, "diff", "--name-only", base, head)
    if rc:
        raise ValueError("cannot enumerate diff: " + err)
    return [line for line in out.splitlines() if line]


def changed_name_status(repo: pathlib.Path, base: str, head: str) -> list[tuple[str, str]]:
    rc, out, err = git(repo, "diff", "--name-status", "--no-renames", base, head)
    if rc:
        raise ValueError("cannot enumerate diff status: " + err)
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise ValueError("unexpected diff status row: " + line)
        rows.append((parts[0], parts[1]))
    return rows


def one_commit_child(repo: pathlib.Path, head: str, parent: str) -> bool:
    rc, out, _ = git(repo, "rev-list", "--parents", "-n", "1", head)
    return rc == 0 and out.split() == [head, parent]


def _trusted_main_head() -> str:
    rc, out, err = git(TRUSTED_ROOT, "rev-parse", "HEAD")
    if rc or len(out) != 40:
        raise ValueError("cannot resolve trusted main head: " + err)
    return out


def _status_integration_id(row: dict) -> int | None:
    parsed = urllib.parse.urlparse(str(row.get("avatar_url") or ""))
    parts = parsed.path.strip("/").split("/")
    return int(parts[1]) if len(parts) == 2 and parts[0] == "in" and parts[1].isdigit() else None


def _matching_current_status(sha: str, context: str, state: str, description: str) -> bool:
    combined = api(f"/commits/{sha}/status?per_page=100")
    statuses = combined.get("statuses") if isinstance(combined, dict) else None
    if not isinstance(statuses, list):
        raise ValueError("combined commit status response lacks statuses array")
    row = next((item for item in statuses if isinstance(item, dict) and item.get("context") == context), None)
    if row is None or row.get("state") != state or row.get("description") != description:
        return False
    if _status_integration_id(row) != STATUS_INTEGRATION_ID:
        return False
    match = RUN_URL_RE.fullmatch(str(row.get("target_url") or ""))
    if not match:
        return False
    workflow_run = api("/actions/runs/" + match.group(1)) or {}
    return (
        workflow_run.get("path") == BRANCH_RECONCILER_WORKFLOW
        and workflow_run.get("event") in STATUS_EVENTS
        and workflow_run.get("status") == "completed"
        and workflow_run.get("conclusion") == "success"
        and workflow_run.get("head_sha") == _trusted_main_head()
        and (workflow_run.get("repository") or {}).get("full_name") == REPO
        and (workflow_run.get("actor") or {}).get("login") == OWNER
    )


def post(sha: str, context: str, state: str, description: str) -> bool:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN missing")
    description = description[:140]
    try:
        if _matching_current_status(sha, context, state, description):
            return False
    except Exception as exc:
        print(f"Status dedup read unavailable for {sha} {context}; publishing replacement: {exc!r}")
    body = {"state": state, "context": context, "description": description}
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if run_id.isdigit():
        body["target_url"] = f"https://github.com/{REPO}/actions/runs/{run_id}"
    payload = strict_json.canonical_dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{API}/statuses/{sha}", data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    urllib.request.urlopen(req, timeout=30).read()
    return True


def _schema_errors(path: str, value) -> list[str]:
    schema = load(TRUSTED_ROOT / path)
    Draft202012Validator.check_schema(schema)
    return [f"{path}: {error.message}" for error in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value)]


def _generation_script_errors(repo: pathlib.Path, generation_head: str, branch: str, cohort: str) -> list[str]:
    errors: list[str] = []
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-generation-data-"))
    try:
        rc, output = run(["git", "worktree", "add", "--detach", str(tmp), generation_head], repo)
        if rc:
            return ["cannot materialize generation data: " + output[-800:]]
        env = os.environ.copy()
        env["SUPERNOVA_VALIDATE_ROOT"] = str(tmp)
        commands = (
            [sys.executable, str(TRUSTED_ROOT / "scripts/validate_branch_bus_v251.py"), "--branch", branch, "--generation-head", generation_head],
            [sys.executable, str(TRUSTED_ROOT / "scripts/generation_delta_guard.py"), "--root-sha", load(tmp / f"control/{cohort}.json")["generation_root_sha"], "--generation-head", generation_head, "--cohort", cohort, "--countable"],
            [sys.executable, str(TRUSTED_ROOT / "scripts/liveness_contract_guard.py"), "--root", str(tmp), "--cohort", cohort],
            [sys.executable, str(TRUSTED_ROOT / "scripts/scheduler_admission_guard.py"), "--root", str(tmp), "--cohort", cohort, "--no-admission"],
        )
        for command in commands:
            rc, output = run(command, TRUSTED_ROOT, env=env)
            if rc:
                errors.append(pathlib.Path(command[1]).name + " failed: " + output[-1000:])
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)], repo)
        shutil.rmtree(tmp, ignore_errors=True)
    return errors


def stage_pointer_errors(repo: pathlib.Path, pointer_head: str, base: str, head_ref: str, head_repo: str, author: str) -> tuple[list[str], dict | None]:
    errors: list[str] = []
    if head_repo != REPO:
        errors.append("staging pointer PR must be same-repository")
    if author != OWNER:
        errors.append("staging pointer PR must be owner-authored")
    try:
        if changed(repo, base, pointer_head) != ["state/STAGED.json"]:
            errors.append("staging pointer PR must change only state/STAGED.json")
        if not one_commit_child(repo, pointer_head, base):
            errors.append("staging pointer PR head must be exactly one commit child of stage base")
        pointer = load_ref(repo, pointer_head, "state/STAGED.json")
    except Exception as exc:
        return errors + [str(exc)], None
    errors.extend(_schema_errors("schemas/staged_candidate.schema.json", pointer))
    cohort = pointer.get("candidate_cohort_id")
    generation_head = pointer.get("generation_head_sha")
    generation_root = pointer.get("generation_root_sha")
    branch = pointer.get("generation_branch")
    expected_paths = [f"control/{cohort}.json", f"assignments/{cohort}.json", f"liveness/{cohort}.json", f"scheduler/{cohort}.json"]
    pointer_paths = [pointer.get("control_path"), pointer.get("assignment_path"), pointer.get("liveness_path"), pointer.get("scheduler_manifest_path")]
    if pointer.get("stage_base_head") != base or generation_root != base:
        errors.append("staging pointer base/root CAS mismatch")
    if head_ref != f"ps/stage/{cohort}":
        errors.append("staging pointer PR branch mismatch")
    if branch != f"ps/gen/{cohort}":
        errors.append("staging generation branch mismatch")
    if pointer_paths != expected_paths or len(set(pointer_paths)) != 4:
        errors.append("staging pointer does not name exact four generation paths")
    try:
        active = load_ref(repo, base, "state/CURRENT.json")
        active_blob = blob_at(repo, base, "state/CURRENT.json")
        if active_blob != pointer.get("active_state_git_identity"):
            errors.append("staging pointer active state blob mismatch")
        if active.get("active_cohort_id") == cohort or cohort in set(active.get("superseded_cohorts") or []):
            errors.append("staging candidate cohort is active or historically superseded")
        if active.get("generation_seq") == 12 and (
            active_blob != GEN12_STATE_BLOB
            or active.get("active_cohort_id") != GEN12_COHORT
            or active.get("generation_head_sha") != GEN12_G
        ):
            errors.append("Gen12 staging base does not match the immutable zero-credit terminal state")
        if active.get("generation_seq") != pointer.get("active_generation_seq") or pointer.get("candidate_generation_seq") != active.get("generation_seq", 0) + 1:
            errors.append("staging pointer generation sequence mismatch")
        if active.get("fresh_allowed_globally") is not False:
            errors.append("staging pointer base must remain fresh-disabled")
    except Exception as exc:
        errors.append("cannot bind active state: " + str(exc))
    if remote_head(repo, str(branch)) != generation_head:
        errors.append("generation branch missing or moved from staged G")
    if not one_commit_child(repo, str(generation_head), str(generation_root)):
        errors.append("generation G must be exactly one commit with sole parent R")
    try:
        observed_status = changed_name_status(repo, str(generation_root), str(generation_head))
        if observed_status != [("A", path) for path in sorted(expected_paths)]:
            errors.append("generation R..G must add exact four fresh C/A/L/S paths")
        for path in expected_paths:
            if blob_at(repo, str(generation_root), path) is not None:
                errors.append("generation path already exists at R: " + path)
        blobs = [blob_at(repo, str(generation_head), path) for path in expected_paths]
        expected_blobs = [pointer.get("control_git_identity"), pointer.get("assignment_git_identity"), pointer.get("liveness_git_identity"), pointer.get("scheduler_manifest_git_identity")]
        if blobs != expected_blobs or any(blob is None for blob in blobs):
            errors.append("staging pointer generation blob map mismatch")
        control, assignment, liveness, manifest = [load_ref(repo, str(generation_head), path) for path in expected_paths]
        for obj, schema_path in ((control,"schemas/control.schema.json"),(assignment,"schemas/assignment.schema.json"),(liveness,"schemas/cohort_liveness_contract.schema.json"),(manifest,"schemas/scheduler_manifest.schema.json")):
            errors.extend(_schema_errors(schema_path, obj))
        nonce = pointer.get("candidate_nonce")
        if any(obj.get("candidate_nonce") != nonce for obj in (control, assignment, liveness, manifest)):
            errors.append("C/A/L/S candidate nonce chain mismatch")
        if any(obj.get("generation_root_sha") != generation_root for obj in (control, assignment, liveness, manifest)):
            errors.append("C/A/L/S generation root chain mismatch")
        if control.get("control_release_commit_sha") != generation_root or control.get("expected_base_head") != generation_root or assignment.get("expected_base_head") != generation_root:
            errors.append("control/assignment generation-base binding mismatch")
        if "scheduler_manifest_git_identity" in control:
            errors.append("control contains forbidden future scheduler blob")
        if "generation_head_sha" in manifest:
            errors.append("manifest contains forbidden future generation head")
        if assignment.get("control_manifest_git_identity") != blobs[0] or liveness.get("control_manifest_git_identity") != blobs[0] or liveness.get("assignment_git_identity") != blobs[1]:
            errors.append("C -> A -> L blob DAG mismatch")
        if manifest.get("control_manifest_git_identity") != blobs[0] or manifest.get("assignment_git_identity") != blobs[1] or manifest.get("liveness_git_identity") != blobs[2]:
            errors.append("C/A/L -> S blob DAG mismatch")
        if manifest.get("generation_branch") != branch:
            errors.append("manifest generation branch mismatch")
        trusted_contract = load_ref(repo, base, "config/countable_control_set_v25.json")
        if control.get("required_control_paths") != trusted_contract.get("required_control_paths"):
            errors.append("candidate control required_control_paths differs from accepted-main contract")
    except Exception as exc:
        errors.append("cannot validate staged generation objects: " + str(exc))
    if not errors:
        errors.extend(_generation_script_errors(repo, str(generation_head), str(branch), str(cohort)))
    return errors, pointer


def _event_pr_current(number: int):
    return api(f"/pulls/{number}")


def reconcile_stage_event(repo: pathlib.Path) -> int:
    try:
        number = int(os.environ.get("SUPERNOVA_STAGE_PR_NUMBER", "0"))
    except ValueError:
        number = 0
    if number <= 0:
        print("STAGE RECONCILIATION FAILED: missing PR number")
        return 1
    observed = _event_pr_current(number)
    head = observed.get("head") or {}
    base = observed.get("base") or {}
    pointer_head = head.get("sha")
    base_sha = base.get("sha")
    event_head = os.environ.get("SUPERNOVA_STAGE_PR_HEAD_SHA")
    event_base = os.environ.get("SUPERNOVA_STAGE_PR_BASE_SHA")
    rc, trusted, _ = git(repo, "rev-parse", "HEAD")
    if rc or pointer_head != event_head or base_sha != event_base or base_sha != trusted:
        print("STAGE RECONCILIATION FAILED: event/current/main binding moved")
        return 1
    git(repo, "fetch", "--no-tags", "origin", "+refs/heads/ps/*:refs/remotes/origin/ps/*", f"pull/{number}/head")
    errors, pointer = stage_pointer_errors(repo, pointer_head, base_sha, head.get("ref"), (head.get("repo") or {}).get("full_name"), (observed.get("user") or {}).get("login"))
    generation_head = pointer.get("generation_head_sha") if isinstance(pointer, dict) else None
    current = _event_pr_current(number)
    current_head = (current.get("head") or {}).get("sha")
    current_base = (current.get("base") or {}).get("sha")
    if current_head != pointer_head or current_base != base_sha:
        errors.append("PR moved during generation validation")
    if isinstance(pointer, dict) and remote_head(repo, str(pointer.get("generation_branch"))) != generation_head:
        errors.append("generation branch moved during generation validation")
    if isinstance(generation_head, str) and len(generation_head) == 40:
        description = f"stage-generation {'FAIL' if errors else 'PASS'} pr={number} pointer={pointer_head} base={base_sha} G={generation_head}"
        post(generation_head, "supernova/branch-generation", "failure" if errors else "success", (errors[0] if errors else description))
    if errors:
        print("STAGE RECONCILIATION FAILED")
        for error in errors:
            print("-", error)
        return 1
    print(f"STAGE_RECONCILIATION_PASS pr={number} pointer={pointer_head} base={base_sha} G={generation_head}")
    return 0


def validate_branch(repo: pathlib.Path, branch: str, generation_head: str) -> tuple[bool, str]:
    head = remote_head(repo, branch)
    if not head:
        return False, "branch missing"
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="supernova-branch-data-"))
    try:
        rc, output = run(["git", "worktree", "add", "--detach", str(tmp), head], repo)
        if rc:
            return False, "candidate worktree failed"
        env = os.environ.copy()
        env["SUPERNOVA_VALIDATE_ROOT"] = str(tmp)
        command = [sys.executable, str(TRUSTED_ROOT / "scripts/validate_branch_bus_v251.py"), "--branch", branch, "--generation-head", generation_head]
        rc, output = run(command, TRUSTED_ROOT, env=env)
        line = output.strip().splitlines()[-1] if output.strip() else "validator failed"
        return rc == 0, line
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp)], repo)
        shutil.rmtree(tmp, ignore_errors=True)



def _exact_gen12_terminal_receipts(repo: pathlib.Path, state: dict) -> bool:
    if (
        state.get("active_cohort_id") != GEN12_COHORT
        or state.get("generation_seq") != 12
        or state.get("generation_head_sha") != GEN12_G
        or blob_at(repo, "HEAD", "state/CURRENT.json") != GEN12_STATE_BLOB
    ):
        return False
    worker_ids = set((state.get("worker_branches") or {}).keys())
    verifier_branch = state.get("verifier_branch")
    integrator_branch = state.get("integrator_branch")
    verifier_head = remote_head(repo, str(verifier_branch))
    integrator_head = remote_head(repo, str(integrator_branch))
    if not worker_ids or verifier_head in (None, GEN12_G) or integrator_head in (None, GEN12_G):
        return False
    try:
        verification = load_ref(repo, verifier_head, f"verification/{GEN12_COHORT}.json")
        integration = load_ref(repo, integrator_head, f"integration/{GEN12_COHORT}.json")
    except Exception:
        return False
    return (
        verification.get("generation_head_sha") == GEN12_G
        and verification.get("calibration_pass") is False
        and verification.get("verdict") == "INCOMPLETE"
        and set(verification.get("missing_workers") or []) == worker_ids
        and integration.get("generation_head_sha") == GEN12_G
        and integration.get("calibration_pass") is False
        and integration.get("verification_head_sha") == verifier_head
        and set(integration.get("missing_workers") or []) == worker_ids
    )

def main() -> int:
    repo = TRUSTED_ROOT
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request_target" or os.environ.get("SUPERNOVA_STAGE_PR_NUMBER"):
        return reconcile_stage_event(repo)
    git(repo, "fetch", "--prune", "origin", "+refs/heads/ps/*:refs/remotes/origin/ps/*")
    state = load(repo / "state/CURRENT.json")
    if state.get("transport_mode") != "BRANCH_GITOPS":
        print("No active branch-GitOps state; nothing to reconcile.")
        return 0
    cohort = state["active_cohort_id"]
    generation_head = state["generation_head_sha"]
    generation_branch = state["generation_branch"]
    head = remote_head(repo, generation_branch)
    if head != generation_head:
        post(generation_head, "supernova/branch-generation", "failure", "generation branch missing or moved")
    else:
        ok, message = validate_branch(repo, generation_branch, generation_head)
        post(generation_head, "supernova/branch-generation", "success" if ok else "failure", message)
    worker_branches = state["worker_branches"]
    awaiting_workers = []
    for worker, branch in worker_branches.items():
        head = remote_head(repo, branch)
        if head is None:
            continue
        if head == generation_head:
            awaiting_workers.append(worker)
            continue
        ok, message = validate_branch(repo, branch, generation_head)
        post(head, "supernova/branch-worker", "success" if ok else "failure", f"{worker}: {message}")
    terminal_gen12 = (
        len(awaiting_workers) == len(worker_branches)
        and _exact_gen12_terminal_receipts(repo, state)
    )
    if terminal_gen12:
        print("Gen12 terminal: preserving immutable 12-MISSING receipt; worker pending status write suppressed")
    elif awaiting_workers:
        post(
            generation_head,
            "supernova/branch-worker",
            "pending",
            f"awaiting immutable report: {len(awaiting_workers)}/{len(worker_branches)} lanes",
        )
    for kind, key, context in (("verify","verifier_branch","supernova/branch-verify"),("integrate","integrator_branch","supernova/branch-integrate")):
        branch = state[key]
        head = remote_head(repo, branch)
        if head is None:
            continue
        if head == generation_head:
            post(head, context, "pending", f"{kind}: awaiting receipt")
            continue
        ok, message = validate_branch(repo, branch, generation_head)
        post(head, context, "success" if ok else "failure", message)
    consolidation_branch = state.get("consolidation_branch")
    consolidation_head = remote_head(repo, consolidation_branch) if consolidation_branch else None
    if consolidation_head:
        receipt_path = f"history/{cohort}/CONSOLIDATION.json"
        if blob_at(repo, consolidation_head, receipt_path) is None:
            post(consolidation_head, "supernova/branch-consolidate", "pending", "awaiting consolidation receipt")
        else:
            try:
                receipt = load_ref(repo, consolidation_head, receipt_path)
                expected_main = receipt.get("expected_main_head")
                rc, _, _ = git(repo, "merge-base", "--is-ancestor", str(expected_main), consolidation_head)
                names = changed(repo, str(expected_main), consolidation_head) if rc == 0 else []
                allowed = all(
                    path.startswith(f"history/{cohort}/")
                    or path == "state/CURRENT.json"
                    or path == "benchmark/registry.json"
                    or path.startswith("control/")
                    or path.startswith("assignments/")
                    or path.startswith("liveness/")
                    or path.startswith("scheduler/")
                    or path.startswith("preactivation/")
                    or path.startswith("superseded/")
                    or path.startswith("transitions/")
                    for path in names
                )
                ok = rc == 0 and allowed and "state/CURRENT.json" in names
                post(
                    consolidation_head,
                    "supernova/branch-consolidate",
                    "success" if ok else "failure",
                    "consolidation CAS/diff policy " + ("PASS" if ok else "FAIL"),
                )
            except Exception as exc:
                post(consolidation_head, "supernova/branch-consolidate", "failure", "consolidation parse error " + str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
