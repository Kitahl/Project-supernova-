# Project Supernova — Pre-countable substrate epoch

**Date:** 2026-08-20  
**Protocol:** 2.5 FROZEN  
**Specification:** Revision 4 FROZEN  
**Plan ID:** `0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`

This document starts the next operational phase without changing protocol, specification revision, scientific state, calibration streak, Gen6 history, or fresh-evidence authority.

## Current substrate staging

### Mastermind

Staged candidate:

`MASTERMIND_v4.4.10_EXECUTION_CLOSURE_CANDIDATE_1_FULL.zip`

Version:

`4.4.10-execution-closure-candidate.1`

SHA-256:

`026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d`

Observed local qualification before Supernova binding:

- archive bytes: 595,605;
- manifest entries: 210/210 verified;
- Python files: 81;
- Python source validation: PASS;
- Python compile: PASS;
- v4.4.9 capability-broker regression family retained: PASS;
- Mastermind full self-test: PASS;
- package verification: PASS, source-only, no unexpected files;
- 4.4.10 execution-closure self-test: catalog complete, capability epoch stable, project write blocked, bounded Python calculation works, Foundry-ready-only handoff preserved.

Mastermind remains `PRE_REVIEW_ONLY`. Its capability broker, probe results, plans, retention estimates, and SEARCH_ONLY outputs do not become mathematical or scientific authority.

### Math Foundry

Current baseline remains Math Foundry 3.0.1 with frozen historical SHA-256:

`a9f220078a0c087a1c80a4bc6255951225734f7e73b50660138c20372257a0e8`

A successor Math Foundry release is expected shortly and is intended to be used for the new countable calibration epoch. Therefore **countable cohort 1 is not frozen against Foundry 3.0.1**. The final successor archive must be supplied, verified, hash-bound, and incorporated into the same final pre-cohort substrate freeze before Gen7 begins.

This avoids deliberately starting cohort 1 on a substrate that would immediately be replaced and force the calibration streak back to zero.

## Future optimization — independent read-only probe parallelism

Parallel execution is **disabled by default**.

A future implementation may parallelize independent read-only probes only after mechanically proving all of the following before dispatch:

1. every probe binds the **same frozen `capability_epoch_sha256`**;
2. exact provider and tool fingerprints are frozen;
3. every call is classified `READ_ONLY`;
4. no pair has an effect conflict;
5. no probe consumes another probe's output;
6. no authoritative shared mutable cache/state is touched;
7. complete-cost and rate-limit accounting remains deterministic;
8. every call emits an epoch-bound receipt;
9. aggregation is deterministic or proven order-independent.

Any unknown effect, epoch drift, missing fingerprint, dependency edge, conflicting effect, ambiguous shared budget, missing receipt, external write, or open-world action forces **serial execution**.

Parallelism is a scheduling optimization only. It has `SEARCH_ONLY` authority and cannot change promotion, verification, product admission, scientific state, runtime state, or GitHub admission authority.

## Countable-cohort launch rule

The next countable protocol-2.5 cohort may start only after:

1. final Mastermind identity is frozen;
2. the new Math Foundry archive is supplied and independently verified;
3. both substrate identities are recorded in the final pre-cohort control release;
4. the complete countable control set is frozen from accepted `main`;
5. new Gen7 control + assignment + canonical state transition are admitted atomically;
6. exact-head `supernova/branch-generation=success` is observed;
7. only then are the 12 worker lanes, MM06, and MF06 resumed.

Generation 6 remains immutable non-countable history. Calibration streak remains 0. Fresh evidence remains disabled.

## Current scheduling state

A01 and BIL00 may remain active for transport/substrate staging and issue consolidation. The 12 workers, MM06, and MF06 remain paused until the new countable generation is published.
