import importlib.util,json,pathlib,tempfile,unittest
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]

def load(path):return json.loads((ROOT/path).read_text())
def mod():
 p=ROOT/'scripts/validate_branch_bus_v251.py';s=importlib.util.spec_from_file_location('v251_contract_test',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class FutureFreshRoleModelContractTests(unittest.TestCase):
 def test_mm05_closed_payload_and_negative_envelope(self):
  s=load('schemas/mastermind_e3_payload.schema.json');v=Draft202012Validator(s)
  p={'schema_version':'PS-MM05-E3-PAYLOAD-2.5-1','arm':'LEARNED_PROPOSAL','artifact_sha256':'a'*64,'evaluator_id':'eval','evaluator_version':'1','security_envelope_id':'sec','mutation_envelope_id':'mut','matched_envelope_verified':True,'complete_cost_binding':'REPORT_COST_LEDGER_COMPLETE','seed_set':[1,2],'scoring_contract_id':'score','origin_task_promotion':False}
  self.assertEqual(list(v.iter_errors(p)),[])
  q=dict(p);q['matched_envelope_verified']=False;self.assertTrue(list(v.iter_errors(q)))
  q=dict(p);q['origin_task_promotion']=True;self.assertTrue(list(v.iter_errors(q)))
  q=dict(p);q['unknown']=1;self.assertTrue(list(v.iter_errors(q)))
 def test_mm07_diagnostic_and_goal2_isolation(self):
  s=load('schemas/mastermind_mm07_payload.schema.json');v=Draft202012Validator(s)
  p={'schema_version':'PS-MM07-PAYLOAD-2.5-1','experiment_kind':'BOUNDED_TRAIN_DIAGNOSTIC','train_only':True,'generation_index':1,'source_identity':'src','evaluator_identity':'eval','model_tools_environment_identity':'env','budget_identity':'budget','cache_retention_identity':'cache','solver_identity':'F','memory_control_identity':'M','improver_identity':'I','claim_status':'DIAGNOSTIC_NOT_GOAL2','improver_treatment_isolated':False,'complete_cost_binding':'REPORT_COST_LEDGER_COMPLETE','origin_task_promotion':False}
  self.assertEqual(list(v.iter_errors(p)),[])
  q=dict(p);q.update(experiment_kind='GOAL2_IMPROVER_COMPARISON',claim_status='IMPROVER_COMPARISON_CANDIDATE',improver_treatment_isolated=False);self.assertTrue(list(v.iter_errors(q)))
  q['improver_treatment_isolated']=True;self.assertEqual(list(v.iter_errors(q)),[])
 def test_typed_role_validator_runs_only_for_fresh_mm05_mm07(self):
  m=mod();base={'mode':'SAFE_REPLAY_ONLY','worker_id':'MM05'};self.assertEqual(m.typed_role_payload_errors(base),[])
  self.assertTrue(m.typed_role_payload_errors({'mode':'FRESH_EXECUTION','worker_id':'MM05','role_payload':{}}))
  self.assertTrue(m.typed_role_payload_errors({'mode':'FRESH_EXECUTION','worker_id':'MM07','role_payload':{}}))
 def test_verified_binding_requires_real_frozen_attestation_and_exact_blob(self):
  m=mod();old=m.ROOT
  try:
   t=pathlib.Path(tempfile.mkdtemp());m.ROOT=t
   (t/'schemas').mkdir();(t/'runtime/model_bindings').mkdir(parents=True)
   (t/'schemas/model_binding_attestation.schema.json').write_text((ROOT/'schemas/model_binding_attestation.schema.json').read_text())
   att={'schema_version':'PS-MODEL-BINDING-ATTESTATION-2.5-1','status':'VALIDATED','task_network_plan_id':m.PLAN,'runtime_state_id':'runtime-X','model_target':'GPT-5.6 Sol','reasoning_effort_target':'EXTRA_HIGH','observed_model_id':'GPT-5.6 Sol','observed_reasoning_effort':'EXTRA_HIGH','model_match':True,'reasoning_match':True,'environment_sha256':'a'*64,'attestor_kind':'RUNTIME_OBSERVED','created_pre_outcome':True,'attestation_id':'A1'}
   p=t/'runtime/model_bindings/A1.json';p.write_text(json.dumps(att,separators=(',',':'))+'\n')
   report={'runtime_state_id':'runtime-X','session_header':{'model_binding_status':'VERIFIED','model_target':'GPT-5.6 Sol','reasoning_effort_target':'EXTRA_HIGH'},'model_binding_attestation_path':'runtime/model_bindings/A1.json','model_binding_attestation_git_identity':m.blob(p)}
   control={'required_control_paths':['runtime/model_bindings/A1.json']}
   self.assertEqual(m.model_binding_errors(report,control),[])
   q=dict(report);q['model_binding_attestation_git_identity']='b'*40;self.assertTrue(m.model_binding_errors(q,control))
   att['observed_reasoning_effort']='LOW';p.write_text(json.dumps(att,separators=(',',':'))+'\n');q=dict(report);q['model_binding_attestation_git_identity']=m.blob(p);self.assertTrue(m.model_binding_errors(q,control))
   self.assertEqual(m.model_binding_errors({'session_header':{'model_binding_status':'PARTIAL_UNVERIFIED'}},{}),[])
  finally:m.ROOT=old
if __name__=='__main__':unittest.main()
