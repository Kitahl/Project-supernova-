# Common Scheduled Worker Protocol v2.3

1. Begin every visible response with the exact standardized session header from `SESSION_STANDARD.md` before any prose.
2. Fetch `state/CURRENT.json`; read generation, active cohort, assignment/control paths+Git identities, checkpoint, runtime, network mode, plan ID, superseded cohorts and benchmark state pointers when present.
3. Fetch the exact active control manifest and every frozen control file. Verify every Git blob identity. Any control drift => no countable report and no fresh evidence.
4. Fetch the active assignment. Verify plan/cohort/generation/parent-state/control/checkpoint/runtime, your worker entry, token, fresh flag, opaque private refs, constraints and evidence ownership.
5. Fetch `config/worker_auth.json`. Verify the SHA-256 commitment of your prompt-private `WORKER_AUTH_SECRET_HEX`, then compute the frozen cohort HMAC proof. Never print or persist the raw secret.
6. If state/plan/control/assignment/auth is missing, stale, mismatched, superseded or unreadable, output a standardized WAITING/BLOCKED report in chat only; consume no fresh evidence and create no countable GitHub worker receipt.
7. If your immutable `reports/<cohort>/<WORKER_ID>.json` already exists, return standardized `ALREADY_DONE_WAIT` and do not repeat or overwrite.
8. During `GITHUB_BUS_CALIBRATION`, use `SAFE_REPLAY_ONLY`, zero fresh/private/benchmark counters and minimal deterministic role work. Do not broaden into public-source research merely to fill time.
9. Outside calibration, fresh work requires `FRESH_ENABLED`, explicit `fresh_allowed=true` and a valid private `FROZEN_PRE_OUTCOME` manifest from `Kitahl/thoma` binding plan/control/cohort/checkpoint/runtime, task/evaluator/checker, observed model/tools/environment, total budget, repeats/randomization, cache/context/retention, accounting, contamination exclusions and exact ownership.
10. Scientific model target is `GPT-5.6 Sol` / `EXTRA_HIGH`. Report actual binding honestly as `VERIFIED|PARTIAL_UNVERIFIED|UNVERIFIED|MISMATCH`; do not fabricate reasoning-effort verification. If the frozen scientific contract requires verified model/effort and it is unavailable, scientific promotion is `NOT_MEASURED`/blocked.
11. Perform only the frozen role from `config/roles.json`. Preserve zero/negative outcomes, unavailable routes, failures, regressions, full costs and `NOT_MEASURED`.
12. No worker deep research. Emit structured research questions only.
13. Build the worker receipt against the frozen `schemas/report.schema.json`. The receipt must contain standardized session header, executive status, task/issue/test ledgers, plan alignment, provenance, HMAC proof, costs, research questions and next action. Top-level undeclared fields are forbidden.
14. Create exactly one immutable GitHub report. A worker may fetch its own report after creation for operational confidence and may say so in chat, but worker self-reread is **not** independent calibration evidence and is not an authoritative report field.
15. MM-06 later performs the authoritative post-write Git reread and schema/HMAC verification. No originating worker may advance network/benchmark/runtime state or promote itself.
