# CS-1 — Cascade Soundness, Revision 4 draft

**Status:** DRAFT / PAPER OBLIGATION / NON-PROMOTION  
**Protocol:** 2.5 frozen  
**Revision:** 4 frozen

## Statement

Fix semantic/runtime bundle `Lambda`, finite horizon `H`, complete budget `b`, a finite execution history and an exact Foundry transition system. Assume:

1. Every executable operator `a` has a machine-checkable contract `{Pre_a} a {Post_a}` interpreted by authoritative Foundry semantics `E_Lambda`.
2. The controller executes only actions Foundry declares legal in the authoritative state.
3. Every mathematical product admitted to reusable product set `P` has an independent formal-verification PASS under the frozen checker semantics and the required `StatementFidelityCertificate` status.
4. Every downstream reuse is mediated by a `ProductUseCertificate` binding the exact product, consumer, obligation and semantic/version relation.
5. Predicted/simulated lemmas and failed/unknown/stale/mismatched verification results never enter `P`.
6. Continuation/value-of-computation may allocate work but cannot weaken items 1–5.

Then every product admitted in a finite cascade of depth at most `H` is valid under the frozen formal semantics and its declared statement-fidelity scope. A finite cascade cannot manufacture mathematical truth from an unverified intermediate state.

## Part (1) proof sketch — finite product validity

Induct on cascade depth. The initial product set satisfies the admission invariant by assumption. Assume all products admitted through depth `t` satisfy it. At `t+1`, Foundry executes only a legal operation. A produced candidate is not inserted into `P` merely because the operation returned it: admission follows only after independent verification plus the required statement-fidelity decision. A prior product may be consumed only through its explicit use certificate. Therefore every newly admitted product again satisfies the invariant, while failed/unknown/stale/mismatched candidates remain outside `P`. Finite induction gives the claim through depth `H`.

## Part (2) — behavioural non-interference wrapper

Let baseline controller output the full decision vector `D0(S)` containing executed action, probe set, ordering, budgets, retention, expansion, cache/context policy, product exposure and stopping. Define the learned wrapper so that inside its declared indifference region it returns `D0(S)` field-for-field rather than merely choosing an action with the same name.

Conditional on entry to that wrapper region, behavioural identity is exact by construction. The separate empirical obligation is whether the indifference region has the promised calibration/risk coverage on the declared support population.

## Not proved here

This draft does not prove calibrated coverage, learned-model accuracy, statement-fidelity correctness beyond the authority contract, prospective cascade utility, checker independence, Goal 1 or Goal 2.
