#!/usr/bin/env python3
"""Dependency-light, rejection-only branch-envelope audit.

This process is intentionally not an authority for any shared
``supernova/branch-*`` context. The checkout-based branch reconciler is the sole
writer of those contexts. This REST audit publishes only the distinct
``supernova/rest-generation-audit`` diagnostic context and therefore cannot mask
an authoritative failure through last-writer-wins status semantics.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from generation_envelope_v25 import generation_path_errors

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
API = "https://api.github.com/repos/" + REPO
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DIAGNOSTIC_CONTEXT = "supernova/rest-generation-audit"
FORBIDDEN_SHARED_CONTEXTS = (
    "supernova/branch-generation",
    "supernova/branch-worker",
    "supernova/branch-verify",
    "supernova/branch-integrate",
    "supernova/branch-consolidate",
)


def request(path: str, method: str = "GET", data=None):
    req = urllib.request.Request(
        API + path,
        data=(json.dumps(data).encode("utf-8") if data is not None else None),
        method=method,
    )
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def content(path: str, ref: str) -> tuple[dict, dict]:
    obj = request(
        "/contents/"
        + urllib.parse.quote(path, safe="/")
        + "?ref="
        + urllib.parse.quote(ref, safe="")
    )
    if not isinstance(obj, dict) or obj.get("type") != "file":
        raise RuntimeError(f"{path}@{ref}: not a file")
    return obj, json.loads(base64.b64decode(obj.get("content", "")).decode("utf-8"))


def branch_head(branch: str) -> str | None:
    try:
        return request("/branches/" + urllib.parse.quote(branch, safe=""))["commit"]["sha"]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def changed_files(base: str, head: str) -> list[str]:
    compare = request(f"/compare/{base}...{head}") or {}
    return [
        row["filename"]
        for row in compare.get("files", [])
        if row.get("status") != "unchanged"
    ]


def post_diagnostic(sha: str, state: str, description: str) -> None:
    request(
        "/statuses/" + sha,
        "POST",
        {
            "state": state,
            "context": DIAGNOSTIC_CONTEXT,
            "description": description[:140],
        },
    )


def audit() -> list[str]:
    _, state = content("state/CURRENT.json", "main")
    if state.get("task_network_plan_id") != PLAN:
        return ["canonical plan mismatch"]
    if state.get("transport_mode") != "BRANCH_GITOPS":
        return ["canonical transport is not BRANCH_GITOPS"]

    cohort = state.get("active_cohort_id")
    generation = state.get("generation_head_sha")
    generation_branch = state.get("generation_branch")
    if not isinstance(generation, str) or not HEX40.fullmatch(generation):
        return ["invalid generation head"]
    if branch_head(str(generation_branch)) != generation:
        return ["generation branch missing or moved"]

    control_meta, control = content(state["active_control_manifest_path"], generation)
    assignment_meta, assignment = content(state["active_assignment_path"], generation)
    errors: list[str] = []
    if control_meta.get("sha") != state.get("active_control_manifest_git_identity"):
        errors.append("state control blob mismatch")
    if assignment_meta.get("sha") != state.get("active_assignment_git_identity"):
        errors.append("state assignment blob mismatch")
    if control.get("cohort_id") != cohort or assignment.get("cohort_id") != cohort:
        errors.append("generation cohort mismatch")
    if control.get("task_network_plan_id") != PLAN or assignment.get("task_network_plan_id") != PLAN:
        errors.append("generation plan mismatch")

    release = control.get("control_release_commit_sha")
    if not isinstance(release, str) or not HEX40.fullmatch(release):
        errors.append("invalid generation release root")
    else:
        errors.extend(generation_path_errors(changed_files(release, generation), state))
    return errors


def main() -> int:
    try:
        _, state = content("state/CURRENT.json", "main")
        generation = state.get("generation_head_sha")
        errors = audit()
        if isinstance(generation, str) and HEX40.fullmatch(generation):
            post_diagnostic(
                generation,
                "failure" if errors else "success",
                ("REST audit FAIL: " + errors[0]) if errors else "REST generation-envelope diagnostic PASS",
            )
        if errors:
            print("REST generation diagnostic failed")
            for error in errors:
                print("-", error)
        else:
            print("REST generation diagnostic passed")
        # Diagnostic-only: the normal admission reconciler must still run, and this
        # process has no authority to turn a shared branch context green or red.
        return 0
    except Exception as exc:
        print("REST generation diagnostic error:", repr(exc))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
