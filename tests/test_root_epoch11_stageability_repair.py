import json
import pathlib
import unittest
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RootEpoch11StageabilityRepairTests(unittest.TestCase):
    def setUp(self):
        self.epoch = json.loads((ROOT / "config/root_epoch11_stageability_repair_epoch_v25.json").read_text())
        self.control = json.loads((ROOT / "schemas/control.schema.json").read_text())
        self.assignment = json.loads((ROOT / "schemas/assignment.schema.json").read_text())
        self.liveness = json.loads((ROOT / "schemas/cohort_liveness_contract.schema.json").read_text())
        self.manifest = json.loads((ROOT / "schemas/scheduler_manifest.schema.json").read_text())
        self.tcb = json.loads((ROOT / "config/root_tcb_epoch_v25.json").read_text())
        self.authority = json.loads((ROOT / "config/admission_authority.json").read_text())

    def test_seed_completeness_amendment_is_durable_root_authority(self):
        self.assertEqual(self.epoch["schema_version"], "PS-ROOT-EPOCH11-STAGEABILITY-REPAIR-EPOCH-2.5-1")
        for key in (
            "root_epoch11_stageability_repair_seed_amendment_install_commit_sha",
            "root_epoch11_stageability_repair_seed_amendment_policy_blob",
            "root_epoch11_stageability_repair_seed_amendment_reconciler_blob",
            "root_epoch11_stageability_repair_seed_amendment_workflow_blob",
        ):
            self.assertRegex(self.tcb[key], r"^[0-9a-f]{40}$")
        authority_paths = set(self.authority["authoritative_status_workflows"]) | set(self.authority["trusted_authority_helpers"]) | set(self.authority["trusted_validator_entrypoints"])
        for path in (
            "config/root_epoch11_stageability_repair_seed_amendment_v25.json",
            "scripts/reconcile_root_epoch11_stageability_repair_seed_amendment.py",
            ".github/workflows/supernova-root-epoch11-stageability-repair-seed-amendment.yml",
            "tests/test_root_epoch11_stageability_repair_seed_amendment.py",
        ):
            self.assertIn(path, authority_paths)

    def test_epoch_declares_constructable_one_commit_four_path_dag(self):
        self.assertEqual(self.epoch["previous_root_epoch"], 10)
        self.assertEqual(self.epoch["new_root_epoch"], 11)
        self.assertEqual(self.epoch["generation_identity_dag"], "CONTROL_TO_ASSIGNMENT_TO_LIVENESS_TO_SCHEDULER")
        self.assertEqual(self.epoch["generation_commit_shape"], "EXACT_ONE_COMMIT_CHILD_OF_GENERATION_ROOT")
        self.assertEqual(self.epoch["generation_path_cardinality"], 4)
        self.assertEqual(self.epoch["scheduler_manifest_generation_head_sha"], "FORBIDDEN")
        self.assertEqual(self.epoch["control_scheduler_manifest_git_identity"], "FORBIDDEN_FOR_ROOT11_CANDIDATES")

    def test_root11_schemas_leave_future_values_out_of_predecessors(self):
        self.assertNotIn("generation_head_sha", self.control["properties"])
        self.assertNotIn("generation_head_sha", self.manifest["properties"])
        self.assertNotIn("scheduler_manifest_git_identity", self.control["required"])
        self.assertIn("candidate_nonce", self.manifest["required"])
        self.assertIn("generation_root_sha", self.manifest["required"])
        self.assertIn("control_manifest_git_identity", self.manifest["required"])
        self.assertIn("assignment_git_identity", self.manifest["required"])
        self.assertIn("liveness_git_identity", self.manifest["required"])

    def test_current_gen12_remains_schema_valid_with_gen13_staged(self):
        state = json.loads((ROOT / "state/CURRENT.json").read_text())
        state_schema = json.loads((ROOT / "schemas/state.schema.json").read_text())
        self.assertTrue(set(state_schema["required"]).issubset(state))
        self.assertEqual(state["active_cohort_id"], self.epoch["active_source_cohort"])
        self.assertEqual(state["generation_head_sha"], self.epoch["active_source_generation_head"])
        staged = json.loads((ROOT / "state/STAGED.json").read_text())
        staged_schema = json.loads((ROOT / "schemas/staged_candidate.schema.json").read_text())
        self.assertEqual(list(Draft202012Validator(staged_schema).iter_errors(staged)), [])
        self.assertEqual(staged["status"], "STAGED")
        self.assertEqual(staged["active_cohort_id"], state["active_cohort_id"])
        self.assertEqual(staged["active_generation_seq"], state["generation_seq"])
        self.assertEqual(staged["candidate_generation_seq"], state["generation_seq"] + 1)
        self.assertNotEqual(staged["candidate_cohort_id"], state["active_cohort_id"])
        self.assertNotEqual(staged["generation_head_sha"], state["generation_head_sha"])

    def test_branch_reconciler_only_runs_stage_prs_as_trusted_main_logic(self):
        text = (ROOT / ".github/workflows/supernova-branch-reconciler.yml").read_text()
        self.assertIn("pull_request_target:", text)
        self.assertIn("statuses: write", text)
        self.assertIn("head.repo.full_name == github.repository", text)
        self.assertIn("github.event.pull_request.user.login == github.repository_owner", text)
        self.assertIn("startsWith(github.event.pull_request.head.ref, 'ps/stage/')", text)
        self.assertIn("persist-credentials: false", text)
        self.assertNotIn("ref: ${{ github.event.pull_request.head", text)
        self.assertNotIn("git checkout ${{ github.event.pull_request.head", text)
        self.assertIn("scripts/reconcile_branch_statuses.py", text)

    def test_trusted_reconciler_enforces_pointer_cas_and_exact_generation_data(self):
        text = (ROOT / "scripts/reconcile_branch_statuses.py").read_text()
        for token in (
            'changed(repo, base, pointer_head) != ["state/STAGED.json"]',
            'one_commit_child(repo, pointer_head, base)',
            'pointer.get("stage_base_head") != base or generation_root != base',
            'one_commit_child(repo, str(generation_head), str(generation_root))',
            'observed_status != [("A", path) for path in sorted(expected_paths)]',
            '"C/A/L/S candidate nonce chain mismatch"',
            '"C -> A -> L blob DAG mismatch"',
            '"C/A/L -> S blob DAG mismatch"',
            '"manifest contains forbidden future generation head"',
        ):
            self.assertIn(token, text)

    def test_root11_policy_keeps_exact_fifteen_and_no_sixteenth_lane(self):
        registry = json.loads((ROOT / "config/task_registry_v25.json").read_text())
        self.assertEqual(self.epoch["active_task_count"], 15)
        self.assertTrue(self.epoch["no_sixteenth_lane"])
        self.assertEqual(registry["active_task_count"], 15)
        self.assertTrue(registry["no_sixteenth_lane"])
        self.assertEqual(len(registry["tasks"]), 15)
        self.assertEqual(len({row["role_id"] for row in registry["tasks"]}), 15)


if __name__ == "__main__":
    unittest.main()
