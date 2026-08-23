import importlib.util
import json
import pathlib
import sys
import unittest

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("reconcile_v25_admission", ROOT / "scripts/reconcile_v25_admission.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)

class CountableControlGateConsistencyTests(unittest.TestCase):
    def contract(self):
        return json.loads((ROOT / "config/countable_control_set_v25.json").read_text(encoding="utf-8"))

    def test_declarative_contract_contains_hardened_minimum(self):
        contract=self.contract()
        self.assertEqual(contract["schema_version"],"PS-COUNTABLE-CONTROL-SET-2.5-25")
        required = MOD.required_countable_paths(contract)
        self.assertTrue(MOD.MINIMUM_HARDENED_CONTROL.issubset(required))
        self.assertIn("scripts/strict_json.py",required)
        self.assertIn("config/root_epoch9_integrity_repair_epoch_v25.json",required)
        self.assertIn("config/root_epoch10_scheduler_admission_epoch_v25.json",required)
        self.assertIn("scripts/scheduler_admission_guard.py",required)
        self.assertIn("schemas/scheduler_manifest.schema.json",required)

    def test_declarative_addition_is_automatically_required(self):
        contract = self.contract();contract["required_control_paths"] = list(contract["required_control_paths"]) + ["tests/future_required_guard.py"]
        self.assertIn("tests/future_required_guard.py", MOD.required_countable_paths(contract))

    def test_dropping_any_hardened_minimum_fails_closed(self):
        contract = self.contract();victim = sorted(MOD.MINIMUM_HARDENED_CONTROL)[0]
        contract["required_control_paths"] = [p for p in contract["required_control_paths"] if p != victim]
        with self.assertRaises(ValueError):MOD.required_countable_paths(contract)

    def test_wrong_plan_or_protocol_fails_closed(self):
        contract = self.contract();contract["protocol_version"] = "2.6"
        with self.assertRaises(ValueError):MOD.required_countable_paths(contract)
        contract = self.contract();contract["task_network_plan_id"] = "wrong"
        with self.assertRaises(ValueError):MOD.required_countable_paths(contract)

    def test_source_bound_creator_is_fixed_not_receipt_selected(self):
        self.assertEqual(MOD.ACTIONS_CREATOR, "github-actions[bot]")

    def safe_ref(self, worker_id):
        return {"worker_id":worker_id,"path_change_commit_count":1,"immutable_history_valid":True,"auth_valid":True,"schema_valid":True,"strict_session_valid":True,"execution_mode_valid":True,"structural_ci_status":"PASS","report_creation_commit_sha":"a"*40}

    def quarantine_ref(self, worker_id="MM02"):
        return {"worker_id":worker_id,"observed_head_sha":"b"*40,"observed_blob_sha":"c"*40,"reason_code":"DETERMINISTIC_TRANSPORT_FAILURE"}

    def liveness(self):
        return [{"lane_id":wid,"receipt_status":"RUN_OBSERVED"} for wid in sorted(MOD.WORKERS)]

    def quarantine_verification(self):
        safe_workers=sorted(MOD.WORKERS-{"MM02"})
        return {"verdict":"VERIFIED_WITH_QUARANTINES","partition_exhaustive_verified":True,"safe_report_refs":[self.safe_ref(w) for w in safe_workers],"quarantined_report_refs":[self.quarantine_ref()],"missing_workers":[],"calibration_pass":False,"liveness_complete":True,"lane_liveness_observations":self.liveness(),"checker_pin_bundle_ref":"config/checker_pins.json","statement_fidelity_policy":"NOT_APPLICABLE_TRANSPORT_ONLY","pre_ci_observation":"PRE_CI","required_post_write_ci_context":"supernova/report-admission"}

    def countable_state(self):return {"calibration_countable_current":True}

    def test_quarantine_terminal_verifier_is_report_admissible(self):
        self.assertEqual(MOD.verification_semantic_errors(self.quarantine_verification(),self.countable_state()),[])

    def test_nonclean_verifier_cannot_claim_calibration_pass(self):
        v=self.quarantine_verification();v["calibration_pass"]=True
        self.assertIn("nonclean verifier verdict cannot grant calibration pass",MOD.verification_semantic_errors(v,self.countable_state()))

    def test_complete_verdict_stays_strict(self):
        v=self.quarantine_verification();v["verdict"]="VERIFIED_COMPLETE"
        self.assertIn("complete verdict requires 12 SAFE and zero quarantine/missing",MOD.verification_semantic_errors(v,self.countable_state()))

    def test_diagnostic_integration_preserves_exact_mm06_partition(self):
        v=self.quarantine_verification();i={"verification_verdict":v["verdict"],"verification_partition_exhaustive":True,"verification_liveness_complete":True,"safe_report_refs":v["safe_report_refs"],"quarantines":v["quarantined_report_refs"],"missing_workers":[],"calibration_pass":False}
        self.assertEqual(MOD.integration_semantic_errors(i,v,self.countable_state()),[])

    def test_diagnostic_integration_cannot_promote_or_drop_quarantine(self):
        v=self.quarantine_verification();i={"verification_verdict":v["verdict"],"verification_partition_exhaustive":True,"verification_liveness_complete":True,"safe_report_refs":v["safe_report_refs"]+[self.safe_ref("MM02")],"quarantines":[],"missing_workers":[],"calibration_pass":True}
        errors=MOD.integration_semantic_errors(i,v,self.countable_state())
        self.assertIn("integration safe refs differ from MM06 safe refs",errors)
        self.assertIn("integration quarantines differ from MM06 quarantine refs",errors)
        self.assertIn("integration calibration pass requires clean MM06 verdict/partition/liveness",errors)
        self.assertIn("diagnostic integration must force calibration pass false",errors)

    def test_integration_schema_accepts_terminal_quarantine_and_forces_zero_credit(self):
        schema=json.loads((ROOT/"schemas"/"branch_integration.schema.json").read_text())
        base={"session_header":{},"task_network_plan_id":MOD.PLAN,"cohort_id":"CAL-TEST","integration_id":"INT-TEST","generation_head_sha":"a"*40,"integrator_branch":"ps/integrate/CAL-TEST","verification_branch":"ps/verify/CAL-TEST","verification_head_sha":"b"*40,"verification_external_ci_context":"supernova/report-admission","verification_external_ci_status":"PASS","verification_external_ci_source":"github-actions[bot]","verification_external_ci_observed_after_receipt":True,"verification_verdict":"VERIFIED_WITH_QUARANTINES","verification_partition_exhaustive":True,"verification_liveness_complete":True,"runtime_state_id":"runtime","executive_status":"TERMINAL_DIAGNOSTIC","safe_report_refs":[{} for _ in range(11)],"task_ledger":[],"issue_ledger":[],"test_ledger":[],"plan_alignment":[],"research_questions":[],"quarantines":[{"worker_id":"MM02"}],"missing_workers":[],"costs_regressions_unknowns":{},"calibration_pass":False,"next_action":"BIL00"}
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(base)),[])
        promoted=dict(base);promoted["calibration_pass"]=True
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(promoted)))

    def test_verification_schema_forces_nonclean_zero_credit(self):
        schema=json.loads((ROOT/"schemas"/"branch_verification.schema.json").read_text())
        quarantine_branch=next(x["then"]["properties"]["calibration_pass"] for x in schema["allOf"] if x.get("if",{}).get("properties",{}).get("verdict",{}).get("const")=="VERIFIED_WITH_QUARANTINES")
        self.assertEqual(quarantine_branch,{"const":False})

    def test_scheduler_admission_is_part_of_trusted_gate_surface(self):
        text=(ROOT/"scripts/reconcile_v25_admission.py").read_text(encoding="utf-8")
        self.assertIn("scheduler_admission_guard",text)
        self.assertIn("source_preactivation_admission",text)
        self.assertIn("SCHEDULER_ADMISSION_PASS",text)

if __name__ == "__main__": unittest.main()
