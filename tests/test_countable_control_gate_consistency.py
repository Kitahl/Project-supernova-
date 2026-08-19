import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reconcile_v25_admission", ROOT / "scripts/reconcile_v25_admission.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


class CountableControlGateConsistencyTests(unittest.TestCase):
    def contract(self):
        return json.loads((ROOT / "config/countable_control_set_v25.json").read_text(encoding="utf-8"))

    def test_declarative_contract_contains_hardened_minimum(self):
        required = MOD.required_countable_paths(self.contract())
        self.assertTrue(MOD.MINIMUM_HARDENED_CONTROL.issubset(required))

    def test_declarative_addition_is_automatically_required(self):
        contract = self.contract()
        contract["required_control_paths"] = list(contract["required_control_paths"]) + ["tests/future_required_guard.py"]
        required = MOD.required_countable_paths(contract)
        self.assertIn("tests/future_required_guard.py", required)

    def test_dropping_any_hardened_minimum_fails_closed(self):
        contract = self.contract()
        victim = sorted(MOD.MINIMUM_HARDENED_CONTROL)[0]
        contract["required_control_paths"] = [p for p in contract["required_control_paths"] if p != victim]
        with self.assertRaises(ValueError):
            MOD.required_countable_paths(contract)

    def test_wrong_plan_or_protocol_fails_closed(self):
        contract = self.contract()
        contract["protocol_version"] = "2.6"
        with self.assertRaises(ValueError):
            MOD.required_countable_paths(contract)
        contract = self.contract()
        contract["task_network_plan_id"] = "wrong"
        with self.assertRaises(ValueError):
            MOD.required_countable_paths(contract)

    def test_source_bound_creator_is_fixed_not_receipt_selected(self):
        self.assertEqual(MOD.ACTIONS_CREATOR, "github-actions[bot]")


if __name__ == "__main__":
    unittest.main()
