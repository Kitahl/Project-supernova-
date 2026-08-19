#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
API = "https://api.github.com/repos/" + REPO
REQUIRED_CONTEXTS = {
    "supernova/static-control",
    "supernova/report-admission",
    "supernova/transition-admission",
}
MARKER_CONTEXT = "supernova/admission-watchdog"
RETRY_AFTER_SECONDS = 30 * 60


def req(path: str, method: str = "GET", data=None):
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(API + path, data=body, method=method)
    r.add_header("Accept", "application/vnd.github+json")
    r.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        r.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(r, timeout=30) as z:
        raw = z.read()
        return json.loads(raw) if raw else None


def parse_utc(value: str | None):
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def latest_by_context(statuses):
    latest = {}
    for item in statuses:
        context = item.get("context")
        if not context:
            continue
        previous = latest.get(context)
        current_time = parse_utc(item.get("created_at") or item.get("updated_at"))
        previous_time = parse_utc((previous or {}).get("created_at") or (previous or {}).get("updated_at"))
        if previous is None or (current_time and (not previous_time or current_time >= previous_time)):
            latest[context] = item
    return latest


def admission_context_state(statuses):
    latest = latest_by_context(statuses)
    seen = REQUIRED_CONTEXTS.intersection(latest)
    if not seen:
        return "MISSING_ALL"
    if seen == REQUIRED_CONTEXTS:
        return "COMPLETE"
    return "PARTIAL"


def marker_is_recent(statuses, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    marker = latest_by_context(statuses).get(MARKER_CONTEXT)
    if not marker:
        return False
    created = parse_utc(marker.get("created_at") or marker.get("updated_at"))
    return bool(created and (now - created).total_seconds() < RETRY_AFTER_SECONDS)


def post_status(sha: str, state: str, description: str):
    req(
        "/statuses/" + urllib.parse.quote(sha, safe=""),
        "POST",
        {"state": state, "context": MARKER_CONTEXT, "description": description[:140]},
    )


def dispatch(pr_number: int):
    return req(
        "/actions/workflows/supernova-v25-admission.yml/dispatches",
        "POST",
        {"ref": "main", "inputs": {"pr_number": str(pr_number)}},
    )


def main():
    pulls = req("/pulls?state=open&base=main&per_page=100") or []
    dispatched = 0
    for pr in pulls:
        number = int(pr["number"])
        head = pr["head"]
        head_repo = (head.get("repo") or {}).get("full_name")
        sha = head.get("sha")
        if head_repo != REPO or not sha:
            print(f"PR #{number}: external/unknown head; native pull_request path only")
            continue

        combined = req("/commits/" + urllib.parse.quote(sha, safe="") + "/status?per_page=100") or {}
        statuses = combined.get("statuses", [])
        state = admission_context_state(statuses)
        if state == "COMPLETE":
            print(f"PR #{number}: admission contexts already present")
            continue
        if state == "PARTIAL":
            post_status(sha, "failure", "partial admission contexts observed; fail closed for investigation")
            print(f"PR #{number}: partial contexts; not auto-rerunning")
            continue
        if marker_is_recent(statuses):
            print(f"PR #{number}: recent watchdog dispatch marker; not duplicating")
            continue

        post_status(sha, "pending", "PR admission event absent; dispatching trusted-main fallback")
        try:
            dispatch(number)
        except urllib.error.HTTPError as exc:
            post_status(sha, "failure", f"fallback dispatch failed HTTP {exc.code}")
            raise
        post_status(sha, "success", "trusted-main fallback dispatch accepted")
        dispatched += 1
        print(f"PR #{number}: dispatched v2.5 admission fallback for {sha}")

    print("PR admission watchdog complete; dispatched", dispatched)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
