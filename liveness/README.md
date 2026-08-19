# Cohort liveness contracts

For a future **countable** protocol-2.5 generation, the immutable generation may include:

`liveness/<cohort_id>.json`

validated against `schemas/cohort_liveness_contract.schema.json`.

The contract explicitly freezes each expected lane receipt's branch, path, start window and deadline. `scripts/check_lane_liveness.py` and the out-of-band GitHub workflow observe GitHub receipt existence only. They never infer why a Scheduled Task did not run; task state remains `TASK_STATE_UNKNOWN` unless an authoritative task-state inspection exists.

A missing receipt before its deadline is observable but not yet transition-blocking. A missing receipt after its frozen deadline is `NO_RECEIPT` and blocks liveness admission. An actual no-finding run must still produce an explicit zero-delta receipt.

This directory is **not** active cohort authority until its exact schema/script/workflow and cohort contract are frozen into a countable control manifest. Generation 6 is unchanged.
