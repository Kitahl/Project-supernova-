# MM01 / T0 control repair notes

This document is non-authoritative explanatory material for issues #97, #98 and #99.

The repair changes frozen protocol-2.5 control bytes, so any affected in-progress countable cohort cannot retain credit. After the repair is admitted, the calibration sequence restarts at streak 0 under a new immutable generation.

Repairs:

- `MM01-T0-REACT-CONTRACT-001`: adds a closed-world React proposal envelope, fail-closed validator enforcement for MM01 fresh proposals, and positive/negative fixtures. Replay-only MM01 reports remain legal without proposal payloads.
- `MM01-T0-SESSION-PHASE-001`: makes the exact frozen assignment phase authoritative; `T0_COUNTABLE_REPLAY_COHORT_1` is no longer outside the documented contract.
- `MM01-T0-REGISTRY-COUNTABILITY-001`: preserves the frozen task-registry snapshot byte-for-byte and adds `config/task_registry_semantics_v25.json`, which explicitly classifies the legacy `activation_status.countable_cohort_eligible` value as historical/non-authoritative. Current countability is resolved only from canonical state + active control + active assignment, and disagreement among those authorities fails closed.

No change enables fresh evidence or gives Mastermind execution/promotion authority.
