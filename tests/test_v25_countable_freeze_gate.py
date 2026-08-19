import unittest

from scripts.v25_countable_freeze import (
    COUNTABLE_REQUIRED_CONTROL_PATHS,
    missing_countable_control_paths,
)


class CountableV25FreezeGateTests(unittest.TestCase):
    def test_complete_required_set_has_no_missing_paths(self):
        self.assertEqual(
            missing_countable_control_paths(COUNTABLE_REQUIRED_CONTROL_PATHS),
            (),
        )

    def test_removing_any_required_path_is_detected(self):
        for path in sorted(COUNTABLE_REQUIRED_CONTROL_PATHS):
            with self.subTest(path=path):
                incomplete = set(COUNTABLE_REQUIRED_CONTROL_PATHS)
                incomplete.remove(path)
                self.assertEqual(missing_countable_control_paths(incomplete), (path,))

    def test_gate_carries_pre_countable_hardening_assets(self):
        required = {
            'config/worker_auth.json',
            'scripts/validate_branch_bus_v251.py',
            'schemas/verifier_assurance.schema.json',
            'schemas/cohort_liveness_contract.schema.json',
            'scripts/check_lane_liveness.py',
            'scripts/dispatch_missing_pr_admission.py',
            'tests/test_pr_admission_watchdog_guard.py',
            '.github/workflows/supernova-v25-admission.yml',
            '.github/workflows/supernova-liveness-monitor.yml',
            'requirements-validation.lock',
        }
        self.assertTrue(required.issubset(COUNTABLE_REQUIRED_CONTROL_PATHS))


if __name__ == '__main__':
    unittest.main()
