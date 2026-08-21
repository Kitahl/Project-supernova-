import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class T0ControlConsistencyTests(unittest.TestCase):
    def test_session_phase_is_assignment_authoritative(self):
        text = (ROOT / "SESSION_STANDARD.md").read_text(encoding="utf-8")
        self.assertIn("PHASE: <EXACT_FROZEN_ASSIGNMENT_PHASE>", text)
        self.assertIn("MUST equal the exact phase string in the frozen assignment", text)
        self.assertIn("T0_COUNTABLE_REPLAY_COHORT_1", text)
        self.assertNotIn("PHASE: <T0|E1|G1|C1|REACTION|DR03|E3|SELECT|IGNITION|CASCADE|E5B|E6|RESEARCH>", text)

    def test_historical_gen7_phase_is_preserved_exactly(self):
        path = ROOT / "assignments" / "CAL-BR-007-v25-c13b6ee4.json"
        self.assertTrue(path.is_file())
        assignment = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(assignment["phase"], "T0_COUNTABLE_REPLAY_COHORT_1")

    def test_task_registry_has_no_current_countability_boolean(self):
        registry = json.loads((ROOT / "config" / "task_registry_v25.json").read_text(encoding="utf-8"))
        activation = registry["activation_status"]
        self.assertNotIn("countable_cohort_eligible", activation)
        self.assertEqual(activation["activation_snapshot_scope"], "HISTORICAL_TASK_DEPLOYMENT_ONLY")
        self.assertEqual(activation["countability_authority"], "main:state/CURRENT.json + active control/assignment")
        self.assertEqual(activation["countability_snapshot"], "NOT_AUTHORITATIVE")
        self.assertEqual(registry["canonical_state"], "main:state/CURRENT.json")

    def test_canonical_state_and_active_assignment_agree_on_countability(self):
        state = json.loads((ROOT / "state" / "CURRENT.json").read_text(encoding="utf-8"))
        assignment = json.loads((ROOT / state["active_assignment_path"]).read_text(encoding="utf-8"))
        self.assertEqual(state["calibration_countable_current"], assignment["calibration_countable"])


if __name__ == "__main__":
    unittest.main()
