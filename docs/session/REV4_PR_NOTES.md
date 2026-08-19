# Revision 4 PR Review Notes

Review this branch as a same-protocol, same-revision reconciliation only. It must not change `state/CURRENT.json`, active control/assignment, benchmark cursors, scheduled task prompts, fresh evidence or calibration streak.

Required review focus:

1. no hidden protocol 2.6 or Revision 5 semantics;
2. authority separation is preserved;
3. control state is distinct from Tribunal scientific state;
4. H0/H1 and offline diagnostics are explicitly non-admissible;
5. scheduled lanes remain T0/replay scoped;
6. Stage 0-LOOP is TRAIN-only and future-gated;
7. Goal-2 ladder is T3-RW -> T5 -> DR27/E5B;
8. SN-WORLD remains a non-authoritative Frontier backend;
9. no scientific status or active cohort changes.
