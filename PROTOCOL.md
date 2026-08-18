# Project Supernova Scheduled Task Bus Protocol v2.3

## 1. Authority
This GitHub network is external experiment/referee/research infrastructure only. Math Foundry owns mathematical/runtime truth. Mastermind is PRE_REVIEW_ONLY. No task receipt, vote, research result, GitHub commit, CI result, benchmark score, or director decision creates runtime truth by itself.

## 2. Canonical plan
`TASK_NETWORK_PLAN_ID=61fbe7206e43ec538f310acf875e72865daf8fbb0e4ccbe27dcd6d1a072ff8a0`.
Runtime identity and network checkpoint are separate. Runtime changes require a separately and independently validated `RUNTIME_UPDATE_RECEIPT`.

## 3. Persistent sessions and naming
The 15 existing scheduled tasks are persistent lanes. Do not recreate them to start a new iteration. Their stable names and every-run header/report format are defined in `SESSION_STANDARD.md`. Dynamic iteration, number, goal, model target, phase and execution mode belong in the session header, not in new chat creation.

## 4. Model target
All lanes target `GPT-5.6 Sol` with `EXTRA_HIGH` reasoning. The available Scheduled Tasks automation surface does not expose a model/reasoning-effort selector, so tasks must not fabricate enforcement. Every run reports `MODEL_BINDING_STATUS`. Model-sensitive fresh benchmark evidence is non-promotable unless the frozen private execution manifest and observed runtime identity satisfy the predeclared model-binding rule.

## 5. Public/private split
`Kitahl/Project-supernova-` is public-safe orchestration/evidence storage. Protected/fresh manifest payloads live only in private `Kitahl/thoma`. Never publish protected benchmark names/item IDs/content, hidden prompts, private manifest payloads, secrets, credentials, raw worker-auth secrets, or confidential artifacts. Public protected references are opaque IDs/hashes only.

## 6. Frozen cohort control
Every countable cohort has one immutable `control/<cohort>.json` containing plan ID, cohort ID, generation sequence, parent-state Git blob and exact Git blob identities of every control file listed by the plan. Every worker, MM-06, MF-06 and BIL-00 must verify the exact frozen control set. Mixed control revisions make a cohort ineligible.

## 7. Worker identity under shared GitHub credentials
Because workers share one GitHub app identity, each worker has a prompt-private 256-bit secret whose SHA-256 commitment is public in `config/worker_auth.json`. A report carries a cohort-bound HMAC proof:
`HMAC-SHA256(secret, task_network_plan_id|cohort_id|assignment_git_identity|control_manifest_git_identity|worker_id)`.
MM-06 independently verifies commitment and HMAC using verifier-side copies. Raw secrets never enter GitHub or research.

## 8. Retry-safe state lineage
BIL-00 fetches the current state blob SHA `S`, creates the next immutable control+assignment bound to `S`, rereads them, then optimistically updates `state/CURRENT.json` with expected SHA `S`. A retry may adopt existing artifacts only when their parent-state SHA is exactly the still-current `S` and all bytes validate; otherwise a new parent-derived cohort ID is required. Orphans are never overwritten.

## 9. Fail closed
Missing/mismatched plan, control, parent state, assignment, checkpoint, runtime, token, HMAC, private manifest, evidence ownership, evaluator/checker, model-binding requirement, benchmark manifest, schema, or explicit failing CI => WAITING/BLOCKED/SAFE_REPLAY_ONLY and no protected evidence. `CI_NOT_OBSERVED` is not PASS.

## 10. Real schema validation and closed-world envelopes
GitHub CI and MM-06 must execute the frozen Draft 2020-12 schemas using the pinned validator in `requirements-validation.txt`; custom field checks are additional controls, not substitutes. Countable top-level receipts use `additionalProperties:false`. Deliberately extensible role payloads are isolated in explicit fields and remain subject to recursive public-safety scanning.

## 11. Post-write reread authority
A worker may attempt a reread, but it cannot independently certify its own later Git event. The worker report does not provide authoritative reread proof. MM-06 must fetch each report after creation and record path/blob/commit plus `verifier_reread_verified=true`; only that later verifier observation counts toward calibration/promotion.

## 12. Standard report framework
All scheduled outputs begin with the `SESSION_STANDARD.md` header. Countable receipts carry standardized session header, executive status, task ledger, issue ledger, test ledger, plan alignment, provenance, cost ledger, research queue/findings, and next action. Negative/zero/unknown results remain first-class.

## 13. Two-cohort short transport calibration
No fresh/protected benchmark work until two consecutive non-superseded replay-only cohorts complete: frozen control+assignment read → exact token/HMAC match → 12 immutable worker reports → MM-06 schema/auth/reread verification → MF-06 integration → BIL-00 decision → retry-safe next state publication. The calibration workload should be short/minimal and is not scientific benchmark evidence. Failure resets the streak.

## 14. Fresh/protected evidence
`FRESH_ENABLED` is transport eligibility only. Fresh work additionally requires explicit assignment ownership and a private `FROZEN_PRE_OUTCOME` manifest binding plan/control/cohort/checkpoint/runtime, task/evaluator/checker, actual model/tools/environment, total budget, randomization/repeats, cache/context/retention, accounting, contamination exclusions and disjoint ownership. Single-route VBS is not a universal ceiling when multi-route schedules are admissible.

## 15. Benchmark succession
Canonical benchmark state is in `benchmark/registry.json`. Mastermind and Math Foundry advance independently. A suite is terminal only when every frozen task/arm/repeat has a terminal status, costs and evaluator/checker receipts are closed, and contamination/adjudication holds are resolved. Terminal does not mean success. BIL-00 advances only after an immutable verified benchmark-completion receipt and successor preflight/private freeze. If no eligible successor exists, enter `BENCHMARK_DISCOVERY_WAIT`; BIL-00's next 12-hour research pass may propose candidates, but no fresh evidence is consumed until a new suite is frozen.

## 16. Verification/integration/director
MM-06 verifies control/assignment lineage, worker HMACs, Draft-2020-12 schema conformance, public safety, independent Git rereads, evidence ownership, model-binding status, costs/confounds and authority boundaries. MF-06 consumes only MM-06 safe refs and reconciles by evidence tier, not vote. BIL-00 alone advances network state and benchmark cursors. Runtime handoffs remain `READY_FOR_EXTERNAL_IMPLEMENTATION` until actual validated code artifacts exist.

## 17. Deep research
BIL-00 is the only scheduled deep-research executor, exactly at 00:58 and 12:58 America/Vancouver. Inputs are only questions surviving MM-06 and MF-06 plus unresolved previously accepted research. Raw worker questions are never direct research inputs. Research is create-once/idempotent, public-safe, cannot promote runtime state and cannot consume sealed holdouts.

## 18. Scientific roadmap
T0 transport → E1 route/schedule truth → one-generation fresh G1 before amplification → C1 → E3 → C2/transfer → executable reaction-affordance/selector/ignition after causal evidence → E5 → E5B → E6. Correctness and clean evidence dominate score.
