import datetime as dt
import unittest

from scripts.check_lane_liveness import evaluate

WORKERS=("MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01")


class LivenessMonitorTests(unittest.TestCase):
    def contract(self):
        cohort='c'
        lanes=[]
        for i,w in enumerate(WORKERS):
            lanes.append({
                'lane_id':w,
                'branch':f'ps/work/{cohort}/{w}',
                'path':f'reports/{cohort}/{w}.json',
                'expected_window_start_utc':f'2026-08-19T08:{i:02d}:00Z',
                'deadline_utc':'2026-08-19T08:30:00Z',
                'eligible_before_deadline':True,
            })
        return {
            'schema_version':'PS-COHORT-LIVENESS-2',
            'cohort_id':cohort,
            'generation_root_sha':'a'*40,
            'control_manifest_id':'CTRL-c',
            'control_manifest_git_identity':'b'*40,
            'assignment_id':'ASSIGN-c',
            'assignment_git_identity':'c'*40,
            'lanes':lanes,
        }

    def test_missing_after_deadline_blocks_without_inventing_pause_cause(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,31,tzinfo=dt.timezone.utc),lambda b,p:False)
        self.assertFalse(r['transition_liveness_pass'])
        self.assertEqual(set(r['blocking_lanes']),set(WORKERS))
        self.assertTrue(all(x['receipt_status']=='NO_RECEIPT' for x in r['observations']))
        self.assertTrue(all(x['task_state']=='TASK_STATE_UNKNOWN' for x in r['observations']))

    def test_missing_before_deadline_is_observed_but_not_yet_blocking(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,20,tzinfo=dt.timezone.utc),lambda b,p:False)
        self.assertTrue(r['transition_liveness_pass'])
        self.assertTrue(all(x['receipt_status']=='NO_RECEIPT' for x in r['observations']))
        self.assertEqual(r['blocking_lanes'],[])

    def test_present_receipt_passes(self):
        r=evaluate(self.contract(),dt.datetime(2026,8,19,8,31,tzinfo=dt.timezone.utc),lambda b,p:True)
        self.assertTrue(r['transition_liveness_pass'])
        self.assertTrue(all(x['receipt_status']=='RUN_OBSERVED' for x in r['observations']))

if __name__=='__main__':
    unittest.main()
