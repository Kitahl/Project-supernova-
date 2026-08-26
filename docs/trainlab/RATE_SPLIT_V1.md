# TRAIN rate split v1

Status: dormant engineering contract. Authority: none. Scientific, fresh, calibration, and promotion credit: zero.

## Decision

Supernova has two clocks and two archives.

The fast clock is a bounded TRAIN-only evolution loop. It may generate, verify, compare, and retain many candidate attempts without creating an assurance generation for every attempt. The slow clock is the existing protocol-2.5 assurance pipeline. It continues to own countability, protected evidence, admission, integration, and promotion.

This is not an early opening of Goal 2. It implements the dormant contract for `plan/PLAN.json` stage `0-LOOP`, which is explicitly non-admissible TRAIN work. Goal 2 remains gated by Goal 1 and the later programme gates.

Nothing in this tranche executes a candidate or changes the active pipeline. Activation remains blocked until all of the following are true:

- T0 is qualified;
- a TRAIN pool is sealed prospectively;
- the pinned formal toolchain is qualified;
- an adversarial candidate sandbox is qualified;
- the execution and authority separation is reviewed independently.

## Rate boundary

Fast TRAIN loop:

`frozen pilot -> homogeneous proposals -> materialized candidates -> DIAG evaluation -> frozen candidates -> SELECT evaluation -> integrity receipts -> deterministic TRAIN selector -> archive snapshot`

Slow assurance loop:

`scientific milestone -> existing stage/preactivation/admission pipeline -> existing integrity and integration authorities -> existing immutable history`

The fast loop may nominate a TRAIN parent. It cannot create a scientific claim, change calibration, request a protected status, alter `state/`, write a `ps/*` ref, or ask the slow loop to promote anything. A later, separately authorized bridge would be required to submit a frozen scientific milestone to assurance.

## Separate archives

The TRAIN evolution archive is a content-addressed object store outside the Git worktree. It stores zero-authority engineering records and immutable snapshots. It is not `ps/gen/*`, `history/*`, `reports/*`, or any other assurance archive.

The assurance archive remains unchanged in Git. A TRAIN object digest is never evidence that an assurance generation ran or passed.

The v1 store has single-writer semantics. Multi-writer publication is not authorized by this tranche.

## Identities

A single identifier cannot both deduplicate executable content and bind lineage/proposer provenance. V1 therefore uses four identities:

1. `artifact_id` identifies only the normalized materialized source tree. Identical executable trees share this identity regardless of parent, patch path, role, task, or cohort.
2. `candidate_id` identifies the canonical candidate record and binds `artifact_id`, parent, patch, mutation operator/configuration, and runtime contract.
3. `proposal_id` separately binds proposer session/label and proposal artifact. Two proposers may nominate one candidate while retaining two proposal events.
4. `snapshot_id` binds the prior snapshot plus the complete sorted evidence-object sets.

Every identifier is SHA-256 domain-separated. The executor must compute the normalized tree digest and `artifact_id`; model-supplied digests are never trusted.

## Cost qualification smoke

Before the 64-instance selector pilot, a separate `COST_SMOKE_MANIFEST` fixes exactly 20 engineering instances, one parent, and three children. It measures Actions minutes, model cost, wall time, compile rate, and container-failure rate only. It cannot select a parent, claim improvement, request assurance, or receive scientific/calibration/fresh credit.

The smoke is sizing evidence, not a smaller scientific pilot. Its observed rates are reported with denominators and uncertainty; three children cannot establish reliable compile or improvement rates.

## Pilot contract

The first possible pilot is exactly 64 unique TRAIN instances:

- 32 `DIAG` instances available to the mutator;
- 32 `SELECT` instances hidden from mutation and used only by the selector.

There is no `SEALED` or `REGRESSION` split at this size. The split, statement digests, benchmark snapshot, toolchain, environment, budget contract, stopping rule, and selector seed must be frozen before outcomes exist. Any instance or statement digest appearing in both partitions invalidates the pilot.

V1 permits only `HOMOGENEOUS_PATCH_MUTATION_V1`. Role-specialized mutation is a future ablation, not an assumed improvement. Stage `0-LOOP` remains capped at four selected-parent transitions. Candidate attempts within a transition do not each consume an assurance generation, but all attempts and costs remain archived.

Both DIAG and SELECT are adaptive TRAIN data. They can never later become CALIBRATION, G1, G8, Goal 1, or Goal 2 evidence.

## Responsibilities

The contract separates data responsibilities; it does not claim that separate Python functions create independent authorities.

- Proposal records preserve mutation provenance and cost.
- Candidate records bind candidate content without role identity.
- Evaluation records cover exactly one frozen partition, bind both candidate-record and executable-artifact identity, and carry complete-cost accounting.
- A pinned Math Foundry verifier owns benchmark execution semantics. GitHub Actions may host the job and transport its receipt, but has no scientific or selection authority. A fresh trusted collector parses bounded output without importing candidate code.
- Integrity records emit only `ADMISSIBLE`, `QUARANTINED`, or `MISSING` plus structural/hash facts. They do not rank or select.
- The deterministic selector consumes only admissible SELECT evaluations. It does not consume DIAG outcomes and cannot promote.
- Archive snapshots bind candidates, provenance, evaluations, integrity, and selections.

The existing MM06, MF06, BIL00, scheduled-task IDs, credentials, and protected status contexts are not used or renamed by this tranche.

## Selection and cost

The v1 selector orders admissible SELECT evaluations by:

1. descending PASS count;
2. ascending `C_complete` total;
3. a frozen seeded SHA-256 tie break;
4. candidate ID as the final deterministic ordering key.

`C_complete` contains instrumentation, data, training amortization, inference, probe, execution, verification, fidelity, revalidation, failure/recovery, and metalevel selection. The total must equal the sum of those components.

This policy is a testable placeholder for a small TRAIN pilot, not evidence that it is the scientifically correct long-run selector.

## Candidate security boundary

Candidate code is untrusted. Omitting a token argument is insufficient. Before activation, execution must occur in a separate capability boundary with:

- no repository or model credentials;
- no GitHub token, OIDC handle, credential helper, or `.git` directory;
- no general network egress; bounded inference is available only through a policy-enforcing host broker that holds raw provider credentials outside the container;
- no Docker/container socket or other host-control interface (a narrowly mounted inference-broker socket is a distinct bounded capability);
- a sanitized candidate worktree with no `.git`, hidden SELECT material, reference solution, or grader implementation;
- SELECT material available only inside a separate trusted grader and never copied into the candidate image;
- no writable trusted source, control, or output files;
- a fresh trusted collector that parses bounded output as data and never imports candidate code.

The current candidate schema says execution is not authorized until that boundary is qualified. This tranche adds no workflow, secret, broker, or runner.

## Implemented checks

`trainlab/rate_split.py` and `trainlab/contracts/rate_split_record.schema.json` implement the dormant record contract, content identities, score-blind integrity classification, deterministic TRAIN selection, content-addressed object storage, and snapshot roots.

`trainlab/tests/test_rate_split.py` checks, among other cases:

- exact 20-instance, one-parent/three-child non-selecting cost smoke;
- exact 32/32 unique DIAG/SELECT membership;
- no extra split at pilot size;
- homogeneous mutation only;
- role/cohort/task/credential fields rejected from candidates;
- artifact identity depends only on the normalized tree while candidate-record identity binds parent, patch, operator, and runtime contract;
- parent, patch, or tree changes alter candidate-record identity;
- proposer changes preserve candidate identity but alter proposal identity;
- record-type digest substitution fails;
- complete partition coverage and exact statement/source/snapshot/artifact binding;
- GitHub Actions cannot substitute for Math Foundry execution authority and the collector cannot import candidate code;
- SELECT material and raw provider credentials are forbidden from the candidate boundary;
- complete-cost arithmetic;
- score-blind integrity classification;
- DIAG and quarantined evidence excluded from selection;
- permutation-invariant deterministic selection;
- BIL00/MM06/promotion fields rejected from selection;
- immutable-store idempotence and corruption detection;
- archive roots inside the Git worktree rejected;
- snapshot roots bind provenance and evidence;
- every record remains zero-authority and zero-credit.

Because `trainlab/**` is intentionally outside the active authority paths, existing Candidate Diagnostics will not discover `trainlab/tests` automatically. Until a later authority-changing CI tranche is explicitly admitted, reviewers must run:

```text
python -B -m unittest discover -s trainlab/tests -p "test_*.py" -v
```

That limitation is explicit: a manual green run is engineering evidence, not an active programme gate.
