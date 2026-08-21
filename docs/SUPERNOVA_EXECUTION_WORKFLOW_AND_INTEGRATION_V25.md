# Project Supernova — Protocol 2.5 Execution, Verification, Integration and Self-Repair Workflow

**Authority:** explanatory map of the frozen Revision-4 / Protocol-2.5 control plane. Machine authority remains `state/CURRENT.json`, immutable generation G, frozen control/assignment/liveness, schemas, validators and protected GitHub status sources.

## 1. Canonical state graph

```text
accepted main:state/CURRENT.json
        |
        v
immutable generation G
        |
        +--> control/<cohort>.json
        +--> assignments/<cohort>.json
        +--> liveness/<cohort>.json
        |
        +--> 12 isolated worker branches
        +--> verifier branch (MM06)
        +--> integrator branch (MF06)
        `--> consolidation branch (BIL00)
```

`main:state/CURRENT.json` is the only mutable canonical pointer. A worker never treats mutable main documentation as the active cohort contract; it resolves exact G and the frozen identities referenced by state.

## 2. Generation admission

For a countable replay cohort:

1. BIL00/transition logic prepares a control-release root from exact accepted main.
2. Immutable G adds exactly the cohort control, assignment and pre-outcome liveness contract.
3. The authoritative structural reconciler validates the frozen control tree, assignment, liveness contract and exact generation diff.
4. `supernova/branch-generation=success` may have exactly one authoritative success writer.
5. Secondary REST diagnostics use distinct diagnostic contexts and can never overwrite authoritative structural status.
6. Only after exact-G structural success may the 15 scheduled lanes be enabled.

Any authoritative control change during an in-progress countable cohort invalidates that cohort's clean credit and restarts at streak 0 under a new frozen generation.

## 3. Worker fan-out

Twelve worker roles run on isolated `ps/work/<cohort>/<role>` branches. Each worker:

1. rereads live canonical state and exact G;
2. verifies its frozen assignment/token/branch/role/mode;
3. performs only its assigned role;
4. writes exactly one create-once `reports/<cohort>/<role>.json`;
5. uses deterministic `PRETTY_SORTED_UTF8_JSON_V1` file transport;
6. signs the entire semantic report with HMAC-2 over compact canonical JSON after removing only `worker_auth_proof`;
7. records all evidence-backed defects in its closed `issue_ledger`;
8. never writes main, another role branch, verifier/integration state or scientific promotion state.

Replay roles must explicitly encode NOT_MEASURED/no-promotion semantics where required. Fresh roles additionally require frozen `FRESH_ENABLED`, worker `fresh_allowed=true`, typed `fresh_scope`, exact opaque private-manifest identity and role-specific closed payload validation.

## 4. Liveness authority

The liveness contract is frozen before worker outcomes. For each lane it binds branch, report path, start window and deadline.

The out-of-band monitor distinguishes:

- `RUN_OBSERVED`: immutable creation time is at/before deadline, or receipt was observed before deadline;
- `RUN_LATE`: immutable creation time is after deadline — transition blocking;
- `RUN_TIMING_UNKNOWN`: report exists after deadline but trustworthy creation time is unavailable — fail closed;
- `NO_RECEIPT`: no report exists — blocking after deadline.

Poll time is never substituted for report creation time.

## 5. MM06 independent verification

MM06 does not integrate. It independently rereads each exact worker branch and proves:

- G ancestry and single assigned-path diff;
- create-once immutable history and exact creation commit;
- authoritative `supernova/branch-worker=success`;
- complete deterministic transport bytes;
- branch report schema and mode-specific role schema;
- strict session/assignment/control/checkpoint/runtime/token bindings;
- whole-report HMAC-2 from the complete committed JSON object;
- public-safety and zero-fresh constraints;
- frozen liveness timing.

MM06 owns one exhaustive disjoint partition:

```text
12 workers = SAFE ∪ QUARANTINED ∪ MISSING
SAFE ∩ QUARANTINED ∩ MISSING = ∅
```

No missing, late, unknown or unverifiable report can be converted to ZERO_DELTA. MM06 writes exactly one create-once `verification/<cohort>.json` and cannot self-attest the later report-admission status.

## 6. Post-write verification admission

After the immutable MM06 receipt exists, the protected GitHub admission path independently evaluates the exact verifier head. The later source-bound context:

`supernova/report-admission=success`

is external evidence. A verifier receipt saying PRE_CI/CI_NOT_OBSERVED is not a pass by itself.

## 7. MF06 integration

MF06 consumes only MM06 SAFE references and the later exact-head report-admission success. It:

- rereads safe blobs for transport integrity;
- preserves negative/zero/unknown/model-binding/checker/fidelity limitations;
- never rescues quarantined or missing evidence;
- never verifies its own inputs;
- writes exactly one create-once `integration/<cohort>.json`.

## 8. BIL00 consolidation and transition

BIL00 is the only director/repair controller. It requires complete liveness, MM06 verification, external report admission and MF06 integration. It then:

1. consolidates the cohort on the assigned consolidation branch;
2. runs the three source-bound protected contexts on exact consolidation head;
3. performs CAS/exact-base guarded transition only;
4. increments calibration streak only for an objectively clean cohort under unchanged frozen control.

Cohort 1 clean => streak 1. Cohort 2 must use the identical frozen authoritative control/substrate/runtime identities; a second clean pass => streak 2. Fresh science remains disabled until the separate private pre-outcome and scientific gates also pass.

## 9. Issue/self-repair pipeline

```text
worker issue_ledger
      |
      +--> MM06 corroboration/quarantine
      +--> A01 independent transport/liveness audit
      |
      v
MF06 safe issue integration
      |
      v
BIL00 dedupe -> GitHub issue
      |
      v
smallest protected repair PR
      |
      +--> positive regression
      +--> negative/mutation falsifier
      +--> Candidate Diagnostics
      +--> trusted bootstrap if authority bytes change
      `--> source-bound required contexts
      |
      v
ordinary protected merge
      |
      v
rerun original falsifier
      |
      +--> fails: issue stays open, new exact-main repair iteration
      `--> passes: CLOSED_WITH_EVIDENCE
```

Default scheduled repair depth is two complete audit/repair/reread loops per eligible run; three is the hard maximum only for lightweight deterministic work. State drift, stale SHA, pending/failing required CI, API/rate limit, disconnect, timeout, malformed receipt or authority mismatch stops the loop immediately.

## 10. Root-TCB changes

The ordinary authority bootstrap cannot authorize its own root replacement. Changes to accepted-main write-capable admission/status authority require a separately installed one-shot seed. The root candidate is exact-main/head/path constrained, cannot modify the seed, passes read-only diagnostics, and becomes permanently inert after the new root epoch marker is accepted.

This rule applies to the Gen9 dual structural-status writer repair: the ordinary semantic/liveness repair lands first; a separate root rotation then makes one structural writer authoritative and demotes REST reconciliation to distinct diagnostic/rejection-only contexts.

## 11. Gen9 disposition

Gen9 `CAL-BR-009-v25-b53ab205` is diagnostic zero-credit evidence. MM06 returned SAFE=0, QUARANTINED=12, MISSING=0 because structural-status authority, late-receipt timing and exact HMAC verification were not all trustworthy. It must not increment the calibration streak. Replacement calibration begins only after Issue #160's ordinary repair and root-status-writer rotation are both admitted and their original falsifiers pass.
