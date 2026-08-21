# Revision 5 Pending After Calibration

**STATUS: CANDIDATE MIGRATION CHECKLIST ONLY**

**CURRENT AUTHORITY:** Revision 4 / Protocol 2.5

**ACTIVATION:** only after two consecutive clean countable protocol-2.5 cohorts and the guarded Revision-5 authority transition.

This file is non-authoritative. It does not modify `plan/PLAN.json`, Protocol 2.5, Revision 4, active state/control/assignment, or any current calibration credit.

## REV5 PENDING CHANGES

1. `foundational_open_q_count = 0`

2. replace vague `STATE_COMPILER_0` with:
   `STRATEGY_FAITHFUL_COMPILER_0`

3. target IR:
   factored partially observed controlled process
   + LIMID/influence factorization

4. compiler correctness:
   bidirectional legal-strategy correspondence
   + visible trace/reward/cost preservation

5. add independent `CompilationCertificate` validator

6. planning complexity:
   constrained induced width
   no `tau_dec`
   no `r-width`

7. controller:
   resumable strategy DAG / transducer
   not atomic option library

8. PUC:
   proof + contract + provenance + authority
   separate validity/fidelity/admissibility

9. Q14:
   hermetic capability denial
   + declared dependencies
   + clean-rebuild/mutation differential

10. complete cost:
    resource vector primary

11. mandatory baseline:
    ordinary state-conditioned controller
    + ordinary VOC/metareasoning

12. make optional:
    reaction graph
    hypergraph
    learned selector
    ignition
    persistent memory

13. revised sequence:
    T0
    → E1
    → G1
    → compiler/product core
    → ordinary baseline
    → ReactionRecords
    → DR03
    → optional mechanism ablations
    → G8
    → T3-RW
    → T5
    → E5B/DR27

14. G8:
    preregistered intersection-union test
    against every claim-critical control

## Activation procedure

After the two-clean-cohort freeze opens:

1. independently review and finalize `PROJECT_SUPERNOVA_REV5_CANDIDATE.md`;
2. publish `PROJECT_SUPERNOVA_SPEC_REV5.md`;
3. create a new source-integrity record;
4. regenerate `plan/PLAN.json` from the approved Revision-5 specification rather than manually splicing prose into the Revision-4 plan;
5. issue a new plan ID / specification revision;
6. update README current authority;
7. admit the transition through the normal protected BIL00 path.
