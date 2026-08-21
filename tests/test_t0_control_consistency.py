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

    def test_task_registry_countability_field_is_explicitly_non_authoritative(self):
        registry = json.loads((ROOT / "config" / "task_registry_v25.json").read_text(encoding="utf-8"))
        semantics = json.loads((ROOT / "config" / "task_registry_semantics_v25.json").read_text(encoding="utf-8"))
        activation = registry["activation_status"]
        legacy = semantics["legacy_field_disposition"]

        self.assertIn("countable_cohort_eligible", activation)
        self.assertEqual(legacy["path"], "config/task_registry_v25.json:activation_status.countable_cohort_eligible")
        self.assertEqual(legacy["status"], "HISTORICAL_SNAPSHOT_NON_AUTHORITATIVE")
        self.assertTrue(legacy["value_may_be_stale"])
        self.assertTrue(legacy["must_not_be_used_for_current_eligibility"])
        self.assertEqual(semantics["registry_role"], "FROZEN_SCHEDULE_AND_DEPLOYMENT_SNAPSHOT")
        self.assertEqual(semantics["registry_activation_status_authority"], "HISTORICAL_INFORMATIONAL_ONLY")
        self.assertEqual(registry["canonical_state"], "main:state/CURRENT.json")

    def test_canonical_state_control_assignment_agree_on_countability(self):
        state = json.loads((ROOT / "state" / "CURRENT.json").read_text(encoding="utf-8"))
        assignment = json.loads((ROOT / state["active_assignment_path"]).read_text(encoding="utf-8"))
        control = json.loads((ROOT / state["active_control_manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(state["calibration_countable_current"], assignment["calibration_countable"])
        self.assertEqual(state["calibration_countable_current"], control["calibration_countable"])

    def test_registry_semantics_contract_is_frozen_for_future_countable_generations(self):
        freeze = json.loads((ROOT / "config" / "countable_control_set_v25.json").read_text(encoding="utf-8"))
        self.assertIn("config/task_registry_semantics_v25.json", freeze["required_control_paths"])


if __name__ == "__main__":
    unittest.main()
