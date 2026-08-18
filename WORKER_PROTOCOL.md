# Common Scheduled Worker Protocol v2.5

1. Fetch canonical `main:state/CURRENT.json` from `Kitahl/Project-supernova-`.
2. When state says `transport_mode=BRANCH_GITOPS`, follow `BRANCH_WORKER_PROTOCOL.md` exactly for state source, immutable generation, branch destination, whole-report authentication and independent reread.
3. Verify plan, protocol, active cohort, supersession, runtime/checkpoint, frozen control/assignment, own role/token/branch and public auth commitment before work.
4. Begin every visible response with the exact `SESSION_STANDARD.md` header using frozen assignment values.
5. Existing assigned report => `ALREADY_DONE_WAIT`; never overwrite.
6. Bootstrap/calibration is replay-only with zero fresh/private/benchmark/deep-research cost unless frozen assignment explicitly authorizes otherwise.
7. Fresh work requires `FRESH_ENABLED`, explicit role ownership and a valid private `FROZEN_PRE_OUTCOME` manifest.
8. Request GPT-5.6 Sol / EXTRA_HIGH but report runtime binding honestly.
9. Perform only the frozen role. Preserve failures, negative/zero/unknown results, unavailable routes, regressions and complete cost.
10. Workers do not deep-research, advance mutable state/benchmark cursors, self-verify or self-promote.
11. Build the closed-world report against the frozen schema and use the branch whole-report HMAC scheme.
12. Write only the assigned report path on the assigned worker branch. MM06 later owns independent branch/head/blob reread and authentication.
