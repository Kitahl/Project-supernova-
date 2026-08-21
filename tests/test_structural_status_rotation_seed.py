import json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]

def load(p):return json.loads((ROOT/p).read_text())

class StructuralStatusRotationSeedTests(unittest.TestCase):
 def test_seed_is_narrow_one_shot_and_cannot_modify_itself(self):
  p=load('config/structural_status_rotation_seed_v25.json')
  self.assertEqual(p['seed_context'],'supernova/structural-status-rotation-seed')
  self.assertEqual(p['head_prefix_required'],'structural-rotation/')
  self.assertEqual(p['one_shot_marker_path'],'config/structural_status_rotation_epoch_v25.json')
  self.assertEqual(p['seed_self_modification'],'FORBIDDEN')
  self.assertEqual(p['calibration_streak_required'],0);self.assertFalse(p['fresh_allowed_globally_required'])
  self.assertTrue(set(p['seed_paths']).isdisjoint(p['allowed_root_candidate_paths']))
  for x in ['state/','control/','assignments/','reports/','runtime/','benchmark/','research/']:self.assertIn(x,p['forbidden_candidate_prefixes'])

 def test_root_candidate_must_fix_single_writer_and_gen9_reset_together(self):
  p=load('config/structural_status_rotation_seed_v25.json');required=set(p['required_root_candidate_paths'])
  for x in ['scripts/reconcile_branch_rest.py','.github/workflows/supernova-rest-branch-reconciler.yml','tests/test_structural_status_single_writer.py','scripts/reconcile_open_prs.py','config/gen9_repair_reset_epoch_v25.json','tests/test_gen9_zero_credit_reset.py','config/root_tcb_epoch_v25.json','config/structural_status_rotation_epoch_v25.json']:
   self.assertIn(x,required)

 def test_candidate_diagnostics_are_read_only_and_status_write_is_separate(self):
  t=(ROOT/'.github/workflows/supernova-structural-status-rotation-seed.yml').read_text()
  self.assertIn('candidate-diagnostics:',t);self.assertIn("GITHUB_TOKEN: ''",t);self.assertIn('persist-credentials: false',t)
  self.assertIn('trusted-seed:',t);self.assertIn('statuses: write',t);self.assertIn('needs: candidate-diagnostics',t)
  self.assertIn('DIAGNOSED_HEAD_SHA:',t);self.assertIn('DIAGNOSED_BASE_SHA:',t)
  # Candidate code is not executed in the write-capable job. The write-capable job clones accepted main.
  trusted=t.split('trusted-seed:',1)[1]
  self.assertIn('git clone --filter=blob:none',trusted)
  self.assertIn('python3 scripts/reconcile_structural_status_rotation_seed.py',trusted)

 def test_seed_script_checks_exact_gen9_target_and_inert_marker(self):
  t=(ROOT/'scripts/reconcile_structural_status_rotation_seed.py').read_text()
  for needle in ['GEN9_STATE_BLOB','GEN9_COHORT','GEN9_G','structural_status_rotation_epoch_v25.json','GEN9_ZERO_CREDIT_RESET','supernova/rest-branch-generation-diagnostic','supernova/rest-branch-worker-diagnostic']:
   self.assertIn(needle,t)

if __name__=='__main__':unittest.main()
