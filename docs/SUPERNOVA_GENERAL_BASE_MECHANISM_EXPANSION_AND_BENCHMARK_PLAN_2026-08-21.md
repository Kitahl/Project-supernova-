# Project Supernova — General Base Mechanism Expansion, Qualification, and Benchmark Plan

**Date:** 2026-08-21  
**Status:** NON-AUTHORITATIVE DERIVED ENGINEERING / RESEARCH PLAN  
**Repository base:** accepted `main` commit `8ab41946fa7a07d267aada67df8f9b4c09c70bf8`  
**Protocol:** 2.5 — FROZEN  
**Specification:** Revision 4 — FROZEN  
**Canonical authority:** `main:state/CURRENT.json`, frozen Revision 4, exact control/assignment/experiment manifests  

This report does **not** modify Protocol 2.5, Revision 4, `plan/PLAN.json`, `state/CURRENT.json`, the active cohort, calibration credit, fresh-evidence eligibility, benchmark pools, Tribunal scientific state, or any frozen control. It is a derived capability and qualification plan only.

---

## 1. Verified current state

Supernova itself remains **Protocol 2.5 / Revision 4**. No Protocol 2.6 or Revision 5 is authorized until two consecutive clean countable Protocol-2.5 cohorts complete.

The canonical software substrate has been updated to **qualified Math Foundry 3.1.1**:

- source archive SHA-256: `57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f`;
- software qualification: 28/28 PASS;
- runtime default wall clock: `NONE`;
- packaging integrity: PASS;
- exact mathematical authority still requires independent exact checking.

The live programme is now:

- generation: **9**;
- cohort: `CAL-BR-009-v25-b53ab205`;
- mode: `GITHUB_BRANCH_CALIBRATION`;
- countable: **true**;
- calibration streak: **0**;
- fresh evidence: **disabled**;
- blocker: `O-T0-TWO_CLEAN_COUNTABLE_V25_COHORTS`.

Gen9 is the first repaired countable replay-only cohort after invalidated zero-credit Gen7 and zero-credit Gen8 Math Foundry 3.1.1 staging. Cohort credit requires the complete `12 workers -> MM06 -> MF06 -> BIL00` path. The current state is therefore not a fresh or scientific result.

Mastermind remains `4.4.10-execution-closure-candidate.1` with `PRE_REVIEW_ONLY` authority. The runtime state identity is unchanged.

---

## 2. Executive decision

Math Foundry 3.1.1 materially improved scoped method execution, routing, exact replay, local SAT, large-state serialization, source qualification and no-default-wall-clock execution. The next major release should not merely add more method labels.

The largest remaining gap is a production **formal-mathematics and proof-producing computation plane**:

```text
immutable toolchain identity
    -> Lean/formal runtime
    -> independent verification court
    -> versioned theorem/library corpus
    -> premise retrieval
    -> heterogeneous prover portfolio
    -> faithful autoformalization
    -> proof-producing SAT/SMT/PB/CAS/optimization adapters
    -> verified-product closure
    -> runtime reactions and causal mechanism tests
    -> controlled evolution only after verifier freeze
```

Recommended future software target: **Math Foundry 3.2 formal-mathematics plane**. It should first be built and qualified in a separate non-admissible engineering environment. Any later Supernova runtime transition must use the same exact source-bound, zero-credit staging and countable-restart discipline used for 3.1.1.

---

## 3. What should be added

| Capability | Current boundary | Addition required |
| --- | --- | --- |
| Formal theorem proving | scoped proof checking; not Mathlib-scale proving | pinned Lean/Mathlib, proof-state API, whole-proof and stepwise search, decomposition, repair, Comparator admission |
| Independent formal verification | authority model exists; full Lean acceptance plane absent | Comparator, `lean4export`, sandbox, statement identity, axiom policy, optional differently structured replay |
| Premise/library retrieval | no production Mathlib-scale retrieval | versioned declaration corpus, legal/import filtering, native/type/lexical/semantic/graph retrieval, proof-memory retrieval |
| Autoformalization | not qualified | extraction, notation/dependency resolution, Lean generation/repair, semantic-fidelity court, counterexample checks, proof attempt |
| Prover planning | method routing exists | proof DAG/blueprint, shared subgoal cache, best-first/beam/tree search, failure-driven replanning |
| SAT/PB/SMT | scoped/local exact paths | CaDiCaL/Kissat/cvc5/VeriPB adapters, models/proofs, independent certificate replay, competition formats |
| CAS/groups/topology | scoped implementations | SageMath, GAP, Singular, FLINT/PARI, nauty/Traces, GUDHI/Ripser adapters with replay/certification |
| Optimization | scoped DP/B&B/LP/SDP | HiGHS/SCIP adapters, exact feasibility/objective replay, incumbent/bound/optimality receipts, MIPLIB qualification |
| Distributed execution | process isolation exists | durable queue, heterogeneous worker receipts, resumable search, shared verified subgoal cache, exact cost aggregation |
| External credibility | strong internal qualification | public pinned benchmark runs, accepted verifier outputs, matched-budget baselines and public manifests |
| Controlled self-improvement | routing loop exists | verifier-frozen evolution of retrieval/search/decomposition with protected holdouts, rollback and lineage |

### 3.1 Formal runtime and Court

Use **Pantograph** as the primary stateful machine-to-Lean interface. Wrap it behind Foundry-owned contracts for environment startup, module loading, goal opening, tactic/term execution, branching, checkpointing, environment inspection and candidate export.

Use the **Lean Eval Comparator** architecture as the formal-admission boundary:

```text
trusted challenge statement
  + solver-owned submission
  -> isolated build
  -> Lean kernel
  -> lean4export
  -> comparator
  -> statement / import / axiom checks
  -> optional independent replay
  -> FormalVerificationReceipt
```

Required formal statuses:

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

`COMPILES` is never sufficient for exact proof admission.

### 3.2 Retrieval and verified library memory

Build a corpus keyed by repository, commit, Lean/Mathlib versions, fully qualified declaration name, normalized type hash, namespace/import scope, dependency edges, informal description, lexical tokens, embedding, successful proof usage, authority and invalidation epoch.

Recommended cascade:

```text
accessible-declaration filter
  -> Mathlib native/type/name search
  -> lexical retrieval
  -> LeanSearch-v2 embedding retrieval
  -> neural reranking
  -> dependency-graph expansion
  -> iterative global premise reasoning
  -> verified Foundry proof-memory retrieval
```

A vector database alone is not a complete retrieval system. A theorem that exists but is not imported or visible is not a legal premise.

### 3.3 Heterogeneous prover portfolio

Define backend-neutral `ProverRequest`, `ProverCandidate`, `ProverSearchTrace`, `SubgoalArtifact`, `ProofMemoryRecord` and `ProverOutcomeReceipt` schemas.

Support at least:

1. whole-proof generation;
2. stepwise best-first/beam/tree search;
3. planner/decomposition plus parallel subgoal proving.

Reuse or adapt:

- LeanDojo-v2 for tracing, theorem databases and prover abstractions;
- BFS-Prover-V2 for planner, shared subgoal cache and best-first search;
- ax-prover-base as a reference or isolated service because AGPL may constrain vendoring;
- Goedel/DeepSeek/Seed/Kimina/OProver/Pythagoras-style models as replaceable `MODEL_ONLY` proposal engines;
- APOLLO-style compiler-feedback repair.

No model receives mathematical authority.

### 3.4 Autoformalization

Use AutoformBot as the first orchestration scaffold and ATLAS as a large corpus/reference. Add a semantic Court:

```text
source document
  -> statement/context extraction
  -> notation and object resolution
  -> dependency retrieval
  -> candidate Lean statement
  -> compilation/repair
  -> backtranslation
  -> bidirectional/symbolic equivalence attempts
  -> missing/extra premise and scope audit
  -> counterexample/refutation search
  -> proof attempt
  -> independent semantic review
  -> FaithfulFormalizationReceipt
```

Required states include `SEMANTICALLY_UNVERIFIED`, `DEPENDENCY_AUDITED`, `COUNTEREXAMPLE_REJECTED`, `BIDIRECTIONALLY_SUPPORTED`, and `FAITHFUL_FORMALIZATION_ADMITTED`. ProofNet-Verified demonstrates why compilation or an LLM judge cannot be the sole faithfulness test.

### 3.5 Proof-producing solver/CAS plane

- **SAT:** CaDiCaL/Kissat; SAT models checked; UNSAT requires LRAT/LPR/GRAT/VeriPB-compatible proof and independent checking.
- **PB:** VeriPB/CakePB and PBLean where feasible; no authority from solver status alone.
- **SMT:** cvc5; independently validate models and proofs where supported; unsupported logic remains `UNKNOWN`.
- **CAS:** SageMath, GAP, Singular, FLINT/Arb/PARI, nauty/Traces, GUDHI/Ripser; substitute results back into original obligations or replay certificates.
- **Optimization:** HiGHS primary, SCIP secondary; independently check feasibility, objective, primal/dual bounds and optimality claims.

### 3.6 Controlled evolution

A-Evolve, ShinkaEvolve or related mechanisms may eventually mutate prompts, retrieval policies, decomposition, tactic order, branching, restarts and solver allocation. They may never mutate theorem statements, exact checkers, Comparator, authority rules, protected evaluators, contamination firewalls, Scientific State semantics or complete-cost accounting.

---

## 4. How the expansion is tested using Supernova methodology

The capability programme is tested as a sequence of causal, authority-preserving mechanisms rather than one aggregate score.

### 4.1 Source/trust qualification

For each component record exact commit, licence, dependency lock, container/build receipt, binary/source hash, advisories and tests. Run smoke, malformed-input, mutation, fuzz, process-tree, memory, timeout, schema and replay tests. Negative tests must prove that an external output cannot self-admit.

### 4.2 Backend conformance

Use small exact fixtures:

- proof accepted/rejected under statement, import and axiom mutations;
- premise exists but is not visible;
- SAT model mutation and UNSAT proof mutation;
- SMT model mutation;
- PB proof mutation;
- MIP incumbent/objective/bound perturbation;
- CAS result substitution;
- canonicalization equivalence/non-equivalence;
- retrieval index/version mismatch;
- autoformalization with missing premise, swapped quantifier, weakened conclusion and wrong scope.

Required result categories remain distinct: `PASS`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`, `ABSTAINED`, `TIMEOUT`, `MEMOUT`, `INFRASTRUCTURE_FAILURE`, `INVALID_CERTIFICATE`, `STATEMENT_MISMATCH`.

### 4.3 H0/H1 failure fixtures

Retain the queued general fixtures: `PAIR`, `XOR`, `ORDER`, `ENABLE`, `SEPARATOR`, `MEMORY`, `COMMUTE`, `RESOURCE`, `HIDDEN_CONTROLLER`, `INTERLEAVE`.

Add formal-math fixtures:

- `PREMISE_SCOPE`;
- `STATEMENT_WEAKEN`;
- `STATEMENT_STRENGTHEN`;
- `AXIOM_ESCAPE`;
- `VERSION_DRIFT`;
- `PROOF_CACHE_STALE`;
- `RETRIEVAL_LEAK`;
- `MODEL_ONLY_UNSAT`;
- `NUMERIC_FALSE_CERT`;
- `COMMON_CHECKER_BUG`.

### 4.4 E1 clean route/schedule truth

After the active countable-calibration prerequisite closes, `MF-E1-CLEAN-ROUTE-TRUTH` should compare at equal complete cost:

- BASE 3.1.1;
- every single route/backend;
- fixed strong schedule (`SBS`);
- diagnostic virtual best (`VBS`);
- current `AUTO`;
- formal-runtime/retrieval variants;
- planner/search variants;
- `ORACLE_SCHEDULE` where admissible;
- random and no-change controls.

Record eligibility, startup/build/index cost, inference/probe/execution/verification/fidelity/revalidation cost, verified result, zero/unknown/abstention/timeout, statement fidelity, route regret, schedule regret and complete-cost-normalized verified utility. E1 is `CALIBRATION`, never G1/G8 promotion evidence.

### 4.5 G1, C1, SN-RXN, DR03, E3, C2, G8 and E5B

- **G1:** disjoint private fresh one-generation parent/candidate test, same untouched parent, frozen mechanism, matched `C_complete`, independent verifier.
- **C1:** product unavailable / available-but-use-forbidden / legal reuse / placebo / stale-invalid controls; measure causal use and later verified success.
- **SN-RXN:** emit typed runtime reactions from real operations, not Method Atlas inference.
- **DR03:** separate factorial interactions, order/interleaving and dynamic sequential-regime estimands from predictive labels.
- **E3:** compare learned mechanism to no-change, random valid mechanism, fixed strong schedule, state-conditioned heuristic, myopic value-of-computation and tiny-world oracle.
- **C2:** freeze and test unrelated domains/operators.
- **G8:** disjoint fresh cascade against strongest simpler controller.
- **E5B:** same untouched start, matched complete R&D budget, controlled memory and explicit `F/M/I` separation.

Frozen future ordering remains:

```text
C1 -> SN-RXN -> DR03 -> E3 -> SELECT -> IGNITION -> G8
```

This report does not activate that Revision-5 queue.

---

## 5. Benchmarks

Public benchmarks provide external comparability and failure diversity. They are not automatically Supernova-fresh because model training may contain them. Use them in `TRAIN_TUNING`, `CALIBRATION`, or a separately declared external-credibility lane unless a contamination-safe prospective contract exists.

### 5.1 Formal theorem proving

| Benchmark | Role |
| --- | --- |
| **Lean Eval** | primary external acceptance; Comparator result, statement identity, axiom policy and complete cost |
| **miniF2F Lean 4** | historical continuity and fast regression; use a pinned corrected Lean-4 fork |
| **PutnamBench** | undergraduate competition generalization; 672 Lean statements; report contamination risk |
| **FATE-M/H/X** | graded frontier algebra; report each tier separately |
| **ProofNet-Verified** | 367 audited theorem/autoformalization pairs; use Comparator |
| **CombiBench** | 100 combinatorial problems, directly relevant to Foundry combinatorial methods |
| **MA-ProofBench** | 200 analysis problems, 100 undergraduate and 100 PhD-level |
| **LeanCat / advanced library sets** | advanced library reasoning after exact preflight |
| **Formal Conjectures / research sets** | `RESEARCH_FROZEN` only until exact contract admission |

### 5.2 Retrieval

- LeanSearch-v2 `MathlibQR`: full 946 rows and fair 810-row/171-declaration subset;
- `MathlibMPR`: 69 theorems with premise-group ground truth;
- `MathlibMPR-Prop`: 50-problem retrieval-to-proof subset;
- FATE-H standard versus reasoning retrieval;
- dependency-held-out Mathlib declarations;
- Foundry verified-proof-memory holdout.

Ablate: no retrieval, native/type search, lexical, embedding, embedding+reranker, graph expansion, iterative reasoning, verified proof memory, full cascade.

### 5.3 Autoformalization

- ProofNet-Verified informal/formal pairs;
- held-out ATLAS textbooks/statements by source;
- AutoformBot extraction/dependency fixtures;
- Herald/backtranslation sets;
- generated adversarial pairs for missing premise, quantifier swap, weakened/strengthened conclusion and wrong scope.

Report compile rate, faithfulness, bidirectional implication support, missing/extra premise rate, counterexample rate, proof success, ambiguity abstention, independent review and complete cost.

### 5.4 SAT/SMT/PB

- SAT Competition 2026 deterministic benchmark set and proof-checker tracks;
- SMT-COMP 2026 single-query and model-validation tracks;
- Foundry small exact oracle/mutation matrix.

Report PAR-2-compatible score, SAT/UNSAT, validated model/proof, invalid certificate rate, timeout, memout, abstain, unknown and checker overhead separately.

### 5.5 Optimization

- MIPLIB 2017 official 240-instance benchmark set;
- current solufile/status frozen at experiment start;
- official solution checker;
- MiniZinc/domain CP sets after adapter preflight;
- Foundry small exact optimization oracle set.

Report feasible incumbent, exact feasibility replay, gap, proved optimality, time-to-first incumbent, bound progress, invalid result rate and route regret.

### 5.6 Discovery/evolution

- SkyDiscover mathematical tasks and Frontier-CS where appropriate;
- AlphaResearchComp;
- public AlphaEvolve mathematical problem repository;
- newly generated private exact-construction tasks;
- withheld known-answer combinatorial designs.

H-668 diagnostics remain research-specific `TRAIN_TUNING` material and cannot be the sole general-base benchmark.

---

## 6. Benchmark governance and metrics

Use the existing pools without relabelling:

- `TRAIN_TUNING` — repeated development only;
- `CALIBRATION` — thresholds, E1 and component qualification;
- `G1_PROSPECTIVE` — sealed one-generation test;
- `G8_CASCADE` — sealed final Goal-1 cascade;
- `GOAL2_E5B` — sealed same-start improver test;
- `RESEARCH_FROZEN` — future capability lane after exact admission.

Every run manifest binds benchmark commit/split hash, statement identity, model/tool/runtime, route/controller/retriever, permitted imports, seeds/samples, resource budgets, evaluators/checkers, contamination exclusions, cache/context policy, primary estimand and stopping rule.

Complete cost remains:

```text
C_complete = instrumentation + data + training_amortized + inference
           + probe + execution + verification + fidelity + revalidation
           + failure/recovery + metalevel_selection
```

Primary scorecard dimensions:

- exact verification and invalid-candidate rejection;
- statement fidelity and axiom/escape detection;
- verified solve rate by domain/difficulty;
- premise recall and proof uplift;
- abstention/intervention coverage;
- complete cost per verified solution;
- route/schedule regret;
- calibration and variance;
- timeout/memout/infrastructure and replay recovery;
- protected-holdout uplift and unrelated-domain transfer;
- verified-product reuse and causal reaction value.

No single composite score may override hard correctness, authority, fidelity or pool-integrity gates.

---

## 7. Implementation order

1. **Verifier substrate:** pin Lean/Mathlib, Comparator, `lean4export`, sandbox, statement/axiom/source receipts and escape tests.
2. **Formal runtime:** Pantograph adapter, process pool, checkpointing, task/result contracts and clean replay.
3. **Retrieval:** trace pinned Mathlib, native/lexical search, LeanSearch-v2 index at the exact corpus pin, reranking, graph expansion and verified proof memory.
4. **Prover portfolio:** whole proof, step search, planner/subgoal cache, repair/replanning and E1 route matrix.
5. **External qualification:** Lean Eval first, then miniF2F, PutnamBench, ProofNet-V, CombiBench, FATE and MA-ProofBench.
6. **Autoformalization:** AutoformBot adapter plus semantic-fidelity Court and held-out source evaluation.
7. **Solver/CAS/optimization:** proof/model-producing adapters and competition/library benchmarks.
8. **Causal closure:** C1, SN-RXN, DR03, E3, C2/G8.
9. **Controlled evolution:** only after verifier and protected benchmark immutability.

The single highest-priority software tranche is:

> **Pinned Lean/Pantograph execution plus Comparator/lean4export/sandbox admission, with a minimal theorem task and exact replay receipt.**

Starting with a large prover model would be premature because every later proving, retrieval, autoformalization and evolution claim depends on that trust floor.

---

## 8. Freeze-safe repository actions

Allowed as non-admissible engineering/qualification work while Gen9 runs:

- add this derived report and correct stale derived status documentation;
- preflight exact open-source commits, licences, dependency locks and checker pins;
- draft schemas and adapter harnesses;
- build exact H0/H1 fixtures in a separate non-admissible environment;
- design private E1 matrices without consuming outcomes;
- prototype formal runtime/verifier/retrieval outside frozen active assignments.

Not authorized by this report:

- Protocol 2.6 or Revision 5;
- mutation or repurposing of Gen9 control/assignments;
- fresh G1/G8/Goal2 consumption;
- scientific promotion;
- granting authority to an external model/retriever/solver;
- treating public benchmark gains as Supernova causal success;
- treating engineering qualification as calibration or scientific credit.

---

## 9. Source ledger for exact preflight

- Lean 4: `https://github.com/leanprover/lean4`
- Mathlib: `https://github.com/leanprover-community/mathlib4`
- Pantograph: `https://github.com/leanprover/Pantograph`
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

Every integration decision must replace moving URLs with exact commits, hashes, licences and build receipts.

---

## 10. Final status

Supernova has updated from Candidate 7 to **qualified Math Foundry 3.1.1** and opened the first repaired **countable replay cohort**, Gen9. The programme remains **Protocol 2.5 / Revision 4**. Gen9 is not yet a completed clean cohort, the calibration streak remains 0, and fresh scientific execution is disabled.

The general-base mechanism is strongest in execution integrity, scoped exact methods, authority separation and controlled experiment design. It remains behind the leading open formal-mathematics ecosystem in full theorem proving, premise retrieval, autoformalization, large solver integration, distributed proof search and externally recognized benchmark performance. The plan above closes those gaps without weakening the core rule: exact execution and independent verification precede scientific or control authority.
