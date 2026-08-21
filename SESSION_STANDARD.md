# Project Supernova Session / Report Standard v2

Every scheduled-task response begins with this header before any prose:

```text
=== PROJECT SUPERNOVA SESSION ===
SESSION_NAME: <stable standardized task title>
TARGET_PROGRAM: MATH_FOUNDRY | MASTERMIND | JOINT
PHASE: <EXACT_FROZEN_ASSIGNMENT_PHASE>
ITERATION_ID: <active cohort/suite/research id>
ITERATION_NUMBER: <generation_seq or research sequence>
ROLE_ID: <MF01...BIL00>
GOAL: <exact assigned goal>
PLAN_ID: <task-network plan id>
RUNTIME_STATE_ID: <runtime identity>
MODEL_TARGET: GPT-5.6 Sol
REASONING_EFFORT_TARGET: EXTRA_HIGH
MODEL_BINDING_STATUS: VERIFIED | PARTIAL_UNVERIFIED | UNVERIFIED | MISMATCH
EXECUTION_MODE: SAFE_REPLAY_ONLY | FRESH_EXECUTION | WAITING | RESEARCH
=== END SESSION HEADER ===
```

`PHASE` is not a separately authoritative closed vocabulary. It MUST equal the exact phase string in the frozen assignment for the active cohort/research object. Examples include `T0_COUNTABLE_REPLAY_COHORT_1`, `T0_COUNTABLE_REPLAY_COHORT_2`, `E1`, `G1`, `C1`, `REACTION`, `DR03`, `E3`, `SELECT`, `IGNITION`, `CASCADE`, `E5B`, `E6`, and `RESEARCH`. If the assignment introduces another valid phase string, the assignment controls; this document must not force a lossy alias such as `T0`.

The associated task/chat is persistent. Stable session titles are:

- `PS-MF-W01 | Representation Lab`
- `PS-MF-W02 | E1 Solver Routing`
- `PS-MF-W03 | Lemma & Operator Lab`
- `PS-MF-W04 | Adversarial Falsifier`
- `PS-MF-W05 | Product Closure`
- `PS-MM-W01 | React Mechanisms`
- `PS-MM-W02 | DeepSWE Mechanisms`
- `PS-MM-W03 | SlopCode Contracts`
- `PS-MM-W04 | Senior SWE Architecture`
- `PS-MM-W05 | E3 Mechanism Controls`
- `PS-MM-W07 | Before/After Self-Bench`
- `PS-JOINT-A01 | Runtime & Transport Audit`
- `PS-JOINT-V01 | Evidence Verifier`
- `PS-JOINT-I01 | Evidence Integrator`
- `PS-JOINT-D01 | Director + 12h Research`

Every countable receipt uses the same logical framework: `session_header`, `executive_status`, `task_ledger`, `issue_ledger`, `test_ledger`, `plan_alignment`, `evidence_and_provenance`, `cost_ledger`, `research_questions` or `research_findings`, and `next_action`. Negative/zero/unknown evidence is preserved.

Model target is requested, not presumed. `VERIFIED` is legal only when both model and reasoning identity are runtime-observed. Model-sensitive fresh evidence is non-promotable without the frozen binding receipt.

A worker self-reread is never independent. MM06 later owns authoritative report-path/blob/creation-commit/history reread evidence.
