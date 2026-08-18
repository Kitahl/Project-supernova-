# Project Supernova Scheduled Task Bus Protocol v2.0

## 1. Authority separation

This repository stores external orchestration/evidence only. Math Foundry owns mathematical/runtime truth. Mastermind is PRE_REVIEW_ONLY. A task receipt, verifier vote, integrator summary, research result, or director decision cannot by itself create a Foundry `ReactionRecord`, `VerifiedProduct`, selector/controller, ignition state, or runtime upgrade.

## 2. Canonical identity

`TASK_NETWORK_PLAN_ID=0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`.

The accepted network checkpoint and runtime identity live in `state/CURRENT.json`. All immutable receipts bind the exact plan/checkpoint/runtime/assignment identities actually observed.

## 3. Public-safe split

`Kitahl/Project-supernova-` is public and may contain only public-safe orchestration/evidence metadata, opaque protected-manifest IDs, hashes, non-sensitive research summaries, and non-protected replay evidence. Never publish hidden benchmark contents, protected benchmark names/item IDs, secrets, credentials, private source payloads, or confidential artifacts here. Protected/fresh manifest payloads live only in an approved private connector surface. Current private vault: `Kitahl/thoma`.

## 4. Active assignment pointer

Workers fetch `state/CURRENT.json`, then read `active_cohort_id`, `active_assignment_path`, and assignment Git identity. They do not derive assignment identity from wall-clock time. BIL-00 changes the pointer only after a new immutable assignment exists and rereads correctly.

## 5. Fail closed

Missing/mismatched state, assignment, plan ID, checkpoint, runtime state, worker entry, visibility token, assignment Git identity, private manifest, evidence ownership, evaluator contract, or other required prerequisite => `SAFE_REPLAY_ONLY` or `WAITING_*`; no fresh/protected evidence.

GitHub validation semantics: an **explicit failing** CI/check result blocks/quarantines. A pending result may wait. If the connector exposes no status/check surface, record `CI_NOT_OBSERVED` and independently perform the schema/public-safety/invariant checks; absence of an observable status is neither a pass nor a permanent failure.

## 6. Create-once receipts

Workers create one immutable `reports/<cohort>/<worker>.json`; MM-06 creates `verification/<cohort>.json`; MF-06 creates `integration/<cohort>.json`; BIL-00 creates `director/<cohort>.json`; deep research creates `research/results/<research_id>.json`. Use create-file only. Existing immutable paths are never overwritten; corrections use explicit superseding lineage.

## 7. Polling, not timing inference

Scheduled minutes are polling cadence only. No component infers predecessor completion from elapsed time. Missing prerequisites => `WAITING_*` and no terminal receipt.

## 8. Two-cohort GitHub calibration

No fresh/protected evidence until two consecutive assigned replay-only cohorts demonstrate assignment fetch → exact token/identity match → all 12 worker report writes+rereads → MM-06 verification → MF-06 integration → BIL-00 decision → next-assignment publication/state update. Any assigned calibration failure resets the streak. `FRESH_ENABLED` means transport eligibility only, not benchmark authorization.

## 9. Fresh/protected evidence

Fresh work requires state `FRESH_ENABLED`; explicit worker `fresh_allowed=true`; opaque `private_manifest_id` plus private Git identity; successful private-vault fetch; `FROZEN_PRE_OUTCOME`; exact plan/cohort/checkpoint/runtime agreement; exact task/evaluator/model/tools/budget/randomization/cache/retention/accounting/contamination contract; exact disjoint ownership; and no sealed/consumed/forbidden evidence. Public GitHub carries only opaque IDs/hashes, never protected task contents.

## 10. Worker roles

Roles live in `config/roles.json`. Workers may produce external observations/candidates and structured `research_questions`; originating workers cannot promote themselves. No worker, verifier, integrator, or auditor may perform deep research.

## 11. Verification and integration

MM-06 independently verifies exact Git receipts, assignment/private-manifest identity, CI status where observable, evidence ownership, schema/public-safety invariants, cost/confound controls, source/evaluator freezes, negative/zero outcomes and authority boundaries. Unsafe receipts are quarantined. MF-06 consumes only MM-06 safe Git refs, reconciles by evidence tier rather than vote, and may emit a `RUNTIME_HANDOFF_PACKET` only as `READY_FOR_EXTERNAL_IMPLEMENTATION`.

## 12. Director and deep research

BIL-00 is the final external director. It advances only network checkpoint/assignment state, never runtime truth by consensus. BIL-00 is the **only** scheduled deep-research executor, exactly at 00:58 and 12:58 America/Vancouver. Other tasks only emit/consolidate questions. Each research slot is idempotent and create-once. Research may redirect later assignments but cannot promote runtime state or consume sealed holdouts.

## 13. Runtime handoff

Runtime state changes only after a separate independently validated `RUNTIME_UPDATE_RECEIPT` containing artifact hashes, validator results, lineage/accounting identity, before/after diagnostics and required fresh prospective evidence. Task consensus never substitutes.

## 14. Protected evidence

Two previously designated Oracle holdout slots remain sealed. Their names, contents and item IDs must not be published in this public repository or exposed to ordinary worker/research runs.
