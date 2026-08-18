# Project Supernova Scheduled Task Bus Protocol v2.0

## 1. Authority separation

This repository stores external orchestration/evidence only. Math Foundry owns mathematical/runtime truth. Mastermind is PRE_REVIEW_ONLY. A task receipt, verifier vote, integrator summary, research result, or director decision cannot by itself create a Foundry `ReactionRecord`, `VerifiedProduct`, selector/controller, ignition state, or runtime upgrade.

## 2. Canonical identity

`TASK_NETWORK_PLAN_ID=0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`.

The currently accepted network checkpoint and runtime identity live in `state/CURRENT.json`. All immutable receipts must bind the exact plan/checkpoint/runtime/assignment identities actually observed.

## 3. Public-safe split

`Kitahl/Project-supernova-` is public and may contain only public-safe orchestration/evidence metadata, opaque protected-manifest IDs, hashes, non-sensitive research summaries, and non-protected replay evidence.

Never publish hidden benchmark contents, protected benchmark names/item IDs, secrets, credentials, private source payloads, or confidential artifacts here. Protected/fresh manifest payloads live only in an approved private connector surface. Current private vault is `Kitahl/thoma`.

## 4. Active assignment pointer

Workers do not derive assignments from wall-clock cohort names. They fetch `state/CURRENT.json`, then read `active_cohort_id`, `active_assignment_path`, and the assignment's Git identity. The director changes the pointer only after a new immutable assignment exists and rereads correctly.

## 5. Fail closed

If state, assignment, plan ID, checkpoint, runtime state, worker entry, visibility token, assignment Git identity, private manifest, evidence ownership, evaluator contract, or required CI status is missing/mismatched, the affected action is `SAFE_REPLAY_ONLY` or `WAITING_*`. No fresh/protected evidence may be consumed.

## 6. Create-once receipts

Workers create exactly one immutable `reports/<cohort>/<worker>.json`. MM-06 creates `verification/<cohort>.json`; MF-06 creates `integration/<cohort>.json`; BIL-00 creates `director/<cohort>.json`; deep research creates `research/results/<research_id>.json`. Use GitHub create-file only. Existing immutable paths are never overwritten; corrections are superseding receipts with explicit lineage.

## 7. Polling, not timing inference

Scheduled minutes are polling cadence only. No component may infer predecessor completion from elapsed time. If prerequisites are absent, return `WAITING_*` and create no terminal receipt.

## 8. Two-cohort GitHub calibration

No fresh/protected evidence until **two consecutive assigned replay-only cohorts** demonstrate the complete chain: assignment fetch → exact token/identity match → all 12 worker report writes+rereads → MM-06 fan-in/verification → MF-06 integration → BIL-00 director decision → next-assignment publication/state update. Any assigned calibration failure resets the streak.

`FRESH_ENABLED` means transport eligibility only. It never by itself authorizes benchmark access.

## 9. Fresh/protected evidence

Fresh work requires all of:
1. state mode `FRESH_ENABLED`;
2. explicit worker `fresh_allowed=true` in the immutable assignment;
3. opaque `private_manifest_id` and private manifest Git/blob identity;
4. successful fetch from the private vault;
5. `FROZEN_PRE_OUTCOME` manifest status;
6. exact plan/cohort/checkpoint/runtime agreement;
7. exact task/evaluator/model/tools/budget/randomization/cache/retention/accounting/contamination contract;
8. exact disjoint task→worker ownership;
9. no sealed/consumed/forbidden evidence.

The public repo carries only the opaque manifest ID and hash/commit identity, never hidden task contents.

## 10. Worker roles

Worker scientific roles are defined in `config/roles.json`. Workers may produce external observations/candidates and `research_questions`; originating workers cannot promote themselves.

## 11. Verification and integration

MM-06 independently verifies exact Git receipts, assignment/fresh-manifest identity, CI status where available, evidence ownership, cost/confound controls, source/evaluator freezes, negative/zero outcomes, and authority boundaries. Unsafe receipts are quarantined.

MF-06 consumes only MM-06 safe Git refs, reconciles by evidence tier rather than vote, and may emit a `RUNTIME_HANDOFF_PACKET` only as `READY_FOR_EXTERNAL_IMPLEMENTATION`.

## 12. Director and deep research

BIL-00 is the final external director. It advances only the network checkpoint/assignment pointer, never runtime truth by consensus.

**BIL-00 is also the only scheduled task allowed to run deep research.** It performs a single consolidated deep-research sweep exactly at `00:58` and `12:58` America/Vancouver. Every other task is prohibited from deep research and may only emit structured `research_questions`/`research_needs`.

Research receipts are create-once and idempotent by slot. Research may redirect later assignments but cannot promote runtime state or consume sealed holdouts.

## 13. Runtime handoff

A runtime state may change only after a separate independently validated `RUNTIME_UPDATE_RECEIPT` containing artifact hashes, validator results, lineage/accounting identity, before/after diagnostics, and required fresh prospective evidence. Task consensus never substitutes for this receipt.

## 14. Protected evidence

Two previously designated Oracle holdout slots remain sealed. Their names, contents, and item IDs must not be published in this public repository or exposed to ordinary worker/research runs.
