import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/root_epoch8_status_writer_repair_seed_v25.json"
SCRIPT = ROOT / "scripts/reconcile_root_epoch8_status_writer_repair_seed.py"
WORKFLOW = ROOT / ".github/workflows/supernova-root-epoch8-status-writer-repair-seed.yml"


class RootEpoch8StatusWriterRepairSeedTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_seed_is_one_shot_epoch7_to_epoch8(self):
        self.assertEqual(self.policy["schema_version"], "PS-ROOT-EPOCH8-STATUS-WRITER-REPAIR-SEED-2.5-1")
        self.assertEqual(self.policy["stable_issue_id"], "O-T0-GEN10-HISTORICAL-INTEGRATION-STATUS-DRIFT")
        self.assertEqual(self.policy["required_current_root_epoch"], 7)
        self.assertEqual(self.policy["target_root_epoch"], 8)
        self.assertEqual(self.policy["calibration_streak_required"], 0)
        self.assertFalse(self.policy["fresh_allowed_globally_required"])
        self.assertEqual(self.policy["one_shot_marker_path"], "config/root_epoch8_status_writer_repair_epoch_v25.json")

    def test_candidate_diff_is_exact_and_complete(self):
        allowed = set(self.policy["allowed_root_candidate_paths"])
        required = set(self.policy["required_root_candidate_paths"])
        self.assertEqual(allowed, required)
        self.assertEqual(len(required), 12)
        for path in (
            "config/admission_authority.json",
            "config/authority_bootstrap_v25.json",
            "config/countable_control_set_v25.json",
            "config/root_tcb_epoch_v25.json",
            "config/root_epoch8_status_writer_repair_epoch_v25.json",
            "scripts/reconcile_v25_admission.py",
            "scripts/reconcile_authority_bootstrap.py",
            "tests/test_structural_status_single_writer.py",
            "tests/test_bootstrap_root_tcb_and_head_binding.py",
            "tests/test_gen10_zero_credit_terminal_transition.py",
            "tests/test_gen9_reset_compat_root.py",
            "tests/test_root_epoch6_repair.py",
        ):
            self.assertIn(path, required)

    def test_seed_cannot_self_modify_or_touch_state_runtime_science(self):
        self.assertTrue(set(self.policy["seed_paths"]).isdisjoint(self.policy["required_root_candidate_paths"]))
        for prefix in ("state/", "runtime/", "benchmark/", "research/"):
            self.assertIn(prefix, self.policy["forbidden_candidate_prefixes"])
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("seed self-modification forbidden", text)
        self.assertIn("root epoch8 status-writer repair marker already exists", text)
        self.assertIn("canonical Gen10 state blob changed", text)

    def test_candidate_is_read_only_and_trusted_seed_uses_accepted_main(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('GITHUB_TOKEN: ""', text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("Clone exact accepted main seed bytes", text)
        self.assertIn("statuses: write", text)
        self.assertIn("scripts/assert_validator_environment.py", text)
        self.assertIn("cd trusted && python3 scripts/reconcile_root_epoch8_status_writer_repair_seed.py", text)

    def test_root_candidate_must_remove_duplicate_structural_writer_without_weakening_admission_fan_in(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for token in (
            "supernova/branch-integrate",
            "ih,ie=integration_check(state,vh)",
            "rs=result_state(ve+ie,ri_wait)",
            "supernova/report-admission",
            "integration_semantic_errors",
            "structural_status_writer_cardinality",
        ):
            self.assertIn(token, text)

    def test_future_control_set_must_freeze_seed_and_repair(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("PS-COUNTABLE-CONTROL-SET-2.5-23", text)
        for path in (
            "scripts/reconcile_v25_admission.py",
            "scripts/reconcile_authority_bootstrap.py",
            "tests/test_structural_status_single_writer.py",
            "tests/test_bootstrap_root_tcb_and_head_binding.py",
            "tests/test_gen10_zero_credit_terminal_transition.py",
            "tests/test_gen9_reset_compat_root.py",
            "tests/test_root_epoch6_repair.py",
        ):
            self.assertIn(path, text)


if __name__ == "__main__":
    unittest.main()
