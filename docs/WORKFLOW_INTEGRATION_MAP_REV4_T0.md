# Project Supernova Revision-4 T0 workflow / integration map

Status: operational documentation for protocol 2.5. This file does not itself grant admission authority.

## Authority graph

`main:state/CURRENT.json`
→ exact immutable control release
→ exact countable generation delta policy
→ immutable generation G
→ 12 isolated create-once worker branches
→ authoritative exact-head `supernova/branch-worker`
→ frozen/server-time liveness evidence
→ MM06 independent verifier
→ exact verifier-head source-bound `supernova/report-admission`
→ MF06 safe-only integrator
→ BIL00 exact-main consolidation / issue-root-cause repair / successor construction
→ exact-head `supernova/transition-admission`
→ protected CAS merge updates canonical history/state.

## Failure semantics

A worker receipt is never rewritten after creation. A failed worker head is placed in MM06 `quarantined_report_refs`; a missing worker is placed in `missing_workers`. A quarantine or missing lane prevents clean calibration credit but MUST NOT by itself suppress the terminal MM06 verification receipt. MM06 uses `VERIFIED_WITH_QUARANTINES`, `INCOMPLETE`, or `INVALID` as appropriate and produces an exhaustive SAFE/QUARANTINED/MISSING partition.

MF06 never bypasses quarantine. For a diagnostic zero-credit cohort it may integrate only MM06 SAFE references while preserving quarantines/missing lanes and `calibration_pass=false`. BIL00 then consolidates the diagnostic evidence at zero credit and constructs a successor from accepted repaired controls.

## Transport serialization

HMAC canonicalization and committed-file serialization are different contracts.

- HMAC input: remove `worker_auth_proof`; sorted-key compact UTF-8 JSON.
- Stored report: `json.dumps(report, sort_keys=true, indent=2, ensure_ascii=false) + "\n"` (`PRETTY_SORTED_UTF8_JSON_V1`).

A semantically correct signed object with wrong committed serialization is quarantined. This is a transport implementation defect, not evidence that the validator should be weakened.

## Self-repair ownership

Workers discover and report issues. MM06 independently verifies and root-cause partitions evidence. MF06 integrates only verified-safe references. A01 audits runtime/transport/liveness. BIL00 owns public-safe GitHub issue mirroring and protected repair PRs. BIL00 must rerun the original falsifier and closes defects only with objective evidence.

Mastermind and FOIL may generate or adversarially review repair proposals, but neither is admission authority. Math Foundry remains executable mathematical/runtime authority, Tribunal/Court remain scientific/fidelity/admission authority, and GitHub CI remains mechanical transport/rejection authority.

## Current Gen10 disposition

Gen10 `CAL-BR-010-v25-fe539297-r2` is diagnostic zero-credit after post-start authoritative repair. Eleven worker heads are structurally green; MM02 is quarantined for violating deterministic stored-report serialization. Gen10 must still receive a terminal MM06 receipt, downstream source-bound report admission, MF06 diagnostic integration, and BIL00 zero-credit consolidation before the successor clean cohort is frozen.
