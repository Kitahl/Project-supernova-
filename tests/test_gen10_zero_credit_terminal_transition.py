import importlib.util
import inspect
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reconcile_open_prs_epoch7", ROOT / "scripts/reconcile_open_prs.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


class Gen10ZeroCreditTerminalTransitionTests(unittest.TestCase):
    def test_exact_historical_evidence_constants_are_frozen(self):
        self.assertEqual(MOD.GEN10_TERMINAL_COHORT, "CAL-BR-010-v25-fe539297-r2")
        self.assertEqual(MOD.GEN10_TERMINAL_G, "25c7c4e4732a5635ae8f47a9194d59a3f5a58e8f")
        self.assertEqual(MOD.GEN10_TERMINAL_STATE_BLOB, "72d5aa0c0f9144bb0cb2faa19ad8300bd38c8ad6")
        self.assertEqual(MOD.GEN10_MM06_HEAD, "500837400c093b0dd53071f649efc022c9314201")
        self.assertEqual(MOD.GEN10_MF06_HEAD, "9631e36f289ca8d7bc750eaa01790171419636ef")
        self.assertEqual(MOD.GEN10_HISTORICAL_INTEGRATION_ISSUE, "O-T0-GEN10-HISTORICAL-INTEGRATION-SCHEMA")

    def test_transition_branch_prefix_is_exact_and_ps_transition_is_not_admitted(self):
        self.assertIn("transition/", MOD.ALLOWED_HEAD_PREFIXES)
        self.assertNotIn("ps/transition/", MOD.ALLOWED_HEAD_PREFIXES)
        base = {"ref": "main", "sha": "a" * 40}
        def pr(ref):
            return {
                "head": {"ref": ref, "sha": "b" * 40, "repo": {"full_name": MOD.REPO}},
                "base": base,
                "user": {"login": MOD.OWNER},
            }
        self.assertEqual(MOD.pr_metadata_errors(pr("transition/CAL-TEST")), [])
        self.assertIn("PR head prefix is not admitted", MOD.pr_metadata_errors(pr("ps/transition/CAL-TEST")))

    def test_gen10_predicate_requires_exact_six_path_transition_and_real_partition(self):
        text = inspect.getsource(MOD.exact_gen10_zero_credit_terminal_parent)
        for token in (
            "expected_changed",
            "GEN10_CONSOLIDATION_PATH",
            "GEN10_SUPERSESSION_PATH",
            "VERIFIED_WITH_QUARANTINES",
            'WORKERS-{"MM02"}',
            'source_bound_status(GEN10_MM06_HEAD,"supernova/report-admission","success")',
            'source_bound_status(GEN10_MF06_HEAD,"supernova/branch-integrate","failure")',
            "GEN10_HISTORICAL_INTEGRATION_ISSUE",
            "compare_paths_api(base,G)",
            "branch_head_api",
        ):
            self.assertIn(token, text)

    def test_successor_worker_contract_requires_both_hmac_and_stored_bytes(self):
        text = inspect.getsource(MOD.exact_gen10_zero_credit_terminal_parent)
        self.assertIn("HMAC input contract is separate from committed-file byte contract", text)
        self.assertIn("outgoing committed bytes MUST equal json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+'\\n'", text)
        self.assertIn("abort without write on mismatch", text)

    def test_special_predicate_is_registered_before_generic_clean_fallback(self):
        source = inspect.getsource(MOD.report_admission)
        self.assertIn("exact_gen10_zero_credit_terminal_parent", source)
        self.assertLess(source.index("exact_gen10_zero_credit_terminal_parent"), source.index("verification verdict not complete"))

    def test_generic_clean_transition_rule_remains_strict(self):
        source = inspect.getsource(MOD.report_admission)
        for token in (
            "verification verdict not complete",
            "verification has quarantine/missing",
            "verification liveness incomplete",
            "integration external CI invalid",
        ):
            self.assertIn(token, source)

    def test_epoch7_authority_and_v22_control_freeze_the_repair(self):
        authority = json.loads((ROOT / "config/admission_authority.json").read_text(encoding="utf-8"))
        control = json.loads((ROOT / "config/countable_control_set_v25.json").read_text(encoding="utf-8"))
        self.assertEqual(authority["root_tcb_epoch"], 7)
        self.assertEqual(authority["transition_pr_head_prefix"], "transition/")
        self.assertIn("EXACT_GEN10_ZERO_CREDIT_PREDICATE_ONLY", authority["terminal_nonclean_state_transition_policy"])
        self.assertEqual(control["schema_version"], "PS-COUNTABLE-CONTROL-SET-2.5-22")
        paths = set(control["required_control_paths"])
        for path in (
            "config/root_epoch7_repair_seed_v25.json",
            "scripts/reconcile_root_epoch7_repair_seed.py",
            ".github/workflows/supernova-root-epoch7-repair-seed.yml",
            "tests/test_root_epoch7_repair_seed.py",
            "config/root_epoch7_repair_epoch_v25.json",
            "scripts/reconcile_open_prs.py",
            "tests/test_gen10_zero_credit_terminal_transition.py",
        ):
            self.assertIn(path, paths)


if __name__ == "__main__":
    unittest.main()
