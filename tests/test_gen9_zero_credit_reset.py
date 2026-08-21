import importlib.util,json,pathlib,tempfile,unittest
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[1];SCRIPT=ROOT/'scripts/reconcile_open_prs.py'
OLD_BLOB='31071464144bde197aca0e3f13153be2d85208d7';OLD_COHORT='CAL-BR-009-v25-b53ab205';OLD_G='67bcfef1a5a1e65c9cc4adb1a2f308ec51c70c3f';MF='57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f';MM='026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d';RT='9d0a88cc9001295b5e4c0f4163e83c0fd64ce04521e34230ad3539af14f3dfaf'

def mod():
 s=importlib.util.spec_from_file_location('gen9_reset',SCRIPT);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def candidate(tmp):
 root=pathlib.Path(tmp)
 for d in ('state','superseded','config'): (root/d).mkdir(parents=True,exist_ok=True)
 cohort='CAL-BR-010-v25-test';state={'generation_seq':10,'active_parent_state_git_identity':OLD_BLOB,'active_cohort_id':cohort,'active_control_manifest_path':f'control/{cohort}.json','active_assignment_path':f'assignments/{cohort}.json','calibration_countable_current':True,'calibration_streak':0,'fresh_allowed_globally':False,'network_mode':'GITHUB_BRANCH_CALIBRATION','foundry_sha256':MF,'mastermind_sha256':MM,'runtime_state_id':RT,'superseded_cohorts':[OLD_COHORT]};(root/'state/CURRENT.json').write_text(json.dumps(state))
 receipt={'schema_version':'PS-COHORT-SUPERSESSION-1','cohort_id':OLD_COHORT,'generation_head_sha':OLD_G,'state_blob_sha':OLD_BLOB,'disposition':'INVALIDATED_ZERO_CREDIT_GEN9_CONTROL_DEFECTS','calibration_credit':0,'fresh_evidence_consumed':False,'replacement_generation_seq':10,'replacement_countable':True};(root/f'superseded/{OLD_COHORT}.json').write_text(json.dumps(receipt))
 epoch={'schema_version':'PS-GEN9-REPAIR-RESET-EPOCH-2.5-1','old_state_blob':OLD_BLOB,'old_cohort_id':OLD_COHORT,'old_generation_head_sha':OLD_G,'allowed_successor_generation_seq':10,'calibration_credit':0,'fresh_evidence_consumed':False,'foundry_sha256':MF,'mastermind_sha256':MM,'runtime_state_id':RT};(root/'config/gen9_repair_reset_epoch_v25.json').write_text(json.dumps(epoch))
 changed=[f'control/{cohort}.json',f'assignments/{cohort}.json',f'liveness/{cohort}.json','state/CURRENT.json',f'superseded/{OLD_COHORT}.json']
 return root,changed

class Gen9ZeroCreditResetTests(unittest.TestCase):
 def old(self):return {'generation_seq':9,'active_cohort_id':OLD_COHORT,'generation_head_sha':OLD_G,'calibration_countable_current':True,'calibration_streak':0,'fresh_allowed_globally':False,'network_mode':'GITHUB_BRANCH_CALIBRATION','foundry_sha256':MF,'mastermind_sha256':MM,'runtime_state_id':RT}
 def check(self,root,changed,old=None,blob=OLD_BLOB):
  m=mod()
  with mock.patch.object(m,'run',return_value=(0,blob+'\n')):return m.exact_gen9_zero_credit_repair_parent(root,'a'*40,self.old() if old is None else old,changed)
 def test_exact_zero_credit_replacement_passes(self):
  with tempfile.TemporaryDirectory() as d:r,c=candidate(d);self.assertTrue(self.check(r,c))
 def test_wrong_parent_blob_or_old_generation_fails(self):
  with tempfile.TemporaryDirectory() as d:r,c=candidate(d);self.assertFalse(self.check(r,c,blob='d'*40))
  with tempfile.TemporaryDirectory() as d:r,c=candidate(d);o=self.old();o['generation_seq']=8;self.assertFalse(self.check(r,c,old=o))
 def test_credit_or_fresh_mutation_fails(self):
  for field,value in [('calibration_credit',1),('fresh_evidence_consumed',True)]:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as d:
    r,c=candidate(d);p=r/f'superseded/{OLD_COHORT}.json';x=json.loads(p.read_text());x[field]=value;p.write_text(json.dumps(x));self.assertFalse(self.check(r,c))
 def test_successor_must_be_countable_streak_zero_fresh_false_same_substrate(self):
  for field,value in [('calibration_countable_current',False),('calibration_streak',1),('fresh_allowed_globally',True),('foundry_sha256','0'*64),('mastermind_sha256','1'*64),('runtime_state_id','wrong')]:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as d:
    r,c=candidate(d);p=r/'state/CURRENT.json';x=json.loads(p.read_text());x[field]=value;p.write_text(json.dumps(x));self.assertFalse(self.check(r,c))
 def test_exact_control_assignment_liveness_state_supersession_paths_required(self):
  with tempfile.TemporaryDirectory() as d:r,c=candidate(d);self.assertFalse(self.check(r,c[:-1]))
 def test_reset_epoch_mutation_fails(self):
  with tempfile.TemporaryDirectory() as d:
   r,c=candidate(d);p=r/'config/gen9_repair_reset_epoch_v25.json';x=json.loads(p.read_text());x['allowed_successor_generation_seq']=11;p.write_text(json.dumps(x));self.assertFalse(self.check(r,c))

if __name__=='__main__':unittest.main()
