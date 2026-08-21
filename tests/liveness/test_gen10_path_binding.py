import copy
import json
import pathlib
import unittest

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "cohort_liveness_contract.schema.json").read_text(encoding="utf-8"))
HISTORICAL = json.loads((ROOT / "liveness" / "CAL-BR-009-v25-b53ab205.json").read_text(encoding="utf-8"))


class Gen10LivenessPathBindingTests(unittest.TestCase):
    def errors(self, value):
        return list(Draft202012Validator(SCHEMA).iter_errors(value))

    def test_historical_contract_without_paths_remains_valid(self):
        self.assertEqual(self.errors(HISTORICAL), [])

    def test_successor_contract_may_bind_exact_control_and_assignment_paths(self):
        value = copy.deepcopy(HISTORICAL)
        value["control_manifest_path"] = "control/CAL-BR-010-v25-example.json"
        value["assignment_path"] = "assignments/CAL-BR-010-v25-example.json"
        self.assertEqual(self.errors(value), [])

    def test_malformed_or_unknown_path_fields_fail_closed(self):
        value = copy.deepcopy(HISTORICAL)
        value["control_manifest_path"] = "../control.json"
        self.assertTrue(self.errors(value))
        value = copy.deepcopy(HISTORICAL)
        value["assignment_path"] = "control/wrong.json"
        self.assertTrue(self.errors(value))
        value = copy.deepcopy(HISTORICAL)
        value["untyped_path_binding"] = "control/x.json"
        self.assertTrue(self.errors(value))

    def test_gen9_reset_fixture_fields_are_schema_admissible(self):
        properties = SCHEMA["properties"]
        self.assertIn("control_manifest_path", properties)
        self.assertIn("assignment_path", properties)


if __name__ == "__main__":
    unittest.main()
