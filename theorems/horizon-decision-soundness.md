# HDS-1 — Horizon Decision Soundness, Revision 4 draft

**Status:** DRAFT + EXECUTABLE H1 CORRESPONDENCE  
**Protocol:** 2.5 frozen  
**Revision:** 4 frozen

For authoritative state `S`, action `a`, finite horizon `H`, complete budget `b` and semantic bundle `Lambda`, let `Q*_H(S,a;b,Lambda)` be exact finite-horizon value. Suppose every admitted `SOUND` interval satisfies `L_a <= Q*_H(S,a;b,Lambda) <= U_a` and binds the exact same state/action/horizon/budget/semantic scope.

## Theorem

If candidate `A` satisfies

`L_A > max_{B != A} U_B + delta`, `delta >= 0`,

then `Q*(A) > Q*(B) + delta` for every frozen rival `B`.

## Proof

For every rival `B`, SOUND containment gives `Q*(A) >= L_A` and `Q*(B) <= U_B`. The stop premise gives `L_A > U_B + delta`; hence `Q*(A) >= L_A > U_B + delta >= Q*(B) + delta`. Since `B` is arbitrary, `A` is delta-better than every rival.

## Executable correspondence

`diagnostics/stage0/h1/horizon_kernel.py` implements exact `BoundScope(state, action, horizon, budget, semantic_version)`, typed evidence, SOUND intersection, contradiction detection and a SOUND-only `certified_stop` matching the theorem premise. `HEURISTIC_ONLY` may select a computation but never narrows a certifying interval.

H0 exact worlds provide enumerated finite oracles. Current synthetic qualification reports:

- exact worlds: 10;
- exact SOUND first-action bounds: 21;
- SOUND containment violations: 0;
- incorrect certified stops: 0.

Negative tests cover contradictory SOUND evidence, stale semantic scope, calibrated-only evidence, overlapping calibrated dependencies, explicit joint calibration identity and unequal heuristic attention.

## Exclusions

This theorem does not establish coverage for calibrated intervals, optimality of computation selection, adequacy of learned consequence models or prospective Supernova utility. Those remain separately qualified and Tribunal/M9 controlled.
