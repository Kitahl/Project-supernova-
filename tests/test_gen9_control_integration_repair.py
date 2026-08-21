import copy
import importlib.util
import json
import pathlib
import unittest

from jsonschema import Draft202012Validator

from scripts.generation_envelope_v25 import expected_generation_paths, generation_path_errors

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def errors(schema_path, value):
    schema = load(schema_path)
    Draft202012Validator.check_schema(schema)
    return list(Draft202012Validator(schema).iter_errors(value))


class GenerationAuthorityTests(unittest.TestCase):
    def state(self, *, countable=True):
        return {
            "active_cohort_id": "CAL-X",
            "active_control_manifest_path": "control/CAL-X.json",
            "active_assignment_path": "assignments/CAL-X.json",
            "calibration_countable_current": countable,
        }

    def test_countable_generation_envelope_is_exactly_three_paths(self):
        expected = {
            "control/CAL-X.json",
            "assignments/CAL-X.json",
            "liveness/CAL-X.json",
        }
        self.assertEqual(expected_generation_paths(self.state()), expected)
        self.assertEqual(generation_path_errors(expected, self.state()), [])

    def test_missing_liveness_or_fourth_path_fails(self):
        two = {"control/CAL-X.json", "assignments/CAL-X.json"}
        four = two | {"liveness/CAL-X.json", "unrelated.txt"}
        self.assertTrue(generation_path_errors(two, self.state()))
        self.assertTrue(generation_path_errors(four, self.state()))

    def test_noncountable_generation_envelope_remains_two_paths(self):
        expected = {"control/CAL-X.json", "assignments/CAL-X.json"}
        self.assertEqual(expected_generation_paths(self.state(countable=False)), expected)

    def test_rest_reconciler_is_diagnostic_only(self):
        text = (ROOT / "scripts/reconcile_branch_rest.py").read_text(encoding="utf-8")
        self.assertIn('DIAGNOSTIC_CONTEXT = "supernova/rest-generation-audit"', text)
        self.assertIn('"context": DIAGNOSTIC_CONTEXT', text)
        self.assertNotIn('"context": "supernova/branch-', text)
        workflow = (ROOT / ".github/workflows/supernova-rest-branch-reconciler.yml").read_text(encoding="utf-8")
        self.assertIn("generation_envelope_v25.py", workflow)
        self.assertIn("reconcile_v25_admission.py", workflow)

    def test_control_map_has_one_success_writer_per_shared_context(self):
        control = load("config/control_workflow_map_v25.json")
        for context, row in control["shared_status_contexts"].items():
            self.assertTrue(context.startswith("supernova/"))
            self.assertEqual(row["writer_count"], 1, context)
            self.assertTrue((ROOT / row["success_writer_workflow"]).is_file())
            if row["success_writer_script"].endswith(".py"):
                self.assertTrue((ROOT / row["success_writer_script"]).is_file())


class StrictIssueTests(unittest.TestCase):
    def issue(self):
        return {
            "issue_id": "X-1",
            "severity": "HIGH",
            "component": "control",
            "status": "OPEN",
            "classification": "CONTROL_GAP",
            "aliases": [],
            "summary": "summary",
            "exact_failure": "exact falsifiable failure",
            "evidence_refs": ["path@blob"],
            "blocker": True,
            "proposed_protocol_2_5_fix_test": "smallest repair",
            "required_test": "negative fixture must fail",
            "owner": "BIL00",
            "authoritative_control_change": True,
            "next_action": "repair prospectively",
        }

    def test_complete_issue_passes(self):
        self.assertEqual(errors("schemas/strict_issue_record_v25.schema.json", self.issue()), [])

    def test_missing_exact_failure_fails(self):
        value = self.issue()
        del value["exact_failure"]
        self.assertTrue(errors("schemas/strict_issue_record_v25.schema.json", value))

    def test_missing_required_test_fails(self):
        value = self.issue()
        del value["required_test"]
        self.assertTrue(errors("schemas/strict_issue_record_v25.schema.json", value))


class MM03ContractTests(unittest.TestCase):
    def payload(self):
        return {
            "schema_version": "PS-MM03-PAYLOAD-2.5-2",
            "slopcode_result": {
                "result_type": "SCIENTIFIC_METRIC",
                "status": "NOT_MEASURED",
                "value": None,
                "reason": "replay only",
                "evidence_refs": ["assignment@blob"],
                "unit": None,
            },
        }

    def test_closed_typed_missingness_passes(self):
        self.assertEqual(errors("schemas/mastermind_mm03_payload_v25.schema.json", self.payload()), [])

    def test_shadow_numeric_metric_fails(self):
        value = self.payload()
        value["slopcode_score"] = 0
        self.assertTrue(errors("schemas/mastermind_mm03_payload_v25.schema.json", value))

    def test_not_measured_numeric_zero_fails(self):
        value = self.payload()
        value["slopcode_result"]["value"] = 0
        self.assertTrue(errors("schemas/mastermind_mm03_payload_v25.schema.json", value))


class MM07ContractTests(unittest.TestCase):
    def replay(self):
        result = {"status": "NOT_MEASURED", "value": None, "reason": "T0 replay"}
        return {
            "schema_version": "PS-MM07-REPLAY-PAYLOAD-2.5-1",
            "experiment_kind": "SAFE_REPLAY_DIAGNOSTIC",
            "before_result": copy.deepcopy(result),
            "after_result": copy.deepcopy(result),
            "numeric_delta": None,
            "next_self_candidate": None,
            "self_promotion": False,
            "goal2_credit": False,
            "solver_memory_improver_separated": True,
            "claim_scope": "CONTROL_REPLAY_ONLY_NO_SELF_IMPROVEMENT_CLAIM",
        }

    def fresh(self):
        metric = {"status": "NOT_MEASURED", "value": None, "reason": "not yet measured", "metric_identity": "m"}
        return {
            "schema_version": "PS-MM07-PAYLOAD-2.5-2",
            "experiment_kind": "BOUNDED_TRAIN_DIAGNOSTIC",
            "train_only": True,
            "generation_index": 1,
            "source_identity": "source",
            "evaluator_identity": "eval",
            "model_tools_environment_identity": "env",
            "budget_identity": "budget",
            "cache_retention_identity": "cache",
            "solver_identity": "F",
            "memory_control_identity": "M",
            "improver_identity": "I",
            "claim_status": "DIAGNOSTIC_NOT_GOAL2",
            "improver_treatment_isolated": False,
            "complete_cost_binding": "REPORT_COST_LEDGER_COMPLETE",
            "origin_task_promotion": False,
            "predeclared_stop_ref": "stop.json",
            "predeclared_stop_frozen_before_start": True,
            "typed_event_trace_ref": "events.json",
            "typed_event_trace_digest": "a" * 64,
            "rho_improve_interpretation": "DESCRIPTIVE_ONLY",
            "before_result": copy.deepcopy(metric),
            "after_result": copy.deepcopy(metric),
            "scores_frozen_before_candidate": True,
            "next_candidate": None,
            "candidate_generation_rule": "AT_MOST_ONE_BOUNDED_NEXT_CANDIDATE",
        }

    def test_replay_null_contract_passes(self):
        self.assertEqual(errors("schemas/mastermind_mm07_replay_payload_v25.schema.json", self.replay()), [])

    def test_replay_numeric_gain_or_candidate_or_credit_fails(self):
        for key, value in (("numeric_delta", 1.0), ("next_self_candidate", "X"), ("self_promotion", True), ("goal2_credit", True)):
            candidate = self.replay()
            candidate[key] = value
            self.assertTrue(errors("schemas/mastermind_mm07_replay_payload_v25.schema.json", candidate), key)

    def test_complete_fresh_stage0_contract_passes(self):
        self.assertEqual(errors("schemas/mastermind_mm07_fresh_payload_v25.schema.json", self.fresh()), [])

    def test_each_missing_stage0_invariant_fails(self):
        for key in (
            "predeclared_stop_ref",
            "typed_event_trace_ref",
            "rho_improve_interpretation",
            "before_result",
            "after_result",
            "scores_frozen_before_candidate",
            "next_candidate",
            "candidate_generation_rule",
        ):
            candidate = self.fresh()
            del candidate[key]
            self.assertTrue(errors("schemas/mastermind_mm07_fresh_payload_v25.schema.json", candidate), key)


class VerificationAssuranceTests(unittest.TestCase):
    def test_transport_only_requires_explicit_empty_disposition(self):
        value = {
            "verifier_assurance_disposition": "TRANSPORT_ONLY_NOT_APPLICABLE",
            "verifier_assurance_records": [],
            "statement_fidelity_policy": "NOT_APPLICABLE_TRANSPORT_ONLY",
        }
        self.assertEqual(errors("schemas/verification_assurance_disposition_v25.schema.json", value), [])

    def test_empty_records_without_disposition_fail(self):
        value = {
            "verifier_assurance_records": [],
            "statement_fidelity_policy": "NOT_APPLICABLE_TRANSPORT_ONLY",
        }
        self.assertTrue(errors("schemas/verification_assurance_disposition_v25.schema.json", value))

    def test_scientific_verification_cannot_use_transport_na(self):
        value = {
            "verifier_assurance_disposition": "TRANSPORT_ONLY_NOT_APPLICABLE",
            "verifier_assurance_records": [],
            "statement_fidelity_policy": "REQUIRED_BY_SCIENTIFIC_MANIFEST",
        }
        self.assertTrue(errors("schemas/verification_assurance_disposition_v25.schema.json", value))


if __name__ == "__main__":
    unittest.main()
