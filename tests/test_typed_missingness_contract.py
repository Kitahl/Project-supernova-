import copy
import json
import pathlib
import unittest

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/branch_report.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)


def base_mm03_report():
    return {
        "session_header": {
            "schema_version": "PS-SESSION-2",
            "session_name": "PS-MM-W03 | SlopCode Contracts",
            "target_program": "MASTERMIND",
            "phase": "T0_COUNTABLE_REPLAY_COHORT_1",
            "iteration_id": "TEST",
            "iteration_number": 8,
            "role_id": "MM03",
            "goal": "typed missingness test",
            "plan_id": "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa",
            "runtime_state_id": "runtime",
            "model_target": "GPT-5.6 Sol",
            "reasoning_effort_target": "EXTRA_HIGH",
            "model_binding_status": "PARTIAL_UNVERIFIED",
            "execution_mode": "SAFE_REPLAY_ONLY",
        },
        "task_network_plan_id": "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa",
        "cohort_id": "TEST",
        "worker_id": "MM03",
        "report_id": "TEST-MM03",
        "generation_seq": 8,
        "generation_head_sha": "a" * 40,
        "worker_branch": "ps/work/TEST/MM03",
        "assignment_id": "A",
        "assignment_git_identity": "b" * 40,
        "parent_state_git_identity": "c" * 40,
        "control_manifest_id": "C",
        "control_manifest_git_identity": "d" * 40,
        "network_checkpoint_id": "checkpoint",
        "runtime_state_id": "runtime",
        "visibility_token": "token",
        "worker_auth_scheme": "PS-HMAC-SHA256-CANONICAL-REPORT-2",
        "worker_auth_commitment": "e" * 64,
        "worker_auth_proof": "f" * 64,
        "status": "VALID_ASSIGNED_REPORT",
        "mode": "SAFE_REPLAY_ONLY",
        "evidence_tier": "REPLAY_DIAGNOSTIC",
        "executive_status": "ZERO_DELTA",
        "fresh_evidence_ids": [],
        "private_manifest_id": None,
        "private_manifest_git_identity": None,
        "task_ledger": [],
        "issue_ledger": [],
        "test_ledger": [],
        "plan_alignment": [],
        "evidence_and_provenance": {},
        "claim_scope": "transport only",
        "runtime_implementation_implication": "none",
        "negative_zero_outcomes": [],
        "research_questions": [],
        "role_payload": {
            "metric_results": [
                {
                    "metric_id": "static_quality",
                    "status": "NOT_MEASURED",
                    "value": None,
                    "reason": "no qualified measurement in replay",
                    "unit": None,
                    "evidence_refs": [],
                }
            ]
        },
        "cost_ledger": {
            "fresh_evidence_units_consumed": 0,
            "protected_manifest_reads": 0,
            "benchmark_executions": 0,
            "deep_research_runs": 0,
            "notes": "replay",
        },
        "public_safety_status": "PASS",
        "origin_reread_claim": False,
        "next_action": "wait",
    }


def errors(report):
    return list(VALIDATOR.iter_errors(report))


class TypedMissingnessContractTests(unittest.TestCase):
    def test_valid_not_measured_null_passes(self):
        self.assertEqual(errors(base_mm03_report()), [])

    def test_mm03_requires_typed_role_payload(self):
        r = base_mm03_report()
        r.pop("role_payload")
        self.assertTrue(errors(r))

    def test_not_measured_numeric_zero_fails(self):
        r = base_mm03_report()
        r["role_payload"]["metric_results"][0]["value"] = 0
        self.assertTrue(errors(r))

    def test_unknown_numeric_value_fails(self):
        r = base_mm03_report()
        m = r["role_payload"]["metric_results"][0]
        m["status"] = "UNKNOWN"
        m["value"] = 1.0
        self.assertTrue(errors(r))

    def test_measured_without_numeric_value_fails(self):
        r = base_mm03_report()
        m = r["role_payload"]["metric_results"][0]
        m["status"] = "MEASURED"
        m["value"] = None
        self.assertTrue(errors(r))

    def test_measured_zero_is_a_valid_measured_result(self):
        r = base_mm03_report()
        m = r["role_payload"]["metric_results"][0]
        m["status"] = "MEASURED"
        m["value"] = 0.0
        m["reason"] = "qualified measurement returned exact zero"
        self.assertEqual(errors(r), [])

    def test_unknown_metric_field_fails_closed(self):
        r = base_mm03_report()
        r["role_payload"]["metric_results"][0]["unexpected"] = True
        self.assertTrue(errors(r))


if __name__ == "__main__":
    unittest.main()
