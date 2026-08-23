import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = (ROOT / 'scripts' / 'reconcile_open_prs.py').read_text(encoding='utf-8')


class Gen11ZeroCreditTerminalTransitionTests(unittest.TestCase):
    def test_exact_gen11_escape_is_closed_and_zero_credit(self):
        for token in (
            'GEN11_COHORT="CAL-BR-011-v25-27955ce6"',
            'GEN11_G="3bb1425d18dbff2f83d69b0738c7151bf4a47355"',
            'GEN11_STATE_BLOB="ad93b7d0a0a4fe329fea2f4855f8eb65a86ce7f9"',
            'GEN11_VERIFIER_HEAD="a58939b12e66ab4604b8f2e5f2033bd70d5c0bd3"',
            'GEN11_SUPERSESSION_DISPOSITION="INVALIDATED_ZERO_CREDIT_ROOT_EPOCH9_FULL_INTEGRITY_REPAIR"',
            'GEN12_COHORT_PREFIX="CAL-BR-012-v25-"',
            'def exact_gen11_zero_credit_terminal_parent',
        ):
            self.assertIn(token, SRC)

    def test_terminal_evidence_is_mm06_invalid_not_fabricated_clean(self):
        for token in (
            "v.get('verdict')!='INVALID'",
            "v.get('calibration_pass') is not False",
            "v.get('liveness_complete') is not False",
            "len(v.get('safe_report_refs') or [])!=12",
            "v.get('quarantined_report_refs')!=[]",
            "v.get('missing_workers')!=[]",
        ):
            self.assertIn(token, SRC)

    def test_repair_requires_all_confirmed_gen11_issue_ids(self):
        for issue in (
            'GEN11-EXACT-G-LIVENESS-NONCLEAN',
            'O-T0-BRANCH-CONFIG-STRUCTURAL-WRITER-DRIFT',
            'PS-MF04-NONFINITEJSON-001',
            'MM03-RPT-TYPED-MISSING-006',
            'MM04-T0-MM04-ROLE-NONVACUITY-SCHEMA-001',
            'MM04-T0-PRIVILEGED-VALIDATOR-ENV-ASSERTION-001',
        ):
            self.assertIn(issue, SRC)

    def test_successor_requires_exact_five_path_transition_and_forty_five_minute_liveness(self):
        self.assertIn("if set(changed)!={'state/CURRENT.json',GEN11_SUPERSESSION_PATH,cp,ap,lp}:return False", SRC)
        self.assertIn('MINIMUM_WORKER_LIVENESS_WINDOW_MINUTES=45', SRC)
        self.assertIn('if minutes<MINIMUM_WORKER_LIVENESS_WINDOW_MINUTES:return False', SRC)
        self.assertIn('"generation_seq":12', SRC)
        self.assertIn('"calibration_streak":0', SRC)
        self.assertIn('"fresh_allowed_globally":False', SRC)

    def test_successor_generation_and_all_role_branches_must_be_frozen_before_state_admission(self):
        self.assertIn("if _remote_compare_paths(base,G)!={cp,ap,lp}", SRC)
        self.assertIn("role_branches=list(branches.values())+[new.get('verifier_branch'),new.get('integrator_branch'),new.get('consolidation_branch')]", SRC)
        self.assertIn('if any(_remote_branch_head(x)!=G for x in role_branches):return False', SRC)

    def test_report_admission_routes_gen11_only_through_closed_escape(self):
        self.assertIn('exact_gen11_zero_credit_terminal_parent', SRC)
        self.assertIn('for predicate in (exact_invalidated_gen7_repair_parent,exact_noncountable_substrate_staging_parent,exact_gen9_zero_credit_reset_parent,exact_gen10_zero_credit_terminal_parent,exact_gen11_zero_credit_terminal_parent)', SRC)


if __name__ == '__main__':
    unittest.main()
