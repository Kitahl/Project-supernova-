# Project Supernova — General Base Mechanism Expansion, Qualification, and Benchmark Plan

**Date:** 2026-08-21  
**Status:** NON-AUTHORITATIVE DERIVED ENGINEERING / RESEARCH PLAN  
**Repository base inspected:** `Kitahl/Project-supernova-` at accepted `main` commit `52b2c8dff2f2246c0170172aad4abb25067e506a`  
**Protocol:** 2.5 — FROZEN  
**Specification:** Revision 4 — FROZEN  
**Canonical live authority:** `main:state/CURRENT.json` and exact frozen experiment manifests  
**Scope:** capability expansion, test architecture, benchmark governance, and implementation order for the general Math Foundry / Supernova base mechanism  

This document does **not** modify Protocol 2.5, Revision 4, `plan/PLAN.json`, `state/CURRENT.json`, the active cohort, calibration credit, fresh-evidence eligibility, Tribunal scientific state, or any frozen experiment manifest. It is a derived implementation and qualification plan. If it conflicts with frozen authority, the frozen authority controls.

---

## 1. Executive decision

Project Supernova now has a stronger software substrate than the older derived documentation implies: accepted `main` is bound to **Math Foundry 3.1.1** in a non-countable, zero-credit Gen8 staging state. That update is real, but it is deliberately **not yet a fresh or scientific capability claim**.

The next large capability increase should not be another expansion of the 57 Method Atlas labels. Math Foundry 3.1.1 already supplies a qualified scoped executor/routing layer. The remaining general-base deficit is that many broad mathematical methods still terminate at comparatively small scoped implementations rather than production integrations with mature formal, retrieval, solver, algebra, and optimization systems.

The recommended expansion is a layered **formal-mathematics and proof-producing computation plane** built on top of the existing Foundry authority model:

```text
immutable toolchain identity
    -> formal runtime
    -> independent verification court
    -> versioned theorem/library corpus
    -> premise retrieval
    -> heterogeneous prover portfolio
    -> faithful autoformalization
    -> proof-producing SAT/SMT/PB/CAS/optimization adapters
    -> verified-product closure
    -> runtime reaction records
    -> causal mechanism tests
    -> controlled evolution only after the verifier is frozen
```

The programme should reuse large open-source systems before implementing substitutes. Integration does not confer authority: generated proofs, retrieved premises, solver answers, models, bounds, formalizations, or evolved policies remain proposed or `SEARCH_ONLY` until the appropriate independent checker or exact replay admits them.

### Recommended release target

Use a future **Math Foundry 3.2 formal-mathematics plane** as the software target. Supernova should first qualify that software in a non-admissible engineering environment. It should enter the canonical runtime only through the same source-bound, zero-credit staging and countable-restart procedure used for 3.1.1.

---

## 2. Verified repository state

### 2.1 Supernova version

The Supernova controller itself remains:

- **Protocol 2.5 — frozen**;
- **Specification Revision 4 — frozen**;
- canonical plan ID `0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`.

No Protocol 2.6 or Revision 5 is authorized before the two-clean-countable-cohort freeze condition is met.

### 2.2 Math Foundry version now bound in Supernova

Accepted `main` now records:

- Math Foundry semantic version: **3.1.1**;
- source archive SHA-256: `57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f`;
- software qualification: **28/28 PASS**;
- runtime default wall clock: `NONE`;
- packaging integrity: `PASS`;
- authority boundary: exact mathematical truth still requires independent exact checking.

### 2.3 Operational status of the update

The 3.1.1 update is canonical in `main`, but its current state is intentionally limited:

- generation: **8**;
- cohort: `STAGE-BR-008-v25-MF311`;
- mode: `BENCHMARK_DISCOVERY_WAIT`;
- countable: **false**;
- calibration credit: **0**;
- fresh evidence: **disabled**;
- worker execution: **not authorized in this staging generation**;
- next blocker: `O-T0-MF311_STAGING_TO_COUNTABLE_RESTART`.

Therefore the correct statement is:

> Supernova has updated its canonical software substrate identity to qualified Math Foundry 3.1.1, but it has not yet qualified a repaired countable replay cohort under that substrate and has not enabled fresh scientific execution.

Mastermind remains version `4.4.10-execution-closure-candidate.1` with `PRE_REVIEW_ONLY` authority. The runtime state identity remains unchanged.

---

## 3. What 3.1.1 solved and what remains

### 3.1 Capabilities materially improved in 3.1.1

- 57 Method Atlas cards have qualified scoped execution paths and independent replay within declared scopes.
- Routing has a stronger mechanism-aware architecture and an internally qualified promotion holdout.
- Local exact SAT fallback is materially better than the former truth-table implementation.
- large compressed-state serialization failure was repaired.
- default mathematical wall-clock stopping was removed while explicit finite controls remain available.
- source, manifest, qualification, authority, and status separation are stronger.

### 3.2 Remaining general-base capability gaps

| Capability | Current practical state | Required addition |
| --- | --- | --- |
| Formal theorem proving | scoped proof checking; no full Mathlib-scale proving plane | Lean runtime, proof-state API, whole-proof and stepwise search, decomposition, proof repair, independent comparator admission |
| Premise/library retrieval | no production Mathlib-scale retrieval plane | versioned declaration corpus, lexical/type/semantic/graph retrieval, accessible-premise filtering, proof-memory retrieval |
| Autoformalization | not a qualified Foundry subsystem | document extraction, dependency retrieval, Lean generation/repair, semantic-faithfulness court, proof attempt and provenance |
| Independent formal verification | Foundry authority model exists but not complete Lean verification substrate | Comparator, `lean4export`, sandbox, axiom/statement identity policy, optional differently structured replay |
| SAT/PB/SMT | scoped DPLL/PB/MILP paths | CaDiCaL/Kissat/cvc5/VeriPB integrations, models/proofs, independent certificate replay, competition-format adapters |
| CAS/algebra/groups/topology | scoped exact implementations | SageMath, GAP, Singular, FLINT/PARI, GUDHI/Ripser adapters with replay/certification |
| Optimization | scoped DP/B&B/LP/SDP and HiGHS-related paths | robust HiGHS/SCIP/MIPLIB adapters, exact feasibility/objective replay, decomposition and incumbent/bound receipts |
| Prover planning | method routing and research planning | proof DAG/blueprint, subgoal cache, best-first/beam/tree search, failure-driven replanning |
| Long-horizon research memory | Scientific State foundation | verified theorem/product memory, dependency graph, reusable proof/certificate artifacts, invalidation/revalidation |
| Distributed execution | process isolation and GitOps control | durable task queue, shared verified subgoal cache, heterogeneous workers, resumable search, exact cost aggregation |
| External credibility | strong internal qualification | independent public benchmark runs, pinned toolchains, public manifests/submissions, matched-budget baseline results |
| Controlled self-improvement | routing improvement loop | verifier-frozen evolution of prompts/search/retrieval/decomposition; protected holdouts; rollback; lineage and cost accounting |

---

## 4. Target architecture

### 4.1 Formal Toolchain Manifest

Add an immutable `FormalToolchainManifest` that binds at minimum:

- Lean commit/toolchain;
- Mathlib commit;
- Pantograph/PyPantograph commit;
- LeanDojo-v2 or LeanInteract commit where used;
- Comparator commit;
- `lean4export` commit;
- sandbox commit and policy;
- independent replay/checker identity;
- permitted axioms and escape-policy version;
- theorem corpus identity;
- retrieval-index identity;
- model/service identities;
- environment/container/driver identity;
- exact dependency lock and build receipt.

No formal execution should be admitted without a complete manifest. A model name or API request string is not a runtime binding receipt.

### 4.2 Canonical Lean runtime

**Primary recommendation:** adapt **Pantograph** as the canonical stateful machine-to-Lean interface.

Required Foundry adapter functions:

```text
start_environment(toolchain_manifest)
load_module(repository, commit, imports)
open_goal(statement_identity)
execute_tactic(proof_state_id, tactic)
execute_term(proof_state_id, term)
branch_state(proof_state_id)
restore_state(checkpoint_id)
inspect_environment(query)
export_candidate(candidate_id)
close_environment()
```

Pantograph should be wrapped, not granted authority. Foundry owns process isolation, resource receipts, source identity, task identity, and result admission.

**Secondary/recovery interfaces:**

- LeanDojo-v2 for repository tracing, theorem databases, agent/prover interfaces and Pantograph-based proving;
- LeanInteract or a pinned Lean server for whole-file elaboration and repair-oriented execution;
- a service wrapper only when its exact source/model/environment identity is observable and frozen.

### 4.3 Independent formal verification court

Use **Lean Eval Comparator** architecture as the default admission boundary:

```text
trusted challenge statement
    + solver-owned submission
    -> isolated build
    -> Lean kernel
    -> lean4export
    -> comparator
    -> axiom / statement identity checks
    -> optional differently structured replay
    -> FormalVerificationReceipt
```

Required status lattice:

```text
FORMAL_CANDIDATE
COMPILES
KERNEL_ACCEPTED
STATEMENT_IDENTITY_VERIFIED
AXIOM_POLICY_VERIFIED
COMPARATOR_ACCEPTED
INDEPENDENT_REPLAY_VERIFIED
EXACT_FORMAL_PROOF
```

`COMPILES` is not a proof-admission status. Same-kernel replay is defence-in-depth but is not labelled external independence.

### 4.4 Formal library and premise retrieval

Build a versioned declaration corpus containing:

- fully qualified declaration name;
- type and normalized type hash;
- source repository and commit;
- Lean and Mathlib versions;
- namespace/import visibility;
- syntax/AST and informal descriptions;
- type/value dependency edges;
- proof references and successful usage;
- lexical tokens, embeddings and reranking features;
- authority and provenance;
- invalidation epoch.

Retrieval cascade:

```text
accessible-declaration filter
    -> native Mathlib/type/name search
    -> lexical/BM25 retrieval
    -> LeanSearch-v2 embedding retrieval
    -> neural reranking
    -> dependency-graph expansion
    -> iterative global premise-set reasoning
    -> verified Foundry proof-memory retrieval
```

A vector database alone is not sufficient. Retrieval must be filtered by what is legally imported and observable at the target theorem.

### 4.5 Heterogeneous prover portfolio

Define backend-neutral contracts:

```text
ProverRequest
ProverCandidate
ProverSearchTrace
SubgoalArtifact
ProofMemoryRecord
ProverOutcomeReceipt
```

Support at least three distinct strategies:

1. **whole-proof generation**;
2. **stepwise best-first/beam/tree search**;
3. **planner/decomposition plus parallel subgoal proving**.

Reusable references/components:

- **BFS-Prover-V2** — planner, shared subgoal cache, multi-agent best-first search;
- **LeanDojo-v2** — proving interfaces, tracing, theorem database, retrieval-agent architecture;
- **ax-prover-base** — proposer/compiler/reviewer/memory loop; use as a reference or isolated service because its AGPL licence may not suit vendoring;
- **Goedel-Prover-V2**, DeepSeek-Prover, Seed-Prover, Kimina, OProver, Pythagoras-style systems — model/prover backends after exact model licence and runtime qualification;
- **APOLLO** — repair loop and compiler-feedback architecture.

No single model should define Foundry's proving architecture. Models are replaceable proposal engines.

### 4.6 Autoformalization plane

Use **AutoformBot** as the first orchestration scaffold and **ATLAS** as a large-scale corpus/reference, not as automatic authority.

Required pipeline:

```text
source document
    -> statement/context extraction
    -> object and notation resolution
    -> dependency/premise retrieval
    -> candidate Lean statement
    -> compilation and error repair
    -> backtranslation
    -> symbolic/bidirectional equivalence attempts
    -> missing-premise and scope audit
    -> counterexample/refutation search
    -> proof attempt
    -> independent semantic review
    -> FaithfulFormalizationReceipt
```

Required states:

```text
FORMALIZATION_PROPOSED
COMPILES
SEMANTICALLY_UNVERIFIED
DEPENDENCY_AUDITED
COUNTEREXAMPLE_REJECTED
BIDIRECTIONALLY_SUPPORTED
SEMANTICALLY_REVIEWED
FAITHFUL_FORMALIZATION_ADMITTED
```

The benchmark audit in ProofNet-Verified demonstrates why compilation or an LLM judge cannot be the sole semantic-fidelity test.

### 4.7 Proof-producing solver and CAS plane

#### SAT

- CaDiCaL and Kissat as high-performance search engines;
- SAT Competition format adapter;
- SAT models independently checked;
- UNSAT proofs in LRAT/LPR/GRAT/VeriPB-compatible forms;
- independent proof checker required for exact admission.

#### PB

- VeriPB/CakePB-compatible proof logging where supported;
- PBLean for formal replay when feasible;
- no UNSAT authority from solver status alone.

#### SMT

- cvc5 as the primary open SMT integration;
- model validation for SAT;
- independently checked proof artifacts where the logic/format supports them;
- unknown/unsupported logic remains `UNKNOWN`, not failure or success.

#### CAS and discrete mathematics

- SageMath umbrella adapter;
- GAP for groups/representation computations;
- Singular for polynomial ideals/Groebner operations;
- FLINT/Arb/PARI for exact and certified arithmetic;
- nauty/Traces or bliss for canonicalization;
- GUDHI/Ripser for scoped topology, with exact claim replay where possible.

#### Optimization

- HiGHS primary LP/MIP engine;
- SCIP secondary CIP/MIP/MINLP and decomposition engine;
- MIP models, incumbents, objective values and bounds independently rechecked;
- explicit distinction among feasible incumbent, proved bound, optimality proof, timeout and unknown.

### 4.8 Distributed execution and shared verified memory

Add:

- durable immutable task queue;
- worker capability and environment receipts;
- resumable proof/search checkpoints;
- shared verified-subgoal cache;
- duplicate/subsumption detection;
- exact cost and resource aggregation;
- deterministic/replayable scheduling where claimed;
- no authority from worker self-report;
- quarantine on version, source, model or statement mismatch.

### 4.9 Controlled evolution

Only after the verifier, benchmark statements, source identity and contamination controls are immutable, consider:

- A-Evolve;
- ShinkaEvolve;
- SkyDiscover/OpenEvolve-style program evolution;
- custom Foundry evolutionary mechanisms.

Permitted mutation targets:

- proof prompts;
- retrieval policy;
- decomposition/blueprint policy;
- tactic ordering;
- restart/branching/search parameters;
- solver routing;
- canonicalization and preprocessing;
- portfolio allocation.

Forbidden mutation targets:

- theorem/benchmark statement;
- exact checker;
- Comparator;
- authority transition rules;
- hidden holdout/evaluator;
- contamination firewall;
- scientific-state semantics;
- complete-cost accounting.

---

## 5. Build / wrap / reference decisions

| System | Recommended use | Initial disposition | Main risk |
| --- | --- | --- | --- |
| Lean 4 + Mathlib | formal kernel/library | DIRECT DEPENDENCY, exact pin | version churn and TCB identity |
| Pantograph / PyPantograph | canonical stateful Lean API | ADAPT / WRAP | Lean-version compatibility |
| Lean Eval Comparator + lean4export + landrun | independent acceptance boundary | DIRECT REUSE / ADAPT | trusted dependency pinning |
| LeanDojo-v2 | tracing, theorem database, prover abstractions | ADAPT | large GPU/training dependency surface |
| LeanSearch-v2 | embedding/reranker/global premise retrieval | ADAPT; rebuild index at Foundry Mathlib pin | two-GPU serving and corpus-version mismatch |
| BFS-Prover-V2 | planner/subgoal cache/search architecture | ADAPT / REFERENCE | model and Lean-version requirements |
| ax-prover-base | minimal iterative proving loop | REFERENCE or isolated service | AGPL-3.0 and external-model dependence |
| AutoformBot | autoformalization orchestration | ADAPT | semantic fidelity and model-cost dependence |
| ATLAS | corpus, dependency/test source | DATA / BENCHMARK / REFERENCE | machine-generated quality and licence/source granularity |
| ProofNet-Verified | theorem/autoformalization benchmark and error taxonomy | BENCHMARK | benchmark contamination after use |
| CaDiCaL/Kissat | SAT search | WRAP | proof-generation configuration and checker compatibility |
| cvc5 | SMT | WRAP | proof/model support varies by logic |
| VeriPB/CakePB/PBLean | PB proof checking | WRAP / CHECKER | proof-format coverage |
| SageMath/GAP/Singular/FLINT | mathematical computation | SERVICE/CLI ADAPTERS | certificate availability and dependency size |
| HiGHS/SCIP | optimization | WRAP | numerical tolerance and independent optimality verification |
| A-Evolve/ShinkaEvolve | later controlled improvement | REFERENCE then ADAPT | benchmark overfitting and mutation of trusted surfaces |

Before adoption, freeze the exact commit, licence, dependency lock, build receipt and security advisories. “Open source” is not a sufficient integration decision.

---

## 6. Supernova test methodology for the general base mechanism

The expansion must be evaluated as a sequence of **causal and authority-preserving mechanisms**, not as one aggregate score.

### 6.1 Layer 0 — source and trust qualification

For every component:

- exact source commit and release;
- licence and reuse decision;
- dependency tree and lock;
- reproducible build/container;
- binary/source identity;
- known advisories;
- smoke tests;
- malformed-input tests;
- mutation/fuzz tests;
- timeout/memory/process-tree tests;
- result-schema and replay tests;
- negative authority tests proving that search output cannot self-admit.

This evidence is `TRAIN_TUNING` or engineering qualification only.

### 6.2 Layer 1 — backend conformance

Create small exact tasks for every adapter and compare against independently computed or kernel-checked answers.

Examples:

- Lean proof accepted/rejected under statement, axiom and import mutations;
- premise visibility errors;
- SAT model mutation and UNSAT proof mutation;
- SMT model mutation;
- PB proof mutation;
- MIP incumbent/objective/bound perturbation;
- CAS result substitution into the original equations;
- graph canonicalization equivalence and non-equivalence fixtures;
- retrieval corpus/version mismatch;
- autoformalization missing-premise and strengthened/weakened-statement fixtures.

Required outcome types:

```text
PASS
FAIL
UNKNOWN
NOT_APPLICABLE
ABSTAINED
TIMEOUT
MEMOUT
INFRASTRUCTURE_FAILURE
INVALID_CERTIFICATE
STATEMENT_MISMATCH
```

No category may be silently collapsed into another.

### 6.3 H0/H1 exact failure fixtures

Use the queued fixtures as general-base falsifiers:

- `PAIR` — interaction hidden by marginal evaluations;
- `XOR` — zero individual effect, positive joint effect;
- `ORDER` — noncommuting operations;
- `ENABLE` — one product changes the legal action set;
- `SEPARATOR` — correct decomposition depends on an information boundary;
- `MEMORY` — controller state is necessary;
- `COMMUTE` — invalid reordering changes semantics;
- `RESOURCE` — hidden coupling or double spending;
- `HIDDEN_CONTROLLER` — observed action insufficient to recover policy state;
- `INTERLEAVE` — atomic option representation loses useful interleaving.

Add formal-math-specific fixtures:

- `PREMISE_SCOPE` — retrieved theorem exists but is not imported/accessible;
- `STATEMENT_WEAKEN` — candidate proof proves a weaker theorem;
- `STATEMENT_STRENGTHEN` — formalization adds an unjustified premise;
- `AXIOM_ESCAPE` — proof compiles using forbidden axiom/escape;
- `VERSION_DRIFT` — proof works under a different Mathlib revision only;
- `PROOF_CACHE_STALE` — cached proof invalid after dependency update;
- `RETRIEVAL_LEAK` — answer/proof text contaminates retrieval;
- `MODEL_ONLY_UNSAT` — solver says UNSAT without a replayable proof;
- `NUMERIC_FALSE_CERT` — numerical incumbent is feasible-looking but violates exact constraints;
- `COMMON_CHECKER_BUG` — two checks share the same faulty parser/TCB.

### 6.4 E1 — clean route/schedule truth

`MF-E1-CLEAN-ROUTE-TRUTH` should be the first system-level calibration suite after transport qualification.

For a hidden multi-domain task matrix, measure at equal complete cost:

- `BASE` — current Foundry 3.1.1;
- each single backend/route;
- fixed schedule (`SBS`);
- single-route virtual best (`VBS`, diagnostic only);
- current `AUTO` routing;
- formal-runtime + retrieval variants;
- planner/search variants;
- `ORACLE_SCHEDULE` where admissible;
- random route and no-change controls.

Record:

- exact task eligibility for each route;
- available/unavailable backend status;
- route startup/build/index cost;
- inference/probe/execution/verification/fidelity cost;
- verified result;
- zero/unknown/abstention/timeout counts;
- statement fidelity;
- route regret and schedule regret;
- family/domain heterogeneity;
- complete-cost-normalized verified utility.

E1 is `CALIBRATION`, never G1/G8 promotion evidence.

### 6.5 G1 — fresh prospective one-generation capability

After E1 freezes the candidate mechanism, use a disjoint private `G1_PROSPECTIVE` pool:

- same untouched parent state;
- parent versus candidate;
- frozen route/controller/model/toolchain;
- matched `C_complete`;
- independent verifier;
- no tuning after outcomes;
- confidence interval, MDE, achieved power;
- preregistered primary metric and failure interpretation.

Passing G1 means one-generation capability improvement, not cumulative verified knowledge benefit and not improver-of-improver.

### 6.6 C1 — verified-product closure

Test whether an admitted proof/certificate/product can be reused by later execution without semantic or authority drift.

Arms:

- product unavailable;
- product available but use prohibited;
- product available and legal reuse enabled;
- placebo product with matched metadata/cost;
- invalid/stale product negative control.

Measure enabled legal actions, direct value, later verified success, verification/fidelity/revalidation cost, and causal use trace.

### 6.7 SN-RXN and DR03

After C1 exists, runtime operations emit typed `ReactionRecord`s. Then test:

- product causes new operation availability;
- product changes route ranking only;
- product changes execution outcome;
- interaction among multiple products;
- order/interleaving effects;
- dynamic sequential-regime effects versus static factorial effects;
- predictive labels versus causal estimands.

No reaction value should be inferred from Method Atlas labels alone.

### 6.8 E3 — mechanism controls

Compare the proposed selector/planner against:

- no-change;
- random valid mechanism;
- fixed strong schedule;
- state-conditioned heuristic;
- myopic value-of-computation;
- exact tiny-world oracle where available.

All arms use the same information filtration and complete-cost envelope. Learned policy uplift without verified outcome uplift is not success.

### 6.9 C2 transfer, G8, and E5B

- **C2:** freeze the mechanism and test on unrelated operators/domains.
- **G8:** disjoint fresh multi-step cascade pool; strongest simpler controller as comparator.
- **E5B:** same untouched start, matched complete R&D budget, separate `F` formalizer/foundry mechanism, `M` memory, and `I` improver policy; causal estimand is improvement of the improver, not merely better final output.

---

## 7. Benchmark programme

Public benchmarks supply external comparability and failure diversity. They do not automatically satisfy Supernova freshness, because their items may be in model training data. Public benchmark evidence belongs in `TRAIN_TUNING`, `CALIBRATION`, or a separately declared external-credibility lane unless a contamination-safe prospective contract exists.

### 7.1 Formal theorem proving

| Benchmark | Use | Key metric / control |
| --- | --- | --- |
| **Lean Eval** | primary external acceptance benchmark | Comparator acceptance, exact statement identity, axiom policy, complete cost |
| **miniF2F Lean 4** | historical continuity and fast regression | verified solve rate under fixed sample/token budget; report modern corrected fork/version |
| **PutnamBench** | undergraduate competition/generalization | verified problems solved of 672; contamination statement; same Lean/Mathlib pin |
| **FATE-M/H/X** | graded frontier algebra | per-tier verified solve rate and abstention; retrieval ablation |
| **ProofNet-Verified** | undergraduate theorem proving + fidelity | 367 verified statements; use audited set only; comparator acceptance |
| **CombiBench** | combinatorial reasoning | 100-problem verified solve rate; particularly relevant to Foundry's combinatorial methods |
| **MA-ProofBench** | analysis and graduate mathematics | Level I/II separately; 100 undergraduate + 100 PhD problems |
| **LeanCat / category benchmarks** | advanced library reasoning | only after exact repo/toolchain preflight |
| **Formal Conjectures / research sets** | research-level formalization | `RESEARCH_FROZEN`; no use until exact contract and legal corpus are frozen |

Do not aggregate all theorem sets into one percentage. Report domain and difficulty strata.

### 7.2 Premise and library retrieval

| Benchmark | Evaluation |
| --- | --- |
| LeanSearch-v2 **MathlibQR** | Recall/MRR/nDCG on full 946 rows and fair 810-row/171-declaration subset |
| LeanSearch-v2 **MathlibMPR** | exact relevant premise-group recall; 69 theorems |
| **MathlibMPR-Prop** | retrieval-to-proof uplift on 50-problem proposition subset |
| **FATE-H retrieval** | proof success with standard vs reasoning retrieval |
| dependency-held-out Mathlib declarations | corpus/version-aware retrieval on new declarations |
| Foundry verified-proof memory holdout | improvement from legal prior proof memory versus no-memory and placebo-memory arms |

Required ablations:

```text
no retrieval
native/type search only
lexical only
embedding only
embedding + reranker
graph expansion
iterative reasoning retrieval
verified proof memory
full cascade
```

### 7.3 Autoformalization and statement fidelity

| Benchmark | Use |
| --- | --- |
| **ProofNet-Verified** informal/formal pairs | primary audited semantic-fidelity set |
| **ATLAS** held-out textbook statements | scale and dependency management; books held out by source |
| AutoformBot extraction fixtures | target extraction, deduplication, dependency DAG and repair |
| Herald/backtranslation test sets | translation/backtranslation consistency |
| generated adversarial statement pairs | missing premise, swapped quantifier, weakened conclusion, extra case, wrong scope |

Metrics must include:

- compile rate;
- exact statement-match/equivalence where decidable;
- bidirectional implication support;
- missing/extra premise rate;
- counterexample rate;
- proof success after formalization;
- human/independent semantic adjudication;
- abstention and ambiguity recognition;
- complete cost.

### 7.4 SAT, PB, and SMT

- **SAT Competition 2026** instances and deterministic selection artifacts;
- Main/UNSAT tracks with required proof output;
- verified checker pipelines such as LRAT/LPR, GRAT, or VeriPB/CakePB;
- **SMT-COMP 2026** single-query and model-validation tracks;
- logic-specific result reporting rather than one blended score;
- Foundry's own exact small-instance oracle matrix for nonvacuity and checker mutation.

Metrics:

- PAR-2 or competition-compatible score;
- solved SAT/UNSAT;
- independently validated models/proofs;
- invalid proof/model rate;
- timeout, memout, abstain and unknown separately;
- checker and proof-generation overhead.

### 7.5 Optimization

- **MIPLIB 2017** official 240-instance benchmark set;
- current benchmark/easy/hard status and solufile version frozen at experiment start;
- official solution checker;
- MiniZinc Challenge or domain-specific CP set after adapter preflight;
- Foundry small exact optimization oracle set.

Metrics:

- feasible incumbent rate;
- exact feasibility replay;
- primal/dual gap;
- proved optimality;
- time-to-first incumbent;
- bound progress versus complete cost;
- invalid numerical result rate;
- route selection regret.

### 7.6 General mathematical discovery and program evolution

- **SkyDiscover** mathematical optimization suite;
- Frontier-CS algorithmic tasks where appropriate;
- **AlphaResearchComp** research tasks;
- public AlphaEvolve mathematical problem repository;
- newly generated/private exact-construction tasks;
- withheld known-answer combinatorial designs;
- Foundry H-668 diagnostics only in `TRAIN_TUNING`/research-specific lanes, never as sole general-base evidence.

Measure exact verified objective/value, code or algorithm validity, transfer, compute, lineage and diversity. A better heuristic score without exact verification is not a mathematical success.

---

## 8. Benchmark governance

### 8.1 Pool assignment

Use the existing six-pool policy:

| Pool | Permitted use |
| --- | --- |
| `TRAIN_TUNING` | repeated development, debugging and learning; never promotion |
| `CALIBRATION` | thresholds, variance, E1 route truth, component qualification; never G1/G8/Goal2 |
| `G1_PROSPECTIVE` | sealed one-generation parent/candidate test |
| `G8_CASCADE` | sealed final Goal-1 cascade |
| `GOAL2_E5B` | sealed same-start improver-of-improver |
| `RESEARCH_FROZEN` | future capability lane after exact contract admission |

Any task touched during development or calibration is permanently ineligible for promotion.

### 8.2 Benchmark manifest

Every run manifest must bind:

- benchmark repository/commit;
- item set and split hash;
- statement/source identity;
- model/tool/runtime/environment;
- route/controller/retriever/prover;
- allowed imports/library corpus;
- seed, samples, repeats;
- time, token, node, memory and complete-cost budget;
- evaluator/checker/fidelity systems;
- contamination exclusions;
- cache/context/retention policy;
- primary estimand and stopping rule;
- output and receipt schema.

### 8.3 Contamination handling

For public theorem benchmarks:

- do not claim freshness solely because proofs are hidden;
- inspect model cards/training disclosures where possible;
- use item-level contamination probes;
- report memorization indicators;
- reserve private paraphrase/new-formalization/new-theorem pools for prospective claims;
- never move public development cases into G1/G8 after use.

### 8.4 Complete cost

Use the frozen formula:

```text
C_complete = instrumentation + data + training_amortized + inference
           + probe + execution + verification + fidelity + revalidation
           + failure/recovery + metalevel_selection
```

Formal proving comparisons must include Mathlib build/cache/index costs under a declared amortization rule. Retrieval-index construction, model serving and proof checking are not free.

---

## 9. Metrics and scorecard

### 9.1 Authority and correctness

- exact verification pass rate;
- invalid candidate rejection rate;
- statement identity/fidelity pass rate;
- prohibited axiom/escape detection;
- proof/model/certificate replay success;
- version/source mismatch rejection;
- stale cache/product rejection.

### 9.2 Capability

- verified solve rate;
- domain-stratified verified solve rate;
- verified progress before final solution;
- theorem/library coverage;
- premise-set recall;
- route applicability and usable intervention coverage;
- abstention versus forced-answer rate.

### 9.3 Efficiency

- complete cost per verified solution;
- verified utility per CPU/GPU hour;
- time/token/sample/node distributions;
- proof-checking and fidelity overhead;
- route and schedule regret;
- parallel efficiency and duplicate work.

### 9.4 Reliability

- calibration/coverage where probabilistic claims are made;
- any-time versus fixed-sample guarantees kept separate;
- variance across seeds/problems/domains;
- timeout/memout/infrastructure incidents;
- recovery/replay success;
- common-mode checker dependencies.

### 9.5 Learning and transfer

- development uplift;
- protected-holdout uplift;
- unrelated-domain transfer;
- regression count;
- overfitting gap;
- reuse benefit of verified products;
- reaction-value and selector-value causal effects;
- cumulative improvement under matched complete cost.

No single composite score should determine promotion unless its weighting was frozen before outcomes and all hard correctness/authority gates pass independently.

---

## 10. Implementation and qualification order

### Phase 0 — verifier substrate

1. pin Lean/Mathlib;
2. integrate Comparator, lean4export and sandbox;
3. implement statement/axiom/source identity receipts;
4. build positive, negative, mutation and escape tests;
5. qualify clean package and replay.

**Gate:** a hand-written candidate proof can be accepted/rejected independently and reproducibly.

### Phase 1 — formal runtime

1. Pantograph adapter;
2. process pool and state checkpointing;
3. task/result schemas;
4. whole-file fallback/recovery;
5. runtime version and resource receipts.

**Gate:** exact goal-state interaction plus independent final admission.

### Phase 2 — library/retrieval

1. trace pinned Mathlib;
2. native/type/lexical search;
3. LeanSearch-v2 adapter/index rebuilt at exact corpus pin;
4. reranking and graph expansion;
5. verified proof-memory store;
6. MathlibQR/MathlibMPR/FATE-H ablations.

**Gate:** material retrieval-to-proof uplift on held-out calibration tasks without visibility violations.

### Phase 3 — prover portfolio

1. whole-proof backend;
2. stepwise best-first backend;
3. planner/subgoal cache;
4. repair/replanning;
5. common budget/receipt adapter;
6. E1 route/schedule matrix.

**Gate:** non-dominated route or schedule under matched complete cost.

### Phase 4 — external benchmark qualification

Lean Eval first, then miniF2F continuity, PutnamBench, ProofNet-Verified, CombiBench, FATE and MA-ProofBench. Publish exact run manifests and checker receipts.

**Gate:** reproducible externally recognizable result; no claim of prospective freshness yet.

### Phase 5 — autoformalization

1. AutoformBot extraction/orchestration adapter;
2. notation/dependency resolution;
3. candidate generation/repair;
4. semantic-fidelity Court;
5. ProofNet-V and held-out ATLAS evaluation.

**Gate:** faithful-formalization metric, not compilation rate alone.

### Phase 6 — solver/CAS/optimization adapters

Integrate proof/model-producing SAT/SMT/PB and replayable CAS/optimization routes. Run competition/library benchmarks and exact negative controls.

### Phase 7 — verified-product causal closure

Implement C1, SN-RXN and DR03 in the frozen Revision-5 order:

```text
C1 -> SN-RXN -> DR03 -> E3 -> SELECT -> IGNITION -> G8
```

### Phase 8 — controlled evolution

Add A-Evolve/ShinkaEvolve only after the full verification and protected benchmark substrate is immutable. Run no-change/random/human-designed controls and rollback on any authority or protected-holdout regression.

---

## 11. Promotion gates

A capability is not promoted merely because an adapter exists.

### Formal proving gate

- exact pinned runtime;
- statement identity;
- forbidden escape tests;
- independent comparator acceptance;
- clean replay;
- public benchmark evidence;
- matched-cost comparison with a reproducible open baseline.

### Retrieval gate

- legal/import-visible corpus filtering;
- premise metrics;
- proof uplift;
- corpus/version invalidation;
- no answer leakage;
- ablation proving the retrieval component contributes unique value.

### Autoformalization gate

- compile rate;
- semantic-equivalence or adjudication;
- missing/extra premise and quantifier checks;
- counterexample attempts;
- proof attempt;
- human/independent review sample;
- ambiguity abstention.

### Solver gate

- model/proof/certificate available where claimed;
- independent replay;
- invalid-certificate mutation suite;
- exact result semantics for timeout/unknown;
- external benchmark and Foundry exact-oracle performance.

### Evolution gate

- immutable verifier and benchmark;
- lineage and rollback;
- protected holdout unseen by evolver;
- no-change/random/human control;
- complete-cost closure;
- transfer after freeze;
- no degradation of authority, calibration, abstention or intervention coverage.

---

## 12. Red-team obligations

Before any fresh or promotable use, attack:

- proof escapes (`sorry`, unsafe axioms, altered challenge, extra imports);
- statement weakening/strengthening;
- retrieval from forbidden or future declarations;
- hidden proof-answer leakage;
- corpus/toolchain version drift;
- stale proof memory;
- model identity substitution;
- service-side unobservable changes;
- certificate parser differential bugs;
- same-TCB checks mislabelled independent;
- solver numerical tolerance exploits;
- incomplete cost accounting;
- benchmark item relabelling;
- test-set adaptation through logs;
- near-total abstention presented as calibration;
- portfolio advantage caused only by more compute;
- route unavailability counted as mathematical failure;
- cached public proof memorization;
- evolution modifying trusted surfaces;
- product-use claims without causal use traces;
- interaction/order effects hidden by additive analysis.

The failure result itself becomes a typed engineering or scientific observation only when its authority and scope are established. Missing receipts remain missingness/liveness incidents.

---

## 13. Repository actions and freeze-safe next steps

### Actions safe during the current freeze

1. add this derived report;
2. correct the derived capability matrix from Candidate 7 to current Math Foundry 3.1.1 staging status;
3. create non-admissible adapter prototypes and exact H0 fixtures outside active scheduled prompts;
4. preflight open-source licences, commits, build environments and checker pins;
5. draft schemas and test harnesses;
6. cost the first five operators/routes with OCN-0A once source/runtime access is exact;
7. prepare private E1 task-matrix design without consuming outcomes;
8. finish the Gen8 staging-to-countable restart and two-clean-cohort requirement first.

### Actions not authorized now

- Protocol 2.6;
- Revision 5 activation;
- mutation of the current Gen8 staging state by this report;
- fresh G1/G8/Goal2 consumption;
- repurposing active scheduled lanes;
- calling public benchmark improvement a Supernova causal success;
- granting authority to an external model, retriever or solver;
- treating engineering qualification as scientific credit.

### Single highest-priority capability build

After the current transport/countable restart closes, the highest-priority non-admissible software tranche is:

> **Pinned Lean/Pantograph execution plus Comparator/lean4export/sandbox admission, with a minimal theorem task and exact replay receipt.**

It dominates starting with a large prover model because every later theorem-proving, retrieval, autoformalization and evolution experiment depends on a trustworthy formal runtime and acceptance boundary.

---

## 14. Source/repository ledger

Primary repositories and benchmark sources to preflight at exact commits:

- Lean 4: `https://github.com/leanprover/lean4`
- Mathlib: `https://github.com/leanprover-community/mathlib4`
- Pantograph: `https://github.com/leanprover/Pantograph`
- PyPantograph: `https://github.com/stanford-centaur/PyPantograph`
- LeanDojo-v2: `https://github.com/lean-dojo/LeanDojo-v2`
- LeanSearch-v2: `https://github.com/frenzymath/LeanSearch-v2`
- Lean Eval: `https://github.com/leanprover/lean-eval`
- Comparator: `https://github.com/leanprover/comparator`
- BFS-Prover-V2: `https://github.com/ByteDance-Seed/BFS-Prover-V2`
- ax-prover-base: `https://github.com/Axiomatic-AI/ax-prover-base`
- Goedel-Prover-V2: `https://github.com/Goedel-LM/Goedel-Prover-V2`
- AutoformBot: `https://github.com/facebookresearch/autoform-bot`
- ATLAS: `https://github.com/facebookresearch/atlas-lean`
- ProofNet-Verified: `https://github.com/marcusm117/ProofNet-Verified`
- PutnamBench: `https://github.com/trishullab/PutnamBench`
- CombiBench: `https://github.com/MoonshotAI/CombiBench`
- MA-ProofBench: `https://github.com/OpenBMB/MA-ProofBench`
- miniF2F Lean 4: `https://github.com/google-deepmind/miniF2F`
- CaDiCaL: `https://github.com/arminbiere/cadical`
- Kissat: `https://github.com/arminbiere/kissat`
- cvc5: `https://github.com/cvc5/cvc5`
- VeriPB: `https://gitlab.com/MIAOresearch/software/VeriPB`
- HiGHS: `https://github.com/ERGO-Code/HiGHS`
- SCIP: `https://github.com/scipopt/scip`
- SageMath: `https://github.com/sagemath/sage`
- GAP: `https://github.com/gap-system/gap`
- Singular: `https://github.com/Singular/Singular`
- FLINT: `https://github.com/flintlib/flint`
- A-Evolve: `https://github.com/A-EVO-Lab/a-evolve`
- ShinkaEvolve: `https://github.com/SakanaAI/ShinkaEvolve`
- SkyDiscover: `https://github.com/skydiscover-ai/skydiscover`
- SAT Competition 2026: `https://satcompetition.github.io/2026/`
- SMT-COMP 2026: `https://smt-comp.github.io/2026/`
- MIPLIB 2017: `https://miplib.zib.de/`

Every final integration decision must replace these moving URLs with exact commits, tags, hashes and licence receipts.

---

## 15. Final status

Supernova has already updated from Candidate 7 to **qualified Math Foundry 3.1.1**, but only through a **non-countable zero-credit staging generation**. The programme itself remains **Protocol 2.5 / Revision 4**. The next legal operational transition is a repaired countable replay cohort under the frozen 3.1.1 substrate—not fresh theorem-proving work.

The general-base mechanism remains strongest in execution integrity, scoped exact methods, authority separation and controlled experiment design. It remains behind the leading open formal-mathematics ecosystem in full theorem proving, premise retrieval, autoformalization, large solver integration, distributed proof search and externally recognized benchmarks. The plan above closes those gaps without weakening Supernova's core rule: exact execution and independent verification precede scientific or control authority.
