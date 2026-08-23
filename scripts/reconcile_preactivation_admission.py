#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from jsonschema import Draft202012Validator, FormatChecker

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import strict_json

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
OWNER = REPO.split("/", 1)[0]
API = "https://api.github.com/repos/" + REPO
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
WORKERS = {"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
PREACTIVATION_ROLES = WORKERS | {"MF06"}
ROLES = PREACTIVATION_ROLES | {"MM06", "BIL00"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
RUN_URL_RE = re.compile(r"https://github\.com/[^/]+/[^/]+/actions/runs/(\d+)")
WORKFLOW = ".github/workflows/supernova-preactivation-admission.yml"
CONTEXT = "supernova/preactivation-admission"
APPROVED_MAX_ATTEMPT_DURATION_SECONDS = 600
APPROVED_SCHEDULER_JITTER_BUDGET_SECONDS = 60


def api(path: str, method: str = "GET", data=None):
    payload = None if data is None else strict_json.canonical_dumps(data).encode("utf-8")
    request = urllib.request.Request(API + path, data=payload, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        request.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        return strict_json.loads(raw.decode("utf-8")) if raw else None


def git(*args: str) -> tuple[int, str]:
    process = subprocess.run(
        ["git", "-C", str(ROOT), *args], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    return process.returncode, process.stdout.strip()


def load(path: str):
    return strict_json.loads((ROOT / path).read_text(encoding="utf-8"))


def trusted_retry_budget_seconds(manifest: dict, authority: dict | None = None) -> int:
    """Return only the exact accepted-main freshness window; candidate widening fails."""
    authority = authority if authority is not None else load("config/scheduler_attestation_authority_v25.json")
    approved = {
        "max_attempt_duration_seconds": APPROVED_MAX_ATTEMPT_DURATION_SECONDS,
        "scheduler_jitter_budget_seconds": APPROVED_SCHEDULER_JITTER_BUDGET_SECONDS,
    }
    if authority.get("retry_budget_authority") != "ACCEPTED_MAIN_EXACT_VALUES_CANDIDATE_OVERRIDE_FORBIDDEN":
        raise ValueError("scheduler retry budget authority mode mismatch")
    for field, exact in approved.items():
        if type(authority.get(field)) is not int or authority.get(field) != exact:
            raise ValueError("accepted-main scheduler retry budget authority mismatch: " + field)
        if type(manifest.get(field)) is not int or manifest.get(field) != exact:
            raise ValueError("candidate scheduler retry budget mismatch: " + field)
    return APPROVED_MAX_ATTEMPT_DURATION_SECONDS + APPROVED_SCHEDULER_JITTER_BUDGET_SECONDS


def load_ref(ref: str, path: str):
    rc, raw = git("show", f"{ref}:{path}")
    if rc:
        raise ValueError(f"cannot read {path}@{ref}")
    return strict_json.loads(raw)


def blob_at(ref: str, path: str) -> str | None:
    rc, value = git("rev-parse", f"{ref}:{path}")
    return value if rc == 0 and HEX40.fullmatch(value) else None


def schema_errors(path: str, value) -> list[str]:
    schema = load(path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [f"{path}: {error.message}" for error in validator.iter_errors(value)]


def canonical_without(value: dict, field: str) -> bytes:
    projected = dict(value)
    projected.pop(field, None)
    return strict_json.canonical_dumps(projected).encode("utf-8")


def secret_bytes(name: str, commitment: str) -> bytes:
    raw = os.environ.get(name, "")
    if not re.fullmatch(r"[0-9a-f]{64}", raw):
        raise ValueError(name + " missing or not a 256-bit lowercase hex key")
    key = bytes.fromhex(raw)
    if not hmac.compare_digest(hashlib.sha256(key).hexdigest(), commitment):
        raise ValueError(name + " does not match accepted-main public commitment")
    return key


def verify_tag(value: dict, field: str, key: bytes, domain: str) -> bool:
    observed = value.get(field)
    if not isinstance(observed, str):
        return False
    payload = domain.encode("utf-8") + b"\0" + canonical_without(value, field)
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(observed, expected)


def binding_description(number: int, role: str, head: str, base: str, head_ref: str, main: str) -> str:
    value = {"pr": number, "role": role, "head": head, "base": base, "head_ref": head_ref, "main": main}
    digest = hashlib.sha256(strict_json.canonical_dumps(value).encode("utf-8")).hexdigest()
    return f"preact PASS pr={number} role={role} main={main} bind={digest[:48]}"


def post(head: str, state: str, description: str) -> None:
    body = {"state": state, "context": CONTEXT, "description": description[:140]}
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if run_id.isdigit():
        body["target_url"] = f"https://github.com/{REPO}/actions/runs/{run_id}"
    api("/statuses/" + head, "POST", body)


def one_added_path_child(head: str, base: str, path: str, blob: str | None = None) -> bool:
    rc, parents = git("show", "-s", "--format=%P", head)
    rc2, names = git("diff-tree", "--no-commit-id", "--name-status", "--no-renames", "-r", head)
    expected = f"A\t{path}"
    return (
        rc == 0 and parents.split() == [base]
        and rc2 == 0 and names.strip() == expected
        and (blob is None or blob_at(head, path) == blob)
    )


def canonical_production_branches(manifest: dict) -> tuple[dict[str, str], list[str]]:
    cohort = manifest.get("cohort_id")
    tasks = {row.get("role_id"): row for row in manifest.get("tasks") or [] if isinstance(row, dict)}
    errors: list[str] = []
    if set(tasks) != ROLES or len(tasks) != 15:
        return {}, ["production branch inventory is not exact canonical 15"]
    expected: dict[str, str] = {}
    for role in sorted(ROLES):
        if role in WORKERS:
            branch = f"ps/work/{cohort}/{role}"
        elif role == "MM06":
            branch = f"ps/verify/{cohort}"
        elif role == "MF06":
            branch = f"ps/integrate/{cohort}"
        else:
            branch = f"ps/consolidate/{cohort}"
        expected[role] = branch
        if (tasks.get(role) or {}).get("production_branch") != branch:
            errors.append(role + " production branch is not canonical")
    if len(set(expected.values())) != 15:
        errors.append("canonical production branch inventory is not one branch per role")
    return expected, errors


def production_ref_snapshot(manifest: dict, generation_head: str) -> tuple[dict[str, str], list[str]]:
    branches, errors = canonical_production_branches(manifest)
    snapshot: dict[str, str] = {}
    for role, branch in branches.items():
        try:
            head = ((api("/branches/" + urllib.parse.quote(branch, safe="")) or {}).get("commit") or {}).get("sha")
        except Exception as exc:
            errors.append(role + " production branch head unavailable: " + repr(exc))
            continue
        snapshot[role] = head
        if head != generation_head:
            errors.append(role + " production branch is not unchanged at generation head G")
    return snapshot, errors


def production_ref_revalidation_errors(manifest: dict, generation_head: str, before: dict[str, str]) -> list[str]:
    after, errors = production_ref_snapshot(manifest, generation_head)
    if after != before:
        errors.append("production branch heads moved during trusted validation")
    return errors


def task_maps(manifest: dict, registry: dict) -> tuple[dict, dict]:
    tasks = {row.get("role_id"): row for row in manifest.get("tasks") or [] if isinstance(row, dict)}
    frozen = {row.get("role_id"): row for row in registry.get("tasks") or [] if isinstance(row, dict)}
    return tasks, frozen


def receipt_semantic_errors(receipt: dict, role: str, pointer: dict, manifest: dict, pointer_blob: str, authority: dict) -> list[str]:
    errors: list[str] = []
    tasks, frozen = task_maps(manifest, load("config/task_registry_v25.json"))
    task = tasks.get(role) or {}
    frozen_task = frozen.get(role) or {}
    expected = {
        "protocol_version": "2.5", "task_network_plan_id": PLAN,
        "candidate_nonce": pointer.get("candidate_nonce"),
        "cohort_id": pointer.get("candidate_cohort_id"),
        "generation_root_sha": pointer.get("generation_root_sha"),
        "generation_head_sha": pointer.get("generation_head_sha"),
        "staged_candidate_git_identity": pointer_blob,
        "scheduler_manifest_git_identity": pointer.get("scheduler_manifest_git_identity"),
        "role_id": role,
        "scheduler_task_id": frozen_task.get("scheduler_task_id"),
        "behavioral_config_sha256": task.get("behavioral_config_sha256"),
        "runtime_state_id": manifest.get("runtime_state_id"),
        "role_auth_scheme": "PS-HMAC-SHA256-PREACTIVATION-RECEIPT-1",
        "role_auth_commitment": (
            task.get("worker_auth_commitment") if role in WORKERS
            else authority.get("mf06_preactivation_key_commitment_sha256")
        ),
        "production_not_before_utc": manifest.get("production_not_before_utc"),
        "normalized_first_production_utc": task.get("normalized_first_production_utc"),
        "production_branch": task.get("production_branch"),
        "production_path": task.get("production_path"),
        "preactivation_branch": task.get("preactivation_branch"),
        "preactivation_path": task.get("preactivation_path"),
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            errors.append(f"{role} semantic mismatch: {key}")
    if receipt.get("challenge_occurrence_utc") not in set(task.get("challenge_occurrences_utc") or []):
        errors.append(role + " challenge is not a frozen manifest occurrence")
    return errors


def worker_keys(authority: dict) -> dict[str, bytes]:
    raw = os.environ.get("SUPERNOVA_WORKER_AUTH_KEYS_JSON", "")
    try:
        value = strict_json.loads(raw)
    except Exception as exc:
        raise ValueError("SUPERNOVA_WORKER_AUTH_KEYS_JSON unavailable: " + str(exc))
    if not isinstance(value, dict) or set(value) != WORKERS:
        raise ValueError("worker verifier-key bundle is not exact 12")
    commitments = load("config/worker_auth.json").get("commitments") or {}
    keys: dict[str, bytes] = {}
    for role in sorted(WORKERS):
        secret = value.get(role)
        if not isinstance(secret, str) or not re.fullmatch(r"[0-9a-f]{64}", secret):
            raise ValueError(role + " verifier key is not 256-bit lowercase hex")
        key = bytes.fromhex(secret)
        if not hmac.compare_digest(hashlib.sha256(key).hexdigest(), str(commitments.get(role))):
            raise ValueError(role + " verifier key commitment mismatch")
        keys[role] = key
    return keys


def role_hmac_valid(receipt: dict, key: bytes) -> bool:
    observed = receipt.get("role_auth_proof")
    expected = hmac.new(key, canonical_without(receipt, "role_auth_proof"), hashlib.sha256).hexdigest()
    return isinstance(observed, str) and hmac.compare_digest(observed, expected)


def inventory_errors(value: dict, pointer: dict, manifest: dict, pointer_blob: str, key: bytes, authority: dict) -> list[str]:
    errors = schema_errors("schemas/scheduler_inventory_attestation.schema.json", value)
    registry = load("config/task_registry_v25.json")
    tasks, frozen = task_maps(manifest, registry)
    expected_common = {
        "protocol_version": "2.5", "task_network_plan_id": PLAN,
        "candidate_nonce": pointer.get("candidate_nonce"), "cohort_id": pointer.get("candidate_cohort_id"),
        "generation_root_sha": pointer.get("generation_root_sha"), "generation_head_sha": pointer.get("generation_head_sha"),
        "staged_candidate_git_identity": pointer_blob,
        "scheduler_manifest_git_identity": pointer.get("scheduler_manifest_git_identity"),
        "attestor_scheduler_task_id": (frozen.get("BIL00") or {}).get("scheduler_task_id"),
    }
    for field, expected in expected_common.items():
        if value.get(field) != expected:
            errors.append("inventory semantic mismatch: " + field)
    before = {row.get("role_id"): row for row in value.get("before_tasks") or [] if isinstance(row, dict)}
    after = {row.get("role_id"): row for row in value.get("after_tasks") or [] if isinstance(row, dict)}
    if set(before) != set(frozen) or set(after) != set(frozen):
        errors.append("inventory role set is not exact canonical 15")
    if len(before) != 15 or len(after) != 15:
        errors.append("inventory does not contain exactly 15 unique canonical roles")
    for role in sorted(frozen):
        b, a, task, known = before.get(role) or {}, after.get(role) or {}, tasks.get(role) or {}, frozen.get(role) or {}
        if b.get("scheduler_task_id") != known.get("scheduler_task_id") or a.get("scheduler_task_id") != known.get("scheduler_task_id"):
            errors.append(role + " canonical scheduler task identity changed")
        if task.get("scheduler_task_id") != known.get("scheduler_task_id"):
            errors.append(role + " manifest scheduler task identity differs from frozen registry")
        if a.get("title") != known.get("title") or a.get("title") != task.get("canonical_title"):
            errors.append(role + " inventory title mismatch")
        for field in ("prompt_sha256","behavioral_config_sha256","normalized_schedule","timing_mode","default_timezone","enabled","execution_mode","preactivation_inactive_result"):
            if a.get(field) != task.get(field):
                errors.append(role + " inventory/manifest readback mismatch: " + field)
        if a.get("enabled") is not True:
            errors.append(role + " canonical task is not active after readback")
    expected_legacy = {(row.get("scheduler_task_id"), row.get("title")) for row in registry.get("noncanonical_supernova_tasks") or []}
    observed_legacy = {(row.get("scheduler_task_id"), row.get("title")) for row in value.get("noncanonical_supernova_tasks") or [] if isinstance(row, dict)}
    if observed_legacy != expected_legacy or len(value.get("noncanonical_supernova_tasks") or []) != len(expected_legacy):
        errors.append("inventory noncanonical Supernova task set is incomplete or changed")
    if value.get("observed_supernova_task_count") != 15 + len(expected_legacy):
        errors.append("inventory Supernova namespace cardinality mismatch")
    bil00_task = tasks.get("BIL00") or {}
    challenge = value.get("challenge_occurrence_utc")
    if challenge not in set(bil00_task.get("challenge_occurrences_utc") or []):
        errors.append("inventory challenge is not a frozen BIL00 scheduled occurrence")
    try:
        budget = trusted_retry_budget_seconds(manifest, authority)
        challenge_dt = parse_utc(str(challenge)); attested_dt = parse_utc(str(value.get("attested_at_utc")))
        if not challenge_dt <= attested_dt <= challenge_dt + timedelta(seconds=budget):
            errors.append("inventory attestation time is outside its frozen BIL00 challenge window")
    except Exception:
        errors.append("inventory challenge/attestation time invalid")
    if not verify_tag(value, "attestation_tag", key, authority["inventory_hmac_domain"]):
        errors.append("inventory attestation HMAC invalid")
    return errors


def parse_utc(value: str) -> datetime:
    observed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if observed.tzinfo is None:
        raise ValueError("timestamp is not offset-aware")
    return observed.astimezone(timezone.utc)


def source_status_observation(commit: str, role: str, cohort: str, generation_head: str, cutoff_utc: str) -> dict | None:
    branch = f"ps/preactivate/{cohort}/{role}"
    try:
        cutoff = parse_utc(cutoff_utc)
        prs = api("/pulls?state=all&head=" + urllib.parse.quote(REPO.split('/')[0] + ":" + branch, safe="") + "&base=" + urllib.parse.quote(f"ps/gen/{cohort}", safe="")) or []
    except Exception:
        return None
    candidates = [pr for pr in prs if (pr.get("head") or {}).get("sha") == commit and (pr.get("base") or {}).get("sha") == generation_head]
    if len(candidates) != 1:
        return None
    pr = candidates[0]
    rows = [row for row in api(f"/commits/{commit}/statuses?per_page=100") or [] if row.get("context") == CONTEXT]
    if not rows:
        return None
    row = max(rows, key=lambda item: int(item.get("id") or 0))
    try:
        created = parse_utc(str(row.get("created_at") or ""))
        if created > cutoff:
            return None
        manifest = load_ref(generation_head, f"scheduler/{cohort}.json")
        task = next(item for item in manifest.get("tasks") or [] if item.get("role_id") == role)
        receipt = load_ref(commit, f"preactivation/{cohort}/{role}.json")
        challenge_value = receipt.get("mm06_challenge_occurrence_utc") if role == "MM06" else receipt.get("challenge_occurrence_utc")
        if challenge_value not in set(task.get("challenge_occurrences_utc") or []):
            return None
        challenge = parse_utc(str(challenge_value))
        budget = trusted_retry_budget_seconds(manifest)
        if not challenge <= created <= challenge + timedelta(seconds=budget):
            return None
    except Exception:
        return None
    description = str(row.get("description") or "")
    match_description = re.fullmatch(rf"preact PASS pr={pr['number']} role={re.escape(role)} main=([0-9a-f]{{40}}) bind=([0-9a-f]{{48}})", description)
    if not match_description:
        return None
    source_main = match_description.group(1)
    expected = binding_description(pr["number"], role, commit, generation_head, branch, source_main)
    if row.get("state") != "success" or (row.get("creator") or {}).get("login") != "github-actions[bot]" or description != expected:
        return None
    match = RUN_URL_RE.fullmatch(str(row.get("target_url") or ""))
    if not match:
        return None
    run = api("/actions/runs/" + match.group(1)) or {}
    if run.get("path") != WORKFLOW or run.get("event") != "pull_request_target" or run.get("status") != "completed" or run.get("conclusion") != "success":
        return None
    # The repository's live workflow-run REST payload binds pull_request_target
    # head_sha/head_branch to the exact same-repository PR head/ref.
    if run.get("head_sha") != commit or run.get("head_branch") not in (None, branch):
        return None
    if (run.get("repository") or {}).get("full_name") != REPO or (run.get("actor") or {}).get("login") != OWNER:
        return None
    rc, _ = git("merge-base", "--is-ancestor", source_main, git_main_head())
    durable_pointer = f"staging/{cohort}.json" if blob_at("HEAD", f"staging/{cohort}.json") else "state/STAGED.json"
    if rc or blob_at(source_main, "state/STAGED.json") != blob_at("HEAD", durable_pointer):
        return None
    current = api("/pulls/" + str(pr["number"])) or {}
    if (current.get("head") or {}).get("sha") != commit or (current.get("base") or {}).get("sha") != generation_head:
        return None
    return row


def source_status_valid(commit: str, role: str, cohort: str, generation_head: str, cutoff_utc: str) -> bool:
    return source_status_observation(commit, role, cohort, generation_head, cutoff_utc) is not None


def current_run_within_challenge_window(role: str, receipt: dict, manifest: dict, cutoff_utc: str) -> bool:
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if not run_id.isdigit():
        return False
    try:
        run = api("/actions/runs/" + run_id) or {}
        created = parse_utc(str(run.get("created_at") or ""))
        task = next(item for item in manifest.get("tasks") or [] if item.get("role_id") == role)
        challenge_value = receipt.get("mm06_challenge_occurrence_utc") if role == "MM06" else receipt.get("challenge_occurrence_utc")
        if challenge_value not in set(task.get("challenge_occurrences_utc") or []):
            return False
        challenge = parse_utc(str(challenge_value))
        budget = trusted_retry_budget_seconds(manifest)
        return challenge <= created <= challenge + timedelta(seconds=budget) and created <= parse_utc(cutoff_utc)
    except Exception:
        return False


def git_main_head() -> str:
    rc, head = git("rev-parse", "HEAD")
    if rc or not HEX40.fullmatch(head):
        raise ValueError("trusted main checkout unavailable")
    return head


def main() -> int:
    errors: list[str] = []
    try:
        number = int(os.environ.get("SUPERNOVA_PREACTIVATION_PR_NUMBER", "0"))
        pr = api("/pulls/" + str(number)) or {}
        head = pr.get("head") or {}; base = pr.get("base") or {}
        head_sha = head.get("sha"); generation_head = base.get("sha"); head_ref = head.get("ref"); base_ref = base.get("ref")
        event = (os.environ.get("SUPERNOVA_PREACTIVATION_PR_HEAD_SHA"), os.environ.get("SUPERNOVA_PREACTIVATION_PR_BASE_SHA"))
        if event != (head_sha, generation_head): errors.append("event/current PR head or base moved")
        if (head.get("repo") or {}).get("full_name") != REPO or (pr.get("user") or {}).get("login") != OWNER: errors.append("preactivation PR is not same-repository owner-authored")
        match = re.fullmatch(r"ps/preactivate/([^/]+)/(MF01|MF02|MF03|MF04|MF05|MM01|MM02|MM03|MM04|MM05|MM07|EXT01|MM06|MF06|BIL00)", str(head_ref))
        if not match: errors.append("preactivation head ref is not canonical"); cohort = ""; role = ""
        else: cohort, role = match.groups()
        if base_ref != f"ps/gen/{cohort}": errors.append("preactivation PR base ref is not exact generation branch")
        main_head = git_main_head()
        observed_main = ((api("/branches/main") or {}).get("commit") or {}).get("sha")
        if main_head != observed_main: errors.append("trusted workflow checkout is not exact current main")
        git("fetch", "--no-tags", "origin", f"+refs/heads/ps/gen/{cohort}:refs/remotes/origin/ps/gen/{cohort}", f"+refs/heads/{head_ref}:refs/remotes/origin/{head_ref}", "+refs/heads/ps/preactivate/*:refs/remotes/origin/ps/preactivate/*")
        pointer = load("state/STAGED.json"); pointer_blob = blob_at("HEAD", "state/STAGED.json")
        if pointer.get("candidate_cohort_id") != cohort or pointer.get("generation_head_sha") != generation_head or pointer.get("generation_branch") != base_ref:
            errors.append("preactivation PR is not bound to accepted-main staged candidate")
        if pointer_blob is None: errors.append("accepted-main staged pointer blob unavailable")
        if blob_at(generation_head, f"scheduler/{cohort}.json") != pointer.get("scheduler_manifest_git_identity"):
            errors.append("generation scheduler manifest blob mismatch")
        manifest = load_ref(generation_head, f"scheduler/{cohort}.json")
        production_snapshot, production_errors = production_ref_snapshot(manifest, str(generation_head))
        errors.extend(production_errors)
        cutoff_utc = manifest.get("admission_cutoff_utc")
        path = f"preactivation/{cohort}/{role}.json"
        blob = blob_at(str(head_sha), path)
        if not one_added_path_child(str(head_sha), str(generation_head), path, blob):
            errors.append("preactivation receipt is not one added-path sole child of G")
        receipt = load_ref(str(head_sha), path)
        if not current_run_within_challenge_window(role, receipt, manifest, str(cutoff_utc)):
            errors.append("preactivation workflow run is outside the signed scheduled challenge window or admission cutoff")
        authority = load("config/scheduler_attestation_authority_v25.json")
        if role in PREACTIVATION_ROLES:
            errors.extend(schema_errors("schemas/preactivation_receipt.schema.json", receipt))
            errors.extend(receipt_semantic_errors(receipt, role, pointer, manifest, str(pointer_blob), authority))
            key = worker_keys(authority)[role] if role in WORKERS else secret_bytes(
                "SUPERNOVA_MF06_PREACTIVATION_KEY", authority["mf06_preactivation_key_commitment_sha256"]
            )
            if not role_hmac_valid(receipt, key): errors.append(role + " preactivation role HMAC invalid")
        elif role == "BIL00":
            key = secret_bytes("SUPERNOVA_SCHEDULER_INVENTORY_KEY", authority["inventory_attestation_key_commitment_sha256"])
            errors.extend(inventory_errors(receipt, pointer, manifest, str(pointer_blob), key, authority))
        elif role == "MM06":
            key = secret_bytes("SUPERNOVA_MM06_ATTESTATION_KEY", authority["mm06_attestation_key_commitment_sha256"])
            errors.extend(schema_errors("schemas/scheduler_admission.schema.json", receipt))
            if not verify_tag(receipt, "attestation_tag", key, authority["mm06_hmac_domain"]): errors.append("MM06 source attestation HMAC invalid")
            inventory_branch = receipt.get("scheduler_inventory_branch"); inventory_path = receipt.get("scheduler_inventory_path")
            inventory_commit = receipt.get("scheduler_inventory_commit_sha"); inventory_blob = receipt.get("scheduler_inventory_blob_sha")
            if inventory_branch != f"ps/preactivate/{cohort}/BIL00" or inventory_path != f"preactivation/{cohort}/BIL00.json": errors.append("MM06 inventory source branch/path mismatch")
            if blob_at(str(inventory_commit), str(inventory_path)) != inventory_blob or not one_added_path_child(str(inventory_commit), str(generation_head), str(inventory_path), str(inventory_blob)): errors.append("MM06 inventory source commit/blob invalid")
            inventory = load_ref(str(inventory_commit), str(inventory_path))
            inventory_key = secret_bytes("SUPERNOVA_SCHEDULER_INVENTORY_KEY", authority["inventory_attestation_key_commitment_sha256"])
            errors.extend(inventory_errors(inventory, pointer, manifest, str(pointer_blob), inventory_key, authority))
            if not source_status_valid(str(inventory_commit), "BIL00", cohort, str(generation_head), str(cutoff_utc)): errors.append("MM06 inventory source lacks exact-PR trusted status before cutoff")
            keys = worker_keys(authority)
            mf06_key = secret_bytes("SUPERNOVA_MF06_PREACTIVATION_KEY", authority["mf06_preactivation_key_commitment_sha256"])
            rows = receipt.get("preactivation_results") or []
            by_role = {row.get("role_id"): row for row in rows if isinstance(row, dict)}
            if len(rows) != 13 or set(by_role) != PREACTIVATION_ROLES: errors.append("MM06 preactivation result set is not exact 12 workers plus MF06")
            tasks, frozen = task_maps(manifest, load("config/task_registry_v25.json"))
            for source_role in sorted(PREACTIVATION_ROLES):
                row = by_role.get(source_role) or {}; commit = row.get("receipt_creation_commit_sha"); source_blob = row.get("receipt_blob_sha")
                source_path = f"preactivation/{cohort}/{source_role}.json"
                if blob_at(str(commit), source_path) != source_blob or not one_added_path_child(str(commit), str(generation_head), source_path, str(source_blob)): errors.append(source_role + " source commit/blob invalid"); continue
                source_receipt = load_ref(str(commit), source_path)
                errors.extend(schema_errors("schemas/preactivation_receipt.schema.json", source_receipt))
                errors.extend(receipt_semantic_errors(source_receipt, source_role, pointer, manifest, str(pointer_blob), authority))
                source_key = keys[source_role] if source_role in WORKERS else mf06_key
                if not role_hmac_valid(source_receipt, source_key): errors.append(source_role + " source HMAC invalid")
                if not source_status_valid(str(commit), source_role, cohort, str(generation_head), str(cutoff_utc)): errors.append(source_role + " source lacks exact-PR trusted status before cutoff")
                expected_row = {"role_id":source_role,"preactivation_branch":f"ps/preactivate/{cohort}/{source_role}","preactivation_path":source_path,"receipt_blob_sha":source_blob,"receipt_creation_commit_sha":commit,"scheduler_task_id_valid":True,"behavioral_config_valid":True,"challenge_timing_valid":True,"role_commitment_valid":True,"role_hmac_valid":True,"mm06_verifier_copy_commitment_valid":True,"production_write_absent":True}
                if row != expected_row: errors.append(source_role + " MM06 result row is not exact trusted rederivation")
            mm06_task = tasks.get("MM06") or {}; mm06_frozen = frozen.get("MM06") or {}
            if receipt.get("mm06_scheduler_task_id") != mm06_frozen.get("scheduler_task_id") or receipt.get("mm06_behavioral_config_sha256") != mm06_task.get("behavioral_config_sha256"): errors.append("MM06 task identity/readback mismatch")
            if receipt.get("mm06_challenge_occurrence_utc") not in set(mm06_task.get("challenge_occurrences_utc") or []): errors.append("MM06 challenge is not a frozen scheduled occurrence")
        errors.extend(production_ref_revalidation_errors(manifest, str(generation_head), production_snapshot))
        current = api("/pulls/" + str(number)) or {}
        if (current.get("head") or {}).get("sha") != head_sha or (current.get("base") or {}).get("sha") != generation_head: errors.append("PR moved during validation")
        if ((api("/branches/" + urllib.parse.quote(str(base_ref), safe="")) or {}).get("commit") or {}).get("sha") != generation_head: errors.append("generation branch moved during validation")
        if ((api("/branches/main") or {}).get("commit") or {}).get("sha") != main_head: errors.append("accepted main moved during validation")
        description = errors[0] if errors else binding_description(number, role, str(head_sha), str(generation_head), str(head_ref), main_head)
        post(str(head_sha), "failure" if errors else "success", description)
    except Exception as exc:
        errors.append(str(exc))
        head_sha = os.environ.get("SUPERNOVA_PREACTIVATION_PR_HEAD_SHA", "")
        if HEX40.fullmatch(head_sha):
            try: post(head_sha, "failure", errors[0])
            except Exception: pass
    if errors:
        print("PREACTIVATION ADMISSION FAILED")
        for error in errors: print("-", error)
        return 1
    print("PREACTIVATION_ADMISSION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
