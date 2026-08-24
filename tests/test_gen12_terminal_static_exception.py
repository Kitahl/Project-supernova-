import unittest

from scripts import reconcile_v25_admission as MOD


def exact_state():
    return {
        'protocol_version':'2.5','task_network_plan_id':MOD.PLAN,'transport_mode':'BRANCH_GITOPS',
        'generation_seq':12,'active_cohort_id':MOD.GEN12_COHORT,'generation_head_sha':MOD.GEN12_G,
        'generation_branch':'ps/gen/'+MOD.GEN12_COHORT,
        'active_control_manifest_path':'control/'+MOD.GEN12_COHORT+'.json',
        'active_control_manifest_git_identity':MOD.GEN12_CONTROL_BLOB,
        'active_assignment_path':'assignments/'+MOD.GEN12_COHORT+'.json',
        'active_assignment_git_identity':MOD.GEN12_ASSIGNMENT_BLOB,
        'calibration_countable_current':True,'calibration_streak':0,'fresh_allowed_globally':False,
    }


class Gen12TerminalStaticExceptionTests(unittest.TestCase):
    def test_exact_immutable_gen12_and_only_expected_prospective_errors_pass(self):
        self.assertTrue(MOD.gen12_terminal_static_exception(
            {'sha':MOD.GEN12_STATE_BLOB}, exact_state(), list(MOD.GEN12_TERMINAL_STATIC_ERRORS)
        ))

    def test_every_bound_identity_or_gate_mismatch_fails(self):
        mutations={
            'state blob':({'sha':'0'*40},exact_state()),
            'generation head':({'sha':MOD.GEN12_STATE_BLOB},{**exact_state(),'generation_head_sha':'0'*40}),
            'control blob':({'sha':MOD.GEN12_STATE_BLOB},{**exact_state(),'active_control_manifest_git_identity':'0'*40}),
            'assignment blob':({'sha':MOD.GEN12_STATE_BLOB},{**exact_state(),'active_assignment_git_identity':'0'*40}),
            'countable':({'sha':MOD.GEN12_STATE_BLOB},{**exact_state(),'calibration_countable_current':False}),
            'streak':({'sha':MOD.GEN12_STATE_BLOB},{**exact_state(),'calibration_streak':1}),
            'fresh':({'sha':MOD.GEN12_STATE_BLOB},{**exact_state(),'fresh_allowed_globally':True}),
        }
        for label,(meta,state) in mutations.items():
            with self.subTest(label=label):
                self.assertFalse(MOD.gen12_terminal_static_exception(meta,state,list(MOD.GEN12_TERMINAL_STATIC_ERRORS)))

    def test_missing_reordered_or_additional_static_error_fails(self):
        cases=[
            list(MOD.GEN12_TERMINAL_STATIC_ERRORS[:1]),
            list(reversed(MOD.GEN12_TERMINAL_STATIC_ERRORS)),
            list(MOD.GEN12_TERMINAL_STATIC_ERRORS)+['unexpected'],
        ]
        for errors in cases:
            with self.subTest(errors=errors):
                self.assertFalse(MOD.gen12_terminal_static_exception({'sha':MOD.GEN12_STATE_BLOB},exact_state(),errors))


if __name__=='__main__':
    unittest.main()
