#!/usr/bin/env python3
from __future__ import annotations
import contextlib, importlib.util, io, json, os, pathlib, re, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
PR_NUMBER = os.environ.get("PR_NUMBER", "")
CONTEXT = "supernova/bootstrap-diagnostic"


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


def status(sha, state, description, context=CONTEXT):
    api("/statuses/" + sha, "POST", {
        "state": state,
        "context": context,
        "description": description[:140],
    })


def reason_code(reason):
    rules = [
        ("read-only candidate diagnostics", "candidate-diagnostics"),
        ("base is not main", "base-main"),
        ("same-repository owner-authored", "same-repo-owner"),
        ("head prefix", "head-prefix"),
        ("invalid head SHA", "head-sha"),
        ("calibration streak", "streak-zero"),
        ("fresh work", "fresh-off"),
        ("resolve exact accepted main", "accepted-main"),
        ("does not descend from exact accepted main", "current-main-ancestor"),
        ("enumerate candidate changes", "candidate-diff"),
        ("empty authority change", "nonempty-change"),
        ("state/scientific/runtime-sensitive path", "forbidden-path"),
        ("outside automated bootstrap allowlist", "path-allowlist"),
        ("candidate git mode", "regular-git-mode"),
        ("non-regular candidate path", "regular-git-mode"),
        ("candidate data worktree", "candidate-worktree"),
        ("plan identity/protocol", "plan-protocol"),
        ("Revision 4 freeze", "revision-freeze"),
        ("bootstrap root self-modification", "root-self-modification"),
        ("repo policy invariant", "repo-policy"),
        ("admission authority invariant", "admission-authority"),
        ("bootstrap policy invariant", "bootstrap-policy"),
        ("protocol freeze", "protocol-freeze"),
        ("countable control", "countable-control"),
        ("candidate policy parse/check", "candidate-policy-check"),
    ]
    for needle, code in rules:
        if needle.lower() in reason.lower():
            return code
    slug = re.sub(r"[^a-z0-9]+", "-", reason.lower()).strip("-")[:48]
    return slug or "unknown"


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
        status(sha, "success", "structural bootstrap eligibility PASS", "supernova/bootstrap-diagnostic/eligible")
        return 0

    reason = "bootstrap structural replay refused"
    if captured:
        reason = captured[-1][2]
    else:
        lines = [x.strip() for x in out.getvalue().splitlines() if x.strip()]
        if lines:
            reason = lines[-1]
    code = reason_code(reason)
    status(sha, "failure", reason)
    status(sha, "failure", reason, "supernova/bootstrap-diagnostic/" + code)
    print(code, reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
