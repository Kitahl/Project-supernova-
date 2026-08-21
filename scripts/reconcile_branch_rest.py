#!/usr/bin/env python3
"""Read-only REST diagnostics for the active Branch-GitOps cohort.

This helper is intentionally incapable of publishing commit statuses. The sole
authoritative structural branch-status writer is
``scripts/reconcile_branch_statuses.py``. REST observations are emitted only as
machine-readable, non-authoritative diagnostic records under distinct names.
They can expose disagreement, but can never overwrite an authoritative result.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/" + REPO
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
WORKERS = (
    "MF01", "MF02", "MF03", "MF04", "MF05",
    "MM01", "MM02", "MM03", "MM04", "MM05", "MM07", "EXT01",
)
GENERATION_DIAGNOSTIC_CONTEXT = "supernova/rest-branch-generation-diagnostic"
WORKER_DIAGNOSTIC_CONTEXT = "supernova/rest-branch-worker-diagnostic"
VERIFY_DIAGNOSTIC_CONTEXT = "supernova/rest-branch-verify-diagnostic"
INTEGRATE_DIAGNOSTIC_CONTEXT = "supernova/rest-branch-integrate-diagnostic"
CONSOLIDATE_DIAGNOSTIC_CONTEXT = "supernova/rest-branch-consolidate-diagnostic"
AUTHORITATIVE_WRITER = "scripts/reconcile_branch_statuses.py"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def request_json(path: str):
    request = urllib.request.Request(API + path, method="GET")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        request.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def content(path: str, ref: str):
    value = request_json(
        "/contents/"
        + urllib.parse.quote(path, safe="/")
        + "?ref="
        + urllib.parse.quote(ref, safe="")
    )
    if not isinstance(value, dict) or value.get("type") != "file":
        raise RuntimeError(f"{path}@{ref}: not a file")
    text = base64.b64decode(value.get("content", "")).decode("utf-8")
    return value, json.loads(text)


def branch_head(branch: str):
    try:
        return request_json("/branches/" + urllib.parse.quote(branch, safe=""))["commit"]["sha"]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def changed_files(base: str, head: str) -> list[str]:
    comparison = request_json("/compare/" + base + "..." + head)
    return [
        item["filename"]
        for item in comparison.get("files", [])
        if item.get("status") != "unchanged"
    ]


def generation_expected_paths(state: dict, control: dict, assignment: dict) -> set[str]:
    paths = {
        state["active_control_manifest_path"],
        state["active_assignment_path"],
    }
    if (
        control.get("calibration_countable") is True
        or assignment.get("calibration_countable") is True
        or state.get("calibration_countable_current") is True
    ):
        paths.add(f"liveness/{state['active_cohort_id']}.json")
    return paths


def diagnostic(context: str, result: str, findings: list[str], **extra):
    return {
        "diagnostic_context": context,
        "authoritative": False,
        "authoritative_writer": AUTHORITATIVE_WRITER,
        "result": result,
        "findings": findings,
        **extra,
    }


def generation_diagnostic(state: dict) -> tuple[dict, dict | None, dict | None]:
    cohort = state["active_cohort_id"]
    generation_head = state["generation_head_sha"]
    generation_branch = state["generation_branch"]
    findings: list[str] = []
    control = assignment = None

    observed_head = branch_head(generation_branch)
    if observed_head != generation_head:
        findings.append(f"generation ref {observed_head} != {generation_head}")
    try:
        control_meta, control = content(state["active_control_manifest_path"], generation_head)
        assignment_meta, assignment = content(state["active_assignment_path"], generation_head)
        if control_meta["sha"] != state["active_control_manifest_git_identity"]:
            findings.append("state control blob mismatch")
        if assignment_meta["sha"] != state["active_assignment_git_identity"]:
            findings.append("state assignment blob mismatch")
        if control.get("task_network_plan_id") != PLAN or assignment.get("task_network_plan_id") != PLAN:
            findings.append("generation plan mismatch")
        if control.get("cohort_id") != cohort or assignment.get("cohort_id") != cohort:
            findings.append("generation cohort mismatch")
        root = control.get("control_release_commit_sha")
        if not isinstance(root, str) or not HEX40.fullmatch(root):
            findings.append("bad generation root")
        elif assignment.get("generation_root_sha") != root:
            findings.append("assignment root mismatch")
        else:
            expected = generation_expected_paths(state, control, assignment)
            observed = set(changed_files(root, generation_head))
            if observed != expected:
                findings.append(
                    "generation root->G paths mismatch "
                    f"expected={sorted(expected)} observed={sorted(observed)}"
                )
    except Exception as exc:
        findings.append("generation diagnostic exception: " + str(exc))

    return (
        diagnostic(
            GENERATION_DIAGNOSTIC_CONTEXT,
            "PASS" if not findings else "FAIL",
            findings,
            target_sha=generation_head,
            cohort_id=cohort,
        ),
        control,
        assignment,
    )


def worker_diagnostics(state: dict) -> list[dict]:
    records: list[dict] = []
    cohort = state["active_cohort_id"]
    generation_head = state["generation_head_sha"]
    for worker in WORKERS:
        branch = state["worker_branches"][worker]
        head = branch_head(branch)
        findings: list[str] = []
        result = "PASS"
        if head is None:
            findings.append("assigned branch missing")
            result = "FAIL"
        elif head == generation_head:
            findings.append("awaiting immutable report")
            result = "PENDING"
        else:
            expected = f"reports/{cohort}/{worker}.json"
            try:
                observed = changed_files(generation_head, head)
                if observed != [expected]:
                    findings.append(f"diff != exactly assigned report: {observed}")
                _, report = content(expected, head)
                if report.get("worker_id") != worker:
                    findings.append("worker binding mismatch")
                if report.get("cohort_id") != cohort:
                    findings.append("cohort binding mismatch")
                if report.get("generation_head_sha") != generation_head:
                    findings.append("generation binding mismatch")
                if findings:
                    result = "FAIL"
            except Exception as exc:
                findings.append("worker diagnostic exception: " + str(exc))
                result = "FAIL"
        records.append(
            diagnostic(
                WORKER_DIAGNOSTIC_CONTEXT,
                result,
                findings,
                worker_id=worker,
                branch=branch,
                target_sha=head,
            )
        )
    return records


def single_receipt_diagnostic(state: dict, branch_key: str, path: str, context: str) -> dict:
    branch = state[branch_key]
    generation_head = state["generation_head_sha"]
    head = branch_head(branch)
    findings: list[str] = []
    result = "PASS"
    if head is None:
        findings.append("assigned branch missing")
        result = "FAIL"
    elif head == generation_head:
        findings.append("awaiting immutable receipt")
        result = "PENDING"
    else:
        try:
            observed = changed_files(generation_head, head)
            if observed != [path]:
                findings.append(f"diff != exactly {path}: {observed}")
            _, value = content(path, head)
            if value.get("task_network_plan_id") != PLAN:
                findings.append("plan binding mismatch")
            if value.get("cohort_id") != state["active_cohort_id"]:
                findings.append("cohort binding mismatch")
            if value.get("generation_head_sha") != generation_head:
                findings.append("generation binding mismatch")
            if findings:
                result = "FAIL"
        except Exception as exc:
            findings.append("receipt diagnostic exception: " + str(exc))
            result = "FAIL"
    return diagnostic(context, result, findings, branch=branch, target_sha=head)


def main() -> int:
    _, state = content("state/CURRENT.json", "main")
    if (
        state.get("task_network_plan_id") != PLAN
        or state.get("transport_mode") != "BRANCH_GITOPS"
    ):
        print(json.dumps({"status": "NOT_APPLICABLE"}, sort_keys=True))
        return 0

    generation, _, _ = generation_diagnostic(state)
    cohort = state["active_cohort_id"]
    records = [generation]
    if generation["result"] == "PASS":
        records.extend(worker_diagnostics(state))
    records.append(
        single_receipt_diagnostic(
            state,
            "verifier_branch",
            f"verification/{cohort}.json",
            VERIFY_DIAGNOSTIC_CONTEXT,
        )
    )
    records.append(
        single_receipt_diagnostic(
            state,
            "integrator_branch",
            f"integration/{cohort}.json",
            INTEGRATE_DIAGNOSTIC_CONTEXT,
        )
    )

    result = {
        "schema_version": "PS-REST-BRANCH-DIAGNOSTICS-2",
        "cohort_id": cohort,
        "generation_head_sha": state["generation_head_sha"],
        "authoritative": False,
        "authoritative_status_writer": AUTHORITATIVE_WRITER,
        "records": records,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    # Diagnostics never gate, publish, or overwrite authoritative CI.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
