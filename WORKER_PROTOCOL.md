# Common Scheduled Worker Protocol v2.1

1. Fetch `state/CURRENT.json` from `Kitahl/Project-supernova-`.
2. Read the active cohort, assignment path+Git identity, control-manifest path+Git identity, network checkpoint, runtime state, network mode, and plan ID.
3. Fetch the exact active `control/<cohort>.json`, assignment, and every control file named by the manifest. Verify all Git blob identities exactly. Any drift or mismatch => no cohort receipt and no fresh evidence.
4. Fetch your role from the frozen `config/roles.json` and report contract from the frozen `schemas/report.schema.json`.
5. If `reports/<cohort>/<WORKER_ID>.json` already exists, fetch it and return `ALREADY_DONE_WAIT`; never repeat or overwrite.
6. During `GITHUB_BUS_CALIBRATION`, all work is replay-safe. `fresh_evidence_ids=[]`, `private_manifest_id=null`, and `private_manifest_git_identity=null`.
7. Outside calibration, fresh work is allowed only when state is `FRESH_ENABLED`, your assignment says `fresh_allowed=true`, and the exact opaque private manifest is fetched from `Kitahl/thoma` and passes the full `FROZEN_PRE_OUTCOME` plan/control/cohort/checkpoint/runtime/evaluator/model/tools/environment/budget/randomization/cache/context/retention/accounting/contamination/ownership/exclusion contract.
8. Never mirror protected task names, item IDs, hidden content, or private-manifest payloads into the public repo.
9. Perform only your frozen role. Freeze material source/evaluator/version semantics before measurement. Preserve zero/negative results, unavailable routes, failed attempts, full costs, regressions, and `NOT_MEASURED`.
10. No worker deep research. Add structured `research_questions` only.
11. A countable report must use:
   - `status=VALID_ASSIGNED_REPORT`;
   - `mode=SAFE_REPLAY_ONLY` during calibration/replay or `FRESH_EXECUTION` only when authorized;
   - exact plan/control/assignment/checkpoint/runtime/token identities;
   - `public_safety_status=PASS`;
   - `git_reread_verified=true`;
   - `ci_status` in `PASS|FAIL|PENDING|CI_NOT_OBSERVED`;
   - standardized `cost_ledger` fields including `fresh_evidence_units_consumed`, `protected_manifest_reads`, `benchmark_executions`, `deep_research_runs`.
12. Create exactly one `reports/<cohort>/<WORKER_ID>.json` with GitHub create-file, reread it, and verify the public copy. If creation/reread fails, there is no valid cohort receipt.
13. No originating worker may advance network/runtime state or promote its own candidate.
