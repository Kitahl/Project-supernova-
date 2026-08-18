# Project Supernova Branch GitOps Overlay v2.4.3

Overlay ID: `78eaafc34bcf56a6c0898d2085ba1462f687c95d9cf0d5d6a46a357d8c2d6f96`  
Base scientific plan: `61fbe7206e43ec538f310acf875e72865daf8fbb0e4ccbe27dcd6d1a072ff8a0`  
Mastermind audit envelope: `04fb7609f0384be488fd49278c23ec8b4cf5829b85300dbe1e5e5500d1badfe2`  
Mastermind native plan: `e3ea181008b109073f09b3cb8801165e138ae813a9d117766bb2ce24c422469d`  
Math Foundry 3.0.1 collaboration validation: `PASS`.

## Purpose and precedence
This overlay changes transport/orchestration only. It does not change Math Foundry mathematical authority, Mastermind PRE_REVIEW_ONLY status, benchmark semantics, holdout rules or runtime state.

For branch cohorts, `BRANCH_WORKER_PROTOCOL.md` is the single authoritative worker protocol for **state source, branch destination, worker authentication, independent reread and branch-validation mechanics**. Where those mechanics conflict with trunk `PROTOCOL.md` or `WORKER_PROTOCOL.md`, the branch-worker protocol wins. Trunk files remain authoritative for scientific role/evidence/benchmark/runtime-authority rules unless the branch layer only strengthens them. Therefore the old trunk identity-HMAC rule is not an alternate option on a branch cohort.

## Branch topology
For each cohort `<C>`: frozen generation `ps/gen/<C>`; workers `ps/work/<C>/<WORKER>`; verifier `ps/verify/<C>`; integrator `ps/integrate/<C>`; consolidation `ps/consolidate/<C>`. `main` is canonical trunk/archive, never in-flight control.

## Validation layers
`validate_bus.py` keeps the frozen 21-file v2.3 trunk contract. `validate_branch_bus.py` validates the branch extension. A branch-generation control manifest must equal exactly the 21 base files plus the **seven** branch overlay files declared in `branch/CONFIG.json`: `BRANCH_PROTOCOL.md`, `BRANCH_WORKER_PROTOCOL.md`, `branch/CONFIG.json`, `schemas/branch_generation.schema.json`, `schemas/branch_consolidation.schema.json`, `scripts/validate_branch_bus.py`, `.github/workflows/validate-branch-bus.yml`.

The branch validator/MM06 independently check the exact 21+7 union, all frozen blob identities, strict assignment/session equality, branch ancestry, closed schemas, public safety and report authentication.

## Generation freeze
BIL00 creates one generation from an exact control-release SHA, writes and validates control+assignment, records final generation head `G`, then never moves that branch. Main/control-release changes after `G` do not affect that cohort.

## Worker isolation and authentication
Every worker branch starts from exact `G`; a worker writes only its one report on its own branch. Branch workers use only `PS-HMAC-SHA256-CANONICAL-REPORT-2`: remove `worker_auth_proof`, canonicalize the complete remaining report as sorted-key compact UTF-8 JSON with `ensure_ascii=false`, then HMAC-SHA256 with the prompt-private secret. MM06 independently reconstructs and verifies the HMAC. Any change to phase, goal, evidence, costs, tests, model-binding status or any field invalidates the proof.

## Strict session equality
MM06/branch validation require exact standardized session name, assignment target program, full assignment phase, cohort, generation number, worker role, exact assignment goal, plan/runtime, `GPT-5.6 Sol`, `EXTRA_HIGH`, and calibration `SAFE_REPLAY_ONLY`. Wrong phase/goal/target mutations must fail even when schema-valid.

## Verification and integration
MM06 independently fetches each assigned worker branch, records branch head/report blob, validates schema/session/HMAC/public safety/ancestry/costs and negative mutations, and writes only `ps/verify/<C>`. MF06 consumes only MM06-safe branch refs, rereads them and writes only `ps/integrate/<C>`.

## Consolidation and CAS merge
BIL00 never merges 12 worker branches. It creates one consolidation branch from current main, copies only MM06-safe artifacts into canonical `history/<C>/...`, adds verifier/integrator/director/consolidation receipts and proposed state/benchmark transition, opens ONE PR, reviews exact head, and merges only with `expected_head_sha` plus state-lineage guards. Stale lineage fails closed; force merge is forbidden. This single PR is the only path to canonical history.

## Retry/orphans and calibration
All outputs are create-once. Retries adopt only exact same-cohort/same-generation artifacts. Stale branches are never silently reused. Fresh/protected work remains disabled until two consecutive complete replay-only cohorts prove immutable generation, 12 isolated authenticated workers, MM06 independent verification, MF06 integration and one CAS-protected consolidation PR/merge. Main drift during the generation must not invalidate it.

## Benchmark succession
Mastermind and Math Foundry cursors advance independently. Completion requires all frozen task/arm/repeat units terminal plus evaluator/checker/cost/contamination/adjudication closure; terminal does not mean success. Verified completion + eligible successor => preflight/private freeze and advance that program only. No successor => `BENCHMARK_DISCOVERY_WAIT` pending BIL00's 12-hour research proposal and later preflight/freeze.

## Model binding, sessions and research
All task prompts target GPT-5.6 Sol / EXTRA_HIGH, but the automation API cannot verify or enforce this; tasks report binding honestly and model-sensitive fresh promotion is inadmissible without a binding receipt. Existing task IDs remain persistent standardized `PS-*` sessions. Only BIL00 performs deep research, exactly 00:58 and 12:58 America/Vancouver, using only MM06-safe/MF06-integrated questions plus unresolved accepted research.
