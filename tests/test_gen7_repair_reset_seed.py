import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class Gen7RepairResetSeedTests(unittest.TestCase):
    def test_seed_is_exact_and_one_shot(self):
        p=json.loads((ROOT/'config/gen7_repair_reset_seed_v25.json').read_text(encoding='utf-8'))
        self.assertEqual(p['exact_invalidated_state_blob'],'856481759722e23ff9a652ce140f304efe13b023')
        self.assertEqual(p['exact_invalidated_cohort'],'CAL-BR-007-v25-c13b6ee4')
        self.assertEqual(p['exact_invalidated_generation_head'],'7c182fb7ce3a3941f86f7508bbb4a18152402bb8')
        self.assertEqual(p['one_shot_marker_path'],'config/gen7_repair_reset_epoch_v25.json')
        self.assertEqual(set(p['required_candidate_paths']),{
            'config/countable_control_set_v25.json','config/gen7_repair_reset_epoch_v25.json','scripts/reconcile_open_prs.py','tests/test_gen7_repair_reset.py'
        })

    def test_candidate_never_runs_with_write_token(self):
        text=(ROOT/'.github/workflows/supernova-gen7-repair-reset-seed.yml').read_text(encoding='utf-8')
        self.assertIn("GITHUB_TOKEN: ''",text)
        self.assertIn('persist-credentials: false',text)
        self.assertIn("startsWith(github.event.pull_request.head.ref, 'repair-reset/')",text)
        self.assertIn('statuses: write',text)

    def test_seed_requires_exact_old_state_and_zero_credit_logic(self):
        text=(ROOT/'scripts/reconcile_gen7_repair_reset_seed.py').read_text(encoding='utf-8')
        for needle in ('exact_invalidated_state_blob','calibration_streak','fresh_allowed_globally','INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS','seed self-modification forbidden'):
            self.assertIn(needle,text)

if __name__=='__main__':unittest.main()
