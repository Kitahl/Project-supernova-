import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/reconcile_branch_rest.py"
SCHEMA = ROOT / "schemas/cohort_liveness_contract.schema.json"


def load_module():
    spec = importlib.util.spec_from_file_location("reconcile_branch_rest_liveness_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CountableLivenessContractGateTests(unittest.TestCase):
    def fixture(self):
        mod = load_module()
        cohort = "CAL-TEST"
        G = "a" * 40
        assignment = {
            "generation_seq": 8,
            "assignment_id": "assignment-test",
            "control_manifest_id": "control-test",
            "workers": {
                wid: {"worker_branch": f"ps/work/{cohort}/{wid}"}
                for wid in mod.WORKERS
            },
        }
        contract = {
            "schema_version": "PS-COHORT-LIVENESS-CONTRACT-2",
            "task_network_plan_id": mod.PLAN,
            "cohort_id": cohort,
            "generation_seq": 8,
            "generation_head_sha": G,
            "assignment_id": "assignment-test",
            "assignment_git_identity": "b" * 40,
            "control_manifest_id": "control-test",
            "control_manifest_git_identity": "c" * 40,
            "lanes": [
                {
                    "lane_id": wid,
                    "branch": f"ps/work/{cohort}/{wid}",
                    "path": f"reports/{cohort}/{wid}.json",
                    "expected_window_start_utc": "2026-08-21T07:00:00Z",
                    "deadline_utc": "2026-08-21T08:00:00Z",
                    "eligible_before_deadline": True,
                }
                for wid in mod.WORKERS
            ],
        }
        return mod, contract, cohort, G, assignment

    def errors(self, contract, cohort, G, assignment):
        mod = load_module()
        return mod.liveness_errors(contract, cohort, G, assignment, "b" * 40, {}, "c" * 40)

    def test_valid_exact_twelve_lane_contract_passes(self):
        _, c, cohort, G, a = self.fixture()
        self.assertEqual(self.errors(c, cohort, G, a), [])

    def test_missing_duplicate_wrong_branch_path_and_bad_interval_fail(self):
        _, c, cohort, G, a = self.fixture()
        c["lanes"] = c["lanes"][:-1]
        self.assertIn("liveness lane count != 12", self.errors(c, cohort, G, a))
        _, c, cohort, G, a = self.fixture()
        c["lanes"][1]["lane_id"] = c["lanes"][0]["lane_id"]
        self.assertTrue(any("lane IDs" in x or "duplicate" in x for x in self.errors(c, cohort, G, a)))
        _, c, cohort, G, a = self.fixture()
        c["lanes"][0]["branch"] = "wrong"
        self.assertTrue(any("branch mismatch" in x for x in self.errors(c, cohort, G, a)))
        _, c, cohort, G, a = self.fixture()
        c["lanes"][0]["path"] = "wrong"
        self.assertTrue(any("report path mismatch" in x for x in self.errors(c, cohort, G, a)))
        _, c, cohort, G, a = self.fixture()
        c["lanes"][0]["deadline_utc"] = c["lanes"][0]["expected_window_start_utc"]
        self.assertTrue(any("interval not increasing" in x for x in self.errors(c, cohort, G, a)))

    def test_wrong_generation_and_assignment_bindings_fail(self):
        _, c, cohort, G, a = self.fixture()
        c["generation_head_sha"] = "d" * 40
        c["assignment_git_identity"] = "e" * 40
        errors = self.errors(c, cohort, G, a)
        self.assertIn("liveness binding generation_head_sha", errors)
        self.assertIn("liveness binding assignment_git_identity", errors)

    def test_schema_requires_exact_twelve_lanes_and_closed_envelope(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        lanes = schema["properties"]["lanes"]
        self.assertEqual(lanes["minItems"], 12)
        self.assertEqual(lanes["maxItems"], 12)
        self.assertFalse(lanes["items"]["additionalProperties"])

    def test_generation_reconciler_requires_liveness_path_when_countable(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("if countable:expected.add(f'liveness/{cohort}.json')", text)
        self.assertIn("content(f'liveness/{cohort}.json',G)", text)


if __name__ == "__main__":
    unittest.main()
