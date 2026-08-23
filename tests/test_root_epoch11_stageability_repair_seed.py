import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "root_epoch11_stageability_repair_seed_v25.json"
SCRIPT = ROOT / "scripts" / "reconcile_root_epoch11_stageability_repair_seed.py"
WORKFLOW = ROOT / ".github" / "workflows" / "supernova-root-epoch11-stageability-repair-seed.yml"


def load_seed_module():
    spec = importlib.util.spec_from_file_location("root11_stageability_seed_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RootEpoch11StageabilityRepairSeedTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_seed_is_exact_root10_to_root11_zero_credit_authority_change(self):
        p = self.policy
        self.assertEqual(p["schema_version"], "PS-ROOT-EPOCH11-STAGEABILITY-REPAIR-SEED-2.5-1")
        self.assertEqual(p["issue_ref"], "#233")
        self.assertEqual(p["required_seed_base_main_sha"], "8a5d2acedc9f29602fc350bb499cedc0769a9a73")
        self.assertEqual(p["required_current_root_epoch"], 10)
        self.assertEqual(p["required_current_root_epoch_blob"], "cf74b9c17bf1d763e7d89dc07f9bb74c334f8b59")
        self.assertEqual(p["target_root_epoch"], 11)
        self.assertEqual(p["required_state_blob"], "826fcdd01701eda04a177f86748878b3755badc0")
        self.assertEqual(p["required_active_cohort"], "CAL-BR-012-v25-4ca0dec6")
        self.assertEqual(p["required_generation_head"], "b366cf01e64e1a00a2e566e14e25cc7c15ce523f")
        self.assertEqual(p["required_verifier_head"], "da657eb8f839f565083d90e5f743472da2a6da63")
        self.assertEqual(p["required_verifier_blob"], "251e306b062de5386f3c8a1ff7d80683515547fd")
        self.assertEqual(p["required_mf06_head"], "70ceb6b88517f5a2b1a2b724fbb1b6c627a192aa")
        self.assertEqual(p["required_mf06_blob"], "c95828e741da0e8c8ed323a821b92fdc920e259b")
        self.assertEqual(p["required_terminal_partition"], {
            "safe": 0,
            "quarantined": 0,
            "missing": 12,
            "calibration_credit": 0,
            "calibration_streak": 0,
            "fresh_allowed_globally": False,
        })
        self.assertEqual(set(p["required_missing_workers"]), {"MF01", "MF02", "MF03", "MF04", "MF05", "MM01", "MM02", "MM03", "MM04", "MM05", "MM07", "EXT01"})
        self.assertEqual(p["seed_self_modification"], "FORBIDDEN")
        self.assertEqual(p["failure_semantics"], "FAIL_CLOSED")
        self.assertNotIn("seed_context", p)
        self.assertEqual(p["historical_status_provenance"], "OBSERVED_GITHUB_ACTIONS_BOT_SUCCESS_WITHOUT_TARGET_URL_NO_WORKFLOW_IDENTITY_CLAIM")
        self.assertNotIn("supernova/root-epoch11-stageability-repair-seed", self.script)

    def test_root10_initial_and_amendment_anchors_are_frozen(self):
        p = self.policy
        self.assertEqual(len(p["frozen_root10_anchors"]), 8)
        self.assertEqual(len(p["frozen_root10_paths"]), 8)
        for path in (
            "config/root_epoch10_scheduler_admission_seed_v25.json",
            "scripts/reconcile_root_epoch10_scheduler_admission_seed.py",
            ".github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml",
            "tests/test_root_epoch10_scheduler_admission_seed.py",
            "config/root_epoch10_scheduler_admission_seed_amendment_v25.json",
            "scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py",
            ".github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml",
            "tests/test_root_epoch10_scheduler_admission_seed_amendment.py",
        ):
            self.assertRegex(p["frozen_root10_paths"][path], r"^[0-9a-f]{40}$")
        self.assertIn('policy["frozen_root10_paths"].items()', self.script)
        self.assertIn('policy["frozen_root10_anchors"].items()', self.script)

    def test_candidate_surface_is_exact_and_excludes_seed_state_and_evidence(self):
        p = self.policy
        expected = {
            ".github/workflows/supernova-branch-reconciler.yml",
            ".github/workflows/supernova-open-pr-reconciler.yml",
            ".github/workflows/supernova-preactivation-admission.yml",
            ".github/workflows/supernova-rest-branch-reconciler.yml",
            "branch/CONFIG.json",
            "config/admission_authority.json",
            "config/authority_bootstrap_v25.json",
            "config/countable_control_set_v25.json",
            "config/generation_delta_policy_v25.json",
            "config/repo_policy.json",
            "config/root_epoch11_stageability_repair_epoch_v25.json",
            "config/root_tcb_epoch_v25.json",
            "config/scheduler_attestation_authority_v25.json",
            "config/task_registry_semantics_v25.json",
            "config/task_registry_v25.json",
            "config/worker_auth.json",
            "schemas/assignment.schema.json",
            "schemas/branch_consolidation.schema.json",
            "schemas/branch_integration.schema.json",
            "schemas/branch_verification.schema.json",
            "schemas/cohort_liveness_contract.schema.json",
            "schemas/control.schema.json",
            "schemas/preactivation_receipt.schema.json",
            "schemas/scheduler_admission_copy.schema.json",
            "schemas/scheduler_admission.schema.json",
            "schemas/scheduler_inventory_attestation.schema.json",
            "schemas/scheduler_manifest.schema.json",
            "schemas/staged_candidate.schema.json",
            "schemas/state.schema.json",
            "scripts/generation_delta_guard.py",
            "scripts/liveness_contract_guard.py",
            "scripts/reconcile_authority_bootstrap.py",
            "scripts/reconcile_branch_statuses.py",
            "scripts/reconcile_open_prs.py",
            "scripts/reconcile_preactivation_admission.py",
            "scripts/reconcile_ruleset_attestation.py",
            "scripts/reconcile_v25_admission.py",
            "scripts/scheduler_admission_guard.py",
            "scripts/transition_guard.py",
            "scripts/validate_branch_bus_v251.py",
            "scripts/validate_bus.py",
            "tests/test_actions_trigger_bridge.py",
            "tests/test_bootstrap_root_tcb_and_head_binding.py",
            "tests/test_bootstrap_status_provenance.py",
            "tests/test_countable_control_freeze.py",
            "tests/test_countable_control_gate_consistency.py",
            "tests/test_countable_scheduler_postpromotion_refs.py",
            "tests/test_gen10_zero_credit_terminal_transition.py",
            "tests/test_gen11_zero_credit_terminal_transition.py",
            "tests/test_gen9_reset_compat_root.py",
            "tests/test_generation_delta_policy.py",
            "tests/test_preactivation_production_absence.py",
            "tests/test_preactivation_status_provenance.py",
            "tests/test_root_epoch10_scheduler_admission.py",
            "tests/test_root_epoch11_stageability_repair.py",
            "tests/test_root_epoch6_repair.py",
            "tests/test_root_epoch9_integrity_repair.py",
            "tests/test_root11_consolidation_evidence.py",
            "tests/test_root11_promotion_create_once.py",
            "tests/test_root11_remote_gates.py",
            "tests/test_ruleset_status_attestation.py",
            "tests/test_scheduler_active_phase_validation.py",
            "tests/test_scheduler_admission_construction.py",
            "tests/test_scheduler_admission_negative.py",
            "tests/test_scheduler_retry_budget_freeze.py",
            "tests/test_scheduler_timing_contract.py",
            "tests/test_staged_candidate_admission.py",
            "tests/test_structural_status_single_writer.py",
            "tests/test_v25_report_contracts.py",
        }
        self.assertEqual(len(expected), 69)
        self.assertEqual(set(p["allowed_root_candidate_paths"]), expected)
        self.assertEqual(set(p["required_root_candidate_paths"]), expected)
        self.assertTrue(set(p["seed_paths"]).isdisjoint(expected))
        self.assertEqual(set(p["expected_root_candidate_blobs"]), expected - {"config/root_tcb_epoch_v25.json"})
        self.assertEqual(len(p["expected_root_candidate_blobs"]), len(expected) - 1)
        self.assertRegex(p["expected_normalized_root_tcb_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(set(p["root_tcb_dynamic_seed_bindings"]), {
            "root_epoch11_stageability_repair_seed_install_commit_sha",
            "root_epoch11_stageability_repair_seed_policy_blob",
            "root_epoch11_stageability_repair_seed_reconciler_blob",
            "root_epoch11_stageability_repair_seed_workflow_blob",
        })
        self.assertEqual(len(set(p["root_tcb_dynamic_seed_bindings"].values())), 4)
        for prefix in ("state/", "control/", "assignments/", "liveness/", "scheduler/", "scheduler_admission/", "preactivation/", "reports/", "verification/", "integration/", "history/", "runtime/", "benchmark/", "research/"):
            self.assertIn(prefix, p["forbidden_candidate_prefixes"])

    def test_seed_requires_acyclic_construction_and_post_g_admission(self):
        p = self.policy
        self.assertEqual(p["candidate_construction_order"], [
            "control/{cohort}.json",
            "assignments/{cohort}.json",
            "liveness/{cohort}.json",
            "scheduler/{cohort}.json",
        ])
        self.assertEqual(p["staging_pointer_path"], "state/STAGED.json")
        for token in (
            "generation_root_sha",
            "generation_head_sha",
            "actual_candidate_head",
            "state/STAGED.json",
            "scheduler_manifest_git_identity",
            "scheduler_admission_copy.schema.json",
            "source_preactivation_admission_commit_sha",
            "source_preactivation_admission_blob_sha",
            "validate_scheduler_admission",
            "PREACTIVATION_WAIT",
            "supernova/branch-generation",
            "SUPERNOVA_VALIDATE_ROOT",
            "exact ordered four-path C->A->L->S DAG",
        ):
            self.assertIn(token, self.script)
        self.assertIn("parse_constant=_reject_constant", self.script)
        self.assertIn("object_pairs_hook=_unique_pairs", self.script)
        self.assertIn("allow_nan=False", self.script)
        self.assertIn("exact_pinned_candidate", self.script)
        self.assertIn("expected_root_candidate_blobs", self.script)
        self.assertIn("expected_normalized_root_tcb_sha256", self.script)

    def test_privileged_workflow_separates_candidate_from_status_writer(self):
        candidate, trusted = self.workflow.split("  trusted-seed:", 1)
        self.assertIn("pull_request_target:", self.workflow)
        self.assertNotIn("workflow_dispatch:", self.workflow)
        self.assertNotIn("statuses: write", candidate)
        self.assertIn('GITHUB_TOKEN: ""', candidate)
        self.assertIn("persist-credentials: false", candidate)
        self.assertIn("scripts/validate_bus.py", candidate)
        self.assertIn("tests.test_scheduler_admission_construction", candidate)
        self.assertIn("unittest discover", candidate)
        self.assertIn("needs: candidate-diagnostics", trusted)
        self.assertIn("statuses: write", trusted)
        self.assertNotIn("contents: write", trusted)
        self.assertIn("remote set-url origin", trusted)
        self.assertIn("reconcile_root_epoch11_stageability_repair_seed.py", trusted)
        self.assertNotIn("GITHUB_TOKEN: \"\"", trusted)

    def test_exact_pin_gate_rejects_unpinned_or_non_dynamic_root_drift(self):
        module = load_seed_module()
        root_path = "config/root_tcb_epoch_v25.json"
        candidate_path = "scripts/pinned.py"
        seed_paths = ["config/seed.json", "scripts/seed.py", ".github/workflows/seed.yml", "tests/test_seed.py"]
        trusted = "1" * 40
        seed_blobs = ["2" * 40, "3" * 40, "4" * 40]
        dynamic = {
            "root_epoch11_stageability_repair_seed_install_commit_sha": "__INSTALL__",
            "root_epoch11_stageability_repair_seed_policy_blob": "__POLICY__",
            "root_epoch11_stageability_repair_seed_reconciler_blob": "__SCRIPT__",
            "root_epoch11_stageability_repair_seed_workflow_blob": "__WORKFLOW__",
        }
        root_tcb = {
            "epoch": 11,
            "static_rule": "FAIL_CLOSED",
            "root_epoch11_stageability_repair_seed_install_commit_sha": trusted,
            "root_epoch11_stageability_repair_seed_policy_blob": seed_blobs[0],
            "root_epoch11_stageability_repair_seed_reconciler_blob": seed_blobs[1],
            "root_epoch11_stageability_repair_seed_workflow_blob": seed_blobs[2],
        }
        normalized = dict(root_tcb)
        for key, sentinel in dynamic.items():
            normalized[key] = sentinel
        policy = {
            "required_root_candidate_paths": [root_path, candidate_path],
            "expected_root_candidate_blobs": {candidate_path: "5" * 40},
            "root_tcb_dynamic_seed_bindings": dynamic,
            "expected_normalized_root_tcb_sha256": module.canonical_sha256(normalized),
            "seed_paths": seed_paths,
        }
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            (tmp / "config").mkdir()
            (tmp / root_path).write_text(json.dumps(root_tcb), encoding="utf-8")
            observed = {
                candidate_path: "5" * 40,
                seed_paths[0]: seed_blobs[0],
                seed_paths[1]: seed_blobs[1],
                seed_paths[2]: seed_blobs[2],
            }
            original = module.blob_at
            module.blob_at = lambda ref, path, cwd=module.ROOT: observed.get(path)
            try:
                self.assertEqual(module.exact_pinned_candidate(tmp, trusted, policy), (True, ""))
                drifted = dict(root_tcb)
                drifted["static_rule"] = "WEAKENED"
                (tmp / root_path).write_text(json.dumps(drifted), encoding="utf-8")
                self.assertFalse(module.exact_pinned_candidate(tmp, trusted, policy)[0])
                policy["expected_root_candidate_blobs"] = {}
                self.assertFalse(module.exact_pinned_candidate(tmp, trusted, policy)[0])
            finally:
                module.blob_at = original


if __name__ == "__main__":
    unittest.main()
