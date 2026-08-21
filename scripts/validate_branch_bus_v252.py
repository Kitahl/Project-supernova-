#!/usr/bin/env python3
"""Protocol-2.5 branch validator composition, revision 2.

The original v251 validator remains immutable historical evidence. This entrypoint
adds one canonical generation envelope plus prospective contract overlays that are
active only when frozen by the cohort control manifest.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import validate_branch_bus_v251 as legacy
from generation_envelope_v25 import local_generation_envelope_errors
from prospective_contracts_v25 import role_contract_errors, verification_contract_errors

ROOT = pathlib.Path(__file__).resolve().parents[1]


def validate(branch: str, generation_head: str) -> list[str]:
    errors = list(legacy.validate(branch, generation_head))
    kind, cohort, worker = legacy.kind(branch)
    if not kind or not cohort:
        return errors

    control_path = ROOT / f"control/{cohort}.json"
    assignment_path = ROOT / f"assignments/{cohort}.json"
    if not control_path.is_file() or not assignment_path.is_file():
        return errors + ["v252 missing control/assignment"]

    try:
        control = legacy.load(control_path)
        assignment = legacy.load(assignment_path)
    except Exception as exc:
        return errors + [f"v252 cannot parse control/assignment: {exc!r}"]

    if kind == "generation":
        state_view = {
            "active_cohort_id": cohort,
            "active_control_manifest_path": f"control/{cohort}.json",
            "active_assignment_path": f"assignments/{cohort}.json",
            "calibration_countable_current": control.get("calibration_countable"),
        }
        errors.extend(local_generation_envelope_errors(ROOT, state_view, control, generation_head))

    if kind == "worker" and worker:
        report_path = ROOT / f"reports/{cohort}/{worker}.json"
        if report_path.is_file():
            try:
                report = legacy.load(report_path)
                errors.extend(role_contract_errors(report, assignment, control, ROOT))
            except Exception as exc:
                errors.append(f"v252 role-contract validation failed: {exc!r}")

    if kind == "verify":
        verification_path = ROOT / f"verification/{cohort}.json"
        if verification_path.is_file():
            try:
                verification = legacy.load(verification_path)
                errors.extend(verification_contract_errors(verification, control, ROOT))
            except Exception as exc:
                errors.append(f"v252 verification overlay failed: {exc!r}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--generation-head", required=True)
    args = parser.parse_args()
    errors = validate(args.branch, args.generation_head)
    if errors:
        print("BRANCH VALIDATION FAILED")
        for error in errors:
            print("-", error)
        return 1
    print("BRANCH VALIDATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
