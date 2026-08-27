#!/usr/bin/env python3
"""Classify one canonical task's prospective preactivation publication state.

This module is deliberately pure: it does not call GitHub or mutate a branch. A
scheduled task can reconstruct the state from authenticated readback and resume
at the first missing transition without producing duplicate receipt commits.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


OUTCOMES = (
    "WAITING_FOR_CHALLENGE",
    "RECEIPT_COMMITTED_PR_MISSING",
    "PR_OPEN_STATUS_PENDING",
    "ADMITTED",
    "REJECTED",
    "BLOCKED",
)

TERMINAL_FAILURE_STATES = {"error", "failure", "cancelled"}


def result(state: str, reason: str, next_action: str) -> dict[str, str]:
    if state not in OUTCOMES:
        raise ValueError(f"unknown publication outcome: {state}")
    return {"state": state, "reason": reason, "next_action": next_action}


def classify(
    *,
    challenge_open: bool,
    receipt_commit_count: int,
    receipt_exact: bool,
    pr_count: int,
    pr_exact: bool,
    status_state: str | None,
    status_within_window: bool | None,
) -> dict[str, str]:
    """Return one typed state and its only safe next transition."""

    if receipt_commit_count < 0 or pr_count < 0:
        raise ValueError("receipt_commit_count and pr_count must be non-negative")

    if not challenge_open:
        if receipt_commit_count == 0 and pr_count == 0 and status_state is None:
            return result(
                "WAITING_FOR_CHALLENGE",
                "the signed preactivation challenge window is not open",
                "WAIT_FOR_CHALLENGE",
            )
        return result(
            "REJECTED",
            "preactivation evidence exists before the signed challenge window",
            "STOP_NO_CONSTRUCTIVE_REPAIR",
        )

    if receipt_commit_count == 0:
        return result(
            "BLOCKED",
            "no receipt commit exists on the canonical preactivation branch",
            "CREATE_EXACT_RECEIPT_COMMIT",
        )
    if receipt_commit_count != 1:
        return result(
            "REJECTED",
            "preactivation branch does not contain exactly one receipt commit",
            "STOP_NO_CONSTRUCTIVE_REPAIR",
        )
    if not receipt_exact:
        return result(
            "REJECTED",
            "the sole receipt commit is not the exact allowed child of G",
            "STOP_NO_CONSTRUCTIVE_REPAIR",
        )

    if pr_count == 0:
        return result(
            "RECEIPT_COMMITTED_PR_MISSING",
            "the exact receipt exists but no preactivation pull request exists",
            "OPEN_OR_REUSE_EXACT_PR_WITHOUT_NEW_COMMIT",
        )
    if pr_count != 1:
        return result(
            "REJECTED",
            "the role has more than one preactivation pull request",
            "STOP_NO_CONSTRUCTIVE_REPAIR",
        )
    if not pr_exact:
        return result(
            "REJECTED",
            "the preactivation pull request head or base is not exact",
            "STOP_NO_CONSTRUCTIVE_REPAIR",
        )

    normalized_status = status_state.lower() if isinstance(status_state, str) else None
    if normalized_status in (None, "pending"):
        return result(
            "PR_OPEN_STATUS_PENDING",
            "the exact pull request exists but its exact-head trusted status is not terminal",
            "REREAD_EXACT_HEAD_TRUSTED_STATUS",
        )
    if normalized_status == "success":
        if status_within_window is True:
            return result(
                "ADMITTED",
                "the exact-head trusted status succeeded inside the signed window",
                "STOP_PREACTIVATION_COMPLETE",
            )
        if status_within_window is False:
            return result(
                "REJECTED",
                "the trusted success was created outside the signed window",
                "STOP_NO_CONSTRUCTIVE_REPAIR",
            )
        return result(
            "BLOCKED",
            "trusted status timing is unknown",
            "REREAD_TRUSTED_STATUS_CREATED_AT",
        )
    if normalized_status in TERMINAL_FAILURE_STATES:
        return result(
            "REJECTED",
            f"the exact-head trusted status is terminal {normalized_status}",
            "STOP_NO_CONSTRUCTIVE_REPAIR",
        )
    return result(
        "BLOCKED",
        f"unrecognized trusted status state: {status_state!r}",
        "REREAD_EXACT_HEAD_TRUSTED_STATUS",
    )


def _load_payload(path: str | None) -> dict[str, Any]:
    if path:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON input path; omit to read stdin")
    args = parser.parse_args()
    payload = _load_payload(args.input)
    print(json.dumps(classify(**payload), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
