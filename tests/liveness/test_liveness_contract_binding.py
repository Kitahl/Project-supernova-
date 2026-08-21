import copy
import importlib.util
import json
import pathlib
import unittest

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("v251", ROOT / "scripts/validate_branch_bus_v251.py")
V251 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V251)
SCHEMA = json.loads((ROOT / "schemas/cohort_liveness_contract.schema.json").read_text(encoding="utf-8"))

WORKERS = ["MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"]


def fixture():
    cohort = "CAL-BR-008-v25-test"
    root = "a" * 40
    cb = "b" * 40
    ab = "c" * 40
    assignment = {
        "cohort_id": cohort,
        "generation_root_sha": root,
        "control_manifest_id": "CTRL-TEST",
        "assignment_id": "ASSIGN-TEST",
        "workers": {w: {"worker_branch": f"ps/work/{cohort}/{w}"} for w in WORKERS},
    }
    control = {"calibration_countable": True}
    lanes = []
    for i, w in enumerate(WORKERS):
        lanes.append({
            "lane_id": w,
            "branch": f"ps/work/{cohort}/{w}",
            "path": f"reports/{cohort}/{w}.json",
            "expected_window_start_utc": f"2026-08-21T07:{i:02d}:00Z",
            "deadline_utc": "2026-08-21T08:30:00Z",
            "eligible_before_deadline": True,
        })
    contract = {
        "schema_version": "PS-COHORT-LIVENESS-2",
        "cohort_id": cohort,
        "generation_root_sha": root,
        "control_manifest_id": "CTRL-TEST",
        "control_manifest_git_identity": cb,
        "assignment_id": "ASSIGN-TEST",
        "assignment_git_identity": ab,
        "lanes": lanes,
    }
    return contract, control, assignment, cb, ab


class LivenessContractBindingTests(unittest.TestCase):
    def test_schema_has_no_self_referential_generation_head(self):
        self.assertEqual(SCHEMA.get("title"), "CohortLivenessContract v2")
        self.assertNotIn("generation_head_sha", SCHEMA.get("properties", {}))
        self.assertNotIn("generation_head_sha", SCHEMA.get("required", []))
        self.assertIn("generation_root_sha", SCHEMA.get("required", []))
        self.assertEqual(SCHEMA["properties"]["schema_version"].get("const"), "PS-COHORT-LIVENESS-2")

    def test_positive_contract_passes_schema_and_binding(self):
        c, control, assignment, cb, ab = fixture()
        self.assertEqual(len(c["lanes"]), 12)
        self.assertEqual({x["lane_id"] for x in c["lanes"]}, set(WORKERS))
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(c)), [])
        self.assertEqual(V251.liveness_contract_errors(c, control, assignment, cb, ab), [])

    def test_wrong_root_fails(self):
        c, control, assignment, cb, ab = fixture(); c["generation_root_sha"] = "d" * 40
        self.assertTrue(V251.liveness_contract_errors(c, control, assignment, cb, ab))

    def test_wrong_control_blob_fails(self):
        c, control, assignment, cb, ab = fixture(); c["control_manifest_git_identity"] = "d" * 40
        self.assertTrue(V251.liveness_contract_errors(c, control, assignment, cb, ab))

    def test_wrong_assignment_blob_fails(self):
        c, control, assignment, cb, ab = fixture(); c["assignment_git_identity"] = "d" * 40
        self.assertTrue(V251.liveness_contract_errors(c, control, assignment, cb, ab))

    def test_duplicate_lane_fails(self):
        c, control, assignment, cb, ab = fixture(); c["lanes"][1]["lane_id"] = c["lanes"][0]["lane_id"]
        self.assertTrue(V251.liveness_contract_errors(c, control, assignment, cb, ab))

    def test_wrong_branch_fails(self):
        c, control, assignment, cb, ab = fixture(); c["lanes"][0]["branch"] = "ps/work/WRONG/MF01"
        self.assertTrue(V251.liveness_contract_errors(c, control, assignment, cb, ab))

    def test_wrong_report_path_fails(self):
        c, control, assignment, cb, ab = fixture(); c["lanes"][0]["path"] = "reports/wrong.json"
        self.assertTrue(V251.liveness_contract_errors(c, control, assignment, cb, ab))

    def test_deadline_before_start_fails(self):
        c, control, assignment, cb, ab = fixture(); c["lanes"][0]["deadline_utc"] = "2026-08-21T06:00:00Z"
        self.assertTrue(V251.liveness_contract_errors(c, control, assignment, cb, ab))

    def test_legacy_self_reference_is_schema_rejected(self):
        c, *_ = fixture(); c["generation_head_sha"] = "f" * 40
        self.assertTrue(list(Draft202012Validator(SCHEMA).iter_errors(c)))

    def test_verification_schema_requires_contract_binding_fields(self):
        v = json.loads((ROOT / "schemas/branch_verification.schema.json").read_text(encoding="utf-8"))
        required = set(v["required"])
        self.assertTrue({"liveness_contract_path","liveness_contract_git_identity","liveness_contract_binding_verified"}.issubset(required))


if __name__ == "__main__":
    unittest.main()
