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
EXPECTED_ACTIONS_APP_ID = 15368
EXPECTED_ACTIONS_SLUG = "github-actions"
REQUIRED = {
    "static": "supernova/static-control",
    "report": "supernova/report-admission",
    "transition": "supernova/transition-admission",
}
DIAGNOSTIC_CONTEXTS = {
    "pr_required": "supernova/ruleset/pr-required",
    "deletion_blocked": "supernova/ruleset/deletion-blocked",
    "non_fast_forward_blocked": "supernova/ruleset/non-fast-forward-blocked",
    "actions_app": "supernova/ruleset/actions-app-15368",
    "static_bound": "supernova/ruleset/static-source-bound",
    "report_bound": "supernova/ruleset/report-source-bound",
    "transition_bound": "supernova/ruleset/transition-source-bound",
    "spoof_resistant": "supernova/ruleset/spoof-resistant",
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


def evaluate_rules(rules, actions_app):
    types = {r.get("type") for r in rules if isinstance(r, dict)}
    checks = []
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
            continue
        params = rule.get("parameters") or {}
        rows = params.get("required_status_checks") or []
        if isinstance(rows, list):
            checks.extend(x for x in rows if isinstance(x, dict))

    app_id = (actions_app or {}).get("id")
    app_slug = (actions_app or {}).get("slug")
    actions_ok = app_id == EXPECTED_ACTIONS_APP_ID and app_slug == EXPECTED_ACTIONS_SLUG

    by_context = {}
    for row in checks:
        ctx = row.get("context")
        if isinstance(ctx, str):
            by_context.setdefault(ctx, []).append(row.get("integration_id"))

    def source_bound(ctx):
        ids = by_context.get(ctx) or []
        return bool(ids) and actions_ok and all(x == app_id for x in ids)

    static_bound = source_bound(REQUIRED["static"])
    report_bound = source_bound(REQUIRED["report"])
    transition_bound = source_bound(REQUIRED["transition"])
    distinct_required = all(name in by_context for name in REQUIRED.values())

    return {
        "pr_required": "pull_request" in types,
        "deletion_blocked": "deletion" in types,
        "non_fast_forward_blocked": "non_fast_forward" in types,
        "actions_app": actions_ok,
        "static_bound": static_bound,
        "report_bound": report_bound,
        "transition_bound": transition_bound,
        "spoof_resistant": distinct_required and static_bound and report_bound and transition_bound,
        "observed_app_id": app_id,
        "observed_app_slug": app_slug,
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
        actions_app = api("https://api.github.com/apps/github-actions", auth=False)
        if not isinstance(rules, list) or not isinstance(actions_app, dict):
            raise RuntimeError("unexpected public GitHub rules/app response")
        result = evaluate_rules(rules, actions_app)
        publish_all(sha, result)
        print("RULESET ATTESTATION", json.dumps(result, sort_keys=True))
    except Exception as exc:
        result = {key: False for key in DIAGNOSTIC_CONTEXTS}
        publish_all(sha, result, "query-error: ")
        print("RULESET ATTESTATION QUERY ERROR", repr(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
