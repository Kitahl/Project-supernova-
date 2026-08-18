# Project Supernova Branch GitOps Overlay v2.4

Overlay ID: `78eaafc34bcf56a6c0898d2085ba1462f687c95d9cf0d5d6a46a357d8c2d6f96`  
Base scientific plan: `61fbe7206e43ec538f310acf875e72865daf8fbb0e4ccbe27dcd6d1a072ff8a0`  
Mastermind audit envelope: `04fb7609f0384be488fd49278c23ec8b4cf5829b85300dbe1e5e5500d1badfe2`  
Mastermind native plan: `e3ea181008b109073f09b3cb8801165e138ae813a9d117766bb2ce24c422469d`  
Math Foundry 3.0.1 collaboration validation: `PASS`.

## Purpose

This overlay changes transport/orchestration only. It does not change Math Foundry mathematical authority, Mastermind PRE_REVIEW_ONLY status, scientific benchmark semantics, holdout rules, or the runtime state. It exists to eliminate mixed-control revisions and shared-branch write races.

## Branch topology

For each cohort `<C>`:

- Frozen generation branch: `ps/gen/<C>`
- Worker branches: `ps/work/<C>/<WORKER>` for MF01, MF02, MF03, MF04, MF05, MM01, MM02, MM03, MM04, MM05, MM07, EXT01
- Verifier branch: `ps/verify/<C>`
- Integrator branch: `ps/integrate/<C>`
- Director consolidation branch: `ps/consolidate/<C>`

`main` is canonical trunk/archive. In-flight workers MUST NOT use mutable `main` as their control source.

## Generation freeze

1. BIL00 captures one trunk SHA `T`.
2. BIL00 creates `ps/gen/<C>` from `T`.
3. On the generation branch, BIL00 creates/validates the control manifest and assignment.
4. BIL00 records the final generation branch head SHA `G` externally in branch state before workers start.
5. After `G` is frozen, `ps/gen/<C>` MUST NOT move. Any head movement invalidates the cohort.
6. Main may change while the generation runs. Those changes apply only to future generations and do not invalidate `<C>`.

## Worker isolation

Each worker branch is created from exact generation SHA `G`. A worker writes only `reports/<C>/<WORKER>.json` on its own branch. Workers never write the generation branch, another worker branch, verifier branch, integrator branch, consolidation branch, or main. A worker report is not authoritative until MM06 independently fetches it from the expected worker branch.

## Verification

MM06 reads the generation branch at exact SHA `G`, then independently fetches each expected worker report from `ps/work/<C>/<WORKER>`. It records branch name, branch head SHA, report blob SHA, HMAC result, schema result, public-safety result, evaluator/source bindings, costs, and quarantine status. MM06 writes one verification receipt to `ps/verify/<C>`.

## Integration

MF06 independently fetches the MM06 verification receipt and only the worker branch refs marked safe by MM06. It writes one integration receipt to `ps/integrate/<C>`. It cannot promote runtime truth.

## Consolidation and CAS merge

BIL00 does not merge 12 worker branches. After verification/integration, it:

1. Captures current main head `M`.
2. Creates `ps/consolidate/<C>` from `M`.
3. Copies only MM06-safe worker receipts plus the verified/integrated/director receipts into canonical `history/<C>/...` paths.
4. Adds the proposed next state/benchmark cursor transition.
5. Opens one PR from `ps/consolidate/<C>` to `main`.
6. Merges only with `expected_head_sha` equal to the reviewed consolidation branch head. If main/state lineage no longer matches the expected parent, fail closed and rebuild the consolidation branch from the new main head; never force-merge stale state.

The PR/merge is the only path by which an external cohort becomes canonical history. Task consensus never changes Math Foundry/Mastermind runtime state.

## Retry and orphan rule

Worker, verifier, integrator, and consolidation paths are create-once. Retries adopt only exact same-cohort same-generation artifacts. Stale branches remain historical/orphaned and are never silently reused. Branch cleanup is optional maintenance and is not part of scientific acceptance.

## Calibration gate

Fresh/protected evidence remains disabled until two consecutive complete replay-only cohorts prove:

- immutable generation ref remains unchanged;
- all 12 worker branches are created from the same `G`;
- all 12 workers write exactly one authenticated report to their own branch;
- MM06 independently rereads all 12 branches and validates HMAC/schema/public safety;
- MF06 integrates only MM06-safe refs;
- BIL00 creates one consolidation PR and performs a CAS-protected merge;
- main may advance independently without invalidating the frozen generation.

## Benchmark succession

Mastermind and Math Foundry cursors advance independently. Completion means every frozen unit/arm/repeat is terminal with evaluator/checker/cost/contamination/adjudication receipts closed; terminal does not mean success. Only a verified completion receipt may advance a cursor. If no eligible successor exists, that program enters `BENCHMARK_DISCOVERY_WAIT`; BIL00's single 12-hour research pass may propose a successor, but adoption still requires source/version/license/access/evaluator/contamination preflight and a private `FROZEN_PRE_OUTCOME` manifest.

## Model binding

All task prompts request `GPT-5.6 Sol` with `EXTRA_HIGH` reasoning. The current automation API does not expose a verifiable model/reasoning selector. Therefore tasks must report model binding honestly as VERIFIED/PARTIAL_UNVERIFIED/UNVERIFIED/MISMATCH. Model-sensitive fresh promotion evidence is inadmissible when the execution manifest cannot verify the required binding.

## Session organization

Existing Scheduled Task IDs are persistent lanes and must be reused. Each lane keeps one standardized title and begins every run with the `SESSION_STANDARD.md` header containing target program, phase, iteration, iteration number, role, goal, runtime identity, requested model/reasoning, binding status, and execution mode.

## Deep research

Only BIL00 may run deep research, exactly at 00:58 and 12:58 America/Vancouver. Inputs are only MM06-safe/MF06-integrated questions plus unresolved accepted prior research. No other task may perform the broad prior sweep.
