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

    def test_active_countable_generation_freeze_or_explicit_hardening_supersession(self):
        """Do not require a historical frozen generation to contain future hardening files.

        If the candidate countable-control set is unchanged relative to the active frozen
        generation, the active control must freeze the entire set. If a hardening change
        deliberately enlarges the future control set, the current generation remains
        immutable historical evidence and the only admissible state is streak=0,
        fresh=false, with the contract explicitly requiring a new generation/reset before
        any countable credit can be earned under the changed control.
        """
        state = json.loads((ROOT / "state/CURRENT.json").read_text(encoding="utf-8"))
        if state.get("calibration_countable_current") is not True:
            self.skipTest("current generation is intentionally non-countable")

        control = json.loads((ROOT / state["active_control_manifest_path"]).read_text(encoding="utf-8"))
        frozen = set(control.get("required_control_paths", []))
        proposed_not_in_frozen = sorted(self.required - frozen)

        self.assertTrue(control.get("calibration_countable") is True)
        self.assertEqual(state.get("repo_policy_status"), "VERIFIED_PROTECTED_SOURCE_BOUND")
        self.assertEqual(state.get("protocol_version"), "2.5")

        if proposed_not_in_frozen:
            self.assertEqual(state.get("calibration_streak"), 0)
            self.assertFalse(state.get("fresh_allowed_globally"))
            self.assertEqual(
                self.contract.get("authoritative_change_after_cohort1"),
                "RESETS_CALIBRATION_STREAK_TO_ZERO",
            )
            return

        self.assertTrue(self.required.issubset(frozen), sorted(self.required - frozen))


if __name__ == "__main__":
    unittest.main()
