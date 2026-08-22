# MM02 Gen10 deterministic transport failure

Stable ID: `O-T0-GEN10-MM02-TRANSPORT-SERIALIZATION`

Observed immutable worker head: `59f0a07a1414153a3aba0f38758f589f8f26bc82`.

The MM02 signed report object is not being rewritten. Its committed JSON placed the top-level `mode` member after `worker_id`, rather than storing the signed report with the already-authoritative `PRETTY_SORTED_UTF8_JSON_V1` rule from `BRANCH_WORKER_PROTOCOL.md`: `json.dumps(report, sort_keys=true, indent=2, ensure_ascii=false) + "\n"`.

The frozen branch validator correctly publishes `supernova/branch-worker=failure`. The prospective repair is implementation-side: every successor worker prompt/tool must explicitly enforce deterministic stored serialization before the create-once write. The validator must not be weakened.

MM06 must quarantine this immutable worker report and still emit a terminal zero-credit verification receipt using the frozen `VERIFIED_WITH_QUARANTINES` path. Gen10 is already zero-credit for independent post-start authoritative repairs.
