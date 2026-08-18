# Common Scheduled Worker Protocol v2.0

For every scheduled worker run:

1. Fetch `PROTOCOL.md`, `state/CURRENT.json`, `config/roles.json`, and `schemas/report.schema.json` from `Kitahl/Project-supernova-`.
2. Read `active_cohort_id`, `active_assignment_path`, `accepted_network_checkpoint_id`, `runtime_state_id`, and `network_mode` from state.
3. Fetch the exact active assignment path. Record its Git blob/commit identity and verify task-network plan ID, cohort, network checkpoint, runtime state, your exact worker entry, visibility token, `fresh_allowed`, opaque private-manifest ID/hash when applicable, constraints and evidence ownership.
4. **No-assignment / mismatch gate:** if state or assignment is missing, stale, mismatched, or unreadable, return `STATUS=WAITING_OR_INVALID_ASSIGNMENT`, `MODE=SAFE_REPLAY_ONLY`, `fresh_evidence_ids=[]`; do not create a cohort report; remain enabled.
5. If `reports/<active_cohort_id>/<WORKER_ID>.json` already exists, fetch and verify it, return `ALREADY_DONE_WAIT`, and do not repeat the work or overwrite the receipt.
6. During `GITHUB_BUS_CALIBRATION`, all workers are replay-safe only. `fresh_evidence_ids=[]` is mandatory.
7. If and only if state mode is `FRESH_ENABLED` and your assignment says `fresh_allowed=true`, fetch the opaque protected manifest from the approved private vault (`Kitahl/thoma`) using the exact `private_manifest_id`/Git identity named in the public assignment. Verify `FROZEN_PRE_OUTCOME`, plan/cohort/checkpoint/runtime IDs, exact evaluator/execution/budget/randomization/cache/retention/accounting/contamination contract, exact task→worker ownership, and sealed/consumed evidence exclusions. Never mirror private manifest contents or protected task names/IDs into the public repo.
8. Any protected-manifest mismatch => do not open fresh evidence; remain `SAFE_REPLAY_ONLY` under the valid assignment.
9. Perform only the scientific role in `config/roles.json`. Freeze material source/evaluator/version semantics before measurement. Preserve zero/negative results, failed attempts, unavailable routes, full costs, regressions and `NOT_MEASURED`.
10. **No worker deep research.** If prior art/current information could materially change a decision, add structured `research_questions`: exact question, parent blocker/claim, why it matters, closure criterion, preferred source families, urgency. BIL-00 handles all deep research twice daily.
11. Build a report conforming to `schemas/report.schema.json`. Do not include hidden/protected benchmark content in the public receipt. Use opaque evidence/manifest IDs only.
12. Create exactly one new GitHub file `reports/<active_cohort_id>/<WORKER_ID>.json` using GitHub create-file. Never overwrite.
13. Reread the public receipt from GitHub and verify its content. Record commit/blob identity. A local file or chat response is not a cohort receipt unless the GitHub copy exists and rereads correctly.
14. If GitHub CI/status is exposed, report it; a failing validation status makes the receipt unsafe for promotion. Pending CI is `WAITING_CI`, not a pass.
15. Task output is external evidence only. No originating worker may promote itself or advance network/runtime state.
