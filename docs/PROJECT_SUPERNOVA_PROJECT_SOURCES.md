# Project Supernova — ChatGPT Project source manifest

**Purpose:** define the files that belong in the ChatGPT Project named `Project Supernova` for human/session context.

**Authority rule:** Project files are reference context only. They are not the Scheduled Task bus and must never outrank current GitHub state. Scheduled Tasks retrieve canonical control material through GitHub/approved connectors; they must not assume Project-file visibility at execution time.

## Core files to keep in the Project

1. `PROJECT_SUPERNOVA_REV4_INTEGRATED_EXECUTION_AND_SESSION_LAUNCH_2026-08-19.md`
   - Fully integrated Revision 4 architecture and execution authority.
   - Protocol 2.5 / Revision 4 remains frozen until two clean countable cohorts.

2. `PROTOCOL.md`
   - Current protocol-2.5 transport authority.

3. `BRANCH_PROTOCOL.md`
   - Branch-GitOps ownership and branch-class rules.

4. `BRANCH_WORKER_PROTOCOL.md`
   - Worker/verifier/integrator/director branch execution contract.

5. `SESSION_STANDARD.md`
   - Stable session titles, headers, issue/test/evidence/cost ledger format.

6. `plan/PLAN.json`
   - Canonical task-network plan `0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`.

7. `config/roles.json`
   - Role and authority separation for all 15 lanes.

8. `config/task_registry_v25.json`
   - Current 15-lane hourly Vancouver cadence and fan-in structure.

9. `config/protocol_freeze.json`
   - No protocol 2.6 / Revision 5 before two clean countable v2.5 cohorts.

10. `config/repo_policy.json`
    - Required main protection and source-bound admission contexts.

11. `config/countable_control_set_v25.json`
    - Complete control/workflow/schema/test set that every new countable v2.5 generation must freeze.

12. `config/worker_auth.json`
    - **Public commitments and HMAC-2 metadata only. Never raw secrets.**

13. `config/checker_pins.json`
    - Checker/version/replay/independence and M7 revalidation policy.

14. `benchmark/pool_disposition.json`
    - TRAIN/CALIBRATION/G1/G8/GOAL2/RESEARCH-FROZEN contamination/freshness boundaries.

15. `schemas/state.schema.json`
    - Canonical state vocabulary, including source-bound repository-policy status.

16. `schemas/branch_report.schema.json`
17. `schemas/branch_verification.schema.json`
18. `schemas/branch_integration.schema.json`
19. `schemas/branch_director.schema.json`
20. `schemas/branch_consolidation.schema.json`
    - Closed transport evidence contracts.

21. `schemas/lane_liveness_observation.schema.json`
22. `schemas/cohort_liveness_contract.schema.json`
23. `schemas/verifier_assurance.schema.json`
    - No-receipt/liveness and verifier-TCB assurance contracts.

24. `docs/session/SESSION_STATUS.md`
25. `docs/session/IMPLEMENTATION_PLAN.md`
26. `docs/session/HANDOFF_RECEIPT.json`
    - Latest engineering-session context and exact unresolved gaps.

27. `theorems/cascade-soundness.md`
28. `theorems/horizon-decision-soundness.md`
    - Current theorem obligations/qualified soundness work.

29. `MATH_FOUNDRY_v3.0.1_EXECUTION_CLOSURE_FINAL.zip`
    - Add only if the exact source package is available and its SHA-256 matches the frozen project record.

30. `MASTERMIND_v4.4.8_TARGETED_COLLAB_WLCRS3_CANDIDATE_1_FULL.zip`
    - Add only if the exact source package is available and its SHA-256 matches the frozen project record.

## Files that should NOT be used as live Project authority

Do not upload a mutable `state/CURRENT.json` snapshot as if it were current truth. It becomes stale immediately. Project chats should fetch the live file from GitHub whenever current state matters.

Do not place any of the following in Project reference files:

- raw worker HMAC secrets;
- protected benchmark prompts/items/outcomes;
- private pre-outcome manifests;
- sealed G1/G8/GOAL2 pool contents;
- hidden evaluator payloads;
- credentials/tokens/API secrets.

Those remain in `Kitahl/thoma` / the private vault or the appropriate protected execution environment.

## Recommended Project instruction

Use this short instruction in Project settings:

> Project Supernova uses the attached files as stable reference context only. For any current operational fact, fetch `Kitahl/Project-supernova-/state/CURRENT.json` and the exact generation/control/assignment it points to. GitHub wins over Project files when they differ. Preserve protocol 2.5 / Revision 4 freeze, Foundry/Mastermind/Tribunal authority separation, fail-closed evidence rules, fresh-pool isolation and no self-promotion. Never expose private manifests, holdouts or worker secrets.

## Update policy

Replace Project reference files only when an admitted repository change supersedes them. Historical reports remain in GitHub; the Project should contain the current operating documents plus a small number of high-value immutable design/source packages, not every cohort receipt.
