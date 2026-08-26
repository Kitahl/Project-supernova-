# FOIL causal autopsy — MM06 missing Gen10 receipt

Observed failure: after a scheduled MM06 retry, `verification/CAL-BR-010-v25-fe539297-r2.json` was still absent.

Competing causes tested:
1. missing worker report — falsified: all 12 assigned report paths exist;
2. scheduler never retried MM06 — falsified: the scheduled verifier ran again;
3. all workers structurally green — falsified: MM02 exact head is red;
4. frozen verifier schema cannot represent quarantine — falsified: it explicitly permits `VERIFIED_WITH_QUARANTINES`;
5. MM06 should repair MM02 — rejected by authority separation: worker receipt is create-once and BIL00 owns repair.

Earliest supported causal chain:
- MM02 committed an otherwise signed replay report with noncanonical stored key ordering; `mode` appears after `worker_id`.
- This violates the already-authoritative `PRETTY_SORTED_UTF8_JSON_V1` file serialization rule.
- The branch validator correctly publishes `supernova/branch-worker=failure` for MM02 while the other 11 worker heads are green.
- MM06 correctly cannot mark MM02 SAFE, but its live prompt did not explicitly require a terminal verification receipt when an exhaustive partition contains a quarantine. It therefore failed to terminalize the diagnostic cohort.

Repair:
- preserve MM02 immutable bytes and quarantine them;
- make MM06 always terminalize once all lanes are classified;
- make MF06 terminalize diagnostic integration while excluding quarantined refs;
- make successor worker implementation perform an exact pre-write stored-byte equality check against sorted pretty JSON;
- do not weaken the validator.

FOIL conclusion: the root is not scientific failure or HMAC failure. It is a transport implementation defect plus a verifier orchestration terminalization defect.
