# Project Supernova Branch Worker Protocol v2.5

For any state with `transport_mode="BRANCH_GITOPS"`, this file is authoritative for worker state source, branch destination, authentication, independent reread and transport validation. Scientific authority remains governed by `PROTOCOL.md`, role registry and frozen assignment.

1. Fetch `state/CURRENT.json` from `main`; it is the only canonical mutable pointer.
2. Require plan `0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`, protocol `2.5`, transport `BRANCH_GITOPS`, active cohort not superseded, fresh/repo-policy gates consistent.
3. Read exact immutable generation branch/head `G`, control/assignment paths+blob SHAs and your assigned worker branch.
4. Fetch control and assignment **from exact `G`**, not mutable main. Verify plan/cohort/generation/runtime/checkpoint, generation base commit/tree, control blob, assignment blob, role/token/goal/target/fresh/constraints and all required control paths against the frozen control-release commit.
5. Verify your worker branch exists and is exactly at `G` before its first receipt. If it has moved, it must contain exactly one existing assigned report and no other diff; otherwise fail closed.
6. Verify SHA-256 of the prompt-private secret equals the public worker commitment. Never print/store/expose the secret.
7. If the assigned report already exists, `ALREADY_DONE_WAIT`; never overwrite.
8. First visible output is the exact `SESSION_STANDARD.md` header. Session name, target program, full phase, cohort, generation, role, exact goal, plan, runtime, model target and reasoning target are copied exactly from frozen assignment/control.
9. Model/reasoning targets are requested metadata. Report observed binding honestly. `VERIFIED` requires affirmative frozen runtime evidence, but `PARTIAL_UNVERIFIED` or `UNVERIFIED` caused solely by unavailable reasoning-effort attestation is non-blocking for structural/auth safety, MM06 SAFE partitioning, admission, calibration credit, fresh eligibility and scientific promotion. Do not convert unobserved reasoning effort into a mismatch; preserve any affirmative observed mismatch as provenance.
10. Calibration/bootstrap is `SAFE_REPLAY_ONLY` with zero fresh evidence, private-manifest reads, benchmark executions and deep-research runs. A non-countable bootstrap may emit transport evidence but never calibration credit.
11. Perform only the frozen role. No worker deep research, mutable state/benchmark changes or self-promotion.
12. Build the complete final report against the frozen report schema. Set `transport_serialization="PRETTY_SORTED_UTF8_JSON_V1"`, `worker_auth_scheme="PS-HMAC-SHA256-CANONICAL-REPORT-2"` and the public commitment.
13. **HMAC canonicalization is independent of file formatting.** Remove `worker_auth_proof`, canonicalize the entire remaining report as sorted-key compact UTF-8 JSON (`json.dumps(obj, sort_keys=true, separators=(",",":"), ensure_ascii=false)`), compute lowercase HMAC-SHA256 with the prompt-private secret bytes, then insert `worker_auth_proof`.
14. **Committed transport serialization is deterministic and chunk-verifiable.** Serialize the complete signed report as `json.dumps(report, sort_keys=true, indent=2, ensure_ascii=false) + "\n"`. The file must be newline-terminated, multi-line UTF-8 JSON, contain no tab characters, and contain no line longer than 8192 UTF-8 bytes. This representation lets MM06 retrieve the exact complete receipt in bounded line ranges without changing the HMAC definition.
15. Write exactly one file `reports/<cohort>/<worker>.json` to the assigned `ps/work/<cohort>/<worker>` branch only. No other path may change.
16. `origin_reread_claim=false`. MM06 owns independent branch/head/blob reread, deterministic transport validation and HMAC verification. MM06 reconstructs the JSON object from the complete committed file, removes only `worker_auth_proof`, recomputes compact canonical JSON, verifies HMAC, and mutates signed fields as negative tests.
17. If a required structural CI status is absent/pending/failing, report that condition but do not reinterpret it as PASS. No protected evidence is consumed.
