import copy
import importlib.util
import json
import pathlib
import unittest

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "mastermind_react_proposal.schema.json"
VALIDATOR_PATH = ROOT / "scripts" / "validate_branch_bus_v251.py"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("branch_v251_mm01_test", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def valid_payload():
    return {
        "schema_version": "PS-MM01-REACT-PROPOSAL-2.5-1",
        "proposal_id": "MM01-PROP-TEST",
        "proposal_class": "BOUNDED_MECHANISM_PROPOSAL",
        "authority": "PRE_REVIEW_ONLY",
        "source_role": "MM01",
        "source_task_id": "task-test",
        "assignment_evidence": {"assignment_id": "assign-test", "cohort_id": "TRAIN-test", "fresh_allowed": True, "stage0_train_only": True},
        "preservation_controls": ["preserve-current-behavior"],
        "observer_contract": {"observed_inputs": ["declared-observation"], "forbidden_hidden_inputs": ["hidden-evaluator-state"], "observation_timing_preserved": True},
        "contract_controls": {"producer_obligations": ["emit-typed-proposal"], "consumer_obligations": ["independent-review"], "invariants": ["no-self-promotion"], "failure_semantics": "FAIL_CLOSED"},
        "contamination_controls": {"origin_task_excluded_from_promotion": True, "protected_eval_not_read": True, "source_versions_frozen": True, "cross_task_leakage_check": "PASS"},
        "mutation_controls": {"mutation_surface": ["proposal-candidate-only"], "bounded_change": True, "rollback_defined": True, "security_envelope": "NO_AUTHORITY_OR_SECRET_EXPANSION", "forbidden_surfaces": ["admission-authority", "scientific-state"]},
        "execution_envelope": {"execution_status": "NOT_EXECUTED", "executable_artifact_ref": None, "complete_cost_accounting_required": True, "equal_compute_control_required": True},
        "evaluator_envelope": {"self_grading_forbidden": True, "independent_evaluator_required": True, "evaluator_ref": None},
        "provenance": {"source_refs": ["frozen-source-ref"], "artifact_digests": [], "model_binding_status": "UNVERIFIED"},
        "negative_controls": [{"control_id": "NO_CHANGE", "purpose": "matched no-change control"}],
        "claim_scope": "PRE_REVIEW_ONLY proposal",
        "self_promotion_requested": False,
        "next_action": "independent review",
    }


class MM01ReactProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)
        cls.module = load_validator_module()

    def errors(self, payload): return list(self.validator.iter_errors(payload))
    def test_valid_payload_passes(self): self.assertEqual(self.errors(valid_payload()), [])
    def test_missing_preservation_fails(self):
        p = valid_payload(); p.pop("preservation_controls"); self.assertTrue(self.errors(p))
    def test_unknown_field_fails(self):
        p = valid_payload(); p["undeclared"] = True; self.assertTrue(self.errors(p))
    def test_self_promotion_fails(self):
        p = valid_payload(); p["self_promotion_requested"] = True; self.assertTrue(self.errors(p))
    def test_missing_contamination_control_fails(self):
        p = valid_payload(); p["contamination_controls"].pop("protected_eval_not_read"); self.assertTrue(self.errors(p))
    def test_missing_observer_contract_fails(self):
        p = valid_payload(); p.pop("observer_contract"); self.assertTrue(self.errors(p))
    def test_unsafe_mutation_envelope_fails(self):
        p = valid_payload(); p["mutation_controls"]["rollback_defined"] = False; self.assertTrue(self.errors(p))
    def test_branch_validator_requires_typed_payload_for_fresh_mm01(self):
        report = {"worker_id": "MM01", "mode": "FRESH_EXECUTION", "role_payload": valid_payload()}
        self.assertEqual(self.module.typed_role_payload_errors(report), [])
        bad = copy.deepcopy(report); bad["role_payload"].pop("observer_contract")
        self.assertTrue(self.module.typed_role_payload_errors(bad))
    def test_replay_mm01_does_not_require_proposal_payload(self):
        self.assertEqual(self.module.typed_role_payload_errors({"worker_id": "MM01", "mode": "SAFE_REPLAY_ONLY"}), [])

if __name__ == "__main__": unittest.main()
