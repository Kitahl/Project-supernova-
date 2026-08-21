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

    def test_failure_is_deduplicated_into_pr_comment(self):
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn("SUPERNOVA_BOOTSTRAP_DIAGNOSTIC", text)
        self.assertIn("report_failure", text)
        self.assertIn("/issues/{pr_number}/comments?per_page=100", text)
        self.assertIn("/issues/comments/{row['id']}", text)
        self.assertIn("accepted-main verifier reason", text)
        self.assertIn("diagnostic only", text)

    def test_trusted_pr_target_invokes_helper_from_cloned_main(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("cd trusted && python scripts/diagnose_authority_bootstrap.py", text)
        self.assertIn("pull_request_target:", text)
        self.assertIn("statuses: write", text)
        self.assertIn("issues: write", text)
        self.assertIn("git clone --filter=blob:none", text)


if __name__ == "__main__":
    unittest.main()
