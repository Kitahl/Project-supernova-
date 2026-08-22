import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "diagnose_authority_bootstrap.py"
WORKFLOW = ROOT / ".github" / "workflows" / "supernova-pr-target-admission.yml"


class BootstrapDiagnosticTests(unittest.TestCase):
    def test_helper_reuses_accepted_bootstrap_code_without_authoritative_context(self):
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn("reconcile_authority_bootstrap.py", text)
        self.assertIn("mod.post = lambda", text)
        self.assertIn('CONTEXT = "supernova/bootstrap-diagnostic"', text)
        self.assertNotIn('CONTEXT = "supernova/bootstrap-admission"', text)
        self.assertIn('CANDIDATE_DIAGNOSTICS_RESULT', text)
        self.assertIn("candidate diagnostics assumed PASS", text)

    def test_diagnostic_binds_exact_live_pr_head_and_base_before_replay(self):
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn('os.environ["DIAGNOSED_HEAD_SHA"] = sha', text)
        self.assertIn('os.environ["DIAGNOSED_BASE_SHA"] = base_sha', text)
        self.assertIn('cannot resolve exact PR head/base', text)
        self.assertIn('exact PR head/base bound', text)

    def test_failure_reason_is_encoded_as_non_authoritative_context(self):
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn("def reason_code", text)
        self.assertIn("supernova/bootstrap-diagnostic/", text)
        self.assertIn("current-main-ancestor", text)
        self.assertIn("countable-control", text)
        self.assertIn("candidate-policy-check", text)
        self.assertIn("diagnosed-head", text)
        self.assertIn("diagnosed-base", text)
        self.assertNotIn("/issues/", text)

    def test_trusted_pr_target_invokes_helper_with_least_privilege(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("cd trusted && python scripts/diagnose_authority_bootstrap.py", text)
        self.assertIn("pull_request_target:", text)
        self.assertIn("statuses: write", text)
        self.assertNotIn("issues: write", text)
        self.assertIn("git clone --filter=blob:none", text)


if __name__ == "__main__":
    unittest.main()
