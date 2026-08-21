import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOUNDRY = "5bfe4bf2cc7e8c4cb9751b831803e28eb45cebe22c0085310c8f00459caf994e"
MASTERMIND = "026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d"

class FrozenSubstrateEpochTests(unittest.TestCase):
    def test_countable_substrate_epoch_is_exact_and_ready(self):
        epoch = json.loads((ROOT / "config" / "substrate_epoch_v25.json").read_text(encoding="utf-8"))
        self.assertEqual(epoch["task_network_plan_id"], "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa")
        self.assertEqual(epoch["protocol_version"], "2.5")
        self.assertEqual(epoch["status"], "FROZEN_FOR_COUNTABLE_CALIBRATION")
        self.assertTrue(epoch["countable_freeze"]["ready"])
        self.assertEqual(epoch["math_foundry"]["source_archive_sha256"], FOUNDRY)
        self.assertEqual(epoch["math_foundry"]["qualification"]["clean_archive_replay"]["tests_passed"], 18)
        self.assertEqual(epoch["math_foundry"]["qualification"]["clean_archive_replay"]["assertions_passed"], 852)
        self.assertEqual(epoch["mastermind"]["sha256"], MASTERMIND)

    def test_parallelism_is_fail_closed_and_disabled(self):
        policy = json.loads((ROOT / "config" / "read_only_probe_parallelism_v25.json").read_text(encoding="utf-8"))
        self.assertFalse(policy["currently_enabled"])
        self.assertEqual(policy["fallback"], "SERIAL_EXECUTION")
        self.assertEqual(policy["authority"], "SEARCH_ONLY_SCHEDULING_OPTIMIZATION")
        self.assertIn("ALL_PROBES_BIND_THE_SAME_FROZEN_CAPABILITY_EPOCH_SHA256", policy["required_preconditions"])
        self.assertIn("EFFECT_CONFLICT_UNKNOWN_OR_PRESENT", policy["fail_closed_conditions"])

    def test_countable_control_set_freezes_substrate_and_contract_tests(self):
        control = json.loads((ROOT / "config" / "countable_control_set_v25.json").read_text(encoding="utf-8"))
        paths = set(control["required_control_paths"])
        required = {
            "config/substrate_epoch_v25.json",
            "config/read_only_probe_parallelism_v25.json",
            "tests/test_transition_expected_base_head.py",
            "tests/test_substrate_epoch_v25.py",
        }
        self.assertEqual(required - paths, set())

if __name__ == "__main__":
    unittest.main()
