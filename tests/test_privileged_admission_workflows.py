import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"


class PrivilegedAdmissionWorkflowTests(unittest.TestCase):
    def text(self, name):
        return (WF / name).read_text(encoding="utf-8")

    def test_candidate_diagnostics_has_no_status_write_authority(self):
        text = self.text("supernova-v25-admission.yml")
        self.assertIn("pull_request:", text)
        self.assertIn("Candidate diagnostics only", text)
        self.assertNotIn("statuses: write", text)
        self.assertNotIn("supernova/static-control", text)
        self.assertNotIn("supernova/report-admission", text)
        self.assertNotIn("supernova/transition-admission", text)

    def test_pr_target_writer_runs_trusted_reconciler(self):
        text = self.text("supernova-pr-target-admission.yml")
        self.assertIn("pull_request_target:", text)
        self.assertIn("statuses: write", text)
        self.assertIn("git clone --filter=blob:none", text)
        self.assertIn("cd trusted && python3 scripts/reconcile_open_prs.py", text)
        self.assertNotIn("actions/checkout@", text)

    def test_comment_writer_runs_trusted_reconciler(self):
        text = self.text("supernova-comment-admission.yml")
        self.assertIn("issue_comment:", text)
        self.assertIn("statuses: write", text)
        self.assertIn("git clone --filter=blob:none", text)
        self.assertIn("cd repo && python3 scripts/reconcile_open_prs.py", text)
        self.assertNotIn("actions/checkout@", text)

    def test_authority_contract_forbids_privileged_candidate_code(self):
        authority = json.loads((ROOT / "config" / "admission_authority.json").read_text(encoding="utf-8"))
        self.assertEqual(authority["candidate_code_execution_with_status_write_token"], "FORBIDDEN")
        self.assertEqual(authority["candidate_bytes_treatment"], "DATA_ONLY_UNDER_TRUSTED_MAIN_VALIDATORS")
        self.assertEqual(authority["required_status_creator"], "github-actions[bot]")


if __name__ == "__main__":
    unittest.main()
