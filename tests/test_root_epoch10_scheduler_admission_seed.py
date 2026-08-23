import json
import pathlib
import unittest

# This seed is installed through the ordinary protected hardening bootstrap path.
ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "root_epoch10_scheduler_admission_seed_v25.json"
SCRIPT = ROOT / "scripts" / "reconcile_root_epoch10_scheduler_admission_seed.py"
WORKFLOW = ROOT / ".github" / "workflows" / "supernova-root-epoch10-scheduler-admission-seed.yml"


class RootEpoch10SchedulerAdmissionSeedTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_seed_is_one_shot_epoch9_to_epoch10_and_zero_credit(self):
        p = self.policy
        self.assertEqual(p["schema_version"], "PS-ROOT-EPOCH10-SCHEDULER-ADMISSION-SEED-2.5-1")
        self.assertEqual(p["issue_ref"], "#225")
        self.assertEqual(p["required_current_root_epoch"], 9)
        self.assertEqual(p["target_root_epoch"], 10)
        self.assertEqual(p["required_active_cohort"], "CAL-BR-012-v25-4ca0dec6")
        self.assertEqual(p["required_generation_head"], "b366cf01e64e1a00a2e566e14e25cc7c15ce523f")
        self.assertEqual(p["required_verifier_blob"], "251e306b062de5386f3c8a1ff7d80683515547fd")
        self.assertEqual(p["required_verifier_verdict"], "INCOMPLETE")
        self.assertFalse(p["required_verifier_calibration_pass"])
        self.assertEqual(set(p["required_missing_workers"]), {"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"})
        self.assertEqual(p["calibration_streak_required"], 0)
        self.assertFalse(p["fresh_allowed_globally_required"])
        self.assertEqual(p["seed_self_modification"], "FORBIDDEN")
        self.assertEqual(p["failure_semantics"], "FAIL_CLOSED")

    def test_seed_closes_exact_scheduler_admission_repair_surface(self):
        p = self.policy
        allowed = set(p["allowed_root_candidate_paths"])
        required = set(p["required_root_candidate_paths"])
        self.assertEqual(allowed, required)
        for path in (
            "config/root_epoch10_scheduler_admission_epoch_v25.json",
            "config/root_tcb_epoch_v25.json",
            "config/countable_control_set_v25.json",
            "config/generation_delta_policy_v25.json",
            "config/task_registry_v25.json",
            "config/task_registry_semantics_v25.json",
            "schemas/control.schema.json",
            "schemas/scheduler_manifest.schema.json",
            "schemas/preactivation_receipt.schema.json",
            "schemas/scheduler_admission.schema.json",
            "scripts/scheduler_admission_guard.py",
            "scripts/transition_guard.py",
            "scripts/reconcile_v25_admission.py",
            "scripts/reconcile_open_prs.py",
            "tests/test_scheduler_admission_negative.py",
        ):
            self.assertIn(path, required)
        for prefix in ("state/", "control/", "assignments/", "liveness/", "reports/", "verification/", "integration/", "history/", "runtime/", "benchmark/", "research/"):
            self.assertIn(prefix, p["forbidden_candidate_prefixes"])

    def test_seed_requires_terminal_gen12_chain_and_machine_scheduler_gate(self):
        for needle in (
            "terminal Gen12 verifier receipt",
            "exact 12 MISSING",
            "terminal Gen12 MF06 receipt",
            "supernova/report-admission",
            "supernova/branch-integrate",
            "scheduler/{cohort}.json",
            "scheduler_admission_guard",
            "PREACTIVATION_WAIT",
            "normalized_first_production_utc",
            "scheduler_cadence_seconds",
            "max_attempt_duration_seconds",
            "scheduler_jitter_budget_seconds",
            "active_task_count",
            "no_sixteenth_lane",
        ):
            self.assertIn(needle, self.script)
        self.assertIn("parse_constant=_reject_constant", self.script)
        self.assertIn("object_pairs_hook=_unique_pairs", self.script)
        self.assertIn("allow_nan=False", self.script)

    def test_privileged_seed_workflow_is_separated_and_environment_bound(self):
        text = self.workflow
        candidate, trusted = text.split("  trusted-seed:", 1)
        self.assertIn("pull_request_target:", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("statuses: write", candidate)
        self.assertIn('GITHUB_TOKEN: ""', candidate)
        self.assertIn("persist-credentials: false", candidate)
        self.assertIn("runs-on: ubuntu-24.04", candidate)
        self.assertIn("python-version: '3.13.15'", candidate)
        self.assertIn("assert_validator_environment.py", candidate)
        self.assertIn("needs: candidate-diagnostics", trusted)
        self.assertIn("statuses: write", trusted)
        self.assertNotIn("contents: write", trusted)
        self.assertIn("runs-on: ubuntu-24.04", trusted)
        self.assertIn("python-version: '3.13.15'", trusted)
        self.assertIn("assert_validator_environment.py", trusted)
        self.assertIn("scripts/reconcile_root_epoch10_scheduler_admission_seed.py", trusted)


if __name__ == "__main__":
    unittest.main()
