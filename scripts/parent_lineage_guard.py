#!/usr/bin/env python3
"""Fail-closed parent-state lineage guard for Project Supernova.

This guard is deliberately outside the frozen v2.3 cohort control set. It closes
the CAL-004 MF04 falsifier that a mutually consistent but nonexistent 40-hex
parent identity could satisfy schema/equality checks. The guard proves that the
parent is a real Git blob, was actually a historical state/CURRENT.json object,
and is an admissible one-step predecessor under conservative runtime invariants.
It may reject a candidate; it must not independently promote scientific/runtime
state until frozen into a later control-plane revision.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"^[0-9a-f]{40}$")
RUNTIME_INVARIANTS = (
    "base_runtime_state_id",
    "runtime_state_id",
    "foundry_sha256",
    "mastermind_sha256",
    "actual_runtime_plan_id",
    "canonical_bus_repo",
    "private_vault_repo",
)


def run_git(root: pathlib.Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def load_json(path: pathlib.Path, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return None


def read_blob_json(root: pathlib.Path, sha: str, errors: list[str]) -> dict[str, Any] | None:
    code, obj_type, stderr = run_git(root, "cat-file", "-t", sha)
    if code:
        errors.append(
            f"state/CURRENT.json: parent object {sha} does not resolve"
            + (f": {stderr}" if stderr else "")
        )
        return None
    if obj_type != "blob":
        errors.append(
            f"state/CURRENT.json: parent object {sha} has Git type {obj_type!r}, expected 'blob'"
        )
        return None

    code, payload, stderr = run_git(root, "cat-file", "-p", sha)
    if code:
        errors.append(
            f"state/CURRENT.json: cannot read parent blob {sha}"
            + (f": {stderr}" if stderr else "")
        )
        return None
    try:
        obj = json.loads(payload)
    except Exception as exc:
        errors.append(f"state/CURRENT.json: parent blob {sha} is not JSON: {exc}")
        return None
    if not isinstance(obj, dict):
        errors.append(f"state/CURRENT.json: parent blob {sha} is not a JSON object")
        return None
    return obj


def blob_was_current_state(root: pathlib.Path, sha: str) -> bool:
    code, commits_text, _ = run_git(root, "log", "--all", "--format=%H", "--", "state/CURRENT.json")
    if code:
        return False
    for commit in (line for line in commits_text.splitlines() if line):
        code, out, _ = run_git(root, "ls-tree", commit, "--", "state/CURRENT.json")
        if code or not out:
            continue
        left = out.split("\t", 1)[0].split()
        if len(left) >= 3 and left[2] == sha:
            return True
    return False


def runtime_update_receipt_exists(root: pathlib.Path, state: dict[str, Any]) -> bool:
    path = state.get("runtime_update_receipt_path")
    if not isinstance(path, str) or not path:
        return False
    receipt = root / path
    return receipt.is_file()


def validate(root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    state_path = root / "state" / "CURRENT.json"
    state = load_json(state_path, errors)
    if not isinstance(state, dict):
        return errors or ["state/CURRENT.json missing or invalid"]

    generation = state.get("generation_seq")
    if not isinstance(generation, int) or generation < 1:
        errors.append("state/CURRENT.json: generation_seq must be a positive integer")
        return errors

    # A genesis state has no predecessor obligation. Every later state does.
    if generation == 1:
        return errors

    parent_sha = state.get("active_parent_state_git_identity")
    if not isinstance(parent_sha, str) or not HEX40.fullmatch(parent_sha):
        errors.append(
            "state/CURRENT.json: active_parent_state_git_identity must be a 40-hex Git blob SHA"
        )
        return errors

    parent = read_blob_json(root, parent_sha, errors)
    if parent is None:
        return errors

    if not blob_was_current_state(root, parent_sha):
        errors.append(
            f"state/CURRENT.json: parent blob {parent_sha} exists but was never a historical state/CURRENT.json"
        )

    parent_generation = parent.get("generation_seq")
    if parent_generation != generation - 1:
        errors.append(
            f"state/CURRENT.json: parent generation {parent_generation!r} is not exactly current-1 ({generation - 1})"
        )

    parent_cohort = parent.get("active_cohort_id")
    current_cohort = state.get("active_cohort_id")
    if not isinstance(parent_cohort, str) or not parent_cohort:
        errors.append("state/CURRENT.json: parent active_cohort_id missing or invalid")
    if not isinstance(current_cohort, str) or not current_cohort:
        errors.append("state/CURRENT.json: current active_cohort_id missing or invalid")
    elif parent_cohort == current_cohort:
        errors.append("state/CURRENT.json: current cohort must differ from its parent cohort")

    parent_superseded = parent.get("superseded_cohorts", [])
    current_superseded = state.get("superseded_cohorts", [])
    if isinstance(parent_superseded, list) and isinstance(current_superseded, list):
        lost = set(x for x in parent_superseded if isinstance(x, str)) - set(
            x for x in current_superseded if isinstance(x, str)
        )
        if lost:
            errors.append(
                f"state/CURRENT.json: superseded cohort history regressed; lost {sorted(lost)}"
            )
    else:
        errors.append("state/CURRENT.json: superseded_cohorts must be arrays in parent and current state")

    runtime_drift = [
        key for key in RUNTIME_INVARIANTS if parent.get(key) != state.get(key)
    ]
    if runtime_drift and not runtime_update_receipt_exists(root, state):
        errors.append(
            "state/CURRENT.json: runtime-bound identity drift without an explicit runtime_update_receipt_path: "
            + ", ".join(runtime_drift)
        )

    control_path_value = state.get("active_control_manifest_path")
    assignment_path_value = state.get("active_assignment_path")
    for label, path_value in (
        ("control", control_path_value),
        ("assignment", assignment_path_value),
    ):
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"state/CURRENT.json: active {label} path missing")
            continue
        obj = load_json(root / path_value, errors)
        if not isinstance(obj, dict):
            continue
        if obj.get("parent_state_git_identity") != parent_sha:
            errors.append(
                f"{path_value}: parent_state_git_identity does not bind the resolved parent blob"
            )
        if obj.get("generation_seq") != generation:
            errors.append(f"{path_value}: generation_seq does not bind current state")
        if obj.get("cohort_id") != current_cohort:
            errors.append(f"{path_value}: cohort_id does not bind current active cohort")

    return errors


def main() -> int:
    errors = validate(ROOT)
    if errors:
        print("SUPERNOVA PARENT LINEAGE GUARD FAILED")
        for error in errors:
            print("-", error)
        return 1
    print("SUPERNOVA PARENT LINEAGE GUARD PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
