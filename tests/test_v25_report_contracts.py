import copy
import hashlib
import hmac
import json
import pathlib
import tempfile
import unittest

from jsonschema import Draft202012Validator
from scripts.validate_branch_bus_v251 import execution_mode_errors, issue_ledger_errors, report_transport_errors

ROOT = pathlib.Path(__file__).resolve().parents[1]
HMAC2 = "PS-HMAC-SHA256-CANONICAL-REPORT-2"
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
TRANSPORT = "PRETTY_SORTED_UTF8_JSON_V1"


def canonical_payload(report):
    signed = copy.deepcopy(report)
    signed.pop("worker_auth_proof", None)
    return json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def proof(secret, report):
    return hmac.new(secret, canonical_payload(report), hashlib.sha256).hexdigest()


def complete_issue(issue_id="ISSUE-1"):
    return {
        "issue_id": issue_id,
        "severity": "HIGH",
        "component": "transport control",
        "status": "OPEN",
        "exact_failure": "exact reproducible failure",
        "evidence_refs": ["commit:abc"],
        "blocker": True,
        "proposed_protocol_2_5_fix_test": "repair and rerun falsifier",
        "required_test": "original falsifier fails before repair and passes after repair",
        "owner": "BIL00",
        "authoritative_control_change": True,
        "next_action": "stage smallest repair",
    }


def mm03_report(result=None):
    if result is None:
        result = {
            "result_type": "SCIENTIFIC_METRIC",
            "status": "NOT_MEASURED",
            "value": None,
            "reason": "T0 replay has no authorized fresh SlopCode metric",
            "evidence_refs": [],
            "unit": None,
        }
    return {
        "session_header": {
            "schema_version": "PS-SESSION-2", "session_name": "PS-MM-W03 | SlopCode Contracts", "target_program": "MASTERMIND",
            "phase": "T0_COUNTABLE_REPLAY_COHORT_TEST", "iteration_id": "CAL-TEST", "iteration_number": 8, "role_id": "MM03", "goal": "typed missingness test",
            "plan_id": PLAN, "runtime_state_id": "runtime-test", "model_target": "GPT-5.6 Sol", "reasoning_effort_target": "EXTRA_HIGH",
            "model_binding_status": "PARTIAL_UNVERIFIED", "execution_mode": "SAFE_REPLAY_ONLY",
        },
        "task_network_plan_id": PLAN, "cohort_id": "CAL-TEST", "worker_id": "MM03", "report_id": "RPT-TEST-MM03", "generation_seq": 8,
        "generation_head_sha": "a" * 40, "worker_branch": "ps/work/CAL-TEST/MM03", "assignment_id": "ASSIGN-TEST", "assignment_git_identity": "b" * 40,
        "parent_state_git_identity": "c" * 40, "control_manifest_id": "CTRL-TEST", "control_manifest_git_identity": "d" * 40,
        "network_checkpoint_id": "checkpoint-test", "runtime_state_id": "runtime-test", "visibility_token": "visibility-test",
        "transport_serialization": TRANSPORT,
        "worker_auth_scheme": HMAC2, "worker_auth_commitment": "e" * 64, "worker_auth_proof": "f" * 64, "status": "VALID_ASSIGNED_REPORT",
        "mode": "SAFE_REPLAY_ONLY", "evidence_tier": "T0_TEST", "executive_status": "ZERO_DELTA_TERMINAL_WORKER_RECEIPT",
        "fresh_evidence_ids": [], "private_manifest_id": None, "private_manifest_git_identity": None, "task_ledger": [], "issue_ledger": [], "test_ledger": [],
        "plan_alignment": [], "evidence_and_provenance": {}, "claim_scope": "transport only", "runtime_implementation_implication": "none",
        "negative_zero_outcomes": [], "research_questions": [], "role_payload": {"slopcode_result": result},
        "cost_ledger": {"fresh_evidence_units_consumed": 0, "protected_manifest_reads": 0, "benchmark_executions": 0, "deep_research_runs": 0, "notes": "test"},
        "public_safety_status": "PASS", "origin_reread_claim": False, "next_action": "MM06",
    }


class V25ReportContractTests(unittest.TestCase):
    def report_schema(self):
        return json.loads((ROOT / "schemas" / "branch_report.schema.json").read_text(encoding="utf-8"))

    def report_errors(self, report):
        return list(Draft202012Validator(self.report_schema()).iter_errors(report))

    def test_auth_metadata_matches_hmac2(self):
        auth = json.loads((ROOT / "config" / "worker_auth.json").read_text(encoding="utf-8"))
        self.assertEqual(auth["scheme"], HMAC2)
        self.assertTrue(auth["raw_secrets_forbidden_in_repo"])
        self.assertEqual(auth["canonicalization"]["remove_field"], "worker_auth_proof")
        self.assertTrue(auth["canonicalization"]["sort_keys"])
        self.assertTrue(auth["canonicalization"]["compact_separators"])
        self.assertFalse(auth["canonicalization"]["ensure_ascii"])

    def test_mutation_of_any_signed_report_area_invalidates_hmac(self):
        secret = bytes.fromhex("11" * 32)
        base = {"task_network_plan_id":"p","cohort_id":"c","worker_id":"MF01","mode":"SAFE_REPLAY_ONLY","session_header":{"execution_mode":"SAFE_REPLAY_ONLY","goal":"g"},"evidence_ledger":[{"id":"e1","status":"ZERO_DELTA"}],"issue_ledger":[{"issue_id":"i1","status":"OPEN"}],"cost_ledger":{"benchmark_executions":0,"deep_research_runs":0},"worker_auth_proof":None}
        expected = proof(secret, base); base["worker_auth_proof"] = expected
        self.assertTrue(hmac.compare_digest(proof(secret, base), expected))
        mutations=[]
        for mut in (
            lambda m:m.__setitem__('cohort_id','other'),
            lambda m:m.__setitem__('mode','FRESH'),
            lambda m:m['session_header'].__setitem__('execution_mode','FRESH'),
            lambda m:m['evidence_ledger'][0].__setitem__('status','PASS'),
            lambda m:m['issue_ledger'][0].__setitem__('status','CLOSED'),
            lambda m:m['cost_ledger'].__setitem__('benchmark_executions',1),
        ):
            x=copy.deepcopy(base); mut(x); mutations.append(x)
        for mutated in mutations:self.assertFalse(hmac.compare_digest(proof(secret, mutated), expected))

    def test_execution_mode_positive(self):
        self.assertEqual(execution_mode_errors({"mode":"SAFE_REPLAY_ONLY","session_header":{"execution_mode":"SAFE_REPLAY_ONLY"}},{"network_mode":"GITHUB_BRANCH_CALIBRATION"}), [])

    def test_execution_mode_mismatch_rejected(self):
        errors=execution_mode_errors({"mode":"SAFE_REPLAY_ONLY","session_header":{"execution_mode":"FRESH"}},{"network_mode":"GITHUB_BRANCH_CALIBRATION"})
        self.assertIn("session_header.execution_mode != report.mode",errors);self.assertIn("calibration session execution_mode != SAFE_REPLAY_ONLY",errors)

    def test_calibration_fresh_mode_rejected_even_when_header_matches(self):
        errors=execution_mode_errors({"mode":"FRESH","session_header":{"execution_mode":"FRESH"}},{"network_mode":"GITHUB_BRANCH_CALIBRATION"})
        self.assertIn("calibration session execution_mode != SAFE_REPLAY_ONLY",errors);self.assertIn("calibration report mode != SAFE_REPLAY_ONLY",errors)

    def test_issue_record_is_closed_and_complete(self):
        issue_schema=self.report_schema()["$defs"]["issue_record"]
        self.assertEqual(list(Draft202012Validator(issue_schema).iter_errors(complete_issue())), [])
        for field in issue_schema["required"]:
            bad=complete_issue();bad.pop(field);self.assertTrue(list(Draft202012Validator(issue_schema).iter_errors(bad)),field)
        extra=complete_issue();extra["self_attested_pass"]=True;self.assertTrue(list(Draft202012Validator(issue_schema).iter_errors(extra)))

    def test_duplicate_issue_ids_fail_trusted_validation(self):
        self.assertIn("duplicate issue_ledger issue_id DUP",issue_ledger_errors({"executive_status":"FINDINGS","issue_ledger":[complete_issue("DUP"),complete_issue("DUP")]}))

    def test_empty_issue_ledger_requires_explicit_zero_delta(self):
        self.assertEqual(issue_ledger_errors({"executive_status":"ZERO_DELTA_TERMINAL_WORKER_RECEIPT","issue_ledger":[]}),[])
        self.assertIn("empty issue_ledger requires explicit ZERO_DELTA executive_status",issue_ledger_errors({"executive_status":"PASS","issue_ledger":[]}))

    def test_zero_delta_cannot_hide_findings(self):
        self.assertIn("ZERO_DELTA executive_status requires empty issue_ledger",issue_ledger_errors({"executive_status":"ZERO_DELTA_TERMINAL_WORKER_RECEIPT","issue_ledger":[complete_issue()]}))

    def test_mm03_valid_not_measured_null_passes(self): self.assertEqual(self.report_errors(mm03_report()),[])
    def test_mm03_role_payload_is_required(self):
        report=mm03_report();report.pop("role_payload");self.assertTrue(self.report_errors(report))
    def test_mm03_not_measured_numeric_zero_fails(self):
        report=mm03_report();report["role_payload"]["slopcode_result"]["value"]=0;self.assertTrue(self.report_errors(report))
    def test_mm03_shadow_sibling_metric_fails(self):
        report=mm03_report();report["role_payload"]["slopcode_score"]=0;self.assertTrue(self.report_errors(report))
    def test_mm03_unknown_numeric_value_fails(self):
        result={"result_type":"SCIENTIFIC_METRIC","status":"UNKNOWN","value":1.0,"reason":"unknown","evidence_refs":[],"unit":None};self.assertTrue(self.report_errors(mm03_report(result)))
    def test_mm03_measured_without_numeric_value_fails(self):
        result={"result_type":"SCIENTIFIC_METRIC","status":"MEASURED","value":None,"reason":"missing value","evidence_refs":[],"unit":None};self.assertTrue(self.report_errors(mm03_report(result)))

    def test_deterministic_pretty_transport_is_required(self):
        report=mm03_report()
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'r.json';p.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            self.assertEqual(report_transport_errors(p,report),[])
            p.write_text(json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
            self.assertIn('report transport must be multi-line JSON',report_transport_errors(p,report))

    def test_integration_plan_binding_is_single_frozen_constant(self):
        schema=json.loads((ROOT/'schemas/branch_integration.schema.json').read_text(encoding='utf-8'))
        self.assertEqual(schema['properties']['task_network_plan_id']['const'],PLAN)
        stale='0aa341106cfc4654d5de358526716cadba8c9199b31e9eb15a90f488757cc30d7'
        self.assertNotEqual(stale,PLAN)
        self.assertNotEqual(schema['properties']['task_network_plan_id']['const'],stale)

    def test_hourly_registry_has_exact_fifteen_staggered_lanes(self):
        reg=json.loads((ROOT/"config"/"task_registry_v25.json").read_text(encoding="utf-8"));self.assertEqual(reg["schedule_hours_local"],list(range(24)));self.assertEqual(reg["minimum_recurrence_per_task"],"PT1H");self.assertEqual(reg["active_task_count"],15);self.assertTrue(reg["no_sixteenth_lane"]);self.assertEqual(len(reg["tasks"]),15)
        minutes={x["role_id"]:x["minute"] for x in reg["tasks"]};workers=["MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"]
        self.assertEqual([minutes[x] for x in workers],list(range(5,17)));self.assertEqual(minutes["MM06"],35);self.assertEqual(minutes["MF06"],45);self.assertEqual(minutes["BIL00"],58)

if __name__ == "__main__": unittest.main()
