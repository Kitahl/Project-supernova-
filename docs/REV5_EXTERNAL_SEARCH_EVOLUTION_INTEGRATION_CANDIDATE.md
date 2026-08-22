# Project Supernova Revision 5 Candidate Annex
# External Search / Evolution Engines and Later Provenance Infrastructure

**STATUS:** CANDIDATE ONLY — NON-AUTHORITATIVE  
**CURRENT AUTHORITY:** Revision 4 / Protocol 2.5  
**ACTIVATION:** only after two consecutive clean countable protocol-2.5 cohorts and the guarded Revision-5 authority transition  
**Purpose:** define how Supernova may safely exploit external candidate-search engines without transferring authority, and how later provenance/signing infrastructure may be evaluated in shadow mode.

This annex is subordinate to `docs/PROJECT_SUPERNOVA_REV5_CANDIDATE.md`. It does not modify `plan/PLAN.json`, Protocol 2.5, Revision 4, `state/CURRENT.json`, any active control/assignment/liveness object, calibration credit, fresh-science eligibility, Math Foundry authority, Mastermind authority, Tribunal/Court authority, or GitHub admission authority.

---

## 1. Executive decision

Supernova may investigate external search/evolution engines as **non-authoritative candidate generators**.

The safety target is not:

> the upstream engine has no bugs.

The safety target is:

> even if an upstream engine is buggy, hangs, generates malicious code, evaluates the wrong candidate, mis-scores a candidate, games an evaluator, loses lineage, or falsely claims improvement, it cannot damage or falsely advance Supernova.

The architecture is therefore:

```text
SUPERNOVA
  = authority + experimental control + verification + admission

ERA / OpenEvolve / ShinkaEvolve
  = untrusted candidate-search engines

in-toto / DSSE / Witness
  = later standardized provenance statements

Sigstore / GitHub Artifact Attestations / Cosign
  = later workload identity / signature infrastructure
```

and never:

```text
search score = scientific truth = Supernova admission
```

The preferred investigation order is:

1. ERA / FUTS first;
2. OpenEvolve only if population/evolutionary search proves a capability ERA does not provide at matched complete cost;
3. ShinkaEvolve only if it proves a non-redundant capability after ERA/OpenEvolve;
4. retain the smallest engine set that passes the required prospective gates;
5. evaluate in-toto/DSSE/Witness only as a shadow provenance layer after search adapters work;
6. evaluate Sigstore/GitHub Artifact Attestations/Cosign only after provenance semantics are stable;
7. migrate any authentication/admission authority only through a later explicit authority revision with equivalence tests and rollback.

---

## 2. Live Supernova boundary at annex creation

This annex was drafted against the live repository state observed on 2026-08-21.

- canonical repository: `Kitahl/Project-supernova-`;
- current protocol: `2.5`;
- current specification authority: Revision 4;
- accepted `main` at planning snapshot: `3f2d10980ead2c75f8ccb532159d270c53898c85`;
- active cohort: `CAL-BR-010-v25-fe539297-r2`;
- generation: 10;
- immutable generation head G: `25c7c4e4732a5635ae8f47a9194d59a3f5a58e8f`;
- calibration streak: `0`;
- countable current cohort: true;
- fresh evidence: globally disabled;
- repository policy: `VERIFIED_PROTECTED_SOURCE_BOUND`;
- Math Foundry substrate: 3.1.1, SHA-256 `57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f`;
- Mastermind substrate: 4.4.10, SHA-256 `026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d`;
- runtime state: `9d0a88cc9001295b5e4c0f4163e83c0fd64ce04521e34230ad3539af14f3dfaf`;
- canonical mutable pointer: `main:state/CURRENT.json` only;
- worker topology: 12 isolated worker branches -> MM06 -> MF06 -> BIL00;
- worker authentication: `PS-HMAC-SHA256-CANONICAL-REPORT-2`;
- external GitHub authority: source-bound status/admission contexts on exact heads;
- root TCB: separately protected from ordinary automated self-amendment.

The snapshot above is planning context, not a permanent hard-coded assumption. Any future implementation MUST reread live `main:state/CURRENT.json` and the exact accepted control release before acting.

### Preserved invariants

1. `main:state/CURRENT.json` is the sole canonical mutable network pointer.
2. Generation G is immutable.
3. Workers have narrowly scoped writable outputs.
4. Candidate code receives no admission credential.
5. Candidate code cannot modify evaluator/checker/trust/control.
6. MM06 independently rereads actual Git/artifact bytes.
7. Verifier, integrator and consolidator remain distinct.
8. External admission occurs only after the subject artifact exists.
9. No receipt may claim its own future CI/admission result.
10. Exact-head and exact-artifact identities matter.
11. Stale-parent transitions fail.
12. CAS/expected-head discipline remains.
13. Missing evidence is never converted into a null scientific result.
14. `UNKNOWN`, `NOT_MEASURED`, `QUARANTINED`, `INVALID` remain typed.
15. Scientific authority remains distinct from transport authority.
16. Search/evolution fitness never equals scientific admission.

### What is permitted before the freeze opens

Permitted now, without changing the active protocol-2.5 experiment:

- source inspection;
- license/dependency review;
- threat modelling;
- non-authoritative local/offline prototypes on non-protected toy tasks;
- schema design;
- sandbox design;
- deterministic replay fixtures;
- documentation and issue-queue work that does not alter current authority.

Not permitted before the freeze opens:

- adding an external engine to an active countable worker contract;
- changing active G/control/assignment/liveness;
- consuming protected/fresh benchmark material;
- allowing search engines to write GitHub statuses or canonical state;
- treating an offline search result as G1/G8/Goal-2 evidence;
- migrating worker/admission authentication to Sigstore or another scheme;
- activating Revision 5 early.

---

## 3. Upstream investigation targets

These are **reference snapshots for investigation only**, not final integration pins. At the entry to each build stage, source, commit/release, license, transitive dependencies, security advisories and API/model terms MUST be re-inspected and frozen independently.

| Candidate | Target upstream repository | Reference snapshot observed 2026-08-21 | Repository license observed | Initial disposition |
|---|---|---:|---|---|
| ERA / FUTS | `google-research/era` | `b836730b5c000526af95116b1d0e2c60c8cf0a10` | Apache-2.0 | INVESTIGATE FIRST |
| OpenEvolve | `algorithmicsuperintelligence/openevolve` | `411fb59c886c18704caaffb611e17cf9e7d824d2` | Apache-2.0 | CONDITIONAL SHADOW |
| ShinkaEvolve | `SakanaAI/ShinkaEvolve` | `9912af12d423504b8d580f4179fd15f5f88b8c50` | Apache-2.0 | CONDITIONAL SHADOW |

`ryanrudes/openevolve` is a separate project with the same/similar name and MUST NOT be silently substituted for the target above. If it is later considered, it receives its own source/license/capability review.

Code license is only one layer. Every candidate review MUST separately record:

- CODE LICENSE;
- DATASET LICENSE;
- MODEL/API TERMS;
- TRADEMARK RIGHTS;
- NOTICE/attribution duties;
- patent provisions;
- transitive dependency licenses;
- benchmark/task licenses;
- whether a proprietary commercial distribution is permitted;
- whether Supernova modifications may remain proprietary.

Repository visibility alone never establishes commercial permission.

---

## 4. ERA / FUTS — first search engine

The Google Research ERA repository exposes a generic FUTS reference implementation whose search loop is supplied by two host functions:

```text
generate_fn(problem, past_solution) -> candidate
execute_fn(problem, candidate) -> score
```

The reference search expands a tree iteratively using Flat UCB / FUTS and returns the best scored solution.

For Supernova this is attractive precisely because the upstream search core is small and does not need to become authority.

### Approved role

```text
Supernova worker
    |
    v
SupernovaSearchAdapter
    |
    v
ERA/FUTS
    |
    +--> candidate A
    +--> candidate B
    +--> candidate C
    |
    v
selected proposal(s)
    |
    v
Supernova-owned independent execution/evaluation
    |
    v
MM06 / Foundry / Court / admission
    |
    v
ADMIT or REJECT
```

ERA MUST NOT:

- write `CURRENT.json`;
- move G;
- modify evaluator/checker/benchmark;
- modify complete-cost accounting;
- modify memory conditions;
- modify admission code;
- write GitHub statuses;
- choose promotion;
- receive root-TCB or worker-auth secrets;
- see hidden holdout material unless the exact frozen experiment explicitly assigns it.

### Initial candidate use cases

- theorem tactic/policy search;
- algorithm optimization;
- experiment-code generation;
- solver-routing policy;
- decomposition policy;
- retrieval policy;
- restart/branching parameters;
- proof-search parameters;
- candidate research-method generation.

No use case is admitted merely because ERA can optimize it. Each use case requires a frozen evaluator and independent held-out evaluation.

---

## 5. SupernovaSearchAdapter boundary

Future interface:

```text
generate(problem, parent_candidate, context) -> Candidate
execute(candidate, frozen_evaluator) -> CandidateEvidence
```

The engine may receive a scalar/vector search fitness derived from `CandidateEvidence`. Supernova retains the evidence object.

### Candidate

Minimum fields:

- `candidate_id`;
- `parent_ids`;
- `genealogy_digest`;
- exact source/content digest;
- engine identity + exact version/commit;
- generation seed;
- model identity/attestation status;
- prompt/template identity;
- frozen problem identity;
- allowed mutation envelope;
- memory/archive identity;
- creation cost.

### CandidateEvidence

Minimum fields:

- candidate ID;
- parent ID(s);
- genealogy;
- exact candidate content digest;
- actual bytes-entering-sandbox digest;
- generation seed;
- engine identity;
- model identity;
- prompt identity;
- evaluator digest;
- checker digest;
- benchmark/task digest;
- environment/image identity;
- frozen G/control/assignment identities when operating under Supernova;
- compute/time/token/API/hardware cost;
- stdout/stderr/output digests;
- measured search score;
- typed execution status;
- held-out status when applicable;
- failure/retry count;
- cache/memory condition;
- complete-cost vector;
- evidence references.

Required invariant:

```text
candidate_generated_digest == candidate_entering_sandbox_digest
```

A framework's statement that it evaluated candidate X is not sufficient evidence that bytes X were actually executed.

---

## 6. Search fitness is non-authoritative

Explicit type separation:

```text
SEARCH_FITNESS
    !=
HELD_OUT_UTILITY
    !=
SUPERNOVA_ADMISSION
```

Search fitness is allowed to guide an engine's internal exploration.

Search fitness MUST NOT:

- create a VerifiedProduct;
- create a causal ReactionRecord label;
- alter scientific state;
- alter calibration state;
- promote a runtime;
- increment a clean-cohort streak;
- certify Goal 1 or Goal 2;
- substitute for independent verification.

Evolutionary search is expected to find weaknesses in evaluators. This is both a risk and a useful red-team capability. Reward hacking discovered by a search engine is classified primarily as an evaluator/control defect, not as candidate improvement.

---

## 7. Supernova-owned sandbox

Generated code is treated as hostile.

Future execution boundary:

- immutable image digest;
- non-root execution;
- no Docker socket;
- no SSH agent;
- no GitHub/admission token;
- no root-TCB secret;
- no worker-auth secret;
- no private benchmark secret except explicit frozen assigned input;
- read-only evaluator;
- read-only checker;
- read-only frozen G;
- narrow writable candidate/output directory;
- explicit CPU limit;
- explicit memory limit;
- explicit wall/compute policy;
- process-tree termination;
- controlled filesystem;
- denied/restricted network egress;
- deterministic cache policy;
- cache partitioned by experiment arm;
- exact environment receipt;
- complete stdout/stderr/output hashes.

Engine-level timeouts are convenience logic only. They are never the security watchdog.

Candidate execution statuses are closed and typed:

```text
SUCCESS
FAILED
TIMEOUT
OOM
INVALID_OUTPUT
SANDBOX_VIOLATION
EVALUATOR_ERROR
NOT_MEASURED
```

No invalid/missing candidate is silently counted as score zero.

---

## 8. OpenEvolve — conditional population search

OpenEvolve is investigated only after ERA demonstrates a real need for a broader population/evolution mechanism.

The source review MUST determine, at the exact candidate commit/release:

- population/archive semantics;
- islands/subpopulation semantics;
- mutation operators;
- parent/candidate selection;
- parallel evaluation;
- evaluator interface;
- checkpoint/resume semantics;
- candidate lineage completeness;
- novelty/diversity mechanisms;
- randomness/replay behavior;
- failure accounting;
- timeout behavior;
- CPU/memory containment assumptions;
- distributed execution semantics;
- model/API adapters;
- transitive dependencies.

Preferred architecture:

```text
Frozen Supernova experiment
        |
        v
OpenEvolve sandboxed candidate-generation process
        |
        v
content-addressed candidate archive
        |
        v
selected candidate proposal(s)
        |
        v
independent Supernova evaluation
```

Questions that must be answered experimentally:

- Does population search materially improve held-out utility at matched complete cost?
- Does it require more evaluator exposure?
- Does it increase reward-hacking/overfitting risk?
- Does archive persistence confound matched-control experiments?
- Can archive state be exactly digested and reset?
- Are failed candidates fully charged?
- Can selection be replayed from frozen seeds/state?
- Can the evaluator/checker be mounted read-only?
- Can the engine run with zero authority credentials?

If population machinery does not show incremental value beyond ERA/ordinary search, do not retain it.

---

## 9. ShinkaEvolve — conditional non-redundant backend

ShinkaEvolve is investigated only after ERA and, where justified, OpenEvolve.

The exact source review MUST cover:

- `ShinkaEvolveRunner`;
- task/evaluator contract;
- population strategy;
- mutation strategy;
- archive/islands;
- local/distributed/Slurm execution;
- resume/checkpoint;
- genealogy;
- model integration;
- parallelism;
- failure handling;
- sandboxability;
- cost observability;
- archive reset/memory condition.

Do not integrate both OpenEvolve and ShinkaEvolve if they are materially redundant.

Selection criterion:

> keep the smallest engine set that provides prospectively measured, non-redundant capability at matched complete cost.

---

## 10. Comparative engine matrix required before implementation selection

The source-inspection report MUST produce an ERA vs OpenEvolve vs ShinkaEvolve matrix containing at least:

- exact repository;
- exact commit/release;
- source size;
- architectural complexity;
- direct/transitive dependencies;
- code license;
- NOTICE/attribution requirements;
- maintenance activity;
- public security/advisory state;
- evaluator exposure;
- parallelism;
- determinism/replayability;
- archive/memory model;
- lineage support;
- checkpointing;
- sandboxability;
- cost-accounting difficulty;
- benchmark-overfitting risk;
- model/API dependency risk;
- integration TCB growth;
- rollback difficulty;
- ease of Supernova adapter implementation.

The matrix records observed facts separately from hypotheses and experimental results.

---

## 11. Archive and memory contamination

Population/archive state is part of the treatment.

Every run that permits persistent search memory MUST bind:

- `archive_digest`;
- `search_history_digest`;
- candidate count;
- prior experiment/task IDs included;
- model/prompt history policy;
- memory condition;
- reset/restore identity.

A later engine run may not be credited as a better improver merely because it retained more prior attempts.

Goal-2 experiments preserve the existing separation:

```text
F = solver/runtime
M = retained products/memory/archive
I = improver/search policy
```

Improver-of-improver claims require controlling `F` and `M` while changing `I`.

---

## 12. Scientific evaluation of the integration

Do not accept:

> OpenEvolve got a higher internal score.

as evidence of Supernova improvement.

Mechanisms are tested separately.

Recommended sequence:

```text
BASE vs ERA

best(BASE, ERA) vs OpenEvolve

best(previous) vs ShinkaEvolve
```

with:

- matched complete compute;
- frozen tasks;
- frozen evaluator;
- frozen checker;
- frozen memory condition;
- equal access to tools;
- equal model identity when required;
- predeclared stopping;
- held-out evaluation;
- independent reruns;
- effect sizes;
- uncertainty;
- failure rate;
- wall time;
- token/API cost;
- hardware cost.

Measure at least:

- discovery efficiency;
- candidate quality;
- held-out utility;
- robustness;
- evaluator-gaming rate;
- diversity;
- duplicate rate;
- invalid-candidate rate;
- total complete cost;
- variance/reproducibility;
- sandbox violation rate.

Any engine that wins only by receiving more evaluator queries, memory, compute, retries or hidden information fails the matched-control claim.

---

## 13. Staged build sequence and mapping into Revision 5

External search is **not a new mandatory Supernova core stage**. It is an optional candidate-generation qualification track that becomes eligible only after the ordinary baseline and trust boundary exist.

### S0 — Baseline

- freeze current Supernova behavior;
- no external search engine in the authoritative path;
- define candidate/evaluator/sandbox/cost contracts.

### S1 — ERA offline prototype

- non-protected toy task family;
- no Git authority;
- no private benchmark;
- no canonical state change;
- sandbox mandatory.

### S2 — ERA replay benchmark

- compare candidate quality/cost to the current baseline;
- freeze seeds/evaluator/memory/complete budget;
- independent rerun.

### S3 — ERA SupernovaSearchAdapter

- still non-authoritative;
- exact candidate genealogy;
- exact candidate/evaluation receipts;
- no search score admission.

### S4 — OpenEvolve shadow

Only if ERA exposes a demonstrated limitation that population search plausibly addresses.

### S5 — ShinkaEvolve shadow

Only if it offers a measurable capability not already obtained from ERA/OpenEvolve.

### S6 — Engine selection

- remove redundant engines;
- freeze one or at most two supported search backends;
- require rollback to ordinary baseline/no-engine path.

### S7 — in-toto / DSSE / Witness shadow

- provenance only;
- no authority effect.

### S8 — Sigstore / GitHub Artifact Attestations / Cosign shadow

- workload identity/signature experiment;
- compare against existing authentication;
- no authority migration yet.

### S9 — Authority migration

Only after a later approved authority revision permits it.

Require:

- exact equivalence tests;
- independent seed/root migration when root TCB changes;
- rollback;
- zero-credit transition where experimental conditions change;
- no search engine access to signing/admission identity.

### Placement in the existing Rev5 stage sequence

The engineering qualification track `S0 -> S6` is inserted **after Rev5 Stage 4 (ordinary control baseline) and before an external search backend is allowed to contribute to a Rev5 Stage-5 G1 treatment candidate**.

This does not mean G1 waits for OpenEvolve/ShinkaEvolve. ERA/OpenEvolve/ShinkaEvolve are optional. If the ordinary baseline or existing Supernova mechanisms already provide the required candidate-generation capability, the external-engine track may be skipped or terminated.

`S7 -> S9` is a separate provenance/identity track and does not gate G1 unless the approved future authority specification explicitly says so.

---

## 14. Future module/file plan

Names below are proposed Rev5 implementation targets only; they MUST NOT be added to the frozen active protocol merely because this annex exists.

```text
search/
  adapter.py
  candidate.py
  evidence.py
  genealogy.py
  cost.py
  memory.py
  backends/
    era_futs.py
    openevolve.py
    shinkaevolve.py

sandbox/
  runner.py
  policy.py
  environment_receipt.py
  process_tree.py

schemas/
  search_candidate.schema.json
  candidate_evidence.schema.json
  candidate_genealogy.schema.json
  search_memory_condition.schema.json
  search_engine_receipt.schema.json
  sandbox_result.schema.json
  complete_search_cost.schema.json

experiments/
  search_engine_baseline.yaml
  era_vs_base.yaml
  openevolve_vs_era.yaml
  shinka_vs_best.yaml

provenance_shadow/
  predicate.py
  intoto_dsse_adapter.py
  witness_adapter.py
  sigstore_adapter.py
  github_attestation_adapter.py
  cosign_adapter.py
```

The exact file layout may change after source inspection; the architectural boundaries may not.

---

## 15. CI integration contract

Search-engine CI is rejection/qualification machinery only.

Future CI MUST verify:

- exact upstream source commit/release digest;
- license inventory;
- dependency lock;
- sandbox image digest;
- candidate/evaluator/checker digests;
- genealogy acyclicity;
- exact candidate bytes entering sandbox;
- no forbidden control/evaluator/checker writes;
- cost completeness;
- seed presence;
- deterministic replay where claimed;
- stale candidate/cohort/G rejection;
- archive/memory identity;
- typed failure semantics;
- rollback path.

Candidate-generated code must never execute in a workflow holding Supernova admission credentials.

---

## 16. Required test matrix

Every engine adapter requires:

```text
UNIT
INTEGRATION
REPLAY
DETERMINISM
COST
SANDBOX
NEGATIVE
MUTATION
HELD_OUT
ROLLBACK
```

Adversarial mutants include at least:

- evaluator modified;
- benchmark modified;
- checker modified;
- cost omitted;
- nonexistent parent claimed;
- genealogy cycle;
- missing seed;
- duplicate candidate;
- control-path write attempt;
- network exfiltration attempt;
- environment-secret read attempt;
- `NaN`/`inf` score;
- malformed output;
- timeout;
- process fork bomb;
- OOM;
- stale candidate replay;
- wrong cohort;
- wrong G;
- generated digest != evaluated digest;
- archive restored from wrong experimental arm;
- failed candidate omitted from cost/accounting;
- search engine reports self-improvement without held-out evidence.

---

## 17. Threat model / failure handling

| Failure | Required Supernova disposition |
|---|---|
| Infinite loop | sandbox kills process; `TIMEOUT` |
| Excess memory | sandbox kills process; `OOM` |
| Evaluator write attempt | `SANDBOX_VIOLATION` |
| Benchmark write attempt | `SANDBOX_VIOLATION` |
| Hard-coded/reward-hacked answer | independent held-out evaluation rejects or quarantines |
| Network exfiltration | denied/restricted network; violation recorded |
| Credential read | credential absent; violation recorded |
| Wrong candidate evaluated | digest mismatch -> reject/quarantine |
| Fake lineage | genealogy validation failure |
| Engine crash | typed `ENGINE_FAILURE` / run failure; no state transition |
| Missing/failed run | not score zero; typed missing/failure |
| Stale checkpoint | identity mismatch -> reject |
| Archive contamination | wrong memory condition -> experiment invalid |
| Engine claims improvement | zero authority until independent Supernova evidence |

The correct architecture does not require trusting upstream execution bookkeeping.

---

## 18. Later in-toto / DSSE / Witness shadow attestation

Do not place in-toto/DSSE/Witness into the authoritative path initially.

Define a Supernova predicate binding at least:

```json
{
  "protocol_version": "...",
  "cohort_id": "...",
  "generation_head_G": "...",
  "control_tree": "...",
  "role": "...",
  "branch": "...",
  "exact_subject_head": "...",
  "subject_digest": "...",
  "parent_heads": ["..."],
  "allowed_output_set": ["..."],
  "workflow_identity": "...",
  "environment_identity": "...",
  "admission_phase": "..."
}
```

Distinction:

```text
ATTESTATION != ADMISSION
```

An attestation may establish provenance claims such as producer/input/environment/digest identity. It does not establish mathematical correctness, scientific validity, calibration success or promotion authority.

Required replay attacks:

- old attestation into new cohort;
- right signature / wrong G;
- right digest / wrong role;
- right artifact / wrong parent;
- stale workflow;
- wrong repository;
- wrong branch;
- historical verifier receipt reuse;
- valid attestation for scientifically invalid output.

Temporal order remains:

```text
artifact exists
    -> attestation generated
    -> independent verifier reads artifact + attestation + Git
    -> external admission decision
```

---

## 19. Later Sigstore / GitHub Artifact Attestations / Cosign shadow identity

Potential future target:

```text
GitHub protected workflow
        |
        v
OIDC workload identity
        |
        v
Sigstore / DSSE attestation
        |
        v
Supernova protected verifier
        |
        v
exact-head admission status
```

Requirements:

- signing identity unavailable to model-generated code;
- expected repository;
- expected workflow identity/ref;
- expected issuer;
- exact commit;
- exact artifact digest;
- archive/offline-verifiable bundle where feasible;
- explicit root/key/identity rotation;
- advisories monitored;
- reviewed fixed releases/pins;
- rollback to existing authentication.

GitHub Artifact Attestations are provenance/integrity evidence, not a guarantee that an artifact is safe or correct. Any future use preserves Supernova's separate content/semantic/scientific verification.

---

## 20. Commercial/license review gate

Before any engine becomes a supported backend, freeze an exact license bill for:

- upstream source;
- copied/modified upstream files;
- dependencies;
- model SDKs/APIs;
- bundled data/tasks;
- optional GPU/distributed libraries;
- documentation/assets;
- trademark references.

Apache-2.0 candidates require their license/notice/modification obligations to be handled correctly. Trademark rights remain separate from the code license.

No commercial-use statement is promoted without exact dependency/API/dataset review at the frozen integration version.

---

## 21. Three mandatory review loops

Before engine selection or any production adapter merge:

### LOOP 1 — capability and scientific-design review

- does the engine solve a measured capability gap?
- is the comparison matched in complete cost/information/memory?
- can held-out evaluation reject evaluator gaming?
- is the mechanism redundant with existing ordinary control/search?

### LOOP 2 — implementation/security/license review

- exact source/commit/release;
- dependency/license inventory;
- sandbox escape review;
- credential/egress review;
- determinism/replay/cost audit;
- checkpoint/archive audit;
- rollback.

### LOOP 3 — adversarial authority/integration review

- attempt evaluator/checker/control mutation;
- attempt authority credential access;
- wrong candidate digest;
- stale evidence/attestation;
- wrong G/cohort/branch/parent;
- self-promotion;
- missing/failed evidence;
- cross-arm archive/cache leakage.

Each loop returns explicit blockers, accepted fixes, remaining risks and a go/no-go decision. The next loop begins from reread exact source and Supernova state, not cached assumptions.

---

## 22. Acceptance gates

An external engine may become a supported **candidate backend** only when all apply:

- exact source commit/release frozen;
- exact license/dependency inventory accepted;
- sandbox escape/credential negatives pass;
- candidate bytes entering evaluation are content-bound;
- genealogy is complete and acyclic;
- failures are typed and fully costed;
- search randomness/state is replayable to the claimed level;
- archive/memory condition is explicit;
- held-out evaluation is independent of search fitness;
- evaluator-gaming mutants are rejected;
- rollback to no-engine/ordinary baseline works;
- matched-complete-cost experiment shows useful incremental value;
- no new admission authority is granted to the engine.

No engine is mandatory merely because it passes qualification.

---

## 23. Build-now / build-later / reject

### BUILD / INVESTIGATE NOW — non-authoritative only

- upstream source and license inspection;
- ERA/FUTS offline adapter prototype;
- `SupernovaSearchAdapter` schema/interface design;
- hostile-code sandbox design/prototype;
- Candidate/CandidateEvidence/genealogy/cost schemas;
- deterministic toy/replay fixtures;
- evaluator-gaming red-team tests;
- comparative engine study.

### BUILD LATER — after relevant Rev5/authority gates

- OpenEvolve shadow adapter if ERA exposes need;
- ShinkaEvolve shadow adapter if non-redundant;
- supported backend selection;
- in-toto/DSSE/Witness shadow attestations;
- Sigstore/GitHub Artifact Attestations/Cosign shadow identity;
- any production authentication migration.

### REJECT

- search engine writing `CURRENT.json` or G;
- search engine writing GitHub admission statuses;
- evaluator/checker mutation by candidate code;
- hidden benchmark access as ordinary search input;
- using internal search score as scientific evidence;
- unmetered candidate attempts;
- invalid candidates treated as score zero without failure accounting;
- persistent archive reuse without a frozen memory condition;
- integrating OpenEvolve + ShinkaEvolve merely for feature count;
- attestation treated as correctness;
- provenance signature treated as scientific truth;
- candidate code receiving signing/root/admission identity.

---

## 24. Final integration workflow

```text
main:state/CURRENT.json
        |
        v
exact frozen experiment / G
        |
        v
role-bounded Supernova worker
        |
        v
SupernovaSearchAdapter
        |
        +--> ERA/FUTS
        +--> OpenEvolve [conditional]
        +--> ShinkaEvolve [conditional]
        |
        v
untrusted candidate(s)
        |
        v
Supernova-owned hostile-code sandbox
        |
        v
CandidateEvidence + complete cost + genealogy
        |
        v
independent Foundry/checker/Court evaluation as applicable
        |
        v
MM06 independent artifact/Git reread
        |
        v
external exact-head report admission
        |
        v
MF06 safe-only integration
        |
        v
BIL00 guarded consolidation/transition
```

Later shadow provenance may attach evidence to the artifact path, but it does not replace any authority step.

---

## 25. Final ruling

The intended end state is not to make ERA/OpenEvolve/ShinkaEvolve trusted.

The intended end state is:

> Supernova can safely exploit powerful external search/evolution systems while remaining correct when those systems fail, mis-score, optimize a loophole, lose state, or behave adversarially.

ERA is the first engine to investigate because its minimal `generate -> execute/score -> tree search` boundary makes the Supernova-owned evaluator/sandbox separation easiest to establish and falsify.

OpenEvolve and ShinkaEvolve must earn their additional complexity prospectively. Provenance/signature infrastructure remains a later shadow layer until its equivalence and authority-migration gates are separately passed.
