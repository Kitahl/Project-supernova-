# Project Supernova Branch GitOps Protocol v2.5

Plan: `0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`.

## Freeze rule
Protocol 2.5 is the calibration protocol. No 2.6 generation is admissible until `main` protection/source policy is independently verified and two consecutive countable v2.5 replay-only cohorts have completed end-to-end. Pre-cohort defects are repaired inside v2.5 and frozen before the first countable cohort; changing the frozen control after cohort 1 begins invalidates the streak.

## Canonical-state rule
`main:state/CURRENT.json` is the **only mutable canonical network pointer**. There is no second branch-state file. In-flight artifacts live on isolated branches referenced by that pointer; only a verified consolidation PR may copy admitted evidence into canonical history and publish the next pointer.

## Topology
For active cohort `<C>`:
- immutable generation: `ps/gen/<C>` at exact frozen head `G`;
- worker branches: `ps/work/<C>/<WORKER>`, each created from exactly `G`;
- verifier: `ps/verify/<C>`, created from `G`;
- integrator: `ps/integrate/<C>`, created from `G`;
- consolidation: `ps/consolidate/<C>`, created only after verified integration and from the then-current exact `main` head;
- optional research: `ps/research/<research_id>`.

Permanent per-worker forks are not used unless a genuinely separate security principal is required. Branch isolation is sufficient for ordinary write separation without creating a competing repository truth.

## Git-native freeze
A generation control manifest freezes a `control_release_commit_sha`, its exact Git tree SHA, and a closed list of required control paths. Git object identity therefore commits to exact file bytes; workers and validators compare every required path against that frozen commit/tree. The generation branch may add only its immutable control and assignment before final head `G` is recorded.

Every **countable** v2.5 control release must include `config/protocol_freeze.json`, `benchmark/pool_disposition.json`, the v2.5 three-context admission workflow, verifier/integrator schemas, branch reconcilers and their negative tests in the required-control set. GitHub Actions in the countable path are pinned by full commit SHA; validation dependencies are hash-locked or equivalently frozen.

## Worker isolation
Each worker branch starts at `G` and may change exactly one path: `reports/<C>/<WORKER>.json`. It may never move generation, verifier, integrator, consolidation, main, benchmark or another worker branch. A branch with additional path changes is rejected. MM06 proves the report path has exactly one path-changing commit; multiple edits to the report path are quarantine, even when final diff bytes look valid.

## Whole-report authentication
Branch cohorts use only `PS-HMAC-SHA256-CANONICAL-REPORT-2`. Remove `worker_auth_proof`, serialize the entire remaining report as UTF-8 JSON with sorted keys, separators `(',', ':')`, `ensure_ascii=false`, then HMAC-SHA256 with the prompt-private worker secret. This binds session fields, evidence, costs, tests and all report content, not merely identity metadata.

## Independent reread and closed verification
MM06 fetches every assigned worker branch and proves:
- branch exists and descends exactly from `G`;
- diff from `G` changes only the assigned report path;
- exact report blob and branch head are recorded;
- exactly one report-path-changing commit exists and its non-null 40-hex commit identity is recorded;
- current report blob equals the report blob at that path-changing commit;
- report path history is immutable after creation;
- schema and strict session equality pass;
- public safety and zero-protected calibration cost pass;
- SHA-256 secret commitment and canonical whole-report HMAC pass;
- structural worker status is successful on that exact worker head.

Safe/quarantined/missing worker partitions are unique, disjoint and exhaustive. Quarantine entries use the closed frozen schema. Worker self-reread has no authority.

## Three non-substitutable admission contexts
The v2.5 evidence path distinguishes:
1. `supernova/static-control` — immutable generation/control/assignment/schemas/action/dependency identities and frozen structural invariants.
2. `supernova/report-admission` — post-write structural admission of the exact MM06 verifier head and the safe/quarantine/missing envelope. It is observed only **after** the MM06 receipt exists.
3. `supernova/transition-admission` — exact BIL00 consolidation head, stale-parent/CAS and allowed mutable transition diff.

Branch-local diagnostic contexts such as `supernova/branch-worker`, `supernova/branch-verify`, or `supernova/branch-integrate` may exist, but never substitute for the three admission contexts. Missing/pending/failing/unobservable/wrong-commit/wrong-source is not PASS.

## Temporal CI rule
MM06 cannot truthfully put a future post-write CI PASS into the receipt that CI is about to evaluate. The verifier receipt records PRE_CI/CI_NOT_OBSERVED only. The external reconciler/workflow later posts `supernova/report-admission` to the exact verifier head. MF06 binds that exact verifier head and requires the later external PASS. The same temporal rule applies to BIL00: transition admission is observed on the exact consolidation head after it exists.

## Integration
MF06 reads only MM06-safe refs, independently rereads them, requires successful `supernova/report-admission` on the exact verifier head, preserves quarantines/negative/zero/unknown/cost/model-binding evidence, and writes only the integrator branch. The integration receipt records the exact verifier head, required context and observed PASS; it never treats the verifier's own pre-CI field as external evidence.

## Consolidation
BIL00 creates one consolidation branch from the exact current `main` head, copies only verified safe artifacts to `history/<C>/...`, adds verification/integration/director/consolidation receipts and any next state/benchmark transition, and opens one PR. The PR must be stale-parent/CAS clean and later receive `supernova/transition-admission=success` on its exact head. The v2.5 PR workflow also republishes/revalidates the three source-bound admission contexts on that PR head for branch-protection consumption. `expected_head_sha` is required at merge. Force merge/rebase is forbidden.

## Scheduled CI reconciliation
A frozen scheduled reconciler validates the active branch topology and publishes exact-head branch diagnostics. The countable v2.5 control also freezes a PR admission workflow that emits `supernova/static-control`, `supernova/report-admission`, and `supernova/transition-admission` using SHA-pinned actions/environment. CI is mechanical rejection authority only; MM06 still owns HMAC/evidence verification and mathematical correctness remains with Foundry/checkers.

## Repository protection gate
No calibration cohort counts and no fresh work is eligible until GitHub itself reports the default branch protected **and** the required pull-request/status/source policy is independently observed. A policy JSON file or task assertion is not proof of protection. Protection must require a PR, forbid force-push/deletion, and require the three admission contexts from the configured GitHub-App/Actions source.

## Calibration and fresh work
Two consecutive complete, non-superseded, replay-only v2.5 branch cohorts are required after repository protection is independently observed. Each closes generation -> 12 isolated worker branches -> MM06 -> exact-head report admission -> MF06 -> integrator structural admission -> one CAS-protected consolidation PR -> exact-head transition admission -> merge. Any failure resets the streak. Fresh transport additionally requires a private `FROZEN_PRE_OUTCOME` manifest per scientific assignment.

## Model binding
Replay-only calibration may use `PARTIAL_UNVERIFIED` or `UNVERIFIED` model binding. Model-sensitive fresh evidence may not be promoted unless the frozen private manifest and runtime receipt establish the required model/reasoning/tools/environment binding. Requested model text is not proof, and G1/G8/Goal-2 comparisons fail closed on unmatched observed execution bindings.

## Benchmark succession and Stage -1 pools
Mastermind and Math Foundry cursors advance independently only from verified completion receipts; terminal does not mean success. Each existing suite has a frozen Stage -1 pool disposition in `benchmark/pool_disposition.json`; development/calibration evidence is never recycled into G1/G8/Goal-2 promotion evidence. No eligible successor enters `BENCHMARK_DISCOVERY_WAIT`.

## Research gate
BIL00 owns research slots at 00:58 and 12:58 America/Vancouver, but a slot performs deep research only against an accepted open lane. While T0 is unqualified, only T0 transport/repository/admission closure is admissible; downstream E1/Stage-0/reaction/selector/Goal-2 questions remain queued. Research inputs still require MM06-safe/MF06-integrated evidence or unresolved accepted research.

## Dual goals
Goal 1 is the finite fresh verified reaction/cascade advantage at equal complete cost. Goal 2 opens only after Goal 1 and requires same-start, matched-budget, controlled-memory `I_t` vs `I_(t+1)` evidence with solver `F`, memory `M`, and improver `I` separated.
