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

15. external candidate search is OPTIONAL and NON-AUTHORITATIVE:
    Supernova remains authority + experiment + verification + admission
    external engines generate candidate proposals only

16. add `SupernovaSearchAdapter` boundary:
    `generate(problem,parent,context) -> Candidate`
    `execute(candidate,frozen_evaluator) -> CandidateEvidence`
    exact generated/evaluated content digests must match

17. investigate engines in this order:
    ERA/FUTS first
    → OpenEvolve shadow only if population search closes a measured ERA limitation
    → ShinkaEvolve shadow only if it adds non-redundant measured capability
    → remove redundant engines

18. freeze source/license identity per engine at stage entry:
    exact repo + exact commit/release + code license + NOTICE/attribution + dependencies + model/API terms + dataset/benchmark licenses + trademark rights

19. hostile-code sandbox before any Supernova worker adapter:
    immutable image digest
    non-root
    no Docker socket/SSH agent
    no GitHub/admission/root/worker-auth credentials
    evaluator/checker/G read-only
    narrow writable output
    CPU/RAM/process-tree/egress controls
    exact environment receipt

20. search result type separation:
    `SEARCH_FITNESS != HELD_OUT_UTILITY != SUPERNOVA_ADMISSION`
    invalid/missing candidate is typed failure, never implicit numeric zero

21. candidate provenance/evidence:
    candidate ID + parent IDs + genealogy + exact bytes digest + engine/model/prompt/seed + evaluator/checker/environment identities + archive/memory identity + complete-cost vector + stdout/stderr/output hashes + typed status

22. archive/memory condition is an experimental treatment:
    bind archive/history digest
    prevent cross-arm cache/archive leakage
    Goal 2 continues to separate solver F, memory M and improver I

23. engine experiment sequence at matched complete cost:
    BASE vs ERA
    → best(previous) vs OpenEvolve
    → best(previous) vs ShinkaEvolve
    use held-out evaluation, independent reruns, uncertainty, failure accounting and rollback

24. insert search-engine engineering qualification after Rev5 Stage 4 ordinary baseline and before an external search backend may contribute to Stage-5 G1:
    S0 baseline/contracts
    → S1 ERA offline
    → S2 ERA replay
    → S3 ERA adapter
    → S4 OpenEvolve conditional shadow
    → S5 Shinka conditional shadow
    → S6 engine selection

25. later provenance track only after search adapters work:
    S7 in-toto/DSSE/Witness SHADOW
    → S8 Sigstore/GitHub Artifact Attestations/Cosign SHADOW
    → S9 authority migration only under a later explicit authority revision

26. preserve:
    `ATTESTATION != ADMISSION`
    provenance/signature proves identity/digest claims only; never mathematical/scientific correctness

27. required search-engine tests:
    UNIT + INTEGRATION + REPLAY + DETERMINISM + COST + SANDBOX + NEGATIVE + MUTATION + HELD_OUT + ROLLBACK
    including evaluator/checker/control mutation, genealogy cycle, stale G/cohort, missing seed, NaN/inf, timeout, fork bomb, OOM, egress/secret attempts, wrong evaluated digest and archive contamination

28. three review loops before supported-backend selection:
    LOOP 1 capability/scientific design
    LOOP 2 implementation/security/license
    LOOP 3 adversarial authority/integration

29. supported-backend rule:
    select the SMALLEST engine set that proves incremental held-out value at matched complete cost and adds zero search-engine admission authority

30. candidate annex to review with Rev5:
    `docs/REV5_EXTERNAL_SEARCH_EVOLUTION_INTEGRATION_CANDIDATE.md`

## Activation procedure

After the two-clean-cohort freeze opens:

1. independently review and finalize `PROJECT_SUPERNOVA_REV5_CANDIDATE.md` and its candidate annexes;
2. complete the three-loop source/security/scientific review for any external engine proposed for build;
3. publish `PROJECT_SUPERNOVA_SPEC_REV5.md` with accepted annex rulings folded into the specification;
4. create a new source-integrity record;
5. regenerate `plan/PLAN.json` from the approved Revision-5 specification rather than manually splicing prose into the Revision-4 plan;
6. issue a new plan ID / specification revision;
7. update README current authority;
8. admit the transition through the normal protected BIL00 path.

External-engine investigation does not itself authorize production integration. Search engines remain proposal generators unless a later frozen Revision-5 implementation contract explicitly admits a qualified adapter.
