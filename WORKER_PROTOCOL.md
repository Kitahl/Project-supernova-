# Common Scheduled Worker Protocol v2.2

1. Fetch `state/CURRENT.json` from `Kitahl/Project-supernova-`.
2. Read `generation_seq`, active cohort, assignment/control paths+Git identities, network checkpoint, runtime state, network mode, plan ID, and superseded cohorts.
3. Fetch the exact active control manifest and every control file it freezes. Verify all Git blob identities. Verify the control manifest `parent_state_git_identity` and generation are consistent with the assignment lineage. Any drift/mismatch => no cohort report and no fresh evidence.
4. Fetch the exact active assignment. Verify plan ID, cohort, generation, parent-state lineage, network checkpoint, runtime state, control manifest, your worker entry, visibility token, `fresh_allowed`, opaque private-manifest refs, constraints, and evidence ownership.
5. Fetch public `config/worker_auth.json`. Verify the SHA-256 commitment corresponding to your prompt-private `WORKER_AUTH_SECRET_HEX`. Compute `worker_auth_proof = HMAC-SHA256(secret_bytes, task_network_plan_id|cohort_id|assignment_git_identity|control_manifest_git_identity|worker_id)`. Never reveal the raw secret.
6. If state/plan/control/assignment/auth is missing, stale, mismatched, superseded, or unreadable, return `WAITING_OR_INVALID_ASSIGNMENT` / `SAFE_REPLAY_ONLY`, consume no fresh evidence, create no countable cohort report, and remain enabled.
7. If `reports/<active_cohort_id>/<WORKER_ID>.json` already exists, fetch it and return `ALREADY_DONE_WAIT`; never repeat or overwrite.
8. During `GITHUB_BUS_CALIBRATION`, all work is replay-safe. `fresh_evidence_ids=[]`, `private_manifest_id=null`, `private_manifest_git_identity=null`, and all protected/fresh cost counters are zero.
9. Outside calibration, fresh work is allowed only when state is `FRESH_ENABLED`, your assignment says `fresh_allowed=true`, and the exact opaque private manifest is fetched from `Kitahl/thoma` and passes the full `FROZEN_PRE_OUTCOME` plan/control/cohort/checkpoint/runtime/evaluator/checker/model/tools/environment/budget/randomization/cache/context/retention/accounting/contamination/ownership/exclusion contract.
10. Never mirror protected task names, item IDs, hidden content, private-manifest payloads, or worker-auth secrets into the public repo.
11. Perform only your frozen role from `config/roles.json`. Freeze material source/evaluator/version semantics before measurement. Preserve zero/negative results, failed attempts, unavailable routes, full costs, regressions, and `NOT_MEASURED`.
12. No worker deep research. Add structured `research_questions` only.
13. A countable report must use the frozen `schemas/report.schema.json`, including exact plan/control/assignment/checkpoint/runtime/token identities; `worker_auth_scheme=PS-HMAC-SHA256-WORKER-PROOF-1`; your public commitment and cohort-bound auth proof; `status=VALID_ASSIGNED_REPORT`; `mode=SAFE_REPLAY_ONLY` during calibration/replay or `FRESH_EXECUTION` only when authorized; standardized cost ledger; `public_safety_status=PASS`; `git_reread_verified=true`; and `ci_status` in `PASS|FAIL|PENDING|CI_NOT_OBSERVED`.
14. Create exactly one new `reports/<cohort>/<WORKER_ID>.json` using GitHub create-file, then reread and verify the public copy. If creation/reread fails, there is no valid cohort receipt.
15. No originating worker may advance network/runtime state or promote its own candidate.
