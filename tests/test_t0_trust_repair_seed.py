import json, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
POLICY=ROOT/'config/t0_trust_repair_seed_v25.json'
SCRIPT=ROOT/'scripts/reconcile_t0_trust_repair_seed.py'
WF=ROOT/'.github/workflows/supernova-t0-trust-repair-seed.yml'

class T0TrustRepairSeedTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(POLICY.read_text())

    def test_seed_is_one_shot_epoch4_to_epoch5(self):
        self.assertEqual(self.p['required_current_root_epoch'],4)
        self.assertEqual(self.p['target_root_epoch'],5)
        self.assertEqual(self.p['calibration_streak_required'],0)
        self.assertFalse(self.p['fresh_allowed_globally_required'])

    def test_candidate_diff_is_closed_and_state_forbidden(self):
        allowed=set(self.p['allowed_root_candidate_paths'])
        required=set(self.p['required_root_candidate_paths'])
        self.assertEqual(allowed,required)
        self.assertIn('scripts/check_lane_liveness.py',required)
        self.assertIn('scripts/reconcile_open_prs.py',required)
        self.assertIn('scripts/reconcile_authority_bootstrap.py',required)
        self.assertIn('config/root_tcb_epoch_v25.json',required)
        self.assertIn('state/',self.p['forbidden_candidate_prefixes'])

    def test_seed_cannot_self_modify(self):
        self.assertTrue(set(self.p['seed_paths']).isdisjoint(self.p['required_root_candidate_paths']))
        text=SCRIPT.read_text()
        self.assertIn('seed self-modification forbidden',text)
        self.assertIn("set(changed)!=required",text)

    def test_candidate_job_has_no_write_token(self):
        text=WF.read_text()
        self.assertIn('GITHUB_TOKEN: ""',text)
        self.assertIn('persist-credentials: false',text)
        self.assertIn('statuses: write',text)
        self.assertIn('cd trusted && python3 scripts/reconcile_t0_trust_repair_seed.py',text)

    def test_seed_requires_provenance_environment_generation_and_bootstrap_checker_repairs(self):
        text=SCRIPT.read_text()
        self.assertIn('COMPLETED_BOOTSTRAP_RUN_ID',text)
        self.assertIn('validator_environment_v25.json',text)
        self.assertIn('generation_delta_policy_v25.json',text)
        self.assertIn('negative_zero_outcomes remains untyped',text)
        self.assertIn('bootstrap invariant checker does not accept strengthened provenance contract',text)
        self.assertIn('bootstrap invariant checker does not protect validator environment contract',text)

if __name__=='__main__': unittest.main()
