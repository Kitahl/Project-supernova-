import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "scripts/reconcile_open_prs.py").read_text(encoding="utf-8")
GEN10 = "CAL-BR-010-v25-fe539297-r2"
MM06 = "500837400c093b0dd53071f649efc022c9314201"
MF06 = "9631e36f289ca8d7bc750eaa01790171419636ef"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Gen10ZeroCreditTerminalTransitionTests(unittest.TestCase):
    def test_exact_gen10_terminal_predicate_is_installed_before_generic_clean_fallback(self):
        self.assertIn("def exact_gen10_zero_credit_terminal_parent", SOURCE)
        self.assertIn(GEN10, SOURCE)
        self.assertIn(MM06, SOURCE)
        self.assertIn(MF06, SOURCE)
        dispatch = SOURCE.index("exact_gen10_zero_credit_terminal_parent")
        generic = SOURCE.index('verification verdict not complete')
        self.assertLess(dispatch, generic)
        self.assertIn("VERIFIED_WITH_QUARANTINES", SOURCE)
        self.assertIn("O-T0-GEN10-HISTORICAL-INTEGRATION-SCHEMA", SOURCE)

    def test_generic_clean_cohort_rule_remains_strict(self):
        self.assertIn('if ver.get("verdict")!="VERIFIED_COMPLETE":e.append("verification verdict not complete")', SOURCE)
        self.assertIn('if ver.get("quarantined_report_refs") or ver.get("missing_workers"):e.append("verification has quarantine/missing")', SOURCE)
        self.assertIn('if ver.get("liveness_complete") is not True:e.append("verification liveness incomplete")', SOURCE)

    def test_terminal_predicate_requires_exact_real_evidence_and_historical_failure_preservation(self):
        for token in (
            "GEN10_VERIFICATION_BLOB",
            "GEN10_INTEGRATION_BLOB",
            "_one_path_child",
            "verification_semantic_errors",
            "integration_semantic_errors",
            "supernova/branch-verify",
            "supernova/report-admission",
            "supernova/branch-integrate",
            "MM02",
            "safe_reports_integrated",
            "scientific_results",
            "NOT_MEASURED",
        ):
            self.assertIn(token, SOURCE)

    def test_successor_requires_complete_v22_freeze_and_exact_branch_topology(self):
        for token in (
            "_remote_compare_paths(base,G)",
            "_remote_branch_head(new.get('generation_branch'))",
            "role_branches",
            "control.get('required_control_paths')",
            "json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+'\\\\n'",
            "abort without write on mismatch",
        ):
            self.assertIn(token, SOURCE)
        contract = load("config/countable_control_set_v25.json")
        self.assertEqual(contract["schema_version"], "PS-COUNTABLE-CONTROL-SET-2.5-22")
        paths = set(contract["required_control_paths"])
        for path in (
            "config/root_epoch7_repair_seed_v25.json",
            "config/root_epoch7_repair_epoch_v25.json",
            "scripts/reconcile_root_epoch7_repair_seed.py",
            ".github/workflows/supernova-root-epoch7-repair-seed.yml",
            "tests/test_root_epoch7_repair_seed.py",
            "tests/test_gen10_zero_credit_terminal_transition.py",
        ):
            self.assertIn(path, paths)

    def test_epoch7_is_zero_credit_and_binds_epoch6_and_seed(self):
        root = load("config/root_tcb_epoch_v25.json")
        marker = load("config/root_epoch7_repair_epoch_v25.json")
        authority = load("config/admission_authority.json")
        self.assertEqual(root["schema_version"], "PS-ROOT-TCB-EPOCH-2.5-7")
        self.assertEqual(root["epoch"], 7)
        self.assertEqual(root["previous_epoch_blob"], "5a087dead0572390565bfe8bfb8f2ce69a80fc7c")
        self.assertEqual(root["root_epoch7_repair_seed_install_commit_sha"], "7af2eba8687b17fe8a3be4569dba02024b3e1d2b")
        self.assertEqual(marker["stable_issue_id"], "O-T0-GEN10-ZERO-CREDIT-PR-ADMISSION-GAP")
        self.assertEqual(marker["calibration_credit_effect"], 0)
        self.assertEqual(marker["fresh_science_effect"], "NONE")
        self.assertEqual(authority["root_tcb_epoch"], 7)


if __name__ == "__main__":
    unittest.main()
