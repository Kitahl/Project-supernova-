import importlib.util
import json
import pathlib
import unittest
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class SchedulerAdmissionNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard = load_module("scheduler_admission_guard_test", "scripts/scheduler_admission_guard.py")
        cls.delta = load_module("generation_delta_guard_test", "scripts/generation_delta_guard.py")

    def test_wrong_generation_delta_without_scheduler_manifest_fails(self):
        cohort = "CAL-NEG"
        errors = self.delta.validate_names([f"control/{cohort}.json",f"assignments/{cohort}.json",f"liveness/{cohort}.json"],cohort,True)
        self.assertTrue(errors);self.assertIn("scheduler", " ".join(errors))

    def test_extra_generation_path_fails(self):
        cohort="CAL-NEG";names=self.delta.expected_paths(cohort,True)+[f"reports/{cohort}/MF01.json"]
        errors=self.delta.validate_names(names,cohort,True);self.assertTrue(errors);self.assertIn("extra"," ".join(errors))

    def test_staged_candidate_cannot_produce_before_exact_activation(self):
        manifest={"cohort_id":"CAL-NEXT","generation_head_sha":"1"*40,"production_not_before_utc":"2030-01-01T01:00:00Z"}
        now=datetime(2030,1,1,2,tzinfo=timezone.utc)
        self.assertFalse(self.guard.production_allowed({"active_cohort_id":"CAL-OLD","generation_head_sha":"0"*40},manifest,now))
        self.assertFalse(self.guard.production_allowed({"active_cohort_id":"CAL-NEXT","generation_head_sha":"0"*40},manifest,now))
        self.assertFalse(self.guard.production_allowed({"active_cohort_id":"CAL-NEXT","generation_head_sha":"1"*40},manifest,datetime(2030,1,1,0,59,tzinfo=timezone.utc)))
        self.assertTrue(self.guard.production_allowed({"active_cohort_id":"CAL-NEXT","generation_head_sha":"1"*40},manifest,now))

    def test_naive_local_time_is_rejected(self):
        with self.assertRaises(ValueError):self.guard.parse_time("2030-01-01T01:00:00")

    def test_public_scheduler_evidence_rejects_raw_auth_key_names(self):
        errors=[];self.guard._scan_public({"worker_auth_secret_hex":"do-not-publish"},errors)
        self.assertTrue(errors);self.assertIn("raw auth material",errors[0])

    def test_behavioral_projection_excludes_mutable_runtime_fields(self):
        semantics=json.loads((ROOT/"config/task_registry_semantics_v25.json").read_text())
        projection=set(semantics["behavioral_config_projection"]);excluded=set(semantics["mutable_runtime_fields_excluded"])
        self.assertNotIn("last_run_time",projection);self.assertIn("last_run_time",excluded)
        self.assertIn("normalized_schedule",projection);self.assertIn("prompt_sha256",projection)
        self.assertEqual(semantics["api_success_semantics"],"NOT_PROOF_OF_POSTCONDITION")

    def test_schemas_are_closed_and_do_not_expose_raw_auth_fields(self):
        for path in ("schemas/scheduler_manifest.schema.json","schemas/preactivation_receipt.schema.json","schemas/scheduler_admission.schema.json"):
            schema=json.loads((ROOT/path).read_text());self.assertFalse(schema["additionalProperties"]);raw=json.dumps(schema).lower()
            self.assertNotIn('"worker_auth_secret"',raw);self.assertNotIn('"worker_auth_secret_hex"',raw);self.assertNotIn('"private_key"',raw)

    def test_guard_covers_known_scheduler_failure_classes(self):
        text=(ROOT/"scripts/scheduler_admission_guard.py").read_text()
        for token in ("duplicate scheduler task id","canonical title/task session mismatch","normalized scheduler timezone","worker auth commitment mismatch","liveness lacks one full retry","preactivation challenge is not strictly before production_not_before","scheduler admission receipt missing; stage and promote must be distinct transactions"):
            self.assertIn(token,text)

if __name__ == "__main__":unittest.main()
