#!/usr/bin/env python3
"""Canonical protocol-2.5 generation-envelope rules.

This module is deliberately side-effect free. Every structural reconciler must use
this predicate rather than independently reconstructing the root-to-generation
allowlist. Shared status contexts have exactly one authoritative writer; other
reconcilers may publish only distinct diagnostic contexts.
"""
from __future__ import annotations

import pathlib
import subprocess
from collections.abc import Iterable


def expected_generation_paths(state: dict) -> set[str]:
    """Return the exact root->G path set for the active generation."""
    cohort = state.get("active_cohort_id")
    control_path = state.get("active_control_manifest_path")
    assignment_path = state.get("active_assignment_path")
    if not all(isinstance(x, str) and x for x in (cohort, control_path, assignment_path)):
        raise ValueError("state lacks active cohort/control/assignment paths")

    expected = {control_path, assignment_path}
    if state.get("calibration_countable_current") is True:
        expected.add(f"liveness/{cohort}.json")
    return expected


def generation_path_errors(actual_paths: Iterable[str], state: dict) -> list[str]:
    actual = set(actual_paths)
    expected = expected_generation_paths(state)
    if actual == expected:
        return []
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    errors: list[str] = []
    if missing:
        errors.append("generation envelope missing: " + ", ".join(missing))
    if extra:
        errors.append("generation envelope has extra paths: " + ", ".join(extra))
    return errors


def _git(root: pathlib.Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def local_generation_envelope_errors(
    root: pathlib.Path,
    state: dict,
    control: dict,
    generation_head_sha: str,
) -> list[str]:
    """Validate exact root->G changed paths in a checked-out repository."""
    release = control.get("control_release_commit_sha")
    if not isinstance(release, str) or len(release) != 40:
        return ["invalid control_release_commit_sha"]
    rc, out, err = _git(root, "diff", "--name-only", f"{release}...{generation_head_sha}")
    if rc:
        return ["cannot enumerate generation envelope: " + (err or out)[-400:]]
    paths = [line for line in out.splitlines() if line]
    return generation_path_errors(paths, state)
