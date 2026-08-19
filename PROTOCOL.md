# Project Supernova Scheduled Experiment Bus Protocol v2.5

## Authority
This GitHub network is external experiment/referee/research infrastructure. Math Foundry owns mathematical/runtime truth. Mastermind is PRE_REVIEW_ONLY. GitHub/CI/tasks/research/scores never establish mathematical truth by themselves.

Current written design authority: `docs/PROJECT_SUPERNOVA_SPEC_REV4.md` (Specification Revision 4). Where older design guides or implementation documents conflict with Revision 4, Revision 4 controls. Frozen per-experiment manifests still control their exact run.

## Canonical plan
`TASK_NETWORK_PLAN_ID=0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`.

## Design / protocol freeze
Protocol **2.5** and Specification **Revision 4** are frozen for calibration. No protocol 2.6 and no Revision 5 may become canonical until repository protection/source policy is independently qualified and two consecutive countable replay-only v2.5 Branch-GitOps cohorts close end-to-end. Defects discovered before cohort 1 are repaired inside v2.5 and frozen before cohort 1 begins. Any authoritative control change after cohort 1 begins resets the streak by default.

## Canonical definition and dual goals
Supernova is a frozen-authority controller that treats independently verified mathematical products as resources enabling further executable operations, gates continuation by certified value-of-computation, and admits improvements only through prospective matched-complete-cost tests.

Goal 1: a finite, fresh, independently verified within-problem cascade beats strong controls at equal complete cost.

Goal 2: only after Goal 1, demonstrate improvement of the improver. Separate solver `F_t`, retained memory/products `M_t`, and improver `I_t`; compare later vs parent improver from identical untouched start under matched complete R&D budget, controlled `M`, identical allowed model/tools/environment/referee and fresh independent evaluation. Better descendants or more memory alone do not count.

“Ignition” means **certified value-gated continuation**, not `R>1`, spectral criticality, a Perron-Frobenius threshold, or a branching-process kill gate.

## Trusted Core vs Frontier

### Trusted Supernova Core
Execution-control order:
1. exact OperatorContract engine `E_Λ`;
2. sound certified viability/deadness and cost lower bounds;
3. verified-product enablement/direct-value priors;
4. lawful class-aware real multi-fidelity probes with successive-halving allocation;
5. SN-COMPARE sibling-fork preferences with `C_path` and `C_policy` kept separate;
6. calibrated behavioural non-interference inside the indifference region;
7. real Foundry execution -> independent verification -> StatementFidelityCertificate -> product admission.

Only stages 1–2 may hard-prune unconditionally. Models never mutate Foundry state. A predicted lemma is hypothetical and cannot enter the product set without real execution, independent PASS and statement-fidelity admission.

### Supernova Frontier
The Frontier has **no execution authority**. Its target is SN-HORIZON: typed lower/upper intervals on finite-horizon action value with a positive choice only when a lower bound for one action exceeds all competing upper bounds under the declared risk/drift rule.

Evidence order is: `sound bounds -> real probes -> SN-COMPARE -> one-step value/outcome heads -> direct horizon/plan prediction -> short residual SN-WORLD rollouts`.

SN-WORLD is Frontier-only. Use ORACLE-WORLD before building a world model. Core admission requires SNW-0 data feasibility, SNW-1 predictive validity/calibration, SNW-2 incremental decision value beyond simpler controls, SNW-3 complete-cost value, SNW-4 prospective transfer, and SNW-5 genuine multi-step value not reproducible by comparator/one-step/direct-horizon mechanisms.

## Global design invariants
- **FINITE-HORIZON:** target quantities are finite-horizon `H`, budget `b`, conditional on frozen `Λ`; otherwise diagnostic only.
- **ONE-SIDED STATIC SCREENS:** positive relaxed reachability is `NO_INFORMATION`; only sound terminal-relevant unreachability may hard-prune.
- **COST-RELATIVE KILLS:** use residual-value UCB versus unavoidable-cost LCB + deployment margin, not percentage-of-headroom thresholds.
- **THREE LEARNED-COMPONENT REPORTS:** predictive accuracy, calibration/risk coverage, usable intervention coverage. Near-total abstention is not successful calibration.
- **CONTINUOUS EFFECT SIZES:** estimate, CI, MDE, `n`, achieved power, complete cost, family heterogeneity, zero/unknown counts.
- **SYMMETRIC FIDELITY:** statement-fidelity and probe cost rules are symmetric across applicable arms.
- **SEPARATE OBLIGATION LAYER:** kernel validity and statement fidelity are orthogonal statuses.
- **TRIANGLE INEQUALITY DEFAULT:** do not assume learned-error cancellation; T4 remains an open target.

## Transport
`state/CURRENT.json` on `main` is the sole mutable canonical pointer. When `transport_mode=BRANCH_GITOPS`, `BRANCH_PROTOCOL.md` and `BRANCH_WORKER_PROTOCOL.md` govern in-flight transport. One immutable generation branch fans out to isolated worker branches, then verifier and integrator branches, then one consolidation PR. Main is never an in-flight worker workspace.

## Frozen generation
Control binds the exact control-release commit/tree plus a closed required-control path set. Generation control+assignment are create-once. Final generation head is immutable. Main/control-release drift after generation freeze does not invalidate an in-flight cohort. The current non-countable pre-Revision-4 bootstrap remains immutable diagnostic history; Revision 4 is frozen into the next countable v2.5 control release.

## Authentication
Branch cohorts use only `PS-HMAC-SHA256-CANONICAL-REPORT-2`, binding the complete report payload. MM06 independently reconstructs the proof using verifier-side secret copies. Raw secrets never enter GitHub.

## Persistent sessions
The 15 scheduled lanes reuse the same task/chat. Stable names and mandatory first-response header are in `SESSION_STANDARD.md`; dynamic phase/cohort/iteration/goal belongs in the header and receipt.

## Model / execution binding — fifth TCB gate
All lanes request GPT-5.6 Sol / EXTRA_HIGH, but the task surface cannot itself prove either binding. Every receipt reports `VERIFIED|PARTIAL_UNVERIFIED|UNVERIFIED|MISMATCH` from observed runtime evidence. Replay-only transport may proceed with partial/unverified model binding. **Model-sensitive fresh evidence is non-promotable unless a frozen execution manifest and runtime receipt prove the predeclared model, reasoning/runtime constraints, tools and environment.** G1/G8/Goal-2 arms use identical observed model/tools/environment unless that dimension is the preregistered treatment. A request string is not a binding receipt.

## Public/private split
Public-safe orchestration/evidence lives in `Kitahl/Project-supernova-`. Protected `FROZEN_PRE_OUTCOME` manifests/payloads live only in `Kitahl/thoma/vault/`. Public refs are opaque only.

## Repository policy and three-context CI
No calibration cohort counts and no fresh work is eligible until GitHub itself reports `main` protected and the required status-check/source policy is independently observed. A repository policy JSON file cannot self-attest protection.

Three status contexts are non-substitutable:
- `supernova/static-control` — frozen protocol/control/assignment/schema/dependency/action identities and generation invariants;
- `supernova/report-admission` — MM06 verifier receipt and its Git/report partition/binding envelope after the receipt exists;
- `supernova/transition-admission` — BIL00 consolidation/next-state CAS, allowed diff and stale-parent transition semantics.

Missing, pending, failing, unobservable, wrong-source or wrong-commit is not PASS. A status for one context never satisfies another context. CI is rejection authority only; it cannot establish mathematical truth.

## Verification closure and temporal CI
A safe worker reference binds worker, assigned branch/path, report blob, non-null 40-hex creation/path-changing commit identity, exactly one report-path-changing commit, generation ancestry, immutable history, schema, exact session, HMAC, public safety and assignment/control/runtime identities. Safe/quarantined/missing worker partitions are unique, disjoint and exhaustive. Quarantine objects are closed and typed.

MM06 cannot self-attest CI that runs after its verifier receipt exists. The verifier receipt records a pre-CI state only. MF06 later observes `supernova/report-admission=success` on the **exact verifier head** before integration can be countable. BIL00 analogously requires later exact-head transition admission for consolidation.

## Supply-chain freeze
Every countable v2.5 control release freezes GitHub Actions by full commit SHA and freezes the complete validation environment with hashes or an equivalent immutable environment receipt. Mutable `@vN` action references are inadmissible in the countable evidence path.

## Calibration
After repository protection and required source-bound contexts are independently observed, require two consecutive complete replay-only v2.5 branch cohorts: immutable generation -> 12 isolated whole-report-HMAC worker branches -> MM06 independent verification -> exact-head report admission -> MF06 integration -> integration structural admission -> one CAS-protected consolidation PR -> exact-head transition admission -> merge. Failure resets the streak. The current non-countable bootstrap diagnoses transport but cannot increment the streak.

## Fresh/protected work
`FRESH_ENABLED` is transport eligibility only. Fresh work also requires exact assignment ownership and a private frozen pre-outcome manifest binding plan/cohort/checkpoint/runtime, task/evaluator/checker, observed model/tools/environment, complete budget, randomization/repeats, cache/context/retention, accounting, contamination exclusions and disjoint ownership.

## Benchmark pools and succession
Mastermind and Math Foundry suites each have an explicit Stage -1 evidence disposition: `TRAIN_TUNING`, `CALIBRATION`, `G1_PROSPECTIVE`, `G8_CASCADE`, `GOAL2_E5B`, or `RESEARCH_FROZEN`. A development/calibration suite can never later become G1/G8/Goal-2 promotion evidence. Canonical dispositions are in `benchmark/pool_disposition.json` and are frozen before fresh-task sealing.

Program cursors advance independently. Suite completion requires every frozen unit terminal, evaluator/checker receipts present, complete costs closed and contamination/adjudication resolved. Terminal is not success. Verified completion + eligible successor -> preflight/private freeze and advance that program only. No eligible successor -> `BENCHMARK_DISCOVERY_WAIT` with no fresh consumption.

## Immediate non-admissible work allowed in parallel
While T0 closes, and only when a frozen assignment/data boundary permits it, the project may use existing development/consumed evidence for:
- Stage -1 pool governance and relation-coverage sizing;
- OCN-0A five-operator contract-costing pilot;
- CID-0 fingerprint/contract-identifiability audit;
- RETRO-0 waste bracket;
- Cascade Soundness parts (1)–(2).

These do not become prospective promotion evidence and must not consume G1/G8/Goal-2 pools.

## Scientific stage sequence
Stage -1 governance -> 0A OCN/CID -> 0B inherited relaxed reachability -> 0C cost-bounded reachability -> 0D RETRO/MF-0R -> 0E synthetic qualification -> 0F MF-0X + COMPARE-0 + ORACLE-WORLD -> 0G targeted causal census -> **T0/E1 first admissible programme evidence** -> G1 -> C1 -> E3 -> selector/VoC -> G8 finite Goal-1 cascade -> E5B Goal 2 -> E6.

Stages -1 through 0G are diagnostic/non-admissible and may proceed only within their frozen data/pool boundaries. T0 transport qualification is still a hard gate on admissible prospective programme evidence.

## Enablement semantics
Use generation-specific positive and inhibitory causal enablement objects separately. Primary finite objects are deduplicated unique causally enabled opportunities and matched-budget value. Pairwise branching projection `rho(K+)` is diagnostic only after adequacy tests and is never a kill gate. Nilpotent useful chains are allowed. Keep transport placebo vs coarse-type semantic placebo and path-conditioned knockout vs free-replanning estimands separate.

## Control ladder
`B0` current Foundry; `B1` exact structural controller; `B2` B1 + real successive-halving multi-fidelity probes; `B3` B2 + SN-COMPARE; `B4` B3 + one-step predictive heads; `B5` B4 + multi-step SN-WORLD. Report incremental deltas and compare B5 to the strongest simpler mechanism. Preserve product controls `C0/C2/C2_STATIC_PRODUCTS` and `VBS_schedule` headroom.

## Roles
Workers execute frozen roles only. MM06 verifies branch ancestry/path/blob/schema/session/HMAC/safety/cost/ownership. MF06 integrates only MM06-safe refs and reconciles by evidence tier. BIL00 alone owns consolidation PRs, network-state/benchmark cursor transitions and scheduled deep research. Runtime changes require an independently validated `RUNTIME_UPDATE_RECEIPT`.

## Typed pathway corpus
Revision 4 permits `typed_events[]` **inside an existing worker report**, never a new competing authority path. The field is public-safe evidence/provenance only and does not itself create products, causal claims or runtime truth. Its schema is frozen before countable use.

## Deep-research gate
BIL00 is the only scheduled deep-research executor and research slots remain 00:58 and 12:58 America/Vancouver, but a slot executes deep research **only when an accepted open research lane exists**. While T0 is unqualified, the only admissible research lane is T0 transport/repository/admission closure. SN-HORIZON, SN-WORLD, E1, reaction, selector and Goal-2 literature expansion stay queued. Inputs are MM06-safe + MF06-integrated questions and unresolved accepted research only. No raw worker bypass or sealed-holdout access. Research cannot promote runtime/science by itself.

## Fail closed
Any missing, stale, mismatched, superseded, unknown, partial, timed-out, unexplained or contradictory admission evidence is not PASS. Correctness and clean evidence dominate score.
