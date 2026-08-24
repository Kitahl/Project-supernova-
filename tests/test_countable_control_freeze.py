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

    def test_root11_scheduler_stageability_surface_and_history_are_frozen(self):
        self.assertEqual(self.contract["schema_version"], "PS-COUNTABLE-CONTROL-SET-2.5-26")
        must = {
            "scripts/reconcile_open_prs.py",
            ".github/workflows/supernova-open-pr-reconciler.yml",
            ".github/workflows/supernova-actions-heartbeat.yml",
            ".github/workflows/supernova-liveness-monitor.yml",
            "scripts/check_lane_liveness.py",
            "scripts/liveness_contract_guard.py",
            "scripts/strict_json.py",
            "config/root_epoch9_integrity_repair_seed_v25.json",
            "config/root_epoch9_integrity_repair_epoch_v25.json",
            "config/root_epoch10_scheduler_admission_seed_v25.json",
            "config/root_epoch10_scheduler_admission_seed_amendment_v25.json",
            "config/root_epoch10_scheduler_admission_epoch_v25.json",
            "config/root_epoch11_stageability_repair_seed_v25.json",
            "config/root_epoch11_stageability_repair_seed_amendment_v25.json",
            "config/root_epoch11_stageability_repair_epoch_v25.json",
            "scripts/reconcile_root_epoch10_scheduler_admission_seed.py",
            "scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py",
            "scripts/reconcile_root_epoch11_stageability_repair_seed.py",
            "scripts/reconcile_root_epoch11_stageability_repair_seed_amendment.py",
            "scripts/scheduler_admission_guard.py",
            "schemas/scheduler_manifest.schema.json",
            "schemas/preactivation_receipt.schema.json",
            "schemas/scheduler_admission.schema.json",
            "schemas/scheduler_admission_copy.schema.json",
            "schemas/staged_candidate.schema.json",
            "tests/test_root_epoch11_stageability_repair_seed_amendment.py",
            "tests/test_root_epoch10_scheduler_admission.py",
            "tests/test_scheduler_admission_negative.py",
            ".github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml",
            ".github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml",
            ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",
            ".github/workflows/supernova-root-epoch11-stageability-repair-seed-amendment.yml",
            "config/worker_auth.json",
            "config/checker_pins.json",
            "tests/test_v25_report_contracts.py",
            "tests/test_gen11_zero_credit_terminal_transition.py",
        }
        self.assertTrue(must.issubset(self.required), sorted(must - self.required))
        self.assertTrue(self.contract["scheduler_manifest_required_for_countable_generation"])
        self.assertTrue(self.contract["scheduler_admission_required_before_promotion"])
        self.assertEqual(self.contract["canonical_scheduled_task_count"], 15)
        self.assertEqual(self.contract["replacement_scheduled_task"], "FORBIDDEN")

    def test_active_countable_generation_freeze_or_explicit_hardening_supersession(self):
        """Historical Gen11/12 stay immutable; root11/v25 stages a replacement at streak zero."""
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
            marker=json.loads((ROOT/'config/root_epoch10_scheduler_admission_epoch_v25.json').read_text(encoding='utf-8'))
            self.assertEqual(marker['calibration_credit_effect'],0)
            self.assertEqual(marker['calibration_streak_effect'],'RESET_OR_RETAIN_ZERO')
            return

        self.assertTrue(self.required.issubset(frozen), sorted(self.required - frozen))


if __name__ == "__main__":
    unittest.main()
