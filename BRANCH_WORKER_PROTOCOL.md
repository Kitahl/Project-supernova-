# Project Supernova Branch Worker Protocol v2.4.3

Overlay ID: `78eaafc34bcf56a6c0898d2085ba1462f687c95d9cf0d5d6a46a357d8c2d6f96`

## Authority and precedence
For any cohort whose active state comes from `state/BRANCH_STATE.json` and whose generation branch matches `ps/gen/<cohort>`, **this file is the authoritative worker transport/authentication protocol**.

When branch transport instructions conflict with trunk `PROTOCOL.md` or trunk `WORKER_PROTOCOL.md`, this file and `BRANCH_PROTOCOL.md` take precedence **only for transport, state source, branch destination, worker authentication, independent reread, and branch validation**. The trunk files remain authoritative for scientific authority separation, role semantics, evidence rules, benchmark semantics, model-binding honesty, public/private safety, deep-research ownership and runtime-promotion restrictions unless explicitly strengthened here.

In particular, for branch cohorts this file supersedes:
- trunk `PROTOCOL.md` §7 identity-only HMAC formula;
- trunk `PROTOCOL.md` retry/state transport details where they assume `state/CURRENT.json`;
- trunk `WORKER_PROTOCOL.md` steps that read `state/CURRENT.json`, write a shared branch, or leave HMAC payload implicit.

There is no choice between schemes. Branch cohorts use only `PS-HMAC-SHA256-CANONICAL-REPORT-2`.

## Worker run contract
1. Fetch `state/BRANCH_STATE.json` from ref `ps/v2.4-control-release`.
2. Read active cohort, exact immutable generation branch/head, control/assignment paths+blob SHAs, assigned worker branch, checkpoint/runtime, superseded cohorts, model/reasoning targets.
3. Fetch every generation control file using the exact immutable `generation_head_sha`, not mutable main/control-release.
4. Verify the generation branch still resolves to the frozen head when branch-head visibility is available. Movement invalidates the cohort.
5. Verify exact 21-base + branch-overlay frozen file set and every blob identity according to `branch/CONFIG.json` and `scripts/validate_branch_bus.py`.
6. Fetch assignment from exact generation SHA. Verify plan/cohort/generation/control/checkpoint/runtime, worker entry/token, goal/target program, fresh flag and constraints.
7. Verify prompt-private worker secret commitment against `config/worker_auth.json`. Never print, persist or expose the raw secret.
8. If any prerequisite is missing/mismatched/superseded, fail closed in chat only; create no countable worker receipt and consume no protected/fresh evidence.
9. If the worker report already exists on the assigned worker branch, return `ALREADY_DONE_WAIT`; never overwrite.
10. Begin visible output with the exact standardized session header. `session_header.phase` is the complete exact assignment phase string, not an alias. Goal and target program are copied exactly from the assignment.
11. During calibration: `SAFE_REPLAY_ONLY`; fresh/protected/benchmark/deep-research counters are exactly zero; perform only minimal deterministic assigned role work.
12. No worker deep research. Emit structured research questions only when needed.
13. Build the complete final report against frozen `schemas/report.schema.json`. Public protected data remains opaque only.
14. Set `worker_auth_scheme="PS-HMAC-SHA256-CANONICAL-REPORT-2"` and the public `worker_auth_commitment`.
15. Compute the proof over the **entire report payload**: remove `worker_auth_proof` key entirely; serialize the complete remaining object to UTF-8 JSON with sorted keys, separators `(',', ':')`, `ensure_ascii=false`; compute lowercase `HMAC-SHA256(secret_bytes, canonical_json_bytes)`; insert as `worker_auth_proof`.
16. Write exactly one report to `reports/<cohort>/<worker>.json` on the exact assigned `ps/work/<cohort>/<worker>` branch. Do not write generation/main/control-release/other worker/verifier/integrator/consolidation branches.
17. `origin_reread_claim=false`. A worker may operationally fetch its report, but only MM06 independent branch reread counts.
18. No worker advances network state, benchmark cursor or runtime truth.

## Verification expectations
MM06 must independently verify strict session equality, Draft-2020-12 schema, public safety, generation ancestry, exact branch/head/blob, SHA-256 commitment and the canonical whole-report HMAC. It must test schema-valid wrong phase/goal/content mutations and require session/HMAC rejection.
