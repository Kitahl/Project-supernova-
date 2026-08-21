import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATE7 = "5bfe4bf2cc7e8c4cb9751b831803e28eb45cebe22c0085310c8f00459caf994e"
MF311 = "57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f"
MASTERMIND = "026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d"


class FrozenSubstrateEpochTests(unittest.TestCase):
    def test_countable_substrate_epoch_is_exact_and_ready(self):
        epoch = json.loads((ROOT / "config" / "substrate_epoch_v25.json").read_text(encoding="utf-8"))
        self.assertEqual(epoch["task_network_plan_id"], "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa")
        self.assertEqual(epoch["protocol_version"], "2.5")
        self.assertEqual(epoch["status"], "FROZEN_FOR_COUNTABLE_CALIBRATION")
        self.assertTrue(epoch["countable_freeze"]["ready"])
        self.assertEqual(epoch["mastermind"]["sha256"], MASTERMIND)

        foundry = epoch["math_foundry"]
        version = foundry.get("semantic_version")
        if version == "3.0.1":
            self.assertEqual(foundry["source_archive_sha256"], CANDIDATE7)
            replay = foundry["qualification"]["clean_archive_replay"]
            self.assertEqual(replay["tests_passed"], 18)
            self.assertEqual(replay["assertions_passed"], 852)
        elif version == "3.1.1":
            self.assertEqual(foundry["source_archive_sha256"], MF311)
            qualification = foundry["qualification"]
            self.assertEqual(qualification["status"], "PASS")
            self.assertEqual(qualification["suites_passed"], 28)
            self.assertEqual(qualification["suites_total"], 28)
            self.assertEqual(
                qualification["qualification_result_sha256"],
                "32c92aee61100fab918b60867be1fc873c274521a64ffbe1ffe10ed4529f1396",
            )
            self.assertEqual(
                qualification["release_receipt_sha256"],
                "13b323fa2c7dc24aa42358a26d918674d1b7558762109d9b729736a468f79b9e",
            )
            self.assertEqual(qualification["qualification_watchdog"], "FINITE_HARNESS_ONLY")
            self.assertEqual(qualification["runtime_default_wall_clock"], "NONE")
            self.assertEqual(qualification["packaging_integrity"], "PASS")
        else:
            self.fail(f"unqualified/unrecognized Math Foundry substrate version: {version!r}")

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
