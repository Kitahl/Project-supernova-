import datetime as dt, unittest
from scripts.check_lane_liveness import evaluate

class LivenessMonitorTests(unittest.TestCase):
    def contract(self):
        return {
            'cohort_id':'c','generation_root_sha':'a'*40,
            'control_manifest_git_identity':'b'*40,'assignment_git_identity':'c'*40,
            'lanes':[{'lane_id':'MF01','branch':'b','path':'reports/c/MF01.json','expected_window_start_utc':'2026-08-19T08:00:00Z','deadline_utc':'2026-08-19T08:30:00Z','eligible_before_deadline':True}]
        }

    def test_missing_after_deadline_blocks_without_inventing_pause_cause(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,31,tzinfo=dt.timezone.utc),lambda b,p:False)
        self.assertFalse(r['transition_liveness_pass'])
        self.assertEqual(r['blocking_lanes'],['MF01'])
        self.assertEqual(r['observations'][0]['receipt_status'],'NO_RECEIPT')
        self.assertEqual(r['observations'][0]['task_state'],'TASK_STATE_UNKNOWN')

    def test_missing_before_deadline_is_observed_but_not_yet_blocking(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,20,tzinfo=dt.timezone.utc),lambda b,p:False)
        self.assertTrue(r['transition_liveness_pass'])
        self.assertEqual(r['observations'][0]['receipt_status'],'NO_RECEIPT')
        self.assertEqual(r['blocking_lanes'],[])

    def test_present_receipt_passes(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,31,tzinfo=dt.timezone.utc),lambda b,p:True)
        self.assertTrue(r['transition_liveness_pass'])
        self.assertEqual(r['observations'][0]['receipt_status'],'RUN_OBSERVED')

    def test_reversed_window_fails(self):
        c=self.contract(); c['lanes'][0]['deadline_utc']='2026-08-19T07:59:00Z'
        with self.assertRaises(ValueError):
            evaluate(c,dt.datetime(2026,8,19,8,31,tzinfo=dt.timezone.utc),lambda b,p:False)

if __name__=='__main__': unittest.main()
