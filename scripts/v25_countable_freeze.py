#!/usr/bin/env python3
from __future__ import annotations

# Minimum immutable control surface required before any protocol-2.5 cohort may
# receive calibration credit. Cohort-specific control/assignment receipts are
# bound separately by state/CURRENT.json and generation_check().
COUNTABLE_REQUIRED_CONTROL_PATHS = frozenset({
    # Protocol, session, plan and authority standards.
    'PROTOCOL.md',
    'WORKER_PROTOCOL.md',
    'BRANCH_PROTOCOL.md',
    'BRANCH_WORKER_PROTOCOL.md',
    'SESSION_STANDARD.md',
    'plan/PLAN.json',
    'branch/CONFIG.json',
    'config/protocol_freeze.json',
    'config/repo_policy.json',
    'config/roles.json',
    'config/worker_auth.json',
    'config/task_registry_v25.json',
    'config/tool_authority.json',
    'config/rev4_execution.json',
    'config/rev4_lane_ownership.json',
    'docs/PROJECT_SUPERNOVA_SPEC_REV4.md',
    'docs/REV4_SOURCE_INTEGRITY.json',
    'research/open_lanes.json',

    # Benchmark separation and dependency lock.
    'benchmark/registry.json',
    'benchmark/pool_disposition.json',
    'requirements-validation.lock',

    # Closed transport/runtime schemas and verifier-assurance/liveness contracts.
    'schemas/state.schema.json',
    'schemas/control.schema.json',
    'schemas/assignment.schema.json',
    'schemas/branch_report.schema.json',
    'schemas/branch_verification.schema.json',
    'schemas/branch_integration.schema.json',
    'schemas/branch_director.schema.json',
    'schemas/branch_consolidation.schema.json',
    'schemas/benchmark_registry.schema.json',
    'schemas/benchmark_completion.schema.json',
    'schemas/private_manifest_contract.schema.json',
    'schemas/runtime_update.schema.json',
    'schemas/cohort_liveness_contract.schema.json',
    'schemas/lane_liveness_observation.schema.json',
    'schemas/verifier_assurance.schema.json',
    'schemas/model_qualification_certificate.schema.json',

    # Validators, reconcilers, admission/liveness watchdogs and transition guards.
    'scripts/validate_bus.py',
    'scripts/validate_branch_bus_v251.py',
    'scripts/ci_guard.py',
    'scripts/parent_lineage_guard.py',
    'scripts/transition_guard.py',
    'scripts/reconcile_branch_statuses.py',
    'scripts/reconcile_branch_rest.py',
    'scripts/reconcile_v25_admission.py',
    'scripts/v25_countable_freeze.py',
    'scripts/check_lane_liveness.py',
    'scripts/dispatch_missing_pr_admission.py',

    # Positive/negative guard tests must travel with the code they authorize.
    'tests/test_ci_guard.py',
    'tests/test_parent_lineage_guard.py',
    'tests/test_transition_guard.py',
    'tests/test_reconcile_branch_rest_guard.py',
    'tests/test_reconcile_v25_admission_states.py',
    'tests/test_v25_countable_freeze_gate.py',
    'tests/test_pr_admission_watchdog_guard.py',
    'tests/liveness/test_liveness_monitor.py',
    'tests/liveness/test_liveness_schema.py',
    'tests/verifier_assurance/test_verifier_assurance_schema.py',

    # Exact workflow bytes are frozen; action references inside them remain
    # subject to the protocol's full-SHA pin rule.
    '.github/workflows/supernova-actions-heartbeat.yml',
    '.github/workflows/supernova-branch-reconciler.yml',
    '.github/workflows/supernova-rest-branch-reconciler.yml',
    '.github/workflows/supernova-v25-admission.yml',
    '.github/workflows/supernova-liveness-monitor.yml',
})


def missing_countable_control_paths(required_paths):
    """Return a deterministic tuple of countable-gate paths not frozen by control."""
    return tuple(sorted(COUNTABLE_REQUIRED_CONTROL_PATHS.difference(set(required_paths or ()))))
