# Project Supernova v2.5 — Automated Authority Bootstrap

Status: staged in the final pre-countable authority bootstrap.

## Purpose

Remove routine manual bypasses for future control-plane authority changes without allowing candidate code to approve itself.

## Trust split

1. `candidate-diagnostics` executes the exact PR head only with read-only repository permission, no persisted GitHub credential, no repository secrets, and no status-write capability.
2. `trusted-bootstrap` executes only exact accepted-`main` bytes. Candidate files are data only in this privileged phase.
3. Exact accepted-main `scripts/reconcile_authority_bootstrap.py` may publish `supernova/bootstrap-admission` only when all bootstrap invariants pass.
4. Exact accepted-main `scripts/reconcile_open_prs.py` accepts authority drift only when the latest bootstrap status is `success` and its creator is `github-actions[bot]`; it then runs the ordinary trusted-main static/report/transition admission path and republishes the existing three required contexts.
5. GitHub's existing source-bound ruleset remains the merge authority. The bootstrap verifier itself does not bypass or merge.

## Fail-closed eligibility

Automated authority bootstrap requires:

- same canonical repository;
- repository-owner authored PR;
- base `main`;
- head descends from exact accepted `main`;
- `hardening/` or `rev4/` head prefix;
- read-only candidate diagnostics succeed;
- calibration streak is exactly zero;
- fresh work is disabled;
- protocol remains 2.5;
- specification remains Revision 4;
- plan identity remains unchanged;
- candidate objects are regular files;
- no state, generation, assignment, report, verification, integration, history, transition, benchmark, research, or worker-auth mutation;
- admission source, candidate-code privilege boundary, ref-selectable-dispatch prohibition, protocol freeze, and fresh gate remain intact.

Any uncertainty or mismatch posts bootstrap failure and leaves the normal three contexts failing.

## Monitoring

`PS-JOINT-A01 | Runtime & Transport Audit` is the liveness/authority monitor. It should verify bootstrap workflow presence, exact accepted-main script identity, bootstrap status source, normal three-context results, stale authority PRs, and any discrepancy between bootstrap and normal admission. `PS-JOINT-D01 | Director + 12h Research` owns bounded remediation and may merge only through the normal ruleset after all required contexts are green; no bypass is permitted.

## Current bootstrap

The workflow and trusted verifier introduced by the same PR cannot authorize their own installation. The final pre-countable PR that installs this mechanism therefore remains the last manual owner bootstrap. Once installed on accepted `main`, subsequent eligible authority changes use this automated path.
