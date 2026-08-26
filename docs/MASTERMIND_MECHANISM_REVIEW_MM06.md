# Mastermind mechanism review — MM06 terminalization repair

Proposed mechanism: terminal verifier receipt with explicit quarantine partition.

Alternative explanation: the verifier silence was necessary because a failed worker made the entire verification object unrepresentable.

Negative control: frozen `branch_verification.schema.json` explicitly admits `VERIFIED_WITH_QUARANTINES`, nonempty `quarantined_report_refs`, and `calibration_pass=false`; therefore silence is not schema-required.

Ablation: keep MM02 immutable/red, change only MM06 orchestration instruction from "wait for clean" to "classify all 12 then terminalize". Expected result is a verifier receipt with 11 SAFE / MM02 QUARANTINED / 0 MISSING, without changing any worker bytes or scientific claims.

Regression: a future worker structural failure must produce a terminal verifier partition rather than indefinite no-receipt; a fully green cohort still produces `VERIFIED_COMPLETE`.

Admission boundary: this mechanism changes scheduler/orchestration behavior, not the frozen Gen10 evidence. It does not authorize rewriting worker receipts or bypassing source-bound report admission.
