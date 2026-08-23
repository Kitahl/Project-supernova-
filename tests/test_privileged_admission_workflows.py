import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
SETUP_PYTHON = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PYTHON_VERSION = "python-version: '3.13.15'"
ENV_ASSERT = "scripts/assert_validator_environment.py"


class PrivilegedAdmissionWorkflowTests(unittest.TestCase):
    def text(self, name):
        return (WF / name).read_text(encoding="utf-8")

    @staticmethod
    def has_top_level_event(text, event):
        return re.search(rf"(?m)^  {re.escape(event)}:\s*$", text) is not None

    def test_no_privileged_workflow_uses_candidate_or_ref_selectable_trigger(self):
        violations = []
        for path in sorted(WF.glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            if "statuses: write" not in text:
                continue
            for event in ("pull_request", "workflow_dispatch"):
                if self.has_top_level_event(text, event):
                    violations.append(f"{path.name}: {event}")
        self.assertEqual(violations, [])

    def test_obsolete_v24_status_writer_is_removed(self):
        self.assertFalse((WF / "supernova-v24-admission.yml").exists())

    def test_pip_only_binary_option_is_not_an_unquoted_yaml_scalar(self):
        violations = []
        for path in sorted(WF.glob("*.yml")):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "--only-binary=:all:" not in line:
                    continue
                if re.search(r"^\s+run:\s+[^\"'|>]", line):
                    violations.append(f"{path.name}:{line_number}")
        self.assertEqual(violations, [])

    def test_candidate_diagnostics_has_no_status_write_authority(self):
        text = self.text("supernova-v25-admission.yml")
        self.assertIn("pull_request:", text)
        self.assertIn("Candidate diagnostics only", text)
        self.assertNotIn("statuses: write", text)
        self.assertNotIn("supernova/static-control", text)
        self.assertNotIn("supernova/report-admission", text)
        self.assertNotIn("supernova/transition-admission", text)

    def assert_privileged_environment_is_frozen(self, text):
        self.assertIn(SETUP_PYTHON, text)
        self.assertIn("runs-on: ubuntu-24.04", text)
        self.assertIn(PYTHON_VERSION, text)
        self.assertIn(ENV_ASSERT, text)

    def test_pr_target_writer_runs_trusted_reconciler_with_exact_validator_environment(self):
        text = self.text("supernova-pr-target-admission.yml")
        self.assertIn("pull_request_target:", text)
        self.assertIn("statuses: write", text)
        self.assertIn("git clone --filter=blob:none", text)
        self.assertIn("cd trusted && python scripts/reconcile_open_prs.py", text)
        self.assert_privileged_environment_is_frozen(text)
        self.assertNotIn("actions/checkout@", text)

    def test_comment_writer_runs_trusted_reconciler_with_exact_validator_environment(self):
        text = self.text("supernova-comment-admission.yml")
        self.assertIn("issue_comment:", text)
        self.assertIn("statuses: write", text)
        self.assertIn("git clone --filter=blob:none", text)
        self.assertIn("cd repo && python scripts/reconcile_open_prs.py", text)
        self.assert_privileged_environment_is_frozen(text)
        self.assertNotIn("actions/checkout@", text)

    def test_open_pr_reconciler_uses_exact_validator_environment(self):
        text = self.text("supernova-open-pr-reconciler.yml")
        self.assertIn("statuses: write", text)
        self.assert_privileged_environment_is_frozen(text)

    def test_authority_bootstrap_separates_candidate_and_privileged_jobs(self):
        text = self.text("supernova-authority-bootstrap.yml")
        candidate, trusted = text.split("  trusted-bootstrap:", 1)
        self.assertIn("pull_request_target:", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("statuses: write", candidate)
        self.assertNotIn("contents: write", candidate)
        self.assertIn("persist-credentials: false", candidate)
        self.assertIn('GITHUB_TOKEN: ""', candidate)
        self.assertIn("needs: candidate-diagnostics", trusted)
        self.assertIn("statuses: write", trusted)
        self.assertNotIn("contents: write", trusted)
        self.assertIn("scripts/reconcile_authority_bootstrap.py", trusted)
        self.assertIn("scripts/reconcile_open_prs.py", trusted)

    def test_authority_contract_forbids_privileged_candidate_code(self):
        authority = json.loads((ROOT / "config" / "admission_authority.json").read_text(encoding="utf-8"))
        self.assertEqual(authority["candidate_code_execution_with_status_write_token"], "FORBIDDEN")
        self.assertEqual(authority["ref_selectable_dispatch_with_status_write_token"], "FORBIDDEN")
        self.assertEqual(authority["privileged_external_dispatch_event"], "repository_dispatch")
        self.assertEqual(authority["candidate_bytes_treatment"], "DATA_ONLY_UNDER_TRUSTED_MAIN_VALIDATORS")
        self.assertEqual(authority["required_status_creator"], "github-actions[bot]")
        self.assertEqual(authority["authority_bootstrap_context"], "supernova/bootstrap-admission")


if __name__ == "__main__":
    unittest.main()
