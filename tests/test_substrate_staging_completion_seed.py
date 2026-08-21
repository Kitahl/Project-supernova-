import json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class SeedTests(unittest.TestCase):
 def test_policy_is_one_shot_and_exact(self):
  p=json.loads((ROOT/'config/substrate_staging_completion_seed_v25.json').read_text())
  self.assertEqual(p['staging_generation_seq'],8);self.assertEqual(p['countable_successor_generation_seq'],9)
  self.assertEqual(p['staging_cohort_id'],'STAGE-BR-008-v25-MF311')
  self.assertEqual(p['target_foundry_sha256'],'57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f')
  self.assertTrue(set(p['seed_paths']).isdisjoint(p['required_candidate_paths']))
 def test_candidate_has_no_write_token(self):
  t=(ROOT/'.github/workflows/supernova-substrate-staging-completion-seed.yml').read_text()
  self.assertIn("GITHUB_TOKEN: ''",t);self.assertIn('persist-credentials: false',t);self.assertIn('statuses: write',t)
 def test_seed_requires_future_completion_logic(self):
  t=(ROOT/'scripts/reconcile_substrate_staging_completion_seed.py').read_text()
  for x in ('exact_noncountable_substrate_staging_parent','candidate diff is not exact staging-completion root set','seed self-modification forbidden'):self.assertIn(x,t)
if __name__=='__main__':unittest.main()
