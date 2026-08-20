import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows/supernova-authority-bootstrap.yml"
BOOT = ROOT / "scripts/reconcile_authority_bootstrap.py"
OPEN = ROOT / "scripts/reconcile_open_prs.py"
POLICY = ROOT / "config/authority_bootstrap_v25.json"
AUTH = ROOT / "config/admission_authority.json"


class AuthorityBootstrapTests(unittest.TestCase):
    def test_policy_is_fail_closed_and_pre_streak_only(self):
        p = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(p["trusted_executable_source"], "EXACT_ACCEPTED_MAIN")
        self.assertEqual(p["candidate_diagnostics"], "READ_ONLY_SEPARATE_JOB_REQUIRED")
        self.assertEqual(p["calibration_streak_required"], 0)
        self.assertIs(p["fresh_allowed_globally_required"], False)
        self.assertEqual(p["worker_auth_change"], "FORBIDDEN_IN_AUTOMATED_BOOTSTRAP")
        self.assertEqual(p["state_or_scientific_change"], "FORBIDDEN_IN_AUTOMATED_BOOTSTRAP")
        self.assertEqual(p["failure_semantics"], "FAIL_CLOSED")

    def test_candidate_job_is_read_only_and_separate_from_status_writer(self):
        text = WF.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^  pull_request_target:\s*$")
        self.assertNotRegex(text, r"(?m)^  workflow_dispatch:\s*$")
        self.assertNotRegex(text, r"(?m)^  pull_request:\s*$")
        candidate, trusted = text.split("  trusted-bootstrap:", 1)
        self.assertIn("candidate-diagnostics:", candidate)
        self.assertNotIn("statuses: write", candidate)
        self.assertNotIn("contents: write", candidate)
        self.assertIn("persist-credentials: false", candidate)
        self.assertIn('GITHUB_TOKEN: ""', candidate)
        self.assertIn("needs: candidate-diagnostics", trusted)
        self.assertIn("statuses: write", trusted)
        self.assertNotIn("contents: write", trusted)
        self.assertIn("scripts/reconcile_authority_bootstrap.py", trusted)
        self.assertIn("scripts/reconcile_open_prs.py", trusted)

    def test_bootstrap_verifier_cannot_mutate_or_merge(self):
        text = BOOT.read_text(encoding="utf-8")
        self.assertIn('"state/CURRENT.json"', text)
        self.assertIn('"config/worker_auth.json"', text)
        self.assertIn('state.get("calibration_streak") != 0', text)
        self.assertIn('state.get("fresh_allowed_globally") is not False', text)
        self.assertIn('CANDIDATE_DIAGNOSTICS_RESULT', text)
        self.assertNotIn('/merge', text)
        self.assertNotIn('git push', text)

    def test_normal_reconciler_requires_source_verified_bootstrap(self):
        text = OPEN.read_text(encoding="utf-8")
        self.assertIn('BOOTSTRAP_CONTEXT = "supernova/bootstrap-admission"', text)
        self.assertIn('BOOTSTRAP_CREATOR = "github-actions[bot]"', text)
        self.assertIn("trusted_bootstrap_success(head_sha)", text)
        self.assertIn("authority bytes changed without source-verified bootstrap", text)

    def test_admission_contract_names_bootstrap_components(self):
        a = json.loads(AUTH.read_text(encoding="utf-8"))
        self.assertEqual(a["trusted_authority_bootstrap_reconciler"], "scripts/reconcile_authority_bootstrap.py")
        self.assertEqual(a["authority_bootstrap_context"], "supernova/bootstrap-admission")
        self.assertIn(".github/workflows/supernova-authority-bootstrap.yml", a["authoritative_status_workflows"])
        self.assertEqual(a["candidate_code_execution_with_status_write_token"], "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
