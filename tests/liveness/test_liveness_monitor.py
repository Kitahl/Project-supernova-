import datetime as dt, unittest
from scripts.check_lane_liveness import evaluate

UTC=dt.timezone.utc

class LivenessMonitorTests(unittest.TestCase):
    def contract(self):
        return {'cohort_id':'c','generation_root_sha':'a'*40,'lanes':[{'lane_id':'MF01','branch':'b','path':'reports/c/MF01.json','expected_window_start_utc':'2026-08-19T08:00:00Z','deadline_utc':'2026-08-19T08:30:00Z','eligible_before_deadline':True}]}

    def test_missing_after_deadline_blocks_without_inventing_pause_cause(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,31,tzinfo=UTC),lambda b,p:{'exists':False})
        self.assertFalse(r['transition_liveness_pass']);self.assertEqual(r['blocking_lanes'],['MF01']);self.assertEqual(r['observations'][0]['receipt_status'],'NO_RECEIPT');self.assertEqual(r['observations'][0]['task_state'],'TASK_STATE_UNKNOWN')

    def test_missing_before_deadline_is_observed_but_not_yet_blocking(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,20,tzinfo=UTC),lambda b,p:{'exists':False})
        self.assertTrue(r['transition_liveness_pass']);self.assertEqual(r['observations'][0]['receipt_status'],'NO_RECEIPT');self.assertEqual(r['blocking_lanes'],[])

    def test_on_time_receipt_observed_after_delayed_poll_passes(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,9,0,tzinfo=UTC),lambda b,p:{'exists':True,'created_at_utc':'2026-08-19T08:29:59Z','head_sha':'b'*40,'blob_sha':'c'*40})
        self.assertTrue(r['transition_liveness_pass']);self.assertEqual(r['observations'][0]['receipt_status'],'RUN_OBSERVED');self.assertEqual(r['observations'][0]['lateness_seconds'],0)

    def test_genuinely_late_receipt_blocks_as_run_late(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,9,0,tzinfo=UTC),lambda b,p:{'exists':True,'created_at_utc':'2026-08-19T08:30:05Z','head_sha':'b'*40,'blob_sha':'c'*40})
        self.assertFalse(r['transition_liveness_pass']);self.assertEqual(r['blocking_lanes'],['MF01']);self.assertEqual(r['observations'][0]['receipt_status'],'RUN_LATE');self.assertEqual(r['observations'][0]['lateness_seconds'],5)

    def test_post_deadline_receipt_without_creation_time_fails_closed(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,31,tzinfo=UTC),lambda b,p:{'exists':True,'head_sha':'b'*40,'blob_sha':'c'*40})
        self.assertFalse(r['transition_liveness_pass']);self.assertEqual(r['observations'][0]['receipt_status'],'RUN_TIMING_UNKNOWN');self.assertEqual(r['blocking_lanes'],['MF01'])

    def test_predeadline_receipt_without_creation_time_can_be_observed(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,20,tzinfo=UTC),lambda b,p:{'exists':True})
        self.assertTrue(r['transition_liveness_pass']);self.assertEqual(r['observations'][0]['receipt_status'],'RUN_OBSERVED')

if __name__=='__main__': unittest.main()
