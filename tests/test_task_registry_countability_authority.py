import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/task_registry_v25.json"
STATE = ROOT / "state/CURRENT.json"


class TaskRegistryCountabilityAuthorityTests(unittest.TestCase):
    def test_registry_does_not_duplicate_canonical_countability_boolean(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        activation = registry["activation_status"]
        self.assertNotIn("countable_cohort_eligible", activation)
        self.assertEqual(
            activation["countability_authority"],
            "main:state/CURRENT.json + active control/assignment",
        )
        self.assertIn("NONAUTHORITATIVE", activation["activation_snapshot_scope"])

    def test_registry_cannot_override_live_canonical_state(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(registry["canonical_state"], "main:state/CURRENT.json")
        self.assertIsInstance(state["calibration_countable_current"], bool)
        self.assertNotIn(
            "countable_cohort_eligible",
            registry["activation_status"],
            "task deployment metadata must not duplicate mutable countability authority",
        )


if __name__ == "__main__":
    unittest.main()
