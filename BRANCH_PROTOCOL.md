# Project Supernova Branch GitOps Protocol v2.5

Plan: `0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa`.

## Canonical-state rule
`main:state/CURRENT.json` is the **only mutable canonical network pointer**. There is no second branch-state file. In-flight artifacts live on isolated branches referenced by that pointer; only a verified consolidation PR may copy admitted evidence into canonical history and publish the next pointer.

## Topology
For active cohort `<C>`:
- immutable generation: `ps/gen/<C>` at exact frozen head `G`;
- worker branches: `ps/work/<C>/<WORKER>`, each created from exactly `G`;
- verifier: `ps/verify/<C>`, created from `G`;
- integrator: `ps/integrate/<C>`, created from `G`;
- consolidation: `ps/consolidate/<C>`, created only after verified integration and from the then-current exact `main` head;
- optional research: `ps/research/<research_id>`.

Permanent per-worker forks are not used unless a genuinely separate security principal is required. Branch isolation is sufficient for ordinary write separation without creating a competing repository truth.

## Git-native freeze
A generation control manifest freezes a `control_release_commit_sha`, its exact Git tree SHA, and a closed list of required control paths. Git object identity therefore commits to exact file bytes; workers and validators compare every required path against that frozen commit/tree. The generation branch may add only its immutable control and assignment before final head `G` is recorded.

## Worker isolation
Each worker branch starts at `G` and may change exactly one path: `reports/<C>/<WORKER>.json`. It may never move generation, verifier, integrator, consolidation, main, benchmark or another worker branch. A branch with additional path changes is rejected.

## Whole-report authentication
Branch cohorts use only `PS-HMAC-SHA256-CANONICAL-REPORT-2`. Remove `worker_auth_proof`, serialize the entire remaining report as UTF-8 JSON with sorted keys, separators `(',', ':')`, `ensure_ascii=false`, then HMAC-SHA256 with the prompt-private worker secret. This binds session fields, evidence, costs, tests and all report content, not merely identity metadata.

## Independent reread
MM06 fetches every assigned worker branch and proves:
- branch exists and descends exactly from `G`;
- diff from `G` changes only the assigned report path;
- report branch head and Git blob are recorded;
- schema and strict session equality pass;
- public safety and zero-protected calibration cost pass;
- SHA-256 secret commitment and canonical whole-report HMAC pass;
- structural branch CI status is successful on that exact worker head.
MM06 writes only the verifier branch. Worker self-reread has no authority.

## Integration
MF06 reads only MM06-safe refs, independently rereads them, requires successful structural verifier status on the exact verifier head, preserves quarantines/negative/zero/unknown/cost evidence, and writes only the integrator branch.

## Consolidation
BIL00 creates one consolidation branch from the exact current `main` head, copies only verified safe artifacts to `history/<C>/...`, adds verification/integration/director/consolidation receipts and any next state/benchmark transition, and opens one PR. The PR must be stale-parent/CAS clean and have `supernova/branch-consolidate=success` on its exact head. `expected_head_sha` is required at merge. Force merge/rebase is forbidden.

## Scheduled CI reconciliation
Because connector-originated pushes/PRs are not assumed to trigger Actions reliably, a frozen scheduled reconciler runs every five minutes. It fetches the active branch topology from canonical `main`, validates each exact branch head against the immutable generation and posts classic statuses to the exact heads. CI is mechanical rejection authority only; MM06 still owns HMAC/evidence verification and mathematical correctness remains with Foundry/checkers.

## Repository protection gate
No calibration cohort counts and no fresh work is eligible until GitHub itself reports the default branch protected with the required consolidation check/source policy. A policy JSON file is not proof of protection.

## Calibration and fresh work
Two consecutive complete, non-superseded, replay-only branch cohorts are required after repository protection is independently observed. Each must close: generation -> 12 isolated worker branches -> MM06 -> structural verifier status -> MF06 -> structural integrator status -> one CAS-protected consolidation PR/merge. Any failure resets the streak. Fresh transport additionally requires a private `FROZEN_PRE_OUTCOME` manifest per scientific assignment.

## Benchmark succession and research
Mastermind and Math Foundry cursors advance independently only from verified completion receipts; terminal does not mean success. No eligible successor enters `BENCHMARK_DISCOVERY_WAIT`. BIL00 alone performs deep research at 00:58 and 12:58 America/Vancouver from MM06-safe/MF06-integrated questions only.

## Dual goals
Goal 1 is the finite fresh verified reaction/cascade advantage at equal complete cost. Goal 2 opens only after Goal 1 and requires same-start, matched-budget, controlled-memory `I_t` vs `I_(t+1)` evidence with solver `F`, memory `M`, and improver `I` separated.
