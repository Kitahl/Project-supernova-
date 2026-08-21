import json
import pathlib
import unittest
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMAS = [
    ROOT / "schemas" / "state.schema.json",
    ROOT / "schemas" / "control.schema.json",
    ROOT / "schemas" / "assignment.schema.json",
]

class ExpectedBaseHeadContractTests(unittest.TestCase):
    def test_expected_base_head_is_optional_and_typed_in_all_transition_schemas(self):
        for path in SCHEMAS:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            self.assertIn("expected_base_head", schema["properties"], path.name)
            self.assertNotIn("expected_base_head", schema["required"], path.name)
            prop = schema["properties"]["expected_base_head"]
            self.assertEqual(prop.get("type"), "string")
            self.assertEqual(prop.get("pattern"), "^[0-9a-f]{40}$")
            validator = Draft202012Validator({
                "type": "object",
                "properties": {"expected_base_head": prop},
                "additionalProperties": False,
            })
            self.assertEqual(list(validator.iter_errors({"expected_base_head": "a" * 40})), [])
            self.assertTrue(list(validator.iter_errors({"expected_base_head": "not-a-commit"})))

    def test_state_schema_accepts_historical_without_and_transition_with_expected_base_head(self):
        schema = json.loads((ROOT / "schemas" / "state.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        current = json.loads((ROOT / "state" / "CURRENT.json").read_text(encoding="utf-8"))

        historical = dict(current)
        historical.pop("expected_base_head", None)
        self.assertEqual(list(validator.iter_errors(historical)), [])

        transitioned = dict(historical)
        transitioned["expected_base_head"] = "a" * 40
        self.assertEqual(list(validator.iter_errors(transitioned)), [])

        malformed = dict(historical)
        malformed["expected_base_head"] = "not-a-commit"
        self.assertTrue(list(validator.iter_errors(malformed)))

    def test_transition_guard_requires_one_exact_base_across_state_control_assignment(self):
        text = (ROOT / "scripts" / "transition_guard.py").read_text(encoding="utf-8")
        self.assertIn('s.get("expected_base_head")!=c.get("expected_base_head")', text)
        self.assertIn('s.get("expected_base_head")!=a.get("expected_base_head")', text)
        self.assertIn('s.get("expected_base_head")!=base', text)

if __name__ == "__main__":
    unittest.main()
