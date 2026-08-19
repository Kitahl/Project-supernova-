# Project Supernova — Construction & Operations Specification, Revision 4

**Status:** DESIGN FROZEN  
**Date:** 2026-08-19  
**Transport protocol:** 2.5  
**Canonical plan:** `0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`

This document is the repository transcription of **Project Supernova Construction & Operations Specification — Revision 4 (Consolidated Update)**. It supersedes the Design Guide V3 and the prior protocol-2.5 Construction & Operations Specification where they conflict. It does not rewrite historical evidence, alter an in-flight frozen generation, or create calibration credit.

## Design freeze

No protocol 2.6 and no Revision 5 until the calibration streak reaches **2**. Defects found before the first countable cohort are repaired as protocol-2.5 hardening and frozen before that cohort starts. Once countable cohort 1 starts, changing authoritative control invalidates the streak.

## Canonical definition

Supernova is a frozen-authority controller that treats independently verified mathematical products as resources enabling further executable operations, gates continuation by certified value-of-computation, and admits improvements only through prospective matched-complete-cost tests. Every finite cascade must remain sound; amplification is measured rather than assumed; improvement of the improver is an empirical result rather than a guaranteed acceleration.

The retained chain is:

`controlled reactions -> measured yield -> value-gated continuation -> verified feedback -> prospective self-improvement`

“Ignition” means a **certified value-gated continuation rule**, not a criticality condition such as `R > 1`.

### Goal 1

A finite, fresh, independently verified within-problem cascade beats strong controls at equal complete cost.

### Goal 2

Only after Goal 1 passes, test whether the improver improves. Separate solver `F`, retained memory/products `M`, and improver `I`. Compare `I_t` and `I_(t+1)` from the same untouched `F*`, matched complete R&D budget, controlled memory, identical allowed model/tools/sandbox/referee, and fresh independent evaluation. A better solver descendant or more retained memory alone is insufficient.

# 1. Trusted Core and Frontier

## 1.1 Trusted Supernova Core — execution control

The ordered decision pipeline is:

1. **Exact OperatorContract engine `E_Λ`** — legality, `ΔA`, obligation creation/discharge, type compatibility, ProductUseCertificates and version semantics. Never learned.
2. **Certified viability/deadness** — sound dead-end certificates and cost lower bounds. Only sound certificates may hard-prune.
3. **Verified-product enablement prior** plus direct-value prior.
4. **Class-aware real multi-fidelity probes** with successive-halving allocation. Fidelity sets `F_k` are declared per operator class and are empty where no lawful reduced fidelity exists.
5. **SN-COMPARE** — pairwise sibling-fork preference `P(A ≻ B | S)`; path-conditioned and policy-level estimands remain separate.
6. **Calibrated behavioural non-interference** — inside the indifference region the learned layer changes nothing: executed action, probe set, ordering, budgets, retention, expansion, cache/context, product exposure and stopping all remain baseline-identical.
7. **Real Foundry execution -> independent verification -> StatementFidelityCertificate -> product admission**.

Only stages 1–2 may prune unconditionally.

## 1.2 Supernova Frontier — research only

The Frontier has **no execution authority**.

Target object: **SN-HORIZON**, a heterogeneous long-horizon metaplanner. For each first action `a`, maintain a typed interval

`L_H(S,a) <= Q*_H(S,a) <= U_H(S,a)`

and choose `A` only when

`L_H(S,A) > max_{B != A} U_H(S,B)`.

Named inherited skeletons: BRTDP / interval-based search, racing/successive elimination, and Selecting Computations / value-of-computation.

### Typed interval algebra

Each bound is either:

- `SOUND` — certificate, exact witness, or sound cost lower bound; or
- `CALIBRATED(alpha, source-set)`.

Rules:

- `SOUND ∩ SOUND` is unconditional.
- `SOUND ∩ CALIBRATED` inherits the calibrated risk.
- overlapping calibrated source sets are combined conservatively; they are never treated as independent by default.
- statistical bounds may widen under drift.
- stopping requires ordering to persist across the declared update/drift rule.
- elimination may only lower `U`; a positive choice requires evidence that raises `L`.

Evidence enters in this order after calibration on the sealed pool:

`sound bounds -> real probes -> SN-COMPARE -> one-step value/outcome heads -> direct horizon/plan prediction -> short residual rollouts (SN-WORLD)`.

Metalevel spend per decision is hard-capped and one-step-lookahead only. A myopic-VOC versus cheapest-probe control is mandatory.

## 1.3 Authority invariants

- Foundry is the sole execution authority.
- Models return predictions with distribution, interval, support score, calibration version, training boundary, model version and predicted inference cost; they never mutate state.
- A predicted lemma is hypothetical, never a product.
- Nothing enters the verified product set without real execution, independent PASS and statement-fidelity admission.
- Frontier-to-Core promotion occurs only through prospective gates `SNW-0..5`.
- If a deterministic transformation exists, execute it rather than rewarding a learned approximation.

# 2. Theorem obligations

## 2.1 Cascade Soundness

Write before the bus is qualified.

Under frozen `Λ`, machine-checkable operator contracts, independent product verification, StatementFidelityCertificate admission, and continuation gated by a lower confidence bound on advantage exceeding complete cost:

1. terminal admitted products remain valid by induction on cascade depth;
2. inside the calibrated indifference region the controller is behaviourally identical to baseline by construction;
3. the realized-value error envelope is a later obligation, with deterministic transitions exact and learned uncertainty confined to the residual layer.

Parts (1)–(2) are the immediate paper theorem target.

## 2.2 Theorem ledger

- **T1 comparator ordering — SPECIALISATION.** Sign-correct when the true gap exceeds calibrated pairwise error. Cycles are measured rather than assumed absent.
- **T2 abstention/non-interference — SPECIALISATION + wrapper.** Exact behavioural identity inside the indifference region; probabilistic coverage remains calibration-dependent.
- **T3 multi-fidelity transport — INHERITED FORM + EMPIRICAL PREMISE.** Safe elimination only under a measured low/full-fidelity transport relation. `MF-0X` determines whether Foundry satisfies it.
- **T4 advantage-form cancellation — OPEN beyond trivial algebra.** Exact prefix cancellation is algebraic; learned-error cancellation needs paired difference-error assumptions. Triangle inequality is the default.
- **T5 finite value-equivalent bound — SPECIALISATION.** Report occupancy-weighted local Bellman discrepancy / span of continuation value, not generic `H^2 U_max`.
- **M7 validation-preserving compression — PROJECT-SPECIFIC / OPEN.** Requires congruence of `E_Λ` for validation semantics, not value equivalence.

# 3. Design invariants

1. **FINITE-HORIZON RULE.** Every target quantity is stated at finite horizon `H`, budget `b`, conditional on `Λ`; otherwise it is diagnostic only.
2. **STATIC SCREENS ARE ONE-SIDED.** Positive relaxed reachability is `NO_INFORMATION`; only sound terminal-relevant unreachability is a result.
3. **COST-RELATIVE KILL RULES.** Defer/kill when an upper confidence bound on residual value beyond the strongest simpler mechanism is below a conservative lower bound on unavoidable mechanism cost plus deployment margin.
4. **THREE LEARNED-COMPONENT QUANTITIES.** Always report predictive accuracy, calibration/risk coverage, and usable intervention coverage. Calibration by near-total abstention fails.
5. **CONTINUOUS EFFECT SIZES.** Every gate records estimate, CI, MDE, `n`, achieved power, complete cost, family heterogeneity, and zero/unknown counts.
6. **SYMMETRIC FIDELITY REGIME.** Statement-fidelity and probe cost are charged identically across relevant arms.
7. **SEPARATE OBLIGATION LAYER.** `KERNEL_VALID` and `STATEMENT_FIDELITY_*` are orthogonal. `CERTIFIED_DEAD_AT_ORIGIN` is a fidelity/status flag, not a global verdict.

# 4. Updated blocker ledger

- **T0 CRITICAL** — complete source-bound main ruleset and demonstrate two clean replay cohorts end-to-end; MM06 must actually issue the verifier receipt.
- **SN-MIG-004/005/006/009 HIGH** — SHA-pinned Actions; closed verification schema; non-substitutable three-context CI; model-binding honesty.
- **FRESH-0 CRITICAL** — six-pool disposition, commit-reveal, procedural generator, relation-level coverage and achievable MDE.
- **OCN-0A CRITICAL** — typed executable OperatorContracts; five-operator costing pilot first.
- **OCN-0B MEDIUM** — inherited invariant/mutex synthesis.
- **CID-0 HIGH** — contract identifiability audit using `Δ_CID = H(A|X_C) - H(A|X_raw)` and fingerprint ablations.
- **RETRO-0 HIGH** — post-doom waste bracket from existing failures with problem-level bootstrap.
- **POWER-0 CRITICAL** — freeze MDE / independent unit / alpha / clustering / maximum budget before causal confirmation.
- **STATEMENT-0 CRITICAL** — StatementFidelityCertificate, non-vacuity, mutation, counterexample and independent formalization.
- **CAR-0 HIGH** — cost-bounded explicit/CP-SAT reachability with budget in state.
- **MF-0 HIGH** — class-aware fidelity census: retrospective `MF-0R` then randomized `MF-0X` with preferred/dispreferred strata.

# 5. Stage sequence and admissibility

## Immediate work

In parallel where allowed by frozen assignments and data boundaries:

- close T0 ruleset/source-bound admission and two replay cohorts;
- keep protocol fixed at 2.5;
- ensure SN-MIG-004/005/006/009 are frozen before countable cohort 1;
- disposition all benchmark suites into evidence pools and size the sealed reservoir;
- start the OCN-0A five-operator costing pilot and RETRO-0 waste bracket on existing development/consumed logs;
- write Cascade Soundness parts (1)–(2).

None of the parallel diagnostics may consume or reveal later prospective pools.

## Stage -1 — Governance

Seal `TRAIN_TUNING / CALIBRATION / G1_PROSPECTIVE / G8_CASCADE / GOAL2_E5B / RESEARCH_FROZEN`, commit-reveal and procedural generation; size FRESH-0 / POWER-0 before confirmatory use.

## Stage 0A — OCN / CID

Contract normalization, contract-identifiability audit, one-step residual monitoring. Non-admissible diagnostic.

## Stage 0B — inherited RPG

Compile qualified contracts to PDDL/SAS+ and use inherited relaxed reachability. `RELAXED_UNREACHABLE` may be evidence; positive reachability is `NO_INFORMATION`.

## Stage 0C — CAR

Cost-bounded reachability, report cost gap and earliest terminal-relevant depth. If nothing affordable within `H` reaches terminal-relevant operators, repair the operator algebra before controller work.

## Stage 0D — RETRO / MF-0R

Waste bracket, retrospective enablement (`ASSOCIATIONAL_ONLY`), retrospective fidelity. Non-admissible.

## Stage 0E — Qualification

Synthetic worlds with planted structure: chains, deduplication, multi-parent effects, inhibition, depletion, hidden variables, misleading fidelities, vacuous contracts and exact `Q*`. An estimator that fails synthetic recovery cannot issue real scientific structure claims.

## Stage 0F — MF-0X + COMPARE-0

Randomized legal alternatives, class-aware fidelities, sibling pairs reuse forks, ORACLE-WORLD ceiling. Non-admissible.

## Stage 0G — causal census

Powered product-withheld / transport-placebo / type-placebo / counterfactual experiments. Path-conditioned and free-replanning estimands remain separate. Never silently lower replication to fit budget.

## T0 / E1 — first admissible programme evidence

The bus must be qualified. Then measure AUTO versus `VBS_schedule` under stable problem/arm/action/result/verifier/cost semantics. If `AUTO ≈ VBS_schedule`, allocation research is low-value and operator capability takes priority.

## G1 -> C1 -> E3 -> G8

Prospective route truth; product closure; bounded Mastermind mechanism controls; finite cascade at matched complete cost.

## E5B — Goal 2

Only after G8. Same untouched `F*`, same complete R&D budget, 2x2 memory/policy control. Saturation is predeclared as a legitimate outcome.

# 6. Enablement measurement

- Primary object: generation-specific causal enablement kernels `K+` and `K-` recorded separately. Do not subtract them and apply Perron–Frobenius to a signed matrix.
- Primary finite quantity: deduplicated unique causally enabled opportunities `G_H^uniq` plus matched-budget `ΔU_H(B)`.
- Linear recursion is an upper bound where joint enablement is double-counted.
- `rho(K+)` is only `PAIRWISE_BRANCHING_PROJECTION` after adequacy tests. No spectral kill gates.
- Nilpotent acyclic chains may have `rho = 0` and still be valuable.
- `1/(1-rho)` is one-type only; multitype stationary diagnostics use `(I-K)^-1` with the usual model assumptions.
- Keep transport placebo and coarse-type semantic placebo separate.
- Keep path-conditioned knockout and free-replanning regime contrasts separate.
- Mandatory baselines include frequency/popularity, current Foundry, `VBS_schedule`, matched portfolio, same-products static control, MaLARea/ENIGMA-style learned relevance and DreamProver-style library reuse where compatible and reproduced under project cost rules.

# 7. Control ladder

- `B0` current Foundry.
- `B1` exact structural controller: contracts + certified pruning + cost-bounded planning.
- `B2` B1 + successive-halving real multi-fidelity probes.
- `B3` B2 + SN-COMPARE.
- `B4` B3 + one-step predictive heads.
- `B5` B4 + multi-step SN-WORLD.

Report `B2-B0`, `B3-B2`, `B4-B3`, and `B5-max(B2,B3,B4)`. Also preserve product closure controls `C0/C2/C2_STATIC_PRODUCTS` and the `VBS_schedule` headroom reference.

Independent problem/family is the unit of inference; product events and transitions are not automatically independent samples.

# 8. SN-HORIZON / SN-WORLD admission

**SN-WORLD ruling: FRONTIER ONLY.** The strongest admissible research form is a hybrid residual model:

`R_t ~ P*(.|S_t,a_t)` and `S_(t+1) = E_Λ(S_t,a_t,R_t)`,

learning only the residual distribution. One-step and direct-horizon quantities precede generative branching. Full branch-content generation has no current scientific case.

Run **ORACLE-WORLD** before building a world model: give an offline oracle actual sampled future outcomes on tiny/randomized forks and measure whether perfect horizon information improves the B3/B4 decision enough to cover world-model cost.

Core admission requires all of:

- `SNW-0` data feasibility with family-diverse interventional data and saturation curves;
- `SNW-1` predictive validity and calibration;
- `SNW-2` incremental decision value beyond B2/B3/B4;
- `SNW-3` complete-cost value including amortised training over declared `Λ` lifetime;
- `SNW-4` prospective transfer with LCB > 0 on new families;
- `SNW-5` genuine multi-step value not reproducible by comparator / one-step / direct-horizon mechanisms.

Only `SNW-5` makes “multi-step” operationally meaningful.

Preferred long-horizon routes before generative rollout: exact search + learned value; exact search + learned heuristic; global exact tiny-world oracles; pure value learning; comparator; hierarchical abstraction; real multi-fidelity racing; certified elimination; retrieval of completed verified pathways; latent value-equivalent models.

All routes need a corpus of complete verified pathways with forks and failures. Accumulate it as `typed_events[]` inside existing worker reports; do not create a competing event-state authority.

# 9. Research-lane rule

This revision opens **no new scheduled research lane**. While T0 is unqualified, BIL00 deep research may address only T0 transport/repository/admission closure. SN-HORIZON, SN-WORLD, E1, reaction, selector and Goal-2 research remain queued unless and until the accepted lane gate opens them.

# 10. Historical correction log

- spectral `rho < 1` kill gates -> removed; finite opportunity/value objects are primary;
- scalar `1/(1-rho)` amplification -> multitype resolvent only under its model assumptions;
- PF eigenvector allocator -> diagnostic prior only;
- theorem-graph heavy-tail threshold -> removed from current design basis;
- LEGO-Prover calibration anchor -> removed; library reuse remains a prior requiring project-cost reproduction;
- ignition = criticality -> ignition = certified value-gated continuation;
- depletion-aware reachability as primary screen -> cost-bounded reachability with persistent products;
- unconditional certified-dead labels -> budget-relative sound viability/deadness;
- sibling learned-error cancellation -> triangle inequality default; cancellation remains T4 target;
- low-fidelity epsilon=0 -> class-specific measured fidelity transport risk;
- SN-WORLD as next build -> Frontier only; ORACLE-WORLD first; SNW-0..5 gates;
- positive optimistic closure as a result -> `NO_INFORMATION`.

# 11. Operational rule for current generation

The active generation that predates this revision remains immutable. This Revision 4 design is frozen into the **next countable protocol-2.5 control release**. Historical non-countable bootstrap receipts remain diagnostic and may not earn calibration credit. No current `state/CURRENT.json` pointer is changed merely because this design document was adopted.
