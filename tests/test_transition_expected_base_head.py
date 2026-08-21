import importlib.util
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
TRANSITION_GUARD = ROOT / "scripts" / "transition_guard.py"


def load_guard():
    spec = importlib.util.spec_from_file_location("transition_guard_behavioral_test", TRANSITION_GUARD)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def bound_fixture(expected_base: str | None):
    control_path = "control/NEXT.json"
    assignment_path = "assignments/NEXT.json"
    state = {
        "expected_base_head": expected_base,
        "active_control_manifest_path": control_path,
        "active_assignment_path": assignment_path,
        "active_parent_state_git_identity": "1" * 40,
        "generation_seq": 8,
        "active_cohort_id": "CAL-BR-008-TEST",
    }
    control = {
        "expected_base_head": expected_base,
        "parent_state_git_identity": "1" * 40,
        "generation_seq": 8,
        "cohort_id": "CAL-BR-008-TEST",
    }
    assignment = dict(control)
    return state, control_path, control, assignment_path, assignment


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

    def _run_guard(self, state, control_path, control, assignment_path, assignment, base):
        guard = load_guard()
        docs = {
            "state/CURRENT.json": state,
            control_path: control,
            assignment_path: assignment,
        }
        guard.load = lambda path: docs[path]
        guard.changed = lambda observed_base, head: [
            "state/CURRENT.json",
            control_path,
            assignment_path,
        ]
        return guard.validate(base, "f" * 40)

    def test_transition_guard_accepts_one_exact_base_across_all_three_objects(self):
        base = "a" * 40
        state, cp, control, ap, assignment = bound_fixture(base)
        self.assertEqual(self._run_guard(state, cp, control, ap, assignment, base), [])

    def test_transition_guard_rejects_state_control_expected_base_mismatch(self):
        base = "a" * 40
        state, cp, control, ap, assignment = bound_fixture(base)
        control["expected_base_head"] = "b" * 40
        errors = self._run_guard(state, cp, control, ap, assignment, base)
        self.assertIn("state/control/assignment expected_base_head mismatch", errors)

    def test_transition_guard_rejects_state_assignment_expected_base_mismatch(self):
        base = "a" * 40
        state, cp, control, ap, assignment = bound_fixture(base)
        assignment["expected_base_head"] = "c" * 40
        errors = self._run_guard(state, cp, control, ap, assignment, base)
        self.assertIn("state/control/assignment expected_base_head mismatch", errors)

    def test_transition_guard_rejects_expected_base_vs_actual_base_mismatch(self):
        expected = "a" * 40
        actual = "b" * 40
        state, cp, control, ap, assignment = bound_fixture(expected)
        errors = self._run_guard(state, cp, control, ap, assignment, actual)
        self.assertTrue(any("stale/wrong expected base head" in error for error in errors), errors)

    def test_transition_guard_rejects_missing_expected_base_on_a_transition(self):
        actual = "a" * 40
        state, cp, control, ap, assignment = bound_fixture(None)
        errors = self._run_guard(state, cp, control, ap, assignment, actual)
        self.assertTrue(any("stale/wrong expected base head" in error for error in errors), errors)

    def test_behavioral_falsifier_is_nonvacuous(self):
        base = "a" * 40
        state, cp, control, ap, assignment = bound_fixture(base)
        control["expected_base_head"] = "d" * 40
        errors = self._run_guard(state, cp, control, ap, assignment, base)
        self.assertEqual(errors.count("state/control/assignment expected_base_head mismatch"), 1)


if __name__ == "__main__":
    unittest.main()
