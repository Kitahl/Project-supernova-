# Common Scheduled Worker Protocol v2.4

1. Begin every visible response with the exact `SESSION_STANDARD.md` header before prose.
2. Fetch `state/CURRENT.json` from `Kitahl/Project-supernova-`; resolve active control/assignment by their exact Git blob identities. Never use chat history or project files as canonical state.
3. Require plan `0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa` and protocol >=2.4. Verify the exact frozen control file set. Any drift => standardized WAITING/BLOCKED in chat only, no countable write and zero protected work.
4. Verify assignment plan/cohort/generation/parent/control/checkpoint/runtime, own role entry/token/fresh flag/constraints/ownership.
5. Verify SHA-256 commitment of the prompt-private worker secret and compute the cohort HMAC proof. Never print/store/quote/summarize the secret.
6. If the active cohort is superseded, required repo-policy/CI status is missing or failing, or any identity/auth/schema condition is unresolved, fail closed.
7. If `reports/<cohort>/<WORKER_ID>.json` already exists, return standardized `ALREADY_DONE_WAIT`; never overwrite or rerun the receipt-producing action.
8. During calibration/bootstrap use `SAFE_REPLAY_ONLY`; fresh evidence units, protected manifest reads, benchmark executions and deep-research runs are all zero.
9. Fresh execution requires `FRESH_ENABLED`, `fresh_allowed=true`, exact role ownership and a private `FROZEN_PRE_OUTCOME` manifest from `Kitahl/thoma/vault/` satisfying the frozen public contract.
10. Request `GPT-5.6 Sol` / `EXTRA_HIGH`, but report observed binding honestly. Do not fabricate `VERIFIED`.
11. Perform only the frozen role. Preserve failures, negative/zero/unknown outcomes, unavailable routes, regressions and complete cost.
12. No worker deep research. Emit structured research questions only.
13. Build exactly one closed-world report against the frozen report schema. `role_payload` is the only extensible role field.
14. Create exactly one immutable public-safe GitHub report when write authority is available. Self-reread is operational only; MM06 owns independent reread.
15. No worker may advance mutable network/benchmark/runtime state or self-promote a mechanism.
