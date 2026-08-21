import importlib.util
import pathlib
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reconcile_open_prs", ROOT / "scripts/reconcile_open_prs.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


class OpenPrAdmissionTrustTests(unittest.TestCase):
    def pr(self, repo="Kitahl/Project-supernova-", base="main", head="hardening/probe", user="Kitahl"):
        return {
            "number": 1,
            "user": {"login": user},
            "base": {"ref": base},
            "head": {"ref": head, "sha": "a" * 40, "repo": {"full_name": repo}},
        }

    def test_same_repo_main_owner_and_allowed_prefix_required(self):
        self.assertEqual(MOD.pr_metadata_errors(self.pr()), [])
        self.assertIn("PR head repository is not canonical repository", MOD.pr_metadata_errors(self.pr(repo="someone/fork")))
        self.assertIn("PR base is not main", MOD.pr_metadata_errors(self.pr(base="dev")))
        self.assertIn("PR author is not repository owner", MOD.pr_metadata_errors(self.pr(user="someone")))
        self.assertIn("PR head prefix is not admitted", MOD.pr_metadata_errors(self.pr(head="feature/untrusted")))

    def test_admission_authority_drift_is_detected(self):
        changed = [
            "scripts/validate_bus.py",
            "tests/test_ci_guard.py",
            "schemas/state.schema.json",
            "config/repo_policy.json",
            ".github/workflows/supernova-v25-admission.yml",
            "requirements-validation.lock",
            "branch/CONFIG.json",
            "research/open_lanes.json",
            "benchmark/pool_disposition.json",
        ]
        self.assertEqual(MOD.authority_path_changes(changed), sorted(changed))
        self.assertEqual(
            MOD.authority_path_changes(["state/CURRENT.json", "history/C/CONSOLIDATION.json", "benchmark/registry.json"]),
            [],
        )

    def test_static_validation_executes_trusted_script_not_candidate_script(self):
        trusted = pathlib.Path("/trusted")
        candidate = pathlib.Path("/candidate")
        with mock.patch.object(MOD, "run", return_value=(0, "PASS")) as run:
            self.assertEqual(MOD.trusted_static_control(trusted, candidate), [])
            cmd, cwd = run.call_args.args[:2]
            env = run.call_args.kwargs["env"]
            self.assertEqual(cmd[1], str(trusted / "scripts/validate_bus.py"))
            self.assertEqual(cwd, trusted)
            self.assertEqual(env["SUPERNOVA_VALIDATE_ROOT"], str(candidate))

    def test_transition_validation_executes_trusted_guards_only(self):
        trusted = pathlib.Path("/trusted")
        candidate = pathlib.Path("/candidate")
        with mock.patch.object(MOD, "run", return_value=(0, "PASS")) as run:
            errors = MOD.transition_admission(trusted, candidate, "a" * 40, "b" * 40, ["state/CURRENT.json"])
            self.assertEqual(errors, [])
            invoked = [call.args[0][1] for call in run.call_args_list]
            self.assertEqual(
                invoked,
                [str(trusted / "scripts/parent_lineage_guard.py"), str(trusted / "scripts/transition_guard.py")],
            )
            for call in run.call_args_list:
                self.assertEqual(call.kwargs["env"]["SUPERNOVA_VALIDATE_ROOT"], str(candidate))

    def test_non_regular_candidate_git_objects_fail_closed(self):
        with mock.patch.object(MOD, "run", return_value=(0, "120000 blob deadbeef\tstate/CURRENT.json\n")):
            errors = MOD.changed_file_mode_errors(pathlib.Path("/repo"), "a" * 40, ["state/CURRENT.json"])
        self.assertTrue(errors)
        self.assertIn("non-regular candidate path", errors[0])

    def bootstrap_states(self):
        old = {
            "generation_seq": 6,
            "active_cohort_id": "CAL-BR-006-v251-433ad83a",
            "calibration_countable_current": False,
            "calibration_streak": 0,
        }
        new = {
            "generation_seq": 7,
            "active_cohort_id": "CAL-BR-007-new",
            "calibration_countable_current": True,
            "calibration_streak": 0,
            "fresh_allowed_globally": False,
            "repo_policy_status": "VERIFIED_PROTECTED_SOURCE_BOUND",
            "superseded_cohorts": [old["active_cohort_id"]],
        }
        return old, new

    def test_first_countable_bootstrap_is_narrowly_admissible(self):
        old, new = self.bootstrap_states()
        self.assertEqual(MOD.first_countable_bootstrap_report_errors(old, new), [])

    def test_first_countable_bootstrap_fail_closed_invariants(self):
        old, new = self.bootstrap_states()
        cases = []
        bad_old = dict(old, calibration_streak=1)
        cases.append((bad_old, new))
        cases.append((old, dict(new, calibration_streak=1)))
        cases.append((old, dict(new, fresh_allowed_globally=True)))
        cases.append((old, dict(new, repo_policy_status="UNVERIFIED_BLOCKING")))
        cases.append((old, dict(new, generation_seq=8)))
        cases.append((old, dict(new, superseded_cohorts=[])))
        for before, after in cases:
            with self.subTest(before=before, after=after):
                self.assertTrue(MOD.first_countable_bootstrap_report_errors(before, after))

    def test_countable_old_cohort_cannot_use_bootstrap_exception(self):
        old, new = self.bootstrap_states()
        old["calibration_countable_current"] = True
        self.assertIsNone(MOD.first_countable_bootstrap_report_errors(old, new))


if __name__ == "__main__":
    unittest.main()
