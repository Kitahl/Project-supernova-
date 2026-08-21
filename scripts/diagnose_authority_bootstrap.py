#!/usr/bin/env python3
from __future__ import annotations
import contextlib, importlib.util, io, json, os, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
PR_NUMBER = os.environ.get("PR_NUMBER", "")
CONTEXT = "supernova/bootstrap-diagnostic"
MARKER = "<!-- SUPERNOVA_BOOTSTRAP_DIAGNOSTIC -->"


def api(path, method="GET", data=None):
    req = urllib.request.Request(
        "https://api.github.com/repos/" + REPO + path,
        data=(json.dumps(data).encode("utf-8") if data is not None else None),
        method=method,
    )
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def status(sha, state, description):
    api("/statuses/" + sha, "POST", {
        "state": state,
        "context": CONTEXT,
        "description": description[:140],
    })


def report_failure(pr_number, sha, reason):
    body = (
        MARKER + "\n"
        "### Supernova bootstrap structural diagnostic\n\n"
        f"- exact head: `{sha}`\n"
        f"- result: `REFUSED`\n"
        f"- accepted-main verifier reason: `{reason}`\n\n"
        "This is diagnostic only. It does not publish `supernova/bootstrap-admission`, does not merge, and does not weaken any required check."
    )
    comments = api(f"/issues/{pr_number}/comments?per_page=100") or []
    for row in comments:
        existing = row.get("body") or ""
        if MARKER in existing and (row.get("user") or {}).get("login") == "github-actions[bot]":
            api(f"/issues/comments/{row['id']}", "PATCH", {"body": body})
            return
    api(f"/issues/{pr_number}/comments", "POST", {"body": body})


def load_bootstrap():
    path = ROOT / "scripts" / "reconcile_authority_bootstrap.py"
    spec = importlib.util.spec_from_file_location("supernova_trusted_bootstrap_diagnostic", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main():
    if not PR_NUMBER.isdigit() or int(PR_NUMBER) <= 0:
        raise SystemExit("PR_NUMBER required")
    number = int(PR_NUMBER)
    pr = api("/pulls/" + PR_NUMBER)
    sha = ((pr or {}).get("head") or {}).get("sha")
    if not isinstance(sha, str):
        raise SystemExit("cannot resolve PR head")

    mod = load_bootstrap()
    captured = []
    mod.post = lambda state, target_sha, description: captured.append((state, target_sha, description))
    old = os.environ.get("CANDIDATE_DIAGNOSTICS_RESULT")
    os.environ["CANDIDATE_DIAGNOSTICS_RESULT"] = "success"
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            rc = mod.main()
    finally:
        if old is None:
            os.environ.pop("CANDIDATE_DIAGNOSTICS_RESULT", None)
        else:
            os.environ["CANDIDATE_DIAGNOSTICS_RESULT"] = old

    if rc == 0:
        status(sha, "success", "structural bootstrap eligible; candidate diagnostics assumed PASS for diagnostic replay")
        return 0

    reason = "bootstrap structural replay refused"
    if captured:
        reason = captured[-1][2]
    else:
        lines = [x.strip() for x in out.getvalue().splitlines() if x.strip()]
        if lines:
            reason = lines[-1]
    status(sha, "failure", reason)
    report_failure(number, sha, reason)
    print(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
