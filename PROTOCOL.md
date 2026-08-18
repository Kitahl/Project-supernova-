# Project Supernova Scheduled Experiment Bus Protocol v2.4

## 1. Authority
This GitHub network is external experiment/referee/research infrastructure. Math Foundry owns mathematical/runtime truth. Mastermind is PRE_REVIEW_ONLY. GitHub, CI, scheduled tasks, research results, scores, votes, or director decisions never establish mathematical truth by themselves.

## 2. Canonical plan and dual goals
`TASK_NETWORK_PLAN_ID=0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`.

Goal 1 is the finite fresh provenance-certified reaction/cascade engine: a pre-registered within-problem cascade must beat ordinary/static/random controls at equal complete resource cost under independent verification.

Goal 2 is improvement of the improver. It is separate and opens only after Goal 1 passes. Solver `F_t`, retained memory/products `M_t`, and improver `I_t` must be separated. A Level-2 claim requires `I_(t+1)` to outperform `I_t` from the same untouched start, matched complete R&D budget, controlled memory carryover, identical allowed model/tools/environment, and fresh independent evaluation. Better descendants or more memory alone are not improver improvement.

## 3. Persistent sessions and standardized naming
The 15 scheduled lanes are persistent. Do not create a new lane/chat for each generation. Stable names and the mandatory first-output header are defined by `SESSION_STANDARD.md`. Dynamic phase, target program, iteration, number and exact assigned goal belong in the header and immutable receipt.

## 4. Model binding
All lanes request `GPT-5.6 Sol` with `EXTRA_HIGH` reasoning. A prompt request is not proof of runtime binding. Every run reports `MODEL_BINDING_STATUS`. Model-sensitive fresh evidence is inadmissible unless the frozen private execution manifest and runtime receipt satisfy the declared binding rule.

## 5. Public/private split
`Kitahl/Project-supernova-` is the public-safe canonical orchestration/evidence bus. `Kitahl/thoma/vault/` contains protected `FROZEN_PRE_OUTCOME` manifests and protected payloads only. Public files may carry opaque IDs/hashes, never protected item names/IDs/content, hidden prompts, private manifest payloads, raw worker secrets or credentials.

## 6. Frozen control
Every countable cohort has immutable `control/<cohort>.json` bound to the exact historical parent state blob and exact Git blob IDs of all frozen control files. Mixed revisions are ineligible. The control manifest freezes schema, validators, guards, adversarial tests, workflow, dependency lock, task registry and tool-authority policy.

## 7. Worker identity
Workers share a GitHub app identity, so each worker has a prompt-private 256-bit secret committed only by SHA-256 in `config/worker_auth.json`. Report proof is `HMAC-SHA256(secret, plan|cohort|assignment_blob|control_blob|worker_id)`. MM06 verifies with verifier-side copies. Secrets never enter GitHub.

## 8. GitHub write classes
Append-only evidence uses one create-once path per role. Mutable control transitions use one `transition/<generation>-<parent8>-<purpose>` pull request containing the full state transition. Permanent worker forks are forbidden by default; use forks only for genuinely separate security principals.

## 9. Repository protection gate
A clean v2.4 calibration cohort is countable only when the default branch is observed protected and the required admission contexts are configured. Until that is independently observed, all runs remain replay-only and `calibration_countable=false`. No task may infer repository protection from a policy file alone.

Required contexts are `supernova/static-control`, `supernova/report-admission`, and `supernova/transition-admission`. Missing/empty/queued/pending/neutral/skipped/cancelled/stale/error/failure is not PASS. A receipt cannot self-attest future CI.

## 10. Retry-safe state lineage / CAS
BIL00 binds every next control+assignment to the exact current state blob `S` and expected base head. The transition guard proves `S` is a real historical `state/CURRENT.json`, generation is exactly parent+1, supersession is monotone, runtime-bound identities do not drift without a runtime-update receipt, and active control/assignment bind the same parent. Stale candidates are rejected rather than silently rebased.

## 11. Schema and environment
Draft 2020-12 schemas are executed by the hash-locked Python validation environment. Top-level countable envelopes are closed-world. Role-specific extension data exists only in explicit `role_payload`. Public-safety scanning is additional to schema validation.

## 12. Independent reread and report admission
A worker may operationally reread its own write, but that is never independent evidence. MM06 must later fetch every report and bind expected path, current blob, unique creation commit, blob-at-creation, unchanged history, schema, HMAC/auth, public safety, assignment/control/runtime/lineage, costs and model-binding honesty. Safe/quarantined/missing partitions are unique and exhaustive.

## 13. Two-cohort calibration
The clean-counting v2.4 streak begins only after repository-protection admission is independently observed. A countable cohort requires 12 replay-only zero-protected-cost reports -> MM06 verification -> exact-commit external CI -> MF06 integration -> BIL00 decision/state transition. Any required failure resets the streak. Two consecutive clean non-superseded cohorts are required before transport may become `FRESH_ENABLED`.

## 14. Fresh/protected work
`FRESH_ENABLED` is transport eligibility, not scientific authorization. Fresh work additionally requires explicit ownership and a private `FROZEN_PRE_OUTCOME` manifest binding plan/control/cohort/checkpoint/runtime, task/evaluator/checker, observed model/tools/environment, complete budget, repeats/randomization, cache/context/retention, accounting, contamination exclusions and disjoint ownership.

## 15. Benchmark succession
`benchmark/registry.json` is canonical benchmark orchestration state. Mastermind and Math Foundry advance independently. A suite is terminal only after every frozen unit has exactly one terminal disposition, evaluator/checker/cost receipts are closed, and contamination/adjudication holds are resolved. Terminal does not mean success. BIL00 advances only from a verified immutable completion receipt plus successor preflight and private pre-outcome freeze. If no eligible successor exists, enter `BENCHMARK_DISCOVERY_WAIT` without consuming fresh evidence.

## 16. Verification / integration / director
MM06 verifies. MF06 consumes only MM06 safe refs plus successful external report-admission status and reconciles by evidence tier, not vote. BIL00 alone stages mutable network transitions and benchmark cursor updates, and cannot bypass CI/lineage/ruleset gates. Runtime changes require independently validated `RUNTIME_UPDATE_RECEIPT`.

## 17. Research
BIL00 is the only scheduled deep-research executor, exactly at 00:58 and 12:58 America/Vancouver. Inputs are MM06-safe + MF06-integrated questions and unresolved accepted research only. Worker research is prohibited. Research is create-once, public-safe and non-promotional.

## 18. Scientific sequence
T0 trustworthy v2.4 transport -> E1 stable problem/arm/action/schedule/cost truth -> G1 fresh one-generation gain -> C1 VerifiedProduct/ProductUseCertificate -> runtime ReactionRecord -> DR03 causal reaction semantics -> E3 executable learned/random/no-change proposals -> collision selector -> ignition/value-of-computation -> finite Goal-1 Supernova benchmark -> only then Goal-2 improver-of-improver programme.

## 19. Fail closed
Unknown, partial, unobserved, timed-out, unexplained or contradictory evidence is not PASS for an admission gate. Correctness and clean evidence dominate score.
