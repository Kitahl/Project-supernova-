# CID-0 data-gap receipt

**Status:** `NOT_MEASURED / INSTRUMENTATION CONTRACT READY`

CID-0 asks whether OperatorContract-semantic features preserve the action information available in raw traces without relying on operational fingerprints.

Required consumed-data views per pre-action decision:

- independent problem/family ID;
- raw semantic state representation;
- contract-semantic representation;
- exact legal action set and actual executed action;
- timing, token, memory, route/tool IDs, executable paths and receipt-format fields isolated as fingerprint features;
- family-held-out split fixed before evaluation.

Planned comparisons: raw inverse-action model; contract-semantic model; fingerprint-only model; duration/token/memory/tool/route/path/format ablations; conditional-entropy or held-out predictive-gap report with family transfer.

No consumed trace corpus satisfying these fields was available in this engineering worktree. `Delta_CID` and all predictive gaps remain `NOT_MEASURED` rather than estimated from incomplete evidence.
