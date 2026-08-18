# Project Supernova Branch GitOps Overlay v2.4.2

Overlay ID: `78eaafc34bcf56a6c0898d2085ba1462f687c95d9cf0d5d6a46a357d8c2d6f96`  
Base scientific plan: `61fbe7206e43ec538f310acf875e72865daf8fbb0e4ccbe27dcd6d1a072ff8a0`  
Mastermind audit envelope: `04fb7609f0384be488fd49278c23ec8b4cf5829b85300dbe1e5e5500d1badfe2`  
Mastermind native plan: `e3ea181008b109073f09b3cb8801165e138ae813a9d117766bb2ce24c422469d`  
Math Foundry 3.0.1 collaboration validation: `PASS`.

## Purpose
This overlay changes transport/orchestration only. It does not change Math Foundry mathematical authority, Mastermind PRE_REVIEW_ONLY status, benchmark semantics, holdout rules, or runtime state. It eliminates mixed-control revisions, shared-branch write races, and unauthenticated report-field mutation.

## Branch topology
For each cohort `<C>`:
- frozen generation: `ps/gen/<C>`
- worker branches: `ps/work/<C>/<WORKER>`
- verifier: `ps/verify/<C>`
- integrator: `ps/integrate/<C>`
- consolidation: `ps/consolidate/<C>`

`main` is canonical trunk/archive. In-flight workers never use mutable `main` as their control source.

## Two-layer validation
`validate_bus.py` is the frozen v2.3 trunk validator and keeps the 21-file base contract. `validate_branch_bus.py` is the branch-overlay validator. A branch-generation control manifest must equal exactly the 21 base files plus the six overlay files declared in `branch/CONFIG.json`: `BRANCH_PROTOCOL.md`, `branch/CONFIG.json`, `schemas/branch_generation.schema.json`, `schemas/branch_consolidation.schema.json`, `scripts/validate_branch_bus.py`, `.github/workflows/validate-branch-bus.yml`.

The trunk validator is not proof that the overlay is complete. MM06 and the branch validator independently check the 21+6 union, frozen blob identities, strict assignment/session equality, branch lineage and public safety.

## Generation freeze
1. BIL00 captures one control-release SHA.
2. It creates `ps/gen/<C>` from that exact SHA.
3. It creates and validates control+assignment on the generation branch.
4. It records final generation SHA `G` in branch state.
5. After `G` is frozen, `ps/gen/<C>` must never move. Movement invalidates the cohort.
6. Main/control-release may later change; those changes affect only future generations.

## Worker isolation
Each worker branch is created from exact `G`. A worker writes only `reports/<C>/<WORKER>.json` on its own branch. Workers never write generation, another worker, verifier, integrator, consolidation, or main. Originating-worker reread is non-authoritative; MM06 independently fetches the report.

## Canonical report authentication
Branch workers use `worker_auth_scheme = PS-HMAC-SHA256-CANONICAL-REPORT-2`.

1. Assemble the complete final report object with every field fixed except `worker_auth_proof`.
2. Remove the `worker_auth_proof` key entirely.
3. Serialize the remaining object as UTF-8 canonical JSON using sorted keys, separators `(',', ':')`, and `ensure_ascii=false`.
4. Compute `HMAC-SHA256(worker_secret_bytes, canonical_json_bytes)` and store lowercase hex in `worker_auth_proof`.
5. `worker_auth_commitment` remains `SHA256(worker_secret_bytes)`.
6. MM06 independently removes the proof key, canonicalizes the fetched report using the same rules, and recomputes the HMAC.

This proof binds the entire report payload: session phase/goal/target, evidence, costs, tests, provenance, model-binding status, and all other fields. Copying an old proof onto mutated report content fails.

## Strict session equality
For every worker report, both the branch validator and MM06 require:
- `session_name` = frozen standardized lane name;
- `target_program` = assignment worker target program;
- `phase` = full exact `assignment.phase` string;
- `iteration_id` = assignment cohort;
- `iteration_number` = assignment generation sequence;
- `role_id` = worker ID;
- `goal` = exact assignment worker goal;
- `plan_id` = task-network plan;
- `runtime_state_id` = assignment runtime;
- `model_target` = `GPT-5.6 Sol`;
- `reasoning_effort_target` = `EXTRA_HIGH`;
- calibration `execution_mode` = `SAFE_REPLAY_ONLY`.

A schema-valid wrong-phase/wrong-goal/wrong-target mutation must still fail the branch validator and MM06.

## Verification
MM06 reads controls at exact `G`, independently fetches each worker report from the assigned worker branch, records branch head + report blob, validates Draft-2020-12 schema, strict session equality, canonical-report HMAC, public safety, source/evaluator bindings, zero/negative outcomes, costs and branch ancestry. It runs negative probes for missing/extra schema fields and for schema-valid critical-field mutations (phase/goal/target), which must be rejected by equality/HMAC checks. MM06 writes only to `ps/verify/<C>`.

## Integration
MF06 fetches MM06 verification and only MM06-safe worker branch refs, independently rereads them, and writes only to `ps/integrate/<C>`. It cannot promote runtime truth.

## Consolidation and CAS merge
BIL00 never merges 12 worker branches. It captures current main head `M`, creates `ps/consolidate/<C>` from `M`, copies only MM06-safe artifacts into canonical `history/<C>/...` paths, adds verification/integration/director/consolidation receipts and proposed state/benchmark transition, opens ONE PR, reviews the exact head, and merges only with GitHub `expected_head_sha` plus state-lineage guards. A stale main/state lineage fails closed; force merge is forbidden.

The single consolidation PR is the only path by which a cohort becomes canonical history. Task consensus never changes Foundry/Mastermind runtime truth.

## Retry/orphan rule
All worker/verifier/integrator/consolidation paths are create-once. Retries adopt only exact same-cohort/same-generation artifacts. Stale branches are historical/orphaned and never silently reused.

## Calibration gate
Fresh/protected evidence remains disabled until two consecutive complete replay-only cohorts prove immutable generation, 12 same-base isolated worker branches, canonical-report HMAC authentication, strict session equality, MM06 independent reread/schema/public-safety checks, MF06 safe-ref integration, and one CAS-protected consolidation PR/merge. Main drift during an in-flight generation must not invalidate that generation.

## Benchmark succession
Mastermind and Math Foundry cursors advance independently. A suite is complete only when every frozen unit/arm/repeat is terminal and evaluator/checker/cost/contamination/adjudication receipts are closed. Terminal does not mean success. Only a verified completion receipt advances a cursor. If no eligible successor exists, that program enters `BENCHMARK_DISCOVERY_WAIT`; BIL00's single 12-hour research pass may propose a successor, but adoption requires source/version/license/access/evaluator/contamination preflight plus a private `FROZEN_PRE_OUTCOME` manifest.

## Model binding
All prompts request `GPT-5.6 Sol` with `EXTRA_HIGH` reasoning. The automation API does not expose a verifiable model/reasoning selector. Tasks therefore report binding honestly as VERIFIED/PARTIAL_UNVERIFIED/UNVERIFIED/MISMATCH. Model-sensitive fresh promotion evidence is inadmissible without a runtime binding receipt.

## Session organization
Existing Scheduled Task IDs are persistent lanes. Each keeps one standardized `PS-*` title and every run begins with the `SESSION_STANDARD.md` header containing target program, phase, iteration, iteration number, role, goal, runtime identity, requested model/reasoning, binding status and execution mode.

## Deep research
Only BIL00 may run deep research, exactly at 00:58 and 12:58 America/Vancouver. Inputs are only MM06-safe/MF06-integrated questions plus unresolved accepted prior research. No other task may perform the broad prior sweep.
