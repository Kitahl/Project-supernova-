import importlib.util
import json
import pathlib
import unittest
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT_SCHEMA = json.loads((ROOT / "schemas/branch_report.schema.json").read_text(encoding="utf-8"))
ASSURANCE_SCHEMA = json.loads((ROOT / "schemas/verifier_assurance.schema.json").read_text(encoding="utf-8"))
REACT_SCHEMA = json.loads((ROOT / "schemas/mastermind_react_proposal.schema.json").read_text(encoding="utf-8"))
SCRIPT = ROOT / "scripts/validate_branch_bus_v251.py"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("branch_validator_contract_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class T0ContractClosureTests(unittest.TestCase):
    def test_issue_record_is_closed_and_nonvacuous(self):
        issue = REPORT_SCHEMA["$defs"]["IssueRecord"]
        Draft202012Validator.check_schema(issue)
        valid = {
            "issue_id": "ZERO_DELTA",
            "severity": "NONE",
            "component": "worker",
            "status": "CLOSED_WITH_EVIDENCE",
            "evidence_refs": [],
            "blocker": "",
            "proposed_fix": "",
            "required_test": "completed assigned replay without a finding",
            "owner": "MM03",
            "authoritative_control_change": False,
            "next_action": "WAIT_FOR_MM06",
        }
        self.assertEqual(list(Draft202012Validator(issue).iter_errors(valid)), [])
        for missing in issue["required"]:
            with self.subTest(missing=missing):
                bad = dict(valid); bad.pop(missing)
                self.assertTrue(list(Draft202012Validator(issue).iter_errors(bad)))
        bad = dict(valid); bad["unexpected"] = True
        self.assertTrue(list(Draft202012Validator(issue).iter_errors(bad)))

    def test_duplicate_issue_ids_are_rejected_by_trusted_validator(self):
        mod = load_validator_module()
        report = {"issue_ledger": [{"issue_id": "A"}, {"issue_id": "A"}]}
        self.assertIn("issue_ledger duplicate issue_id", mod.issue_ledger_errors(report))

    def test_metric_result_never_collapses_typed_missing_to_zero(self):
        metric = REPORT_SCHEMA["$defs"]["MetricResult"]
        v = Draft202012Validator(metric)
        self.assertEqual(list(v.iter_errors({"status":"NOT_MEASURED","value":None,"reason":"not executed","evidence_refs":[]})), [])
        self.assertTrue(list(v.iter_errors({"status":"NOT_MEASURED","value":0,"reason":"not executed","evidence_refs":[]})))
        self.assertTrue(list(v.iter_errors({"status":"UNKNOWN","value":0,"reason":"unknown","evidence_refs":[]})))
        self.assertTrue(list(v.iter_errors({"status":"MEASURED","value":None,"reason":"measured","evidence_refs":[]})))
        self.assertEqual(list(v.iter_errors({"status":"MEASURED","value":0,"reason":"measured zero","evidence_refs":["receipt"]})), [])

    def test_mm03_role_payload_requires_typed_slopcode_result(self):
        text = (ROOT / "schemas/branch_report.schema.json").read_text(encoding="utf-8")
        self.assertIn('"worker_id": {"const": "MM03"}', text)
        self.assertIn('"slopcode_contract_result": {"$ref": "#/$defs/MetricResult"}', text)

    def test_verifier_assurance_empty_record_fails_strict_assurance_schema(self):
        self.assertTrue(list(Draft202012Validator(ASSURANCE_SCHEMA).iter_errors({})))
        mod = load_validator_module()
        self.assertTrue(mod.schema_errors({}, "schemas/verifier_assurance.schema.json", "assurance"))

    def test_react_proposal_is_closed_and_blocks_self_promotion(self):
        Draft202012Validator.check_schema(REACT_SCHEMA)
        valid = {
            "schema_version":"PS-MASTERMIND-REACT-PROPOSAL-1",
            "proposal_id":"p1","mechanism_id":"m1",
            "preservation_obligations":["preserve baseline"],
            "observer_contract":{"observer_id":"observer","blindness_scope":"outcome","read_only":True},
            "task_contract":{"task_class":"TRAIN","allowed_inputs":["train"],"forbidden_outputs":["holdout"]},
            "contamination_controls":["no holdout access"],
            "mutation_security_envelope":{"mutation_scope":["proposal"],"forbidden_paths":["state/"],"security_review_required":True,"unsafe_expansion_allowed":False},
            "authority_boundary":{"proposal_authority":"MM01_PRE_REVIEW_ONLY","execution_authority":"external executor","evaluation_authority":"independent evaluator","scientific_promotion_authority":"NOT_MM01"},
            "provenance_refs":["frozen assignment"],"execution_artifact_ref":"artifact","evaluator_ref":"eval","complete_cost_envelope_ref":"cost",
            "negative_controls":["no-change"],"proposal_only":True,"self_promotion_allowed":False,
        }
        v = Draft202012Validator(REACT_SCHEMA)
        self.assertEqual(list(v.iter_errors(valid)), [])
        for missing in ("observer_contract","contamination_controls","mutation_security_envelope","authority_boundary"):
            bad=dict(valid);bad.pop(missing)
            self.assertTrue(list(v.iter_errors(bad)))
        bad=dict(valid);bad["self_promotion_allowed"]=True
        self.assertTrue(list(v.iter_errors(bad)))
        bad=dict(valid);bad["unexpected"]="x"
        self.assertTrue(list(v.iter_errors(bad)))

    def test_mm01_fresh_requires_typed_react_proposal(self):
        mod = load_validator_module()
        self.assertIn("MM01 fresh execution missing role_payload.react_proposal", mod.role_contract_errors({"mode":"FRESH_EXECUTION","role_payload":{}}, "MM01"))
        self.assertEqual(mod.role_contract_errors({"mode":"SAFE_REPLAY_ONLY"}, "MM01"), [])


if __name__ == "__main__":
    unittest.main()
