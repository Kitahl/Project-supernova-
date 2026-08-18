# Project Supernova Scheduled Task Bus Protocol v2.1

## 1. Authority separation
This repository is an external experiment/referee/research bus only. Math Foundry owns mathematical/runtime truth. Mastermind is PRE_REVIEW_ONLY. A worker receipt, verifier verdict, integration, director decision, research result, GitHub commit, or CI result cannot by itself create a Foundry `ReactionRecord`, `VerifiedProduct`, selector/controller, ignition state, or runtime upgrade.

## 2. Canonical identity
`TASK_NETWORK_PLAN_ID=90d04ec1f293d153fde2ea518e530b594d602d17a4c77411ae56c71ca21a3682`.
The mutable network pointer lives in `state/CURRENT.json`. Runtime identity and network checkpoint are separate. A runtime state changes only through a separate independently validated `RUNTIME_UPDATE_RECEIPT`.

## 3. Public/private split
`Kitahl/Project-supernova-` is public-safe orchestration/evidence storage. It may contain public replay evidence, non-sensitive research summaries, opaque protected-manifest/evidence IDs, hashes, and receipts. It must never contain protected benchmark names/item IDs/content, hidden prompts, private manifest payloads, secrets, credentials, or confidential artifacts.
Protected/fresh manifest payloads live only in the approved private vault `Kitahl/thoma`.

## 4. Cohort control freeze
Every countable cohort has exactly one immutable `control/<cohort>.json`. The control manifest freezes the exact Git blob identities of the plan, protocol, worker protocol, roles, all receipt schemas, validator, and validation workflow. The assignment binds the control-manifest path and blob identity. Every worker, MM-06, MF-06, and BIL-00 must fetch that exact control manifest and verify every frozen file identity before accepting the cohort.
A cohort containing mixed control-plane revisions is **ineligible** for calibration or scientific promotion.

## 5. Active assignment pointer
Workers fetch `state/CURRENT.json`, then read `active_cohort_id`, `active_assignment_path`, `active_assignment_git_identity`, `active_control_manifest_path`, and `active_control_manifest_git_identity`. They never derive cohort identity from wall-clock time.
BIL-00 changes the pointer only after the next immutable control manifest and assignment both exist and reread correctly.

## 6. Fail closed
Missing/mismatched state, plan, control manifest, frozen control file, assignment, checkpoint, runtime state, worker entry, token, Git identity, private manifest, evidence ownership, evaluator contract, or other required prerequisite => `SAFE_REPLAY_ONLY`/`WAITING_*`; no fresh/protected evidence.
An explicit failing GitHub check blocks/quarantines. Pending may wait. `CI_NOT_OBSERVED` is neither PASS nor permanent failure; MM-06 must independently run the repository invariant/schema/public-safety checks available through the connector.

## 7. Create-once receipts and supersession
Workers create one immutable `reports/<cohort>/<worker>.json`; MM-06 creates `verification/<cohort>.json`; MF-06 creates `integration/<cohort>.json`; BIL-00 creates `director/<cohort>.json`; BIL-00 deep research creates `research/results/<research_id>.json`.
Use create-file only. Never overwrite immutable receipts. Corrections create explicit superseding lineage.
A superseded cohort is recorded under `superseded/<cohort>.json`; it remains historical evidence but can never increment calibration streak or support promotion.

## 8. Polling, not timing inference
Scheduled minutes are polling cadence only. No task infers predecessor completion from elapsed time. Missing prerequisites => `WAITING_*` and no terminal receipt.

## 9. Two-cohort canonical calibration
No fresh/protected evidence until **two consecutive non-superseded replay-only cohorts**, each bound to one frozen control manifest, demonstrate:
control+assignment fetch → exact identity/token match → all 12 worker report writes+rereads → MM-06 verification → MF-06 integration → BIL-00 decision → next control+assignment publication/state update.
A failed assigned calibration cohort resets the streak. `FRESH_ENABLED` means transport eligibility only, not benchmark authorization.

## 10. Fresh/protected evidence
Fresh work additionally requires explicit `fresh_allowed=true`, opaque private manifest ID+Git identity, successful private-vault fetch, `FROZEN_PRE_OUTCOME`, exact plan/control/cohort/checkpoint/runtime agreement, exact task/evaluator/checker/model/tools/environment/budget/randomization/cache/context/retention/accounting/contamination contract, exact disjoint task ownership, and sealed/consumed/forbidden-evidence exclusions.
The public repo carries only opaque IDs/hashes for protected work. Single-route VBS is not a universal ceiling when the admissible policy can schedule multiple complementary routes.

## 11. Worker reporting
Roles live in `config/roles.json`. Workers may produce external observations/candidates and structured `research_questions`; originating workers cannot promote themselves. No worker, auditor, verifier, or integrator may perform deep research.
Every countable report must bind the frozen control manifest, use standardized status/mode/cost fields, preserve negative/zero/unknown results, and prove Git reread.

## 12. Verification and integration
MM-06 independently verifies exact Git receipts, control+assignment identity, private-manifest identity without publishing its payload, evidence ownership, schema/public-safety invariants, cost/confound controls, source/evaluator freezes, negative/zero outcomes, and authority boundaries. Unsafe reports are quarantined.
MF-06 consumes only MM-06-safe Git refs, reconciles by evidence tier rather than vote, and may emit a `RUNTIME_HANDOFF_PACKET` only as `READY_FOR_EXTERNAL_IMPLEMENTATION`.

## 13. Director and deep research
BIL-00 is the final external director. It advances network assignment/checkpoint state only.
BIL-00 is the **only** scheduled deep-research executor, at 00:58 and 12:58 America/Vancouver. Research inputs are restricted to questions that survived MM-06 verification and MF-06 integration, plus unresolved previously accepted research. Raw unverified worker questions are never direct research inputs.
Each slot is idempotent/create-once. If no new verified questions exist, BIL-00 continues unresolved accepted questions or records a no-new-input receipt; it does not broaden from unverified material. Research may redirect later assignments but cannot promote runtime state or consume sealed holdouts.

## 14. Scientific progression
Immediate progression: transport calibration → E1 route/schedule truth → one-generation fresh prospective G1 gain on an objectively selected gap → C1 product closure when justified → E3 learned/random/no-change executable controls → C2/operator transfer → actual runtime reaction-affordance structures/selectors only after executable causal evidence → E5 multi-generation → E5B improver-of-improver → E6 independent capability admission.
Correctness and clean evidence dominate benchmark score.

## 15. Protected evidence
The previously designated Oracle holdout slots remain opaque and sealed. Their names, contents, item IDs, and private assignment payloads must not appear in the public bus or ordinary deep research.
