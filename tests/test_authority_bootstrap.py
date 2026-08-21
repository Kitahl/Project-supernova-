import importlib.util
import json
import pathlib
import re
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows/supernova-authority-bootstrap.yml"
BOOT = ROOT / "scripts/reconcile_authority_bootstrap.py"
OPEN = ROOT / "scripts/reconcile_open_prs.py"
POLICY = ROOT / "config/authority_bootstrap_v25.json"
AUTH = ROOT / "config/admission_authority.json"


def load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("reconcile_authority_bootstrap_test", BOOT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


INVARIANT_INPUTS = [
    "config/repo_policy.json",
    "config/admission_authority.json",
    "config/authority_bootstrap_v25.json",
    "config/protocol_freeze.json",
    "config/countable_control_set_v25.json",
]


def copy_invariant_inputs(dst: pathlib.Path):
    for rel in INVARIANT_INPUTS:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)


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

    def test_root_bootstrap_assets_are_not_self_updatable(self):
        mod = load_bootstrap_module()
        self.assertEqual(
            mod.ROOT_BOOTSTRAP_PATHS,
            {
                "config/authority_bootstrap_v25.json",
                "scripts/reconcile_authority_bootstrap.py",
                ".github/workflows/supernova-authority-bootstrap.yml",
            },
        )
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            trusted, candidate = base / "trusted", base / "candidate"
            copy_invariant_inputs(trusted)
            copy_invariant_inputs(candidate)
            errors = mod.bootstrap_invariant_errors(
                trusted,
                candidate,
                ["scripts/reconcile_authority_bootstrap.py"],
            )
            self.assertTrue(any("bootstrap root self-modification" in e for e in errors))

    def test_valid_installed_invariants_pass(self):
        mod = load_bootstrap_module()
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            trusted, candidate = base / "trusted", base / "candidate"
            copy_invariant_inputs(trusted)
            copy_invariant_inputs(candidate)
            self.assertEqual(mod.bootstrap_invariant_errors(trusted, candidate, []), [])

    def test_repo_policy_weakening_rejected(self):
        mod = load_bootstrap_module()
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            trusted, candidate = base / "trusted", base / "candidate"
            copy_invariant_inputs(trusted)
            copy_invariant_inputs(candidate)
            path = candidate / "config/repo_policy.json"
            p = json.loads(path.read_text(encoding="utf-8"))
            p["required_protected"] = False
            path.write_text(json.dumps(p), encoding="utf-8")
            errors = mod.bootstrap_invariant_errors(trusted, candidate, ["config/repo_policy.json"])
            self.assertIn("repo policy invariant weakened: required_protected", errors)

    def test_expected_source_weakening_rejected(self):
        mod = load_bootstrap_module()
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            trusted, candidate = base / "trusted", base / "candidate"
            copy_invariant_inputs(trusted)
            copy_invariant_inputs(candidate)
            path = candidate / "config/admission_authority.json"
            p = json.loads(path.read_text(encoding="utf-8"))
            p["required_status_creator"] = "other-app[bot]"
            path.write_text(json.dumps(p), encoding="utf-8")
            errors = mod.bootstrap_invariant_errors(trusted, candidate, ["config/admission_authority.json"])
            self.assertIn("admission authority invariant weakened: required_status_creator", errors)

    def test_countable_control_shrinkage_rejected(self):
        mod = load_bootstrap_module()
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            trusted, candidate = base / "trusted", base / "candidate"
            copy_invariant_inputs(trusted)
            copy_invariant_inputs(candidate)
            path = candidate / "config/countable_control_set_v25.json"
            p = json.loads(path.read_text(encoding="utf-8"))
            p["required_control_paths"].remove(".github/workflows/supernova-authority-bootstrap.yml")
            path.write_text(json.dumps(p), encoding="utf-8")
            errors = mod.bootstrap_invariant_errors(trusted, candidate, ["config/countable_control_set_v25.json"])
            self.assertTrue(any("countable control set shrank" in e for e in errors))
            self.assertTrue(any("countable control missing installed authority/substrate path" in e for e in errors))

    def test_protocol_freeze_weakening_rejected(self):
        mod = load_bootstrap_module()
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            trusted, candidate = base / "trusted", base / "candidate"
            copy_invariant_inputs(trusted)
            copy_invariant_inputs(candidate)
            path = candidate / "config/protocol_freeze.json"
            p = json.loads(path.read_text(encoding="utf-8"))
            p["no_successor_before"]["consecutive_countable_clean_v25_cohorts"] = 1
            path.write_text(json.dumps(p), encoding="utf-8")
            errors = mod.bootstrap_invariant_errors(trusted, candidate, ["config/protocol_freeze.json"])
            self.assertIn("protocol freeze weakened: clean cohort count", errors)


if __name__ == "__main__":
    unittest.main()
