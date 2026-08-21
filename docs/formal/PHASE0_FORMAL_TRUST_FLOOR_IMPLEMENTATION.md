# Math Foundry 3.2 / Supernova — Phase-0 Formal Trust Floor

**Status:** NON-ADMISSIBLE ENGINEERING ONLY  
**Authority:** NONE  
**Supernova calibration/fresh/scientific credit:** 0 / false / 0  
**Active Gen9 effect:** NONE

This tranche implements contracts and source preflight for the first formal-mathematics trust floor described by `docs/SUPERNOVA_GENERAL_BASE_MECHANISM_EXPANSION_AND_BENCHMARK_PLAN_2026-08-21.md`. It does not activate formal theorem proving in Gen9 and does not modify `state/CURRENT.json`, `plan/PLAN.json`, active control/assignment, benchmark pools, existing workflows, fresh eligibility, calibration credit, Tribunal state, or the qualified Math Foundry 3.1.1 substrate.

## 1. Why this tranche exists

The formal plane must be trustworthy before a large prover model is attached. The minimum dependency chain is:

```text
exact source/toolchain identity
    -> clean formal runtime
    -> statement/axiom/source checks
    -> proposer-independent admission
    -> typed verification receipt
```

A model-generated Lean term, successful compilation, kernel acceptance, and Comparator acceptance are not interchangeable statuses. Exact proof authority is a derived predicate over validity, statement fidelity, axiom policy and source/toolchain identity.

## 2. Upstream compatibility finding

A naive “latest of every dependency” stack is currently inconsistent:

- current Mathlib master is on Lean `v4.34.0-rc2`;
- current Comparator master is on Lean `v4.34.0-rc2`;
- current lean4export master is on Lean `v4.34.0-rc2`;
- Pantograph `dev` is on Lean `v4.31.0`;
- Pantograph `main` is substantially older.

Therefore this tranche does **not** mix current heads. It records a coherent Lean 4.31 candidate set whose own `lean-toolchain` files all declare `leanprover/lean4:v4.31.0`:

- Mathlib `fabf563a7c95a166b8d7b6efca11c8b4dc9d911f`;
- Pantograph `d704b851542b1d2caf1287f65c49f5011f687c05`;
- Comparator `fd2e25de155523dbce1f35d410511f9f63998461`;
- lean4export `8554815c2dc6b7abe99ec1f08849c9759ba77947`;
- Lean toolchain tag `v4.31.0`.

This is **source-level compatibility evidence only**. No combined build has passed yet; licences, source archives, OS/kernel/sandbox identity, security configuration and replay remain unresolved. The candidate manifest therefore stays `ENGINEERING_ONLY / PARTIAL / UNQUALIFIED`.

## 3. Artifacts in this tranche

### `schemas/formal_toolchain_manifest.schema.json`

Defines a source-bound formal toolchain manifest with:

- exact repository/ref/source identity;
- common Lean toolchain declaration;
- component role;
- licence/build/qualification state;
- environment/sandbox state;
- explicit missing requirements;
- hard-coded zero Supernova authority/fresh/calibration effects for engineering candidates.

### `schemas/formal_verification_receipt.schema.json`

Defines orthogonal formal assurance fields:

```text
validity_status
statement_fidelity_status
axiom_policy_status
source_toolchain_status
verifier_assurance_status
```

`derived_exact_formal_proof=true` is schema-valid only when:

- validity is `COMPARATOR_ACCEPTED`;
- statement fidelity is `VERIFIED`;
- axiom policy is `VERIFIED`;
- source/toolchain identity is `VERIFIED`;
- authority is `EXACT_FORMAL_PROOF`.

Otherwise authority must remain `NONE`.

### `scripts/formal_toolchain_preflight.py`

Fail-closed static preflight. It checks:

- manifest JSON Schema;
- common declared Lean toolchain;
- exact commit/source binding for commit refs;
- component build/licence conditions before component qualification;
- sandbox, compatibility, missing-requirement and component gates before manifest qualification;
- canonical manifest digest and zero-credit receipt.

Warnings such as an unresolved tag-to-source commit do not create authority and prevent later qualification until explicitly closed.

### `docs/formal/FORMAL_TOOLCHAIN_CANDIDATE_V1.json`

First coherent source candidate. It is deliberately **not** a qualification receipt.

### `docs/general_base_engineering_queue.json`

Machine-readable bounded engineering queue. The automation policy forbids active/frozen paths and permits at most one non-admissible tranche per run.

## 4. Phase-0 acceptance sequence

The current tranche covers contract/source preflight only. Phase 0 is complete only after all of the following pass:

1. resolve the Lean tag to exact source/archive identity;
2. verify licences and dependency locks;
3. clean-build all five components under one pinned image;
4. execute a minimal Pantograph theorem session;
5. execute Comparator + lean4export positive and negative fixtures;
6. mutate theorem statement, imports and axiom policy and confirm rejection;
7. configure and freeze OS/kernel/sandbox/privilege/network/cache policy;
8. run escape, malformed-input and mutation/fuzz suites;
9. record shared TCB and independence limitations;
10. produce deterministic package and fresh-replay qualification receipts.

Until step 10, no external prover output can be promoted to `EXACT_FORMAL_PROOF` through this new plane.

## 5. Automation boundary

During Gen9 the formal engineering programme is deliberately **outside the frozen active control set**. Automatic work must:

- use `rev4/` branches;
- advance at most one queue tranche per scheduled run;
- use existing repository admission, not add or weaken workflows;
- never modify any active/frozen control path;
- never consume fresh/private promotion benchmarks;
- never write calibration/scientific/Tribunal state;
- stop on stale main, failed checks, merge conflict, authority ambiguity, or any requirement for a frozen-path edit.

A later formal substrate transition into canonical Supernova requires a separately authorized zero-credit transition after the current countable-calibration freeze permits it. This engineering queue cannot self-promote.
