import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/root_epoch6_repair_seed_v25.json"
SCRIPT = ROOT / "scripts/reconcile_root_epoch6_repair_seed.py"
WORKFLOW = ROOT / ".github/workflows/supernova-root-epoch6-repair-seed.yml"


class RootEpoch6RepairSeedTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_seed_is_one_shot_epoch5_to_epoch6(self):
        self.assertEqual(self.policy["required_current_root_epoch"], 5)
        self.assertEqual(self.policy["target_root_epoch"], 6)
        self.assertEqual(self.policy["calibration_streak_required"], 0)
        self.assertFalse(self.policy["fresh_allowed_globally_required"])
        self.assertEqual(self.policy["one_shot_marker_path"], "config/root_epoch6_repair_epoch_v25.json")

    def test_candidate_diff_is_exact_and_covers_both_repairs_and_epoch_history_regression(self):
        allowed = set(self.policy["allowed_root_candidate_paths"])
        required = set(self.policy["required_root_candidate_paths"])
        self.assertEqual(allowed, required)
        for path in (
            "scripts/reconcile_v25_admission.py",
            "schemas/branch_verification.schema.json",
            "schemas/branch_integration.schema.json",
            "scripts/reconcile_open_prs.py",
            "scripts/reconcile_authority_bootstrap.py",
            "scripts/diagnose_authority_bootstrap.py",
            "config/root_tcb_epoch_v25.json",
            "config/root_epoch6_repair_epoch_v25.json",
            "tests/test_gen9_reset_compat_root.py",
        ):
            self.assertIn(path, required)
        self.assertEqual(len(required), 17)
        self.assertIn("state/", self.policy["forbidden_candidate_prefixes"])
        self.assertIn("runtime/", self.policy["forbidden_candidate_prefixes"])
        self.assertIn("benchmark/", self.policy["forbidden_candidate_prefixes"])

    def test_seed_cannot_self_modify(self):
        self.assertTrue(set(self.policy["seed_paths"]).isdisjoint(self.policy["required_root_candidate_paths"]))
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("seed self-modification forbidden", text)
        self.assertIn('set(changed) != required', text)
        self.assertIn("root epoch6 repair marker already exists", text)

    def test_candidate_job_is_read_only_and_trusted_seed_is_accepted_main(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('GITHUB_TOKEN: ""', text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("statuses: write", text)
        self.assertIn("Clone exact accepted main seed bytes", text)
        self.assertIn("scripts/assert_validator_environment.py", text)
        self.assertIn("cd trusted && python3 scripts/reconcile_root_epoch6_repair_seed.py", text)

    def test_root_candidate_must_close_quarantine_and_bootstrap_durability(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED", text)
        self.assertIn("open-PR reconciler lacks persistent workflow-run provenance re-derivation", text)
        self.assertIn("bootstrap diagnostic does not bind diagnosed head/base", text)
        self.assertIn("VERIFIED_WITH_QUARANTINES", text)
        self.assertIn("terminal quarantine admission repair incomplete", text)


if __name__ == "__main__":
    unittest.main()
