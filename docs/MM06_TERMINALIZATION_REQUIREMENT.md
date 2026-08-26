# MM06 terminalization requirement

A failed or missing worker is evidence, not a reason for verifier silence.

For a complete 12-lane observation, MM06 must produce exactly one terminal immutable verifier receipt with a unique/disjoint/exhaustive `SAFE / QUARANTINED / MISSING` partition. The frozen schema supports `VERIFIED_COMPLETE`, `VERIFIED_WITH_QUARANTINES`, `INCOMPLETE`, and `INVALID`.

For Gen10, if the independently reread state remains 11 structurally valid workers plus MM02 deterministic transport failure and no missing workers, MM06 must classify MM02 in `quarantined_report_refs`, set `calibration_pass=false`, use `VERIFIED_WITH_QUARANTINES`, and require later exact-head `supernova/report-admission`. It must not repair MM02, reinterpret its red structural status as green, or suppress the verifier receipt.
