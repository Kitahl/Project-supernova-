import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

from jsonschema import Draft202012Validator


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SchedulerRetryBudgetFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard = load_module("root11_retry_budget_guard", "scripts/scheduler_admission_guard.py")
        cls.preactivation = load_module("root11_retry_budget_preactivation", "scripts/reconcile_preactivation_admission.py")
        cls.authority = json.loads((ROOT / "config/scheduler_attestation_authority_v25.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((ROOT / "schemas/scheduler_manifest.schema.json").read_text(encoding="utf-8"))

    def test_exact_values_are_frozen_outside_candidate_manifest(self):
        self.assertEqual(self.authority["max_attempt_duration_seconds"], 600)
        self.assertEqual(self.authority["scheduler_jitter_budget_seconds"], 60)
        self.assertEqual(
            self.authority["retry_budget_authority"],
            "ACCEPTED_MAIN_EXACT_VALUES_CANDIDATE_OVERRIDE_FORBIDDEN",
        )
        self.assertEqual(self.schema["properties"]["max_attempt_duration_seconds"], {"const": 600})
        self.assertEqual(self.schema["properties"]["scheduler_jitter_budget_seconds"], {"const": 60})

    def test_schema_rejects_oversized_attempt_and_jitter(self):
        attempt = Draft202012Validator(self.schema["properties"]["max_attempt_duration_seconds"])
        jitter = Draft202012Validator(self.schema["properties"]["scheduler_jitter_budget_seconds"])
        self.assertEqual(list(attempt.iter_errors(600)), [])
        self.assertEqual(list(jitter.iter_errors(60)), [])
        self.assertTrue(list(attempt.iter_errors(601)))
        self.assertTrue(list(attempt.iter_errors(10**9)))
        self.assertTrue(list(jitter.iter_errors(61)))
        self.assertTrue(list(jitter.iter_errors(10**9)))

    def test_guard_rejects_candidate_window_widening_against_accepted_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "config").mkdir()
            shutil.copyfile(
                ROOT / "config/scheduler_attestation_authority_v25.json",
                root / "config/scheduler_attestation_authority_v25.json",
            )
            approved = {
                "max_attempt_duration_seconds": 600,
                "scheduler_jitter_budget_seconds": 60,
            }
            self.assertEqual(self.guard.scheduler_retry_budget_errors(root, approved), [])
            for field, oversized in (
                ("max_attempt_duration_seconds", 601),
                ("max_attempt_duration_seconds", 10**9),
                ("scheduler_jitter_budget_seconds", 61),
                ("scheduler_jitter_budget_seconds", 10**9),
            ):
                candidate = dict(approved)
                candidate[field] = oversized
                with self.subTest(field=field, oversized=oversized):
                    errors = self.guard.scheduler_retry_budget_errors(root, candidate)
                    self.assertTrue(any(field in error for error in errors), errors)

    def test_trusted_status_writer_cannot_use_oversized_candidate_window(self):
        approved = {
            "max_attempt_duration_seconds": 600,
            "scheduler_jitter_budget_seconds": 60,
        }
        self.assertEqual(self.preactivation.trusted_retry_budget_seconds(approved, self.authority), 660)
        for field, oversized in (
            ("max_attempt_duration_seconds", 601),
            ("scheduler_jitter_budget_seconds", 61),
        ):
            candidate = dict(approved)
            candidate[field] = oversized
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field):
                    self.preactivation.trusted_retry_budget_seconds(candidate, self.authority)

    def test_tampered_external_authority_fails_closed(self):
        manifest = {
            "max_attempt_duration_seconds": 600,
            "scheduler_jitter_budget_seconds": 60,
        }
        for field, oversized in (
            ("max_attempt_duration_seconds", 601),
            ("scheduler_jitter_budget_seconds", 61),
        ):
            authority = dict(self.authority)
            authority[field] = oversized
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field):
                    self.preactivation.trusted_retry_budget_seconds(manifest, authority)


if __name__ == "__main__":
    unittest.main()
