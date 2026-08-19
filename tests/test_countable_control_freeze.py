import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class CountableControlFreezeTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT / "config/countable_control_set_v25.json").read_text(encoding="utf-8"))
        self.required = set(self.contract["required_control_paths"])

    def test_required_hardening_files_exist(self):
        missing = sorted(path for path in self.required if not (ROOT / path).exists())
        self.assertEqual(missing, [], f"required countable-control files missing: {missing}")

    def test_workaround_and_liveness_are_in_frozen_set(self):
        must = {
            "scripts/reconcile_open_prs.py",
            ".github/workflows/supernova-open-pr-reconciler.yml",
            ".github/workflows/supernova-actions-heartbeat.yml",
            ".github/workflows/supernova-liveness-monitor.yml",
            "scripts/check_lane_liveness.py",
            "config/worker_auth.json",
            "config/checker_pins.json",
            "tests/test_v25_report_contracts.py",
        }
        self.assertTrue(must.issubset(self.required), sorted(must - self.required))

    def test_active_countable_generation_must_freeze_entire_set(self):
        state = json.loads((ROOT / "state/CURRENT.json").read_text(encoding="utf-8"))
        if state.get("calibration_countable_current") is not True:
            self.skipTest("current generation is intentionally non-countable")
        control = json.loads((ROOT / state["active_control_manifest_path"]).read_text(encoding="utf-8"))
        frozen = set(control.get("required_control_paths", []))
        self.assertTrue(self.required.issubset(frozen), sorted(self.required - frozen))
        self.assertTrue(control.get("calibration_countable") is True)
        self.assertEqual(state.get("repo_policy_status"), "VERIFIED_PROTECTED_SOURCE_BOUND")
        self.assertEqual(state.get("protocol_version"), "2.5")


if __name__ == "__main__":
    unittest.main()
