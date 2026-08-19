# Project Supernova Scheduled Experiment Bus Protocol v2.5

## Authority
This GitHub network is external experiment/referee/research infrastructure. Math Foundry owns mathematical/runtime truth. Mastermind is PRE_REVIEW_ONLY. GitHub/CI/tasks/research/scores never establish mathematical truth by themselves.

## Canonical plan
`TASK_NETWORK_PLAN_ID=0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`.

## Protocol freeze
Protocol **2.5 is frozen for calibration**. No protocol 2.6 control revision may become canonical until repository protection is independently verified and two consecutive countable replay-only v2.5 Branch-GitOps cohorts have closed end-to-end. Defect repairs discovered before that gate must be implemented as v2.5 hardening, frozen into the next countable v2.5 control release, and covered by negative tests before cohort 1 starts. Spec churn is not a substitute for cohort closure.

## Dual goals
Goal 1: a finite, provenance-certified, independently verified within-problem reaction cascade prospectively beats ordinary/static/random controls at equal complete resource cost.

Goal 2: only after Goal 1, demonstrate improvement of the improver. Separate solver `F_t`, retained memory/products `M_t`, and improver `I_t`; compare later vs parent improver from identical untouched start under matched complete R&D budget, controlled `M`, identical allowed model/tools/environment and fresh independent evaluation. Better descendants or more memory alone do not count.

## Transport
`state/CURRENT.json` on `main` is the sole mutable canonical pointer. When `transport_mode=BRANCH_GITOPS`, `BRANCH_PROTOCOL.md` and `BRANCH_WORKER_PROTOCOL.md` govern in-flight transport. One immutable generation branch fans out to isolated worker branches, then verifier and integrator branches, then one consolidation PR. Main is never an in-flight worker workspace.

## Frozen generation
Control binds the exact control-release commit/tree plus a closed required-control path set. Generation control+assignment are create-once. Final generation head is immutable. Main/control-release drift after generation freeze does not invalidate an in-flight cohort.

## Authentication
Branch cohorts use only `PS-HMAC-SHA256-CANONICAL-REPORT-2`, binding the complete report payload. MM06 independently reconstructs the proof using verifier-side secret copies. Raw secrets never enter GitHub.

## Persistent sessions
The 15 scheduled lanes reuse the same task/chat. Stable names and mandatory first-response header are in `SESSION_STANDARD.md`; dynamic phase/cohort/iteration/goal belongs in the header and receipt.

## Model / execution binding — fifth TCB gate
All lanes request GPT-5.6 Sol / EXTRA_HIGH, but the task surface cannot itself prove either binding. Every receipt must report `VERIFIED|PARTIAL_UNVERIFIED|UNVERIFIED|MISMATCH` from actually observed runtime evidence. Replay-only transport may proceed with partial/unverified model binding. **Model-sensitive fresh evidence is non-promotable unless a frozen execution manifest and runtime receipt prove the predeclared model, reasoning/runtime constraints, tools and environment.** G1/G8/Goal-2 arms must use identical observed model/tools/environment unless the treatment explicitly includes that dimension. A request string is not a binding receipt.

## Public/private split
Public-safe orchestration/evidence lives in `Kitahl/Project-supernova-`. Protected `FROZEN_PRE_OUTCOME` manifests/payloads live only in `Kitahl/thoma/vault/`. Public refs are opaque only.

## Repository policy and three-context CI
No calibration cohort counts and no fresh work is eligible until GitHub itself reports `main` protected and the required status-check/source policy is independently observed. A repository policy JSON file cannot self-attest protection.

Three status contexts are non-substitutable:
- `supernova/static-control`: frozen protocol/control/assignment/schema/dependency/action identities and generation invariants;
- `supernova/report-admission`: MM06 verifier receipt and its Git/report partition/binding envelope after the receipt exists;
- `supernova/transition-admission`: BIL00 consolidation/next-state CAS, allowed diff and stale-parent transition semantics.

Missing, pending, failing, unobservable, wrong-source, or wrong-commit status is not PASS. A status for one context never satisfies another context. CI is mechanical rejection authority only; it cannot establish mathematical truth.

## Verification closure and temporal CI
A safe worker reference must bind worker, assigned branch/path, report blob, non-null 40-hex creation/path-changing commit identity, exactly one report-path-changing commit, generation ancestry, immutable history, schema, exact session, HMAC, public safety and assignment/control/runtime identities. Safe/quarantined/missing worker partitions must be unique, disjoint and exhaustive. Quarantine objects are closed and typed.

MM06 cannot self-attest CI that runs after its verifier receipt exists. The verifier receipt records a pre-CI state only. MF06 must later observe `supernova/report-admission=success` on the **exact verifier head** before integration can be countable. BIL00 analogously requires later exact-head transition admission for consolidation.

## Supply-chain freeze
Every countable v2.5 control release freezes GitHub Actions by full commit SHA and freezes the complete validation environment with hashes or an equivalent immutable environment receipt. Mutable `@vN` action references are inadmissible in the countable evidence path.

## Calibration
After repository protection and required source-bound contexts are independently observed, require two consecutive complete replay-only v2.5 branch cohorts: immutable generation -> 12 isolated whole-report-HMAC worker branches -> MM06 independent verification -> exact-head report admission -> MF06 integration -> integration structural admission -> one CAS-protected consolidation PR -> exact-head transition admission -> merge. Failure resets the streak. The current non-countable bootstrap may diagnose transport but cannot increment the streak.

## Fresh/protected work
`FRESH_ENABLED` is transport eligibility only. Fresh work also requires exact assignment ownership and a private frozen pre-outcome manifest binding plan/cohort/checkpoint/runtime, task/evaluator/checker, observed model/tools/environment, complete budget, randomization/repeats, cache/context/retention, accounting, contamination exclusions and disjoint ownership.

## Benchmark pools and succession
Mastermind and Math Foundry suites must each have an explicit disposition under the Stage -1 evidence pools: `TRAIN_TUNING`, `CALIBRATION`, `G1_PROSPECTIVE`, `G8_CASCADE`, `GOAL2_E5B`, or `RESEARCH_FROZEN`. A development/calibration suite can never later become G1/G8/Goal-2 promotion evidence. Canonical dispositions are in `benchmark/pool_disposition.json` and are frozen before fresh-task sealing.

Program cursors still advance independently. Suite completion requires every frozen unit terminal, evaluator/checker receipts present, complete costs closed and contamination/adjudication resolved. Terminal is not success. Verified completion + eligible successor -> preflight/private freeze and advance that program only. No eligible successor -> `BENCHMARK_DISCOVERY_WAIT` with no fresh consumption.

## Roles
Workers execute frozen roles only. MM06 verifies branch ancestry/path/blob/schema/session/HMAC/safety/cost/ownership. MF06 integrates only MM06-safe refs and reconciles by evidence tier. BIL00 alone owns consolidation PRs, network-state/benchmark cursor transitions and scheduled deep research. Runtime changes require an independently validated `RUNTIME_UPDATE_RECEIPT`.

## Deep-research gate
BIL00 is the only scheduled deep-research executor and research slots remain 00:58 and 12:58 America/Vancouver, but a slot executes deep research **only when an accepted open research lane exists**. While T0 is unqualified, the only admissible research lane is T0 transport/repository/admission closure; all E1/Stage-0/reaction/selector/Goal-2 literature expansion stays queued. Inputs are MM06-safe + MF06-integrated questions and unresolved accepted research only. No raw worker bypass or sealed-holdout access. Research cannot promote runtime/science by itself.

## Scientific sequence
T0 trustworthy branch bus -> Stage -1 fresh-pool governance -> OCN-0A/0B and static/cost diagnostics -> targeted causal qualification -> E1 stable ProblemSpec/ArmSpec/ExecutableActionSpec/ScheduleSpec/ActionReceipt/VerificationReceipt/complete cost and route/schedule truth -> G1 fresh one-generation gain -> C1 VerifiedProduct/ProductUseCertificate + statement fidelity -> runtime ReactionRecord -> DR03 causal semantics -> E3 executable learned/random/no-change -> selector/value-of-computation -> finite Goal-1 G8 cascade -> Goal-2 E5B improver-of-improver -> E6.

## Fail closed
Any missing, stale, mismatched, superseded, unknown, partial, timed-out, unexplained or contradictory admission evidence is not PASS. Correctness and clean evidence dominate score.
