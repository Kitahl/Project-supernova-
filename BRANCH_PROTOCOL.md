# Project Supernova Branch GitOps Overlay v2.4.1

Overlay ID: `78eaafc34bcf56a6c0898d2085ba1462f687c95d9cf0d5d6a46a357d8c2d6f96`  
Base scientific plan: `61fbe7206e43ec538f310acf875e72865daf8fbb0e4ccbe27dcd6d1a072ff8a0`  
Mastermind audit envelope: `04fb7609f0384be488fd49278c23ec8b4cf5829b85300dbe1e5e5500d1badfe2`  
Mastermind native plan: `e3ea181008b109073f09b3cb8801165e138ae813a9d117766bb2ce24c422469d`  
Math Foundry 3.0.1 collaboration validation: `PASS`.

## Purpose
This overlay changes transport/orchestration only. It does not change Math Foundry mathematical authority, Mastermind PRE_REVIEW_ONLY status, scientific benchmark semantics, holdout rules, or runtime state. It eliminates mixed-control revisions and shared-branch write races.

## Branch topology
For each cohort `<C>`:
- frozen generation: `ps/gen/<C>`
- worker branches: `ps/work/<C>/<WORKER>`
- verifier: `ps/verify/<C>`
- integrator: `ps/integrate/<C>`
- consolidation: `ps/consolidate/<C>`

`main` is canonical trunk/archive. In-flight workers never use mutable `main` as their control source.

## Two-layer validation
`validate_bus.py` is the frozen v2.3 **trunk** validator and keeps the 21-file base control contract. `validate_branch_bus.py` is the v2.4 **branch-overlay** validator. A branch-generation control manifest must equal the exact union of the 21 base files and the six overlay files declared in `branch/CONFIG.json`: `BRANCH_PROTOCOL.md`, `branch/CONFIG.json`, `schemas/branch_generation.schema.json`, `schemas/branch_consolidation.schema.json`, `scripts/validate_branch_bus.py`, and `.github/workflows/validate-branch-bus.yml`.

This separation is intentional. The trunk validator is not used as proof that the branch overlay is complete; the branch validator independently checks the overlay extension, frozen blob identities, assignment/report bindings, and public-safety/schema rules. A mismatch between either declared set and its validator fails closed.

## Generation freeze
1. BIL00 captures one source/control-release SHA.
2. BIL00 creates `ps/gen/<C>` from that exact SHA.
3. It creates and validates the control manifest and assignment on the generation branch.
4. It records final generation SHA `G` in branch state.
5. After `G` is frozen, `ps/gen/<C>` must never move. Movement invalidates the cohort.
6. Main/control-release may later change; those changes apply only to future generations.

## Worker isolation
Each worker branch is created from exact `G`. A worker writes only `reports/<C>/<WORKER>.json` on its own branch. Workers never write generation, another worker, verifier, integrator, consolidation, or main. Originating-worker reread is non-authoritative; MM06 must independently fetch the report.

## Verification
MM06 reads frozen generation controls at `G`, then independently fetches each report from the exact assigned worker branch. It records branch head, report blob, HMAC, Draft-2020-12 schema result, public-safety result, source/evaluator bindings, costs and quarantine status. It also runs the branch validator/negative schema probes. MM06 writes only to `ps/verify/<C>`.

## Integration
MF06 fetches MM06 verification and only MM06-safe worker branch refs, independently rereads them, and writes only to `ps/integrate/<C>`. It cannot promote runtime truth.

## Consolidation and CAS merge
BIL00 does not merge 12 worker branches. It captures current main head `M`, creates `ps/consolidate/<C>` from `M`, copies only verified safe artifacts to `history/<C>/...`, adds director/consolidation receipts and the proposed state/benchmark transition, opens one PR, reviews the exact head, and merges only with GitHub `expected_head_sha` plus state-lineage guards. A stale main/state lineage fails closed and requires rebuilding from the new main; force merge is forbidden.

The single consolidation PR is the only path by which a cohort becomes canonical history. Task consensus never changes Math Foundry/Mastermind runtime state.

## Retry/orphan rule
All worker/verifier/integrator/consolidation output paths are create-once. Retries adopt only exact same-cohort/same-generation artifacts. Stale branches are historical/orphaned and never silently reused.

## Calibration gate
Fresh/protected evidence remains disabled until two consecutive complete replay-only cohorts prove immutable generation, 12 same-base worker branches, authenticated reports, MM06 independent reread/schema/HMAC/public-safety checks, MF06 safe-ref integration, and one CAS-protected consolidation PR/merge. Main drift during an in-flight generation must not invalidate that generation.

## Benchmark succession
Mastermind and Math Foundry cursors advance independently. A suite is complete only when every frozen unit/arm/repeat is terminal and evaluator/checker/cost/contamination/adjudication receipts are closed. Terminal does not mean success. Only a verified completion receipt advances a cursor. If no eligible successor exists, that program enters `BENCHMARK_DISCOVERY_WAIT`; BIL00's single 12-hour research pass may propose a successor, but adoption requires source/version/license/access/evaluator/contamination preflight plus a private `FROZEN_PRE_OUTCOME` manifest.

## Model binding
All prompts request `GPT-5.6 Sol` with `EXTRA_HIGH` reasoning. The automation API does not expose a verifiable model/reasoning selector. Tasks therefore report binding honestly as VERIFIED/PARTIAL_UNVERIFIED/UNVERIFIED/MISMATCH. Model-sensitive fresh promotion evidence is inadmissible without a runtime binding receipt.

## Session organization
Existing Scheduled Task IDs are persistent lanes. Each keeps one standardized `PS-*` title and every run begins with the `SESSION_STANDARD.md` header: target program, phase, iteration, iteration number, role, goal, runtime identity, requested model/reasoning, binding status, and execution mode.

## Deep research
Only BIL00 may run deep research, exactly at 00:58 and 12:58 America/Vancouver. Inputs are only MM06-safe/MF06-integrated questions plus unresolved accepted prior research. No other task may perform the broad prior sweep.
