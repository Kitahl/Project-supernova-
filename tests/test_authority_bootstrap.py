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
    def _assert_json_mutation_rejected(self, rel, keys, value, expected, changed=None):
        mod = load_bootstrap_module()
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            trusted, candidate = base / "trusted", base / "candidate"
            copy_invariant_inputs(trusted)
            copy_invariant_inputs(candidate)
            path = candidate / rel
            payload = json.loads(path.read_text(encoding="utf-8"))
            target = payload
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
            path.write_text(json.dumps(payload), encoding="utf-8")
            errors = mod.bootstrap_invariant_errors(
                trusted,
                candidate,
                [rel] if changed is None else changed,
            )
            self.assertIn(expected, errors)

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
        self.assertIn("trusted_bootstrap_success(sha,base,n)", text)
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

    def test_every_repo_policy_security_field_is_fail_closed(self):
        cases = [
            ("required_pull_request_for_consolidation", False),
            ("forbid_force_push", False),
            ("forbid_branch_deletion", False),
            ("required_main_status_contexts", ["supernova/static-control"]),
            ("required_status_source_creator_logins", ["other-app[bot]"]),
            ("operational_source_binding_proof_required", False),
            ("candidate_code_execution_with_status_write_token", "ALLOWED"),
            ("fresh_gate", "OPEN"),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                self._assert_json_mutation_rejected(
                    "config/repo_policy.json",
                    [key],
                    value,
                    f"repo policy invariant weakened: {key}",
                )

    def test_every_admission_authority_security_field_is_fail_closed(self):
        cases = [
            ("protocol_version", "2.6"),
            ("task_network_plan_id", "0" * 64),
            ("candidate_code_execution_with_status_write_token", "ALLOWED"),
            ("ref_selectable_dispatch_with_status_write_token", "ALLOWED"),
            ("candidate_bytes_treatment", "EXECUTABLE"),
            ("trusted_reconciler", "scripts/candidate_reconciler.py"),
            ("trusted_authority_bootstrap_reconciler", "scripts/candidate_bootstrap.py"),
            ("authority_bootstrap_context", "supernova/spoofed-bootstrap"),
            ("same_repository_required", False),
            ("owner_authored_required_for_privileged_reconciliation", False),
            ("exact_current_main_ancestor_required", False),
            ("required_contexts", ["supernova/static-control"]),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                self._assert_json_mutation_rejected(
                    "config/admission_authority.json",
                    [key],
                    value,
                    f"admission authority invariant weakened: {key}",
                )

    def test_bootstrap_policy_content_is_checked_even_if_changed_list_is_incomplete(self):
        cases = [
            ("required_status_creator", "other-app[bot]"),
            ("trusted_executable_source", "CANDIDATE_HEAD"),
            ("candidate_bytes_in_privileged_phase", "EXECUTABLE"),
            ("candidate_diagnostics", "OPTIONAL"),
            ("same_repository_required", False),
            ("owner_authored_required", False),
            ("base_branch_required", "candidate"),
            ("exact_current_main_ancestor_required", False),
            ("calibration_streak_required", 1),
            ("fresh_allowed_globally_required", True),
            ("worker_auth_change", "ALLOWED"),
            ("state_or_scientific_change", "ALLOWED"),
            ("merge_authority", "BOOTSTRAP_VERIFIER"),
            ("bootstrap_verifier_may_bypass_ruleset", True),
            ("bootstrap_verifier_may_merge", True),
            ("failure_semantics", "FAIL_OPEN"),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                self._assert_json_mutation_rejected(
                    "config/authority_bootstrap_v25.json",
                    [key],
                    value,
                    f"bootstrap policy invariant weakened: {key}",
                    changed=[],
                )

    def test_protocol_source_and_epoch_gates_are_fail_closed(self):
        cases = [
            (["frozen_protocol_version"], "2.6", "protocol freeze weakened: frozen_protocol_version"),
            (["frozen_specification_revision"], 5, "protocol freeze weakened: frozen_specification_revision"),
            (["status"], "OPEN", "protocol freeze weakened: status"),
            (["no_successor_before", "repository_policy_independently_verified"], False, "protocol freeze weakened: repository policy gate"),
            (["no_successor_before", "required_source_bound_contexts"], ["supernova/static-control"], "protocol freeze weakened: source-bound contexts"),
            (["mid_streak_change_rule"], "PRESERVE_STREAK", "protocol freeze weakened: mid-streak reset rule"),
        ]
        for keys, value, expected in cases:
            with self.subTest(keys=keys):
                self._assert_json_mutation_rejected(
                    "config/protocol_freeze.json",
                    keys,
                    value,
                    expected,
                )

    def test_countable_control_identity_and_privilege_gates_are_fail_closed(self):
        cases = [
            ("protocol_version", "2.6", "countable control identity weakened"),
            ("task_network_plan_id", "0" * 64, "countable control identity weakened"),
            ("authoritative_change_after_cohort1", "PRESERVE_STREAK", "countable control mid-streak reset invariant weakened"),
            ("candidate_code_with_status_write_token", "ALLOWED", "countable control candidate privilege invariant weakened"),
            ("fresh_science", "ALLOWED", "countable control fresh-science invariant weakened"),
        ]
        for key, value, expected in cases:
            with self.subTest(key=key):
                self._assert_json_mutation_rejected(
                    "config/countable_control_set_v25.json",
                    [key],
                    value,
                    expected,
                )

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
