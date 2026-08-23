import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/root_epoch10_scheduler_admission_seed_amendment_v25.json"
SCRIPT = ROOT / "scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py"
WORKFLOW = ROOT / ".github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml"


class RootEpoch10SchedulerAdmissionSeedAmendmentTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_amendment_binds_first_seed_and_exact_gen12_zero_credit_verifier(self):
        p = self.policy
        self.assertEqual(p["schema_version"], "PS-ROOT-EPOCH10-SCHEDULER-ADMISSION-SEED-AMENDMENT-2.5-1")
        self.assertEqual(p["required_current_root_epoch"], 9)
        self.assertEqual(p["target_root_epoch"], 10)
        self.assertEqual(p["first_seed_install_commit_sha"], "7bc97d2bed9fb285feb2e9ae1c31fb4331919d00")
        self.assertEqual(p["required_active_cohort"], "CAL-BR-012-v25-4ca0dec6")
        self.assertEqual(p["required_generation_head"], "b366cf01e64e1a00a2e566e14e25cc7c15ce523f")
        self.assertEqual(p["required_verifier_blob"], "251e306b062de5386f3c8a1ff7d80683515547fd")
        self.assertEqual(p["required_verifier_verdict"], "INCOMPLETE")
        self.assertEqual(len(p["required_missing_workers"]), 12)
        self.assertFalse(p["terminal_mf06_chain_required_before_root_repair"])
        self.assertEqual(p["first_seed_modification"], "FORBIDDEN")
        self.assertEqual(p["seed_self_modification"], "FORBIDDEN")
        self.assertEqual(p["failure_semantics"], "FAIL_CLOSED")

    def test_amendment_is_narrowly_scoped_to_demonstrated_deadlock_and_regressions(self):
        required = set(self.policy["required_root_candidate_paths"])
        self.assertEqual(required, set(self.policy["allowed_root_candidate_paths"]))
        for path in (
            ".github/workflows/supernova-rest-branch-reconciler.yml",
            "tests/test_rest_admission_dependency.py",
            "tests/test_root_epoch9_integrity_repair.py",
            "tests/test_gen10_zero_credit_terminal_transition.py",
            "tests/test_gen11_zero_credit_terminal_transition.py",
        ):
            self.assertIn(path, required)
        for path in (
            "state/CURRENT.json",
            "config/worker_auth.json",
            "reports/anything.json",
        ):
            self.assertNotIn(path, required)
        for prefix in ("state/","control/","assignments/","liveness/","scheduler/","scheduler_admission/","preactivation/","reports/","verification/","integration/","history/","runtime/","benchmark/","research/"):
            self.assertIn(prefix, self.policy["forbidden_candidate_prefixes"])

    def test_deadlock_proof_is_machine_checked(self):
        for token in (
            "for name in ('reconcile_branch_rest.py','reconcile_v25_admission.py')",
            "strict_json.py",
            "python3 /tmp/reconcile_v25_admission.py",
            "import strict_json",
            "trusted_deadlock_present",
            "terminal Gen12 verifier",
            "exact 12 MISSING",
        ):
            self.assertIn(token, self.script)
        self.assertIn("parse_constant=_reject_constant", self.script)
        self.assertIn("object_pairs_hook=_unique_pairs", self.script)
        self.assertIn("allow_nan=False", self.script)

    def test_candidate_must_replace_tmp_loader_with_frozen_repository_environment(self):
        for token in (
            "actions/checkout@",
            "actions/setup-python@",
            "requirements-validation.lock",
            "scripts/assert_validator_environment.py",
            "python scripts/reconcile_branch_rest.py",
            "python scripts/reconcile_v25_admission.py",
        ):
            self.assertIn(token, self.script)

    def test_privileged_amendment_workflow_is_separated(self):
        candidate, trusted = self.workflow.split("  trusted-seed-amendment:", 1)
        self.assertIn("pull_request_target:", self.workflow)
        self.assertNotIn("workflow_dispatch:", self.workflow)
        self.assertNotIn("statuses: write", candidate)
        self.assertIn('GITHUB_TOKEN: ""', candidate)
        self.assertIn("persist-credentials: false", candidate)
        self.assertIn("requirements-validation.lock", candidate)
        self.assertIn("assert_validator_environment.py", candidate)
        self.assertIn("needs: candidate-diagnostics", trusted)
        self.assertIn("statuses: write", trusted)
        self.assertNotIn("contents: write", trusted)
        self.assertIn("reconcile_root_epoch10_scheduler_admission_seed_amendment.py", trusted)


if __name__ == "__main__":
    unittest.main()
