# Project Supernova — General Base Mechanism Expansion, Qualification, and Benchmark Plan

**Date:** 2026-08-21  
**Status:** NON-AUTHORITATIVE DERIVED ENGINEERING / RESEARCH PLAN — DOUBLE-LOOP AUDITED R3  
**Repository base:** accepted `main` commit `8ab41946fa7a07d267aada67df8f9b4c09c70bf8`  
**Protocol:** 2.5 — FROZEN  
**Specification:** Revision 4 — FROZEN  
**Canonical authority:** `main:state/CURRENT.json`, frozen Revision 4, and exact control, assignment, liveness, benchmark and experiment manifests

This report does **not** modify Protocol 2.5, Revision 4, `plan/PLAN.json`, `state/CURRENT.json`, the active cohort, calibration credit, fresh-evidence eligibility, benchmark pools, Tribunal scientific state, or any frozen control. If it conflicts with frozen authority, frozen authority controls.

**Audit scope.** R3 incorporates two independent passes:

1. exact Supernova/GitHub state, authority, freeze, transition and benchmark-pool consistency;
2. primary-source review of the named formal runtimes, verifiers, retrieval systems, benchmarks and certificate formats.

Project capabilities and benchmark counts below are observations as of 2026-08-21. Every implementation or run still requires an exact commit, split hash, licence, toolchain and build receipt.

---

## 1. Verified current state

Supernova remains **Protocol 2.5 / Revision 4**. Protocol 2.6 and Revision 5 remain blocked until two consecutive clean countable Protocol-2.5 cohorts complete.

The canonical substrate is qualified **Math Foundry 3.1.1**:

- source archive SHA-256 `57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f`;
- 28/28 software-qualification suites PASS;
- packaging integrity PASS;
- runtime default mathematical wall clock `NONE`;
- mathematical results still require exact admission under the declared authority contract.

The live programme is:

- generation **9**;
- cohort `CAL-BR-009-v25-b53ab205`;
- mode `GITHUB_BRANCH_CALIBRATION`;
- countable `true`;
- calibration streak `0`;
- fresh evidence disabled;
- blocker `O-T0-TWO_CLEAN_COUNTABLE_V25_COHORTS`.

Gen9 is the first repaired countable replay-only cohort after invalidated zero-credit Gen7 and zero-credit Gen8 Math Foundry 3.1.1 staging. It is not a fresh or scientific result. Cohort credit requires the complete `12 workers -> MM06 -> MF06 -> BIL00` path.

Mastermind remains `4.4.10-execution-closure-candidate.1` with `PRE_REVIEW_ONLY` authority. The runtime-state identity remains unchanged.

---

## 2. Executive decision

Math Foundry 3.1.1 materially improved scoped method execution, routing, exact replay, local SAT, large-state serialization, source qualification, and no-default-wall-clock execution. The next major release should not merely add more Method Atlas labels.

The largest remaining deficit is a production **formal-mathematics and proof-producing computation plane**:

```text
immutable toolchain identity
    -> formal runtime
    -> proposer-independent verification and admission
    -> versioned theorem/library corpus
    -> legal premise retrieval
    -> heterogeneous prover portfolio
    -> faithful autoformalization
    -> proof/model-producing SAT/SMT/PB/CAS/optimization adapters
    -> verified-product closure
    -> runtime reactions and causal mechanism tests
    -> controlled evolution only after verifier freeze
```

A future **Math Foundry 3.2 formal-mathematics plane** is the appropriate software target. It should first be built and qualified in a separate non-admissible engineering environment.

A later canonical substrate change requires a **new, explicitly authorized, exact source-bound zero-credit transition** with safeguards equivalent to the 3.1.1 transition, followed by a clean countable restart. The one-shot 3.1.1 seed and transition exception are not reusable authority for another version.

---

## 3. Capability additions

| Capability | Current boundary | Addition required |
| --- | --- | --- |
| Formal theorem proving | scoped proof checking; not Mathlib-scale proving | pinned Lean/Mathlib, stateful runtime, whole-proof and stepwise search, decomposition, repair and exact admission |
| Formal verification/admission | authority model exists; full Lean plane absent | Comparator, `lean4export`, sandbox, statement and axiom policy, source identity and typed verifier assurance |
| Premise/library retrieval | no production Mathlib-scale retrieval | versioned declaration corpus, import/accessibility filtering, native/type/lexical/semantic/graph retrieval and proof memory |
| Autoformalization | not qualified | extraction, notation/dependency resolution, Lean generation/repair, semantic-fidelity Court, counterexample checks and proof attempt |
| Prover planning | method routing exists | proof DAG/blueprint, best-first/beam/tree search, subgoal reuse and failure-driven replanning |
| SAT/PB/SMT | scoped/local exact paths | CaDiCaL/Kissat/cvc5/VeriPB integrations with models/proofs and independently replayed certificates |
| CAS/groups/topology | scoped implementations | SageMath, GAP, Singular, FLINT/PARI, nauty/Traces and GUDHI/Ripser adapters with replay/certification |
| Optimization | scoped DP/B&B/LP/SDP | HiGHS/SCIP adapters, feasibility/objective replay, bound and optimality receipts and MIPLIB qualification |
| Distributed execution | process isolation exists | durable queue, capability/environment receipts, resumable search, verified subgoal cache and exact cost aggregation |
| External credibility | strong internal qualification | pinned public benchmark runs, accepted checker outputs, matched-budget baselines and public manifests |
| Controlled self-improvement | routing loop exists | verifier-frozen evolution of retrieval/search/decomposition with protected holdouts, rollback, lineage and complete cost |

### 3.1 Formal runtime

Use **Pantograph** as the primary candidate for a stateful machine-to-Lean interface. Wrap it behind Foundry-owned contracts for environment startup, module loading, goal opening, tactic/term execution, branching, checkpointing, environment inspection and candidate export.

LeanDojo-v2 and LeanInteract are secondary tracing, repository, file-elaboration or recovery interfaces. Their exact Lean/Mathlib compatibility must be frozen before use.

### 3.2 Formal verification and admission Court

Use the **Lean Eval Comparator** architecture as the default proposer-independent admission boundary:

```text
trusted challenge statement
  + solver-owned submission
  -> isolated build
  -> Lean kernel
  -> lean4export
  -> Comparator
  -> statement / import / axiom checks
  -> optional differently implemented replay
  -> FormalVerificationReceipt
```

*Proposer-independent* means the checker does not trust the solver submission. It does **not** by itself establish a different-implementation or statistically independent verifier.

Formal assurance must be typed rather than represented as one linear confidence ladder:

```text
FormalProofAssurance = (
  validity_status,
  statement_fidelity_status,
  axiom_policy_status,
  source_toolchain_status,
  verifier_assurance_status
)

validity_status in {
  FORMAL_CANDIDATE,
  COMPILES,
  KERNEL_ACCEPTED,
  COMPARATOR_ACCEPTED,
  EXACT_FORMAL_PROOF
}

verifier_assurance_status in {
  PRIMARY_KERNEL_ONLY,
  SAME_KERNEL_REPLAY,
  DIFFERENT_IMPLEMENTATION_REPLAY,
  NO_INDEPENDENCE_CLAIM
}
```

`COMPILES` is not proof admission. `EXACT_FORMAL_PROOF` requires the declared exact validity, statement-fidelity, axiom-policy and source/toolchain predicates. Same-kernel replay is defence-in-depth and must not be described as external independence. Different-implementation replay is an orthogonal assurance property, not a mandatory final rung for every exact result.

### 3.3 Library and retrieval

Build a corpus keyed by repository, commit, Lean/Mathlib versions, fully qualified declaration name, normalized type hash, namespace/import scope, dependency edges, informal description, lexical features, embeddings, successful proof use, authority and invalidation epoch.

Recommended cascade:

```text
accessible-declaration filter
  -> Mathlib native/type/name search
  -> lexical retrieval
  -> LeanSearch-v2 embedding retrieval
  -> reranking
  -> dependency-graph expansion
  -> iterative global premise reasoning
  -> verified Foundry proof-memory retrieval
```

A theorem that exists but is not imported or legally visible is not a legal premise.

### 3.4 Heterogeneous prover portfolio

Support three independent strategies:

1. whole-proof generation;
2. stepwise best-first/beam/tree search;
3. planner/decomposition plus parallel subgoal proving.

Candidate references include LeanDojo-v2, BFS-Prover-V2, ax-prover-base, APOLLO, and replaceable Goedel/DeepSeek/Seed/Kimina/OProver/Pythagoras-style backends.

BFS-Prover-V2 is evidence for planner-enhanced multi-agent tree search and hierarchical planning. Any claimed cache, deduplication or persistence mechanism must be confirmed from the exact frozen source before reuse. Secondary prover names are candidate references, not frozen dependencies, until repository, commit, licence, model terms, Lean/Mathlib version and runtime are recorded.

### 3.5 Autoformalization

Use AutoformBot as an orchestration candidate and ATLAS as a corpus/reference, not automatic authority:

```text
source document
  -> statement/context extraction
  -> notation and object resolution
  -> dependency retrieval
  -> candidate Lean statement
  -> compilation/repair
  -> backtranslation
  -> symbolic or bidirectional equivalence attempts
  -> missing/extra premise and scope audit
  -> counterexample/refutation search
  -> proof attempt
  -> independent semantic review
  -> FaithfulFormalizationReceipt
```

Compilation alone is not semantic fidelity.

### 3.6 Proof-producing solver and computation plane

**SAT**

- CaDiCaL/Kissat as candidate search engines;
- SAT models independently checked;
- freeze one solver/checker-compatible UNSAT pipeline per run, for example DPR/LPR, GRAT, or VeriPB/CakePB where supported;
- record generator, format, converter and checker versions;
- do not assume every backend emits every proof format.

**PB**

- VeriPB/CakePB and PBLean where feasible;
- no exact UNSAT authority from solver status alone.

**SMT**

- cvc5 as the primary open integration candidate;
- validate models and proofs where the selected logic and format support it;
- unsupported logic remains `UNKNOWN`.

**CAS and discrete mathematics**

- SageMath, GAP, Singular, FLINT/Arb/PARI, nauty/Traces, GUDHI/Ripser;
- substitute results into original obligations or replay certificates where possible.

**Optimization**

- HiGHS primary and SCIP secondary;
- independently check feasibility, objective, primal/dual bounds and any optimality claim;
- keep incumbent, proved bound, optimality, timeout and unknown distinct.

### 3.7 Controlled evolution

A-Evolve, ShinkaEvolve or related mechanisms may mutate prompts, retrieval policies, decomposition, tactic order, branching, restarts or solver allocation only after verifier, statement, authority and protected benchmark immutability.

They may never mutate theorem statements, exact checkers, Comparator, authority rules, protected evaluators, contamination firewalls, Scientific State semantics or complete-cost accounting.

---

## 4. Supernova qualification sequence

### 4.1 Source and trust qualification

For every component record exact commit, licence, dependency lock, container/build receipt, binary/source hash, advisories and tests. Run malformed-input, mutation, fuzz, process-tree, memory, timeout, schema and replay tests. Negative tests must prove an external output cannot self-admit.

### 4.2 Backend conformance

Use exact fixtures for:

- statement/import/axiom mutation;
- invisible premises;
- SAT model and UNSAT proof mutation;
- SMT model mutation;
- PB proof mutation;
- MIP incumbent/objective/bound perturbation;
- CAS substitution;
- canonicalization equivalence and non-equivalence;
- retrieval index/version mismatch;
- autoformalization premise, quantifier, conclusion and scope defects.

Keep `PASS`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`, `ABSTAINED`, `TIMEOUT`, `MEMOUT`, `INFRASTRUCTURE_FAILURE`, `INVALID_CERTIFICATE` and `STATEMENT_MISMATCH` distinct.

### 4.3 H0/H1 falsifiers

Retain `PAIR`, `XOR`, `ORDER`, `ENABLE`, `SEPARATOR`, `MEMORY`, `COMMUTE`, `RESOURCE`, `HIDDEN_CONTROLLER` and `INTERLEAVE`.

Add `PREMISE_SCOPE`, `STATEMENT_WEAKEN`, `STATEMENT_STRENGTHEN`, `AXIOM_ESCAPE`, `VERSION_DRIFT`, `PROOF_CACHE_STALE`, `RETRIEVAL_LEAK`, `MODEL_ONLY_UNSAT`, `NUMERIC_FALSE_CERT` and `COMMON_CHECKER_BUG`.

### 4.4 E1 clean route/schedule truth

After the active countable-calibration prerequisite closes, `MF-E1-CLEAN-ROUTE-TRUTH` compares at equal complete cost:

- BASE 3.1.1;
- every single eligible route/backend;
- fixed strong schedule (`SBS`);
- diagnostic virtual best (`VBS`);
- current `AUTO`;
- formal-runtime/retrieval variants;
- planner/search variants;
- `ORACLE_SCHEDULE` where admissible;
- random and no-change controls.

Record route eligibility, startup/build/index cost, inference, probe, execution, verification, fidelity and revalidation cost, verified result, zero/unknown/abstention/timeout, statement fidelity, route/schedule regret and domain heterogeneity. E1 remains `CALIBRATION`, never G1/G8 promotion evidence.

### 4.5 Causal programme

- **G1:** disjoint private fresh parent/candidate test, same untouched parent, frozen mechanism, matched `C_complete`, independent verifier.
- **C1:** unavailable / available-but-prohibited / legal reuse / placebo / stale-invalid product controls.
- **SN-RXN:** typed runtime reactions from real operations, not Method Atlas inference.
- **DR03:** distinguish factorial interaction, order/interleaving and dynamic sequential estimands from predictive labels.
- **E3:** compare learned mechanism with no-change, random valid, fixed strong, state-conditioned heuristic, myopic value-of-computation and tiny-world oracle.
- **C2:** freeze and test unrelated domains/operators.
- **G8:** disjoint fresh cascade against the strongest simpler controller.
- **E5B:** same untouched start, matched complete R&D budget, controlled memory and explicit `F/M/I` separation.

The queued future order remains:

```text
C1 -> SN-RXN -> DR03 -> E3 -> SELECT -> IGNITION -> G8
```

This report does not activate Revision 5.

---

## 5. Benchmark programme

Public benchmarks provide external comparability, not automatic Supernova freshness. Put used public cases in `TRAIN_TUNING`, `CALIBRATION`, or a separately declared external-credibility lane unless a contamination-safe prospective contract exists.

### 5.1 Formal theorem proving

| Benchmark | Audited use |
| --- | --- |
| **Lean Eval** | primary external acceptance framework; Comparator, statement identity, axiom policy and complete cost |
| **miniF2F Lean 4** | historical continuity and fast regression at an exact corrected fork/toolchain |
| **PutnamBench** | pinned Lean split: 672 statements at the report date; obey its request not to publish proofs publicly and record contamination risk |
| **FATE-M/H/X** | report M/H/X separately: 150/100/100 at the report date; do not combine tiers |
| **ProofNet-Verified** | 367 audited statements/pairs at the report date; Comparator and semantic-fidelity analysis |
| **CombiBench** | 100 combinatorial problems at the report date |
| **MA-ProofBench** | 200 analysis problems: 100 undergraduate and 100 PhD-level at the report date |
| **LeanCat** | 100 category-theory statement problems at the report date, after exact preflight |
| **Formal Conjectures** | `RESEARCH_FROZEN`; immutable benchmark tag required; unproved/potentially misformalized statements are not automatic truth authority |

Counts are date-stamped observations, not permanent constants.

### 5.2 Retrieval

- LeanSearch-v2 `MathlibQR`: 946 rows; fair 810-row/171-declaration subset;
- `MathlibMPR`: 69 theorems;
- `MathlibMPR-Prop`: 50-problem subset;
- FATE-H: 100 problems;
- dependency-held-out Mathlib declarations;
- Foundry verified-proof-memory holdout.

Ablate no retrieval, native/type, lexical, embedding, embedding+reranker, graph expansion, iterative reasoning, verified proof memory and full cascade.

### 5.3 Autoformalization

- ProofNet-Verified informal/formal pairs;
- held-out ATLAS sources;
- AutoformBot extraction/dependency fixtures;
- a frozen Herald-derived or equivalent backtranslation set only after exact items, source revision and licence are frozen;
- adversarial premise, quantifier, conclusion and scope mutations.

Report compile rate, fidelity, implication/equivalence support, missing/extra premises, counterexamples, proof success, ambiguity abstention, independent review and complete cost.

### 5.4 SAT/SMT/PB

- SAT Competition 2026 deterministic set and applicable proof-checker tracks;
- SMT-COMP 2026 single-query and **experimental** model-validation tracks, separately by logic and official rules;
- Foundry exact oracle/mutation matrix.

Report competition-compatible score, SAT/UNSAT, validated model/proof, invalid certificate, timeout, memout, abstain, unknown and checker overhead separately.

### 5.5 Optimization

- MIPLIB 2017 official 240-instance set;
- freeze the exact downloadable benchmark archive, solufile and easy/hard metadata because those can change;
- official solution checker;
- MiniZinc/domain CP sets after preflight;
- Foundry exact optimization oracle set.

### 5.6 Discovery/evolution

- SkyDiscover mathematical tasks;
- SkyDiscover's frozen `frontier-cs-eval` subset rather than an ambiguous standalone “Frontier-CS” label;
- exact AlphaResearchComp task release from `answers111/alpha-research` after licence/evaluation preflight;
- exact `google-deepmind/alphaevolve_repository_of_problems` revision;
- private exact-construction tasks and withheld known-answer designs.

H-668 diagnostics remain research-specific development material and cannot be the sole general-base evidence.

---

## 6. Governance and scorecard

Use existing pools without relabelling:

- `TRAIN_TUNING` — repeated development only;
- `CALIBRATION` — thresholds, E1 and component qualification;
- `G1_PROSPECTIVE` — sealed one-generation test;
- `G8_CASCADE` — sealed final Goal-1 cascade;
- `GOAL2_E5B` — sealed same-start improver test;
- `RESEARCH_FROZEN` — future admitted research lane.

Every run binds benchmark commit and split hash, statement identity, model/tool/runtime, route/controller/retriever, permitted imports, seeds/samples, budgets, evaluators/checkers, contamination exclusions, cache/context policy, primary estimand and stopping rule.

```text
C_complete = instrumentation + data + training_amortized + inference
           + probe + execution + verification + fidelity + revalidation
           + failure/recovery + metalevel_selection
```

No composite score overrides correctness, authority, statement fidelity or pool-integrity gates.

---

## 7. Implementation order

1. **Verifier substrate:** pin Lean/Mathlib, Comparator, `lean4export`, sandbox, statement/axiom/source receipts and escape tests.
2. **Formal runtime:** Pantograph adapter, process pool, checkpointing, task/result contracts and replay.
3. **Retrieval:** trace pinned Mathlib, native/lexical search, LeanSearch-v2 index at the exact corpus pin, reranking, graph expansion and verified proof memory.
4. **Prover portfolio:** whole-proof, stepwise, planner/subgoal reuse, repair/replanning and E1 route matrix.
5. **External qualification:** Lean Eval first, then miniF2F, PutnamBench, ProofNet-Verified, CombiBench, FATE and MA-ProofBench.
6. **Autoformalization:** AutoformBot adapter plus semantic-fidelity Court.
7. **Solver/CAS/optimization:** proof/model-producing adapters and external benchmarks.
8. **Causal closure:** C1, SN-RXN, DR03, E3 and C2/G8.
9. **Controlled evolution:** only after verifier and protected benchmark immutability.

Highest-priority tranche:

> **Pinned Lean/Pantograph execution plus Comparator/lean4export/sandbox admission, with a minimal theorem task and exact replay receipt.**

---

## 8. Freeze-safe actions

Allowed outside frozen active assignments as non-admissible engineering:

- exact source/licence/dependency/checker preflight;
- schemas and adapter harnesses;
- H0/H1 fixtures;
- private E1 design without consuming outcomes;
- formal runtime, verifier and retrieval prototypes.

Not authorized:

- Protocol 2.6 or Revision 5;
- mutation or repurposing of Gen9 control/assignments;
- fresh G1/G8/Goal2 consumption;
- scientific promotion;
- authority for an external model/retriever/solver;
- public benchmark gain described as Supernova causal success.

---

## 9. Exact-preflight source ledger

- Lean 4: `https://github.com/leanprover/lean4`
- Mathlib: `https://github.com/leanprover-community/mathlib4`
- Pantograph: `https://github.com/leanprover/Pantograph`
- LeanDojo-v2: `https://github.com/lean-dojo/LeanDojo-v2`
- LeanInteract: `https://github.com/augustepoiroux/LeanInteract`
- LeanSearch-v2: `https://github.com/frenzymath/LeanSearch-v2`
- Lean Eval: `https://github.com/leanprover/lean-eval`
- Comparator: `https://github.com/leanprover/comparator`
- BFS-Prover-V2: `https://github.com/ByteDance-Seed/BFS-Prover-V2`
- APOLLO: `https://github.com/aziksh-ospanov/APOLLO`
- ax-prover-base: `https://github.com/Axiomatic-AI/ax-prover-base`
- AutoformBot: `https://github.com/facebookresearch/autoform-bot`
- ATLAS: `https://github.com/facebookresearch/atlas-lean`
- Herald: `https://github.com/lean-dojo/Herald`
- ProofNet-Verified: `https://github.com/marcusm117/ProofNet-Verified`
- PutnamBench: `https://github.com/trishullab/PutnamBench`
- CombiBench: `https://github.com/MoonshotAI/CombiBench`
- MA-ProofBench: `https://github.com/OpenBMB/MA-ProofBench`
- LeanCat: `https://github.com/sciencraft/LeanCat`
- Formal Conjectures: `https://github.com/google-deepmind/formal-conjectures`
- miniF2F Lean 4: `https://github.com/google-deepmind/miniF2F`
- CaDiCaL: `https://github.com/arminbiere/cadical`
- Kissat: `https://github.com/arminbiere/kissat`
- cvc5: `https://github.com/cvc5/cvc5`
- VeriPB: `https://gitlab.com/MIAOresearch/software/VeriPB`
- PBLean: `https://github.com/Seasawher/PBLean`
- HiGHS: `https://github.com/ERGO-Code/HiGHS`
- SCIP: `https://github.com/scipopt/scip`
- SageMath: `https://github.com/sagemath/sage`
- GAP: `https://github.com/gap-system/gap`
- Singular: `https://github.com/Singular/Singular`
- FLINT: `https://github.com/flintlib/flint`
- A-Evolve: `https://github.com/A-EVO-Lab/a-evolve`
- ShinkaEvolve: `https://github.com/SakanaAI/ShinkaEvolve`
- SkyDiscover: `https://github.com/skydiscover-ai/skydiscover`
- AlphaResearchComp source: `https://github.com/answers111/alpha-research`
- AlphaEvolve problem repository: `https://github.com/google-deepmind/alphaevolve_repository_of_problems`
- SAT Competition 2026: `https://satcompetition.github.io/2026/`
- SMT-COMP 2026: `https://smt-comp.github.io/2026/`
- MIPLIB 2017: `https://miplib.zib.de/`

Moving URLs are discovery references only. Final integration replaces them with exact commits, tags, hashes, licences and build receipts.

---

## 10. Final status

Supernova has updated to qualified Math Foundry 3.1.1 and opened the first repaired countable replay cohort, Gen9. Supernova remains Protocol 2.5 / Revision 4. Gen9 is incomplete, the calibration streak remains 0, and fresh scientific execution remains disabled.

The general-base mechanism is strongest in execution integrity, scoped exact methods, authority separation and controlled experiment design. It remains behind leading open formal-mathematics systems in full theorem proving, premise retrieval, faithful autoformalization, mature solver integration, distributed proof search and externally recognized benchmark performance.
