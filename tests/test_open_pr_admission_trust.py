import importlib.util
import json
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

    @staticmethod
    def gen6_state():
        return {
            "generation_seq": 6,
            "active_cohort_id": MOD.GEN6_BOOTSTRAP_COHORT,
            "calibration_countable_current": False,
            "calibration_streak": 0,
            "fresh_allowed_globally": False,
            "repo_policy_status": "UNVERIFIED_BLOCKING",
            "generation_head_sha": "c86c091c3be840559a46670218705be1277acd8f",
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

    def test_exact_noncountable_gen6_boundary_skips_missing_historical_fanin(self):
        old = self.gen6_state()

        def fake_run(cmd, cwd, env=None):
            if cmd[:2] == ["git", "show"]:
                return 0, json.dumps(old)
            if cmd[:2] == ["git", "rev-parse"]:
                return 0, MOD.GEN6_BOOTSTRAP_STATE_BLOB
            raise AssertionError(cmd)

        with mock.patch.object(MOD, "run", side_effect=fake_run):
            self.assertEqual(
                MOD.report_admission(pathlib.Path("/candidate"), "a" * 40, ["state/CURRENT.json"]),
                [],
            )

    def test_gen6_boundary_near_miss_does_not_skip_historical_fanin(self):
        cases = []
        countable = self.gen6_state(); countable["calibration_countable_current"] = True; cases.append(countable)
        fresh = self.gen6_state(); fresh["fresh_allowed_globally"] = True; cases.append(fresh)
        wrong_cohort = self.gen6_state(); wrong_cohort["active_cohort_id"] = "OTHER"; cases.append(wrong_cohort)
        wrong_generation = self.gen6_state(); wrong_generation["generation_seq"] = 5; cases.append(wrong_generation)
        wrong_policy = self.gen6_state(); wrong_policy["repo_policy_status"] = "VERIFIED_PROTECTED_SOURCE_BOUND"; cases.append(wrong_policy)

        for old in cases:
            def fake_run(cmd, cwd, env=None, old=old):
                if cmd[:2] == ["git", "show"]:
                    return 0, json.dumps(old)
                if cmd[:2] == ["git", "rev-parse"]:
                    return 0, MOD.GEN6_BOOTSTRAP_STATE_BLOB
                raise AssertionError(cmd)
            with self.subTest(old=old), mock.patch.object(MOD, "run", side_effect=fake_run):
                errors = MOD.report_admission(pathlib.Path("/candidate"), "a" * 40, ["state/CURRENT.json"])
                self.assertTrue(errors)
                self.assertIn("report admission", errors[0])

    def test_wrong_gen6_state_blob_does_not_get_bootstrap_exception(self):
        old = self.gen6_state()

        def fake_run(cmd, cwd, env=None):
            if cmd[:2] == ["git", "show"]:
                return 0, json.dumps(old)
            if cmd[:2] == ["git", "rev-parse"]:
                return 0, "0" * 40
            raise AssertionError(cmd)

        with mock.patch.object(MOD, "run", side_effect=fake_run):
            errors = MOD.report_admission(pathlib.Path("/candidate"), "a" * 40, ["state/CURRENT.json"])
        self.assertTrue(errors)
        self.assertIn("report admission", errors[0])


if __name__ == "__main__":
    unittest.main()
