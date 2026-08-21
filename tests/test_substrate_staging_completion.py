import importlib.util,json,pathlib,tempfile,unittest
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[1];SPEC=importlib.util.spec_from_file_location('m',ROOT/'scripts/reconcile_open_prs.py');M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
def old():return {'generation_seq':8,'active_cohort_id':M.STAGING_COHORT,'generation_branch':'ps/gen/'+M.STAGING_COHORT,'generation_head_sha':'a'*40,'calibration_countable_current':False,'calibration_streak':0,'fresh_allowed_globally':False,'network_mode':'BENCHMARK_DISCOVERY_WAIT','foundry_sha256':M.MF311,'mastermind_sha256':M.MM4410,'runtime_state_id':M.RUNTIME,'runtime_update_receipt_path':M.STAGING_RECEIPT,'superseded_cohorts':[M.GEN7_INVALIDATED_COHORT]}
def candidate(d,blob='b'*40):
 r=pathlib.Path(d);(r/'state').mkdir();(r/'superseded').mkdir();cohort='CAL-BR-009-v25-test';state={'generation_seq':9,'active_parent_state_git_identity':blob,'active_cohort_id':cohort,'active_control_manifest_path':f'control/{cohort}.json','active_assignment_path':f'assignments/{cohort}.json','calibration_countable_current':True,'calibration_streak':0,'fresh_allowed_globally':False,'network_mode':'GITHUB_BRANCH_CALIBRATION','foundry_sha256':M.MF311,'mastermind_sha256':M.MM4410,'runtime_state_id':M.RUNTIME,'runtime_update_receipt_path':M.STAGING_RECEIPT,'superseded_cohorts':[M.GEN7_INVALIDATED_COHORT,M.STAGING_COHORT]};(r/'state/CURRENT.json').write_text(json.dumps(state));rec={'schema_version':'PS-COHORT-SUPERSESSION-1','cohort_id':M.STAGING_COHORT,'generation_head_sha':'a'*40,'state_blob_sha':blob,'disposition':'NONCOUNTABLE_SUBSTRATE_STAGING_COMPLETE_ZERO_CREDIT','calibration_credit':0,'fresh_evidence_consumed':False,'replacement_generation_seq':9,'replacement_countable':True};(r/M.STAGING_SUPERSESSION_PATH).write_text(json.dumps(rec));return r,state
class Tests(unittest.TestCase):
 def check(self,r,o=None,blob='b'*40):
  _,s=candidate(r,blob);changed=['state/CURRENT.json',M.STAGING_SUPERSESSION_PATH,s['active_control_manifest_path'],s['active_assignment_path'],f"liveness/{s['active_cohort_id']}.json"]
  with mock.patch.object(M,'run',return_value=(0,blob+'\n')):return M.exact_noncountable_substrate_staging_parent(pathlib.Path(r),'c'*40,old() if o is None else o,changed)
 def test_exact_passes(self):
  with tempfile.TemporaryDirectory() as d:self.assertTrue(self.check(d))
 def test_old_countable_fails(self):
  with tempfile.TemporaryDirectory() as d:o=old();o['calibration_countable_current']=True;self.assertFalse(self.check(d,o))
 def test_wrong_foundry_fails(self):
  with tempfile.TemporaryDirectory() as d:o=old();o['foundry_sha256']='0'*64;self.assertFalse(self.check(d,o))
 def test_credit_mutation_fails(self):
  with tempfile.TemporaryDirectory() as d:
   r,s=candidate(d);p=r/M.STAGING_SUPERSESSION_PATH;x=json.loads(p.read_text());x['calibration_credit']=1;p.write_text(json.dumps(x));changed=['state/CURRENT.json',M.STAGING_SUPERSESSION_PATH,s['active_control_manifest_path'],s['active_assignment_path'],f"liveness/{s['active_cohort_id']}.json"]
   with mock.patch.object(M,'run',return_value=(0,'b'*40+'\n')):self.assertFalse(M.exact_noncountable_substrate_staging_parent(r,'c'*40,old(),changed))
 def test_successor_must_be_countable_streak0_freshfalse(self):
  for k,v in [('calibration_countable_current',False),('calibration_streak',1),('fresh_allowed_globally',True)]:
   with self.subTest(k=k),tempfile.TemporaryDirectory() as d:
    r,s=candidate(d);s[k]=v;(r/'state/CURRENT.json').write_text(json.dumps(s));changed=['state/CURRENT.json',M.STAGING_SUPERSESSION_PATH,s['active_control_manifest_path'],s['active_assignment_path'],f"liveness/{s['active_cohort_id']}.json"]
    with mock.patch.object(M,'run',return_value=(0,'b'*40+'\n')):self.assertFalse(M.exact_noncountable_substrate_staging_parent(r,'c'*40,old(),changed))
if __name__=='__main__':unittest.main()
