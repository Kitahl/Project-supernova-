import datetime as dt, unittest
from scripts.check_lane_liveness import evaluate

UTC=dt.timezone.utc

class LivenessMonitorTests(unittest.TestCase):
    def contract(self):
        return {'cohort_id':'c','generation_root_sha':'a'*40,'lanes':[{'lane_id':'MF01','branch':'b','path':'reports/c/MF01.json','expected_window_start_utc':'2026-08-19T08:00:00Z','deadline_utc':'2026-08-19T08:30:00Z','eligible_before_deadline':True}]}
    def test_missing_after_deadline_blocks_without_inventing_pause_cause(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,31,tzinfo=UTC),lambda b,p:None)
        self.assertFalse(r['transition_liveness_pass']);self.assertEqual(r['blocking_lanes'],['MF01']);self.assertEqual(r['observations'][0]['receipt_status'],'NO_RECEIPT');self.assertEqual(r['observations'][0]['task_state'],'TASK_STATE_UNKNOWN')
    def test_missing_before_deadline_is_observed_but_not_yet_blocking(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,20,tzinfo=UTC),lambda b,p:None)
        self.assertTrue(r['transition_liveness_pass']);self.assertEqual(r['observations'][0]['receipt_status'],'NO_RECEIPT');self.assertEqual(r['blocking_lanes'],[])
    def test_on_time_receipt_observed_after_deadline_still_passes(self):
        created=dt.datetime(2026,8,19,8,29,tzinfo=UTC)
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,45,tzinfo=UTC),lambda b,p:created)
        self.assertTrue(r['transition_liveness_pass']);self.assertEqual(r['blocking_lanes'],[]);self.assertEqual(r['observations'][0]['receipt_status'],'RUN_OBSERVED');self.assertEqual(r['observations'][0]['lateness_seconds'],0)
    def test_genuinely_late_receipt_blocks(self):
        created=dt.datetime(2026,8,19,8,31,tzinfo=UTC)
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,45,tzinfo=UTC),lambda b,p:created)
        self.assertFalse(r['transition_liveness_pass']);self.assertEqual(r['blocking_lanes'],['MF01']);self.assertEqual(r['observations'][0]['receipt_status'],'RUN_LATE');self.assertEqual(r['observations'][0]['lateness_seconds'],60)
    def test_existing_receipt_without_creation_time_fails_closed(self):
        with self.assertRaises(ValueError):evaluate(self.contract(),dt.datetime(2026,8,19,8,31,tzinfo=UTC),lambda b,p:True)

if __name__=='__main__':unittest.main()
