# Project Supernova Scheduled Task Bus Protocol v2.2

## 1. Authority separation
This repository is an external experiment/referee/research bus only. Math Foundry owns mathematical/runtime truth. Mastermind is PRE_REVIEW_ONLY. A worker receipt, verifier verdict, integration, director decision, research result, GitHub commit, or CI result cannot by itself create a Foundry `ReactionRecord`, `VerifiedProduct`, selector/controller, ignition state, or runtime upgrade.

## 2. Canonical identity
`TASK_NETWORK_PLAN_ID=ec86c19d38aec9a8a5f8f6c88169d7b4d770897e44b2aad82e02c0afba40545f`.
The mutable network pointer lives in `state/CURRENT.json`. Runtime identity and network checkpoint are separate. A runtime state changes only through a separate independently validated `RUNTIME_UPDATE_RECEIPT`.

## 3. Public/private split
`Kitahl/Project-supernova-` is public-safe orchestration/evidence storage. It may contain public replay evidence, non-sensitive research summaries, opaque protected-manifest/evidence IDs, hashes, and receipts. It must never contain protected benchmark names/item IDs/content, hidden prompts, private manifest payloads, secrets, credentials, worker-auth raw secrets, or confidential artifacts. Protected/fresh manifest payloads live only in the approved private vault `Kitahl/thoma`.

## 4. Cohort control freeze
Every countable cohort has exactly one immutable `control/<cohort>.json`. It binds the plan ID, cohort ID, generation sequence, exact `parent_state_git_identity`, and the exact Git blob identities of all control files named by the plan, including protocol, worker protocol, plan, roles, worker-auth commitments, state/control/receipt schemas, validator, and workflow. The assignment binds the control-manifest path and blob identity. Every worker, MM-06, MF-06, and BIL-00 must fetch that exact manifest and verify every frozen file identity. A cohort containing mixed control-plane revisions is ineligible for calibration or scientific promotion.

## 5. Worker identity proof under shared GitHub credentials
All scheduled writes currently use one GitHub app/account identity, so GitHub actor identity alone cannot distinguish workers. Each worker therefore has a prompt-private 256-bit capability secret. Only SHA-256 commitments are public in `config/worker_auth.json`.
For a report, worker `W` computes:
`worker_auth_proof = HMAC-SHA256(secret_W, TASK_NETWORK_PLAN_ID|cohort_id|assignment_git_identity|control_manifest_git_identity|worker_id)`.
The report contains the public commitment plus this cohort-bound proof, never the secret. MM-06 holds verifier copies of the worker secrets and independently recomputes the proof. Reusing a proof in another cohort fails because assignment/control identities change. This mitigates sibling-worker spoofing and accidental cross-writes; it does not create separate GitHub credentials and does not protect against a compromised MM-06/verifier.

## 6. Active state and retry-safe lineage
Workers fetch `state/CURRENT.json`, then read `generation_seq`, `active_cohort_id`, assignment/control paths and Git identities, checkpoint, runtime state, network mode, and supersession ledger. They never derive cohort identity from wall-clock time.
Every new control+assignment binds the exact Git blob SHA of the parent `state/CURRENT.json`. BIL-00 derives the next cohort ID from generation sequence plus the parent-state SHA prefix. BIL-00 creates and rereads immutable control+assignment artifacts first, then updates state using the previously fetched state blob SHA. If that optimistic update fails, a retry may adopt the existing artifacts only if their `parent_state_git_identity` equals the still-current state SHA and every immutable artifact rereads/validates exactly. If state advanced, the retry uses a different parent-derived cohort ID; stale orphan artifacts are never overwritten or adopted.

## 7. Fail closed
Missing/mismatched state, parent lineage, plan, control manifest, frozen control file, assignment, checkpoint, runtime state, worker entry, token, worker-auth proof, Git identity, private manifest, evidence ownership, evaluator contract, or other required prerequisite => `SAFE_REPLAY_ONLY`/`WAITING_*`; no fresh/protected evidence. An explicit failing GitHub check blocks/quarantines. Pending may wait. `CI_NOT_OBSERVED` is neither PASS nor permanent failure; MM-06 must independently perform the repository invariant/schema/public-safety checks available through the connector.

## 8. Create-once receipts and supersession
Workers create one immutable `reports/<cohort>/<worker>.json`; MM-06 creates `verification/<cohort>.json`; MF-06 creates `integration/<cohort>.json`; BIL-00 creates `director/<cohort>.json`; BIL-00 deep research creates `research/results/<research_id>.json`. Use create-file only. Never overwrite immutable receipts. Corrections create explicit superseding lineage. A superseded cohort is recorded under `superseded/<cohort>.json`; it remains historical evidence but can never increment calibration streak or support promotion.

## 9. Polling, not timing inference
Scheduled minutes are polling cadence only. No task infers predecessor completion from elapsed time. Missing prerequisites => `WAITING_*` and no terminal receipt.

## 10. Two-cohort canonical calibration
No fresh/protected evidence until two consecutive non-superseded replay-only cohorts, each bound to one frozen control manifest and valid worker-auth proofs, demonstrate: control+assignment fetch → exact identity/token/auth match → all 12 worker report writes+rereads → MM-06 verification → MF-06 integration → BIL-00 decision → next control+assignment publication/state update. A failed assigned calibration cohort resets the streak. `FRESH_ENABLED` means transport eligibility only, not benchmark authorization.

## 11. Fresh/protected evidence
Fresh work additionally requires explicit `fresh_allowed=true`, opaque private manifest ID+Git identity, successful private-vault fetch, `FROZEN_PRE_OUTCOME`, exact plan/control/cohort/checkpoint/runtime agreement, exact task/evaluator/checker/model/tools/environment/budget/randomization/cache/context/retention/accounting/contamination contract, exact disjoint task ownership, and sealed/consumed/forbidden-evidence exclusions. The public repo carries only opaque IDs/hashes for protected work. Single-route VBS is not a universal ceiling when the admissible policy can schedule multiple complementary routes.

## 12. Worker reporting
Roles live in `config/roles.json`. Workers may produce external observations/candidates and structured `research_questions`; originating workers cannot promote themselves. No worker, auditor, verifier, or integrator may perform deep research. Every countable report must bind the frozen control manifest, assignment, worker-auth commitment/proof, checkpoint/runtime, use standardized status/mode/cost fields, preserve negative/zero/unknown results, and prove Git reread.

## 13. Verification and integration
MM-06 independently verifies exact Git receipts, frozen control+assignment lineage, worker-auth proofs, private-manifest identity without publishing its payload, evidence ownership, schema/public-safety invariants, cost/confound controls, source/evaluator freezes, negative/zero outcomes, and authority boundaries. Unsafe reports are quarantined. MF-06 consumes only MM-06-safe Git refs, reconciles by evidence tier rather than vote, and may emit a `RUNTIME_HANDOFF_PACKET` only as `READY_FOR_EXTERNAL_IMPLEMENTATION`.

## 14. Director and deep research
BIL-00 is the final external director. It advances network assignment/checkpoint state only. BIL-00 is the only scheduled deep-research executor, at 00:58 and 12:58 America/Vancouver. Research inputs are restricted to questions that survived MM-06 verification and MF-06 integration, plus unresolved previously accepted research. Raw unverified worker questions are never direct research inputs. Each slot is idempotent/create-once. Research may redirect later assignments but cannot promote runtime state or consume sealed holdouts.

## 15. Scientific progression
Immediate progression: transport calibration → E1 route/schedule truth → one-generation fresh prospective G1 gain on an objectively selected gap → C1 product closure when justified → E3 learned/random/no-change executable controls → C2/operator transfer → actual runtime reaction-affordance structures/selectors only after executable causal evidence → E5 multi-generation → E5B improver-of-improver → E6 independent capability admission. Correctness and clean evidence dominate benchmark score.

## 16. Protected evidence
The previously designated Oracle holdout slots remain opaque and sealed. Their names, contents, item IDs, and private assignment payloads must not appear in the public bus or ordinary deep research.
