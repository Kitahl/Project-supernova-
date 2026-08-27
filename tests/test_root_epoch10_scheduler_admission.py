import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class RootEpoch10SchedulerAdmissionTests(unittest.TestCase):
    def test_root_epoch_and_seed_are_bound(self):
        epoch = load("config/root_tcb_epoch_v25.json")
        self.assertEqual(epoch["schema_version"], "PS-ROOT-TCB-EPOCH-2.5-11")
        self.assertEqual(epoch["epoch"], 11)
        self.assertEqual(epoch["previous_epoch_blob"], "cf74b9c17bf1d763e7d89dc07f9bb74c334f8b59")
        self.assertEqual(epoch["root_epoch10_scheduler_admission_seed_install_commit_sha"], "7bc97d2bed9fb285feb2e9ae1c31fb4331919d00")
        self.assertEqual(epoch["root_epoch10_scheduler_admission_seed_policy_blob"], "19e7cc66a6152871327b40017e0114115ed76db6")
        self.assertEqual(epoch["root_epoch10_scheduler_admission_seed_reconciler_blob"], "03f8d39d205e8d3f548f1700363e6d714882dca2")
        self.assertEqual(epoch["root_epoch10_scheduler_admission_seed_workflow_blob"], "bd26a6f0f76140e2586bd79e25350a898f942cac")
        self.assertEqual(epoch["scheduler_task_cardinality"], 15)
        self.assertEqual(epoch["scheduler_sixteenth_lane"], "FORBIDDEN")
        self.assertEqual(epoch["scheduler_repair_after_activation"], "REJECTION_ONLY_DISABLE_UNSAFE; NO_CONSTRUCTIVE_REKEY_RESCHEDULE_OR_PROMPT_MUTATION")

    def test_countable_generation_is_four_path_scheduler_bound(self):
        policy = load("config/generation_delta_policy_v25.json")
        self.assertEqual(policy["countable"]["exact_cardinality"], 4)
        self.assertIn("scheduler/{cohort}.json", policy["countable"]["exact_path_templates"])
        self.assertTrue(policy["countable"]["scheduler_admission_required_before_promotion"])
        control = load("schemas/control.schema.json")
        self.assertIn("scheduler_manifest_path", control["properties"])
        self.assertIn("scheduler_admission_required", control["properties"])
        self.assertNotIn("scheduler_manifest_git_identity", control["required"])
        self.assertIn("scheduler_manifest_git_identity", control["properties"])
        self.assertTrue(any(x.get("if", {}).get("required") == ["candidate_nonce"] for x in control["allOf"]))

    def test_authority_inventory_and_countable_surface_include_scheduler_gate(self):
        authority = load("config/admission_authority.json")
        self.assertEqual(authority["root_tcb_epoch"], 11)
        self.assertTrue(authority["scheduler_admission_required_for_countable_promotion"])
        inventory = set(authority["trusted_validator_entrypoints"]) | set(authority["trusted_authority_helpers"]) | set(authority["authoritative_status_workflows"])
        for path in (
            "scripts/scheduler_admission_guard.py",
            "schemas/scheduler_manifest.schema.json",
            "schemas/preactivation_receipt.schema.json",
            "schemas/scheduler_admission.schema.json",
            ".github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml",
        ):
            self.assertIn(path, inventory)
        frozen = set(load("config/countable_control_set_v25.json")["required_control_paths"])
        for path in (
            "config/root_epoch10_scheduler_admission_seed_v25.json",
            "config/root_epoch10_scheduler_admission_epoch_v25.json",
            "scripts/reconcile_root_epoch10_scheduler_admission_seed.py",
            "scripts/scheduler_admission_guard.py",
            "tests/test_scheduler_admission_negative.py",
        ):
            self.assertIn(path, frozen)

    def test_task_registry_keeps_exact_fifteen_same_sessions(self):
        registry = load("config/task_registry_v25.json")
        self.assertEqual(registry["active_task_count"], 15)
        self.assertTrue(registry["no_sixteenth_lane"])
        self.assertTrue(registry["same_task_session_each_run"])
        roles = [row["role_id"] for row in registry["tasks"]]
        self.assertEqual(len(roles), 15)
        self.assertEqual(len(set(roles)), 15)
        self.assertEqual(registry["replacement_task_for_existing_role"], "FORBIDDEN")
        semantics = load("config/task_registry_semantics_v25.json")
        self.assertEqual(semantics["same_task_session_rule"], "SAME_TASK_SESSION")
        self.assertEqual(semantics["active_cohort_repair_rule"], "NO_POST_ACTIVATION_CONSTRUCTIVE_REPAIR")
        self.assertEqual(semantics["scheduler_readback_rule"], "NORMALIZED_SCHEDULER_READBACK")
        self.assertEqual(semantics["preactivation_completion_rule"], "RECEIPT_COMMIT_ALONE_IS_NOT_SUCCESS")
        self.assertEqual(semantics["preactivation_retry_rule"], "RESUME_FROM_FIRST_MISSING_TRANSITION_AND_NEVER_CREATE_A_SECOND_RECEIPT_COMMIT")
        self.assertEqual(semantics["preactivation_state_classifier"], "scripts/preactivation_publication_state.py")

    def test_transition_guard_invokes_scheduler_admission(self):
        text = (ROOT / "scripts/transition_guard.py").read_text(encoding="utf-8")
        self.assertIn("scheduler_admission_guard", text)
        self.assertIn("validate_scheduler_admission", text)
        self.assertIn("validate_countable_scheduler", text)


if __name__ == "__main__":
    unittest.main()
