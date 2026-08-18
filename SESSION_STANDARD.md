# Project Supernova Session / Report Standard v1

Every scheduled-task response must begin with the following header before any prose:

```text
=== PROJECT SUPERNOVA SESSION ===
SESSION_NAME: <stable standardized task title>
TARGET_PROGRAM: MATH_FOUNDRY | MASTERMIND | JOINT
PHASE: <T0|E1|G1|C1|E3|C2|E5|E5B|E6|RESEARCH>
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

The associated task/chat is persistent. Do not create a new scheduled task/chat for a new generation. The stable task title identifies the persistent lane; dynamic iteration information belongs in the session header and GitHub receipt.

## Stable task/chat names

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

## Standard report sections

Every countable worker/verifier/integrator/director/research receipt has these logical sections:

1. `session_header`
2. `executive_status`
3. `task_ledger`
4. `issue_ledger`
5. `test_ledger`
6. `plan_alignment`
7. `evidence_and_provenance`
8. `cost_ledger`
9. `research_questions` or `research_findings`
10. `next_action`

### Task ledger
Each item has `task_id`, `status`, `description`, `evidence_refs`, and `next_action`.

### Issue ledger
Each item has `issue_id`, severity `CRITICAL|HIGH|MEDIUM|LOW`, status `OPEN|BLOCKED|FIXED|NOT_MEASURED|QUARANTINED`, summary, evidence refs, owner, and fix/next action.

### Test ledger
Each item has `test_id`, kind, status `PASS|FAIL|BLOCKED|NOT_MEASURED`, description, evidence refs, and result.

### Plan alignment
Each item binds an exact plan obligation/stage to `ALIGNED|PARTIAL|BLOCKED|NOT_APPLICABLE` plus evidence and notes.

## Model binding
Scientific target is `GPT-5.6 Sol` with `EXTRA_HIGH` reasoning. The Scheduled Tasks API used by this orchestration does not expose a model/reasoning-effort selector or reliable runtime effort receipt. Therefore tasks must request that target but must not fabricate verification. `MODEL_BINDING_STATUS` is `VERIFIED` only when the runtime exposes both model and effort identity. `PARTIAL_UNVERIFIED` means model identity is known but effort is not. Model-sensitive fresh benchmark evidence is non-promotable unless the frozen private execution manifest and runtime receipt satisfy the predeclared model-binding rule.

## Reread authority
A worker may say it attempted a reread, but a worker cannot independently certify its own post-write event. Only MM-06's later independent Git fetch/blob observation counts as `verifier_reread_verified=true` for calibration/promotion.
