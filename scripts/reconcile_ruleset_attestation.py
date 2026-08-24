#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/" + REPO
EXPECTED_STATUS_APP_INTEGRATION_ID = 4697060
REQUIRED = {
    "static": "supernova/static-control",
    "report": "supernova/report-admission",
    "transition": "supernova/transition-admission",
}
DIAGNOSTIC_CONTEXTS = {
    "pr_required": "supernova/ruleset/pr-required",
    "deletion_blocked": "supernova/ruleset/deletion-blocked",
    "non_fast_forward_blocked": "supernova/ruleset/non-fast-forward-blocked",
    "status_app": "supernova/ruleset/status-app-4697060",
    "static_bound": "supernova/ruleset/static-source-bound",
    "report_bound": "supernova/ruleset/report-source-bound",
    "transition_bound": "supernova/ruleset/transition-source-bound",
    "spoof_resistant": "supernova/ruleset/spoof-resistant",
    "strict_up_to_date": "supernova/ruleset/strict-up-to-date",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def api(url: str, method: str = "GET", data=None, auth: bool = False):
    req = urllib.request.Request(
        url,
        data=(json.dumps(data).encode("utf-8") if data is not None else None),
        method=method,
    )
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if auth and TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def post(sha: str, context: str, state: str, description: str):
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN missing")
    api(
        API + "/statuses/" + sha,
        "POST",
        {"state": state, "context": context, "description": description[:140]},
        auth=True,
    )


def evaluate_rules(rules):
    types = {r.get("type") for r in rules if isinstance(r, dict)}
    checks = []
    status_rules = []
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
            continue
        params = rule.get("parameters") or {}
        rows = params.get("required_status_checks") or []
        if isinstance(rows, list):
            checks.extend(x for x in rows if isinstance(x, dict))
            status_rules.append((params, [x for x in rows if isinstance(x, dict)]))

    by_context = {}
    for row in checks:
        ctx = row.get("context")
        if isinstance(ctx, str):
            by_context.setdefault(ctx, []).append(row.get("integration_id"))

    def source_bound(ctx):
        ids = by_context.get(ctx) or []
        return bool(ids) and all(type(x) is int and x == EXPECTED_STATUS_APP_INTEGRATION_ID for x in ids)

    static_bound = source_bound(REQUIRED["static"])
    report_bound = source_bound(REQUIRED["report"])
    transition_bound = source_bound(REQUIRED["transition"])
    distinct_required = all(name in by_context for name in REQUIRED.values())
    status_app = distinct_required and all(source_bound(ctx) for ctx in REQUIRED.values())
    strict_up_to_date = any(
        params.get("strict_required_status_checks_policy") is True
        and all(
            [row.get("integration_id") for row in rows if row.get("context") == ctx]
            == [EXPECTED_STATUS_APP_INTEGRATION_ID]
            for ctx in REQUIRED.values()
        )
        for params, rows in status_rules
    )

    return {
        "pr_required": "pull_request" in types,
        "deletion_blocked": "deletion" in types,
        "non_fast_forward_blocked": "non_fast_forward" in types,
        "status_app": status_app,
        "static_bound": static_bound,
        "report_bound": report_bound,
        "transition_bound": transition_bound,
        "spoof_resistant": distinct_required and static_bound and report_bound and transition_bound and strict_up_to_date,
        "strict_up_to_date": strict_up_to_date,
        "expected_status_app_integration_id": EXPECTED_STATUS_APP_INTEGRATION_ID,
        "required_context_integrations": {name: by_context.get(name, []) for name in REQUIRED.values()},
        "rule_types": sorted(x for x in types if isinstance(x, str)),
    }


def publish_all(sha: str, result, prefix: str = ""):
    for key, context in DIAGNOSTIC_CONTEXTS.items():
        ok = bool(result.get(key))
        desc = (prefix + ("PASS" if ok else "FAIL"))[:140]
        post(sha, context, "success" if ok else "failure", desc)


def main():
    try:
        number = int(os.environ.get("PR_NUMBER", "0"))
    except ValueError:
        number = 0
    if number <= 0:
        print("RULESET ATTESTATION SKIP: missing PR number")
        return 0

    pr = api(API + f"/pulls/{number}", auth=True)
    head = (pr or {}).get("head") or {}
    sha = head.get("sha")
    if not isinstance(sha, str) or not HEX40.fullmatch(sha):
        print("RULESET ATTESTATION SKIP: invalid PR head")
        return 0

    try:
        rules = api(API + "/rules/branches/main", auth=False)
        if not isinstance(rules, list):
            raise RuntimeError("unexpected public GitHub rules response")
        result = evaluate_rules(rules)
        publish_all(sha, result)
        print("RULESET ATTESTATION", json.dumps(result, sort_keys=True))
    except Exception as exc:
        result = {key: False for key in DIAGNOSTIC_CONTEXTS}
        publish_all(sha, result, "query-error: ")
        print("RULESET ATTESTATION QUERY ERROR", repr(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
