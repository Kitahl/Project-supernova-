#!/usr/bin/env python3
"""Monotone Project Supernova CI guard.

This guard is intentionally outside the frozen v2.3 control set. It may reject a
candidate, but it MUST NOT be used by itself to promote runtime/scientific state.
Its purpose is to mechanically verify Git bindings and verifier completeness that
JSON Schema alone cannot establish. A later control-plane revision may freeze it.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def git_blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def load_json(path: pathlib.Path, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return None


def run_git(root: pathlib.Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def verify_report_ref(
    root: pathlib.Path,
    cohort_id: str,
    ref: dict[str, Any],
    errors: list[str],
) -> None:
    worker_id = ref.get("worker_id")
    expected_path = f"reports/{cohort_id}/{worker_id}.json"
    path_value = ref.get("path")

    if path_value != expected_path:
        errors.append(
            f"verification/{cohort_id}: {worker_id} path {path_value!r} != {expected_path!r}"
        )
        return

    report_path = root / expected_path
    if not report_path.is_file():
        errors.append(f"verification/{cohort_id}: missing safe report {expected_path}")
        return

    observed_blob = git_blob_sha(report_path)
    claimed_blob = ref.get("blob_sha")
    if claimed_blob != observed_blob:
        errors.append(
            f"verification/{cohort_id}: {worker_id} blob mismatch "
            f"claimed={claimed_blob!r} observed={observed_blob}"
        )

    report = load_json(report_path, errors)
    if isinstance(report, dict):
        if report.get("worker_id") != worker_id:
            errors.append(
                f"{expected_path}: worker_id {report.get('worker_id')!r} != {worker_id!r}"
            )
        if report.get("cohort_id") != cohort_id:
            errors.append(
                f"{expected_path}: cohort_id {report.get('cohort_id')!r} != {cohort_id!r}"
            )

    commit_sha = ref.get("commit_sha")
    if not isinstance(commit_sha, str) or not HEX40.fullmatch(commit_sha):
        errors.append(
            f"verification/{cohort_id}: {worker_id} commit_sha must be a non-null 40-hex Git commit"
        )
        return

    code, _, stderr = run_git(root, "cat-file", "-e", f"{commit_sha}^{{commit}}")
    if code:
        errors.append(
            f"verification/{cohort_id}: {worker_id} commit {commit_sha} is not locally resolvable"
            + (f": {stderr}" if stderr else "")
        )
        return

    code, out, stderr = run_git(root, "ls-tree", commit_sha, "--", expected_path)
    if code or not out:
        errors.append(
            f"verification/{cohort_id}: {worker_id} report absent at claimed commit {commit_sha}"
            + (f": {stderr}" if stderr else "")
        )
    else:
        left = out.split("\t", 1)[0].split()
        tree_blob = left[2] if len(left) >= 3 else None
        if tree_blob != observed_blob:
            errors.append(
                f"verification/{cohort_id}: {worker_id} claimed creation commit "
                f"contains blob {tree_blob!r}, current immutable blob is {observed_blob}"
            )

    code, out, stderr = run_git(root, "log", "--format=%H", "--", expected_path)
    history = [line for line in out.splitlines() if line] if code == 0 else []
    if code:
        errors.append(
            f"verification/{cohort_id}: cannot inspect history for {worker_id}"
            + (f": {stderr}" if stderr else "")
        )
    elif history != [commit_sha]:
        errors.append(
            f"verification/{cohort_id}: {worker_id} report is not create-once immutable; "
            f"history={history!r}, claimed_creation={commit_sha}"
        )

    code, out, stderr = run_git(
        root, "log", "--diff-filter=A", "--format=%H", "--", expected_path
    )
    creations = [line for line in out.splitlines() if line] if code == 0 else []
    if code:
        errors.append(
            f"verification/{cohort_id}: cannot inspect creation history for {worker_id}"
            + (f": {stderr}" if stderr else "")
        )
    elif creations != [commit_sha]:
        errors.append(
            f"verification/{cohort_id}: {worker_id} creation commit mismatch; "
            f"git={creations!r}, claimed={commit_sha}"
        )


def superseded_cohorts(root: pathlib.Path, state: dict[str, Any]) -> set[str]:
    result = set(state.get("superseded_cohorts", []))
    folder = root / "superseded"
    if folder.is_dir():
        for path in folder.glob("*.json"):
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            cohort = obj.get("cohort_id")
            if isinstance(cohort, str):
                result.add(cohort)
    return result


def validate(root: pathlib.Path) -> list[str]:
    errors: list[str] = []

    state_path = root / "state" / "CURRENT.json"
    state = load_json(state_path, errors)
    if not isinstance(state, dict):
        return errors or ["state/CURRENT.json missing or invalid"]

    superseded = superseded_cohorts(root, state)
    verification_dir = root / "verification"
    if not verification_dir.is_dir():
        return errors

    for manifest_path in sorted(verification_dir.glob("*.json")):
        manifest = load_json(manifest_path, errors)
        if not isinstance(manifest, dict):
            continue

        cohort_id = manifest.get("cohort_id")
        if not isinstance(cohort_id, str):
            errors.append(f"{manifest_path}: cohort_id missing or invalid")
            continue
        if cohort_id in superseded:
            continue

        assignment_path = root / "assignments" / f"{cohort_id}.json"
        assignment = load_json(assignment_path, errors)
        if not isinstance(assignment, dict):
            errors.append(f"{manifest_path}: cannot resolve assignment {assignment_path}")
            continue

        workers = assignment.get("workers")
        if not isinstance(workers, dict):
            errors.append(f"{assignment_path}: workers must be an object")
            continue
        expected = set(workers)

        safe_refs = manifest.get("safe_report_refs", [])
        quarantined_refs = manifest.get("quarantined_report_refs", [])
        missing_workers = manifest.get("missing_workers", [])
        auth = manifest.get("worker_auth_verification", {})

        if not isinstance(safe_refs, list):
            errors.append(f"{manifest_path}: safe_report_refs must be an array")
            safe_refs = []
        if not isinstance(quarantined_refs, list):
            errors.append(f"{manifest_path}: quarantined_report_refs must be an array")
            quarantined_refs = []
        if not isinstance(missing_workers, list):
            errors.append(f"{manifest_path}: missing_workers must be an array")
            missing_workers = []
        if not isinstance(auth, dict):
            errors.append(f"{manifest_path}: worker_auth_verification must be an object")
            auth = {}

        safe_ids: list[str] = []
        for ref in safe_refs:
            if not isinstance(ref, dict):
                errors.append(f"{manifest_path}: each safe_report_ref must be an object")
                continue
            worker_id = ref.get("worker_id")
            if isinstance(worker_id, str):
                safe_ids.append(worker_id)
            else:
                errors.append(f"{manifest_path}: safe report ref missing worker_id")
                continue
            verify_report_ref(root, cohort_id, ref, errors)

        quarantine_ids: list[str] = []
        for ref in quarantined_refs:
            if not isinstance(ref, dict):
                errors.append(f"{manifest_path}: each quarantined_report_ref must be an object")
                continue
            worker_id = ref.get("worker_id")
            if isinstance(worker_id, str):
                quarantine_ids.append(worker_id)
            else:
                errors.append(
                    f"{manifest_path}: quarantined report ref must identify worker_id"
                )

        missing_ids = [x for x in missing_workers if isinstance(x, str)]
        if len(missing_ids) != len(missing_workers):
            errors.append(f"{manifest_path}: missing_workers entries must be strings")

        for label, ids in (
            ("safe_report_refs", safe_ids),
            ("quarantined_report_refs", quarantine_ids),
            ("missing_workers", missing_ids),
        ):
            if len(ids) != len(set(ids)):
                errors.append(f"{manifest_path}: duplicate worker in {label}")

        safe_set, quarantine_set, missing_set = (
            set(safe_ids),
            set(quarantine_ids),
            set(missing_ids),
        )
        if safe_set & quarantine_set or safe_set & missing_set or quarantine_set & missing_set:
            errors.append(
                f"{manifest_path}: safe/quarantined/missing worker partitions overlap"
            )

        observed = safe_set | quarantine_set | missing_set
        if observed - expected:
            errors.append(
                f"{manifest_path}: verification references unknown workers "
                f"{sorted(observed - expected)}"
            )

        if set(auth) != expected:
            errors.append(
                f"{manifest_path}: worker_auth_verification keys "
                f"{sorted(auth)} != expected {sorted(expected)}"
            )

        calibration_pass = manifest.get("calibration_pass") is True
        verified_complete = manifest.get("verdict") == "VERIFIED_COMPLETE"
        if calibration_pass or verified_complete:
            if safe_set != expected:
                errors.append(
                    f"{manifest_path}: complete/pass verdict requires every assigned worker safe; "
                    f"safe={sorted(safe_set)} expected={sorted(expected)}"
                )
            if quarantine_set or missing_set:
                errors.append(
                    f"{manifest_path}: complete/pass verdict cannot contain quarantined or missing workers"
                )
            bad_auth = sorted(k for k in expected if auth.get(k) != "PASS")
            if bad_auth:
                errors.append(
                    f"{manifest_path}: complete/pass verdict requires PASS auth for {bad_auth}"
                )

        # Do not require manifest.ci_observation == PASS here. The manifest is
        # written before CI can validate that same manifest. This workflow
        # publishes a later external GitHub commit status; BIL00 must consume
        # that later status rather than a temporally impossible self-assertion.

    return errors


def main() -> int:
    errors = validate(ROOT)
    if errors:
        print("SUPERNOVA CI GUARD FAILED")
        for error in errors:
            print("-", error)
        return 1
    print("SUPERNOVA CI GUARD PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
