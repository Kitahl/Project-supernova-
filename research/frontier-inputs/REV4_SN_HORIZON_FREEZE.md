# Revision 4 Frontier Input Freeze

**Protocol:** 2.5 frozen  
**Revision:** 4 frozen  
**Authority:** FRONTIER / NON-AUTHORITATIVE / NON-ADMISSIBLE until gates pass

This file records the Frontier inputs permitted to be implemented/qualified during the Revision-4 freeze without creating Revision 5.

## SN-HORIZON

Target finite object:

`L_H(S,a;b,Λ) <= Q*_H(S,a;b,Λ) <= U_H(S,a;b,Λ)`.

Evidence kinds: `SOUND`, `ANYTIME_CALIBRATED(alpha)`, `FIXED_SAMPLE_CALIBRATED(alpha)`, `HEURISTIC_ONLY`.

HEURISTIC_ONLY may select the next reasoning computation but cannot narrow a certifying interval. SOUND interval separation is the first executable qualification target. Statistical sources that overlap in data/model/features/forks/calibration population require joint calibration or conservative common-alpha accounting.

Metalevel controls: cheapest probe M0, fixed order M1, myopic VOC M2, learned selector M3, exact tiny oracle M*. Every selection emits a `ComputationSelectionTrace` and complete metalevel cost.

## Query-conditioned consequence stack

Recommended service names:

- `SN-COMPARE`: direct sibling/plan comparison;
- `SN-CONSEQUENCE` / `SN-GAMMA`: query-conditioned Bellman-relevant consequences;
- `SN-WORLD`: later residual/short-rollout backend;
- `SN-HORIZON`: typed-evidence metareasoner/planning interface within General-rho.

The query determines interventions/candidate set, witness class, horizon, continuation-policy family, error tolerance, risk allocation, complete-cost budget, semantic version and support population.

## Exact/residual authority split

Authoritative transition remains `S' = E_ν(S,a,R)`. A learner may estimate `P(R|z,a)` or query-specific functionals but never legality, type compatibility, verification, product admission or scientific truth.

## Qualification order

H0 exact worlds -> H1 SOUND interval kernel -> real decision-event corpus -> RETRO/CID/MF -> ORACLE-WORLD/HEADROOM -> SN-COMPARE -> one-step/direct-horizon SN-CONSEQUENCE -> FACTOR-0 -> SN-HORIZON -> short residual SN-WORLD -> SNW-0..5.

## HEADROOM-0

Keep separate ceilings for same-menu reranking, candidate generation and information-action selection. Kill/defer a model class if recoverable-value UCB is below unavoidable model-cost LCB plus deployment margin.

## FACTOR-0

`G_contract != G_stochastic` unless demonstrated. Compare contract scope, +1, +2 and global models at identical targets/training budgets. M8 remains the continuing locality falsifier after any initial qualification.

## Revision-freeze rule

H0/H1 implementation and synthetic qualification are allowed now. Real learned-model admission, new scientific claims or architectural changes outside this frozen input require the existing prospective gates; the specification itself remains Revision 4 until calibration streak = 2.
