import importlib.util,json,pathlib,tempfile,unittest
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]

def load(path):return json.loads((ROOT/path).read_text())
def mod():
 p=ROOT/'scripts/validate_branch_bus_v251.py';s=importlib.util.spec_from_file_location('v251_contract_test',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def metric(status='NOT_MEASURED',value=None):return {'result_type':'SCIENTIFIC_METRIC','status':status,'value':value,'reason':'test','evidence_refs':[],'unit':None}
def assignment(worker='MM01',pool='TRAIN',stage='STAGE0_LOOP'):
 return {'assignment_id':'A','cohort_id':'C','network_mode':'FRESH_ENABLED','workers':{worker:{'fresh_allowed':True,'fresh_scope':{'pool':pool,'stage':stage,'purpose_id':'P'},'private_manifest_id':'M','private_manifest_git_identity':'a'*40}}}

class FutureFreshRoleModelContractTests(unittest.TestCase):
 def test_mm05_requires_exact_three_arm_comparison(self):
  s=load('schemas/mastermind_e3_payload.schema.json');v=Draft202012Validator(s)
  cost={'proposal_compute':1,'execution_compute':2,'model_tokens':3,'tool_calls':4,'feature_probe_compute':5,'selection_compute':6,'wall_seconds':7}
  arm={'artifact_sha256':'a'*64,'evaluator_id':'eval','evaluator_version':'1','complete_cost':cost,'raw_outcome_ref':'raw'}
  p={'schema_version':'PS-MM05-E3-PAYLOAD-2.5-2','experiment_id':'E','shared_execution_context':{'runtime_state_id':'r','task_identity':'t','model_tools_identity':'m','proposal_budget_identity':'pb','execution_budget_identity':'eb','cache_retention_identity':'c','security_envelope_id':'s','mutation_envelope_id':'u'},'seed_set':[1,2],'scoring_contract_id':'score','arms':{'LEARNED_PROPOSAL':arm,'RANDOM_ADMISSIBLE':arm,'NO_CHANGE_EQUAL_COMPUTE':arm},'matched_envelope_verified':True,'origin_task_promotion':False}
  self.assertEqual(list(v.iter_errors(p)),[])
  q=json.loads(json.dumps(p));q['arms'].pop('RANDOM_ADMISSIBLE');self.assertTrue(list(v.iter_errors(q)))
  q=json.loads(json.dumps(p));q['arms']['EXTRA']=arm;self.assertTrue(list(v.iter_errors(q)))
  q=json.loads(json.dumps(p));q['origin_task_promotion']=True;self.assertTrue(list(v.iter_errors(q)))

 def test_mm07_stage0_contract_is_nonvacuous(self):
  s=load('schemas/mastermind_mm07_payload.schema.json');v=Draft202012Validator(s)
  p={'schema_version':'PS-MM07-PAYLOAD-2.5-2','experiment_kind':'BOUNDED_TRAIN_DIAGNOSTIC','train_only':True,'generation_index':1,'predeclared_stop':True,'typed_event_trace_ref':'events','rho_improve_claim':'DESCRIPTIVE_ONLY','before_result':metric(),'after_result':metric(),'scores_frozen_before_candidate':True,'next_candidate':None,'source_identity':'src','evaluator_identity':'eval','model_tools_environment_identity':'env','budget_identity':'budget','cache_retention_identity':'cache','solver_identity':'F','memory_control_identity':'M','improver_identity':'I','claim_status':'DIAGNOSTIC_NOT_GOAL2','improver_treatment_isolated':False,'complete_cost_binding':'cost-id','origin_task_promotion':False}
  self.assertEqual(list(v.iter_errors(p)),[])
  for field in ('predeclared_stop','typed_event_trace_ref','rho_improve_claim','scores_frozen_before_candidate'):
   q=dict(p);q.pop(field);self.assertTrue(list(v.iter_errors(q)),field)
  q=dict(p);q['origin_task_promotion']=True;self.assertTrue(list(v.iter_errors(q)))
  q=dict(p);q.update(experiment_kind='GOAL2_IMPROVER_COMPARISON',claim_status='IMPROVER_COMPARISON_CANDIDATE',improver_treatment_isolated=False);self.assertTrue(list(v.iter_errors(q)))
  q['improver_treatment_isolated']=True;self.assertEqual(list(v.iter_errors(q)),[])

 def test_mm07_replay_forbids_numeric_gain_candidate_and_promotion(self):
  s=load('schemas/mastermind_mm07_replay_payload.schema.json');v=Draft202012Validator(s)
  p={'schema_version':'PS-MM07-REPLAY-PAYLOAD-2.5-1','before_result':metric(),'after_result':metric(),'numeric_delta':None,'next_self_candidate':None,'self_promotion':False,'goal2_credit':False,'solver_memory_improver_separated':True,'claim_scope':'replay'}
  self.assertEqual(list(v.iter_errors(p)),[])
  for field,val in [('numeric_delta',1),('next_self_candidate','x'),('self_promotion',True),('goal2_credit',True)]:
   q=dict(p);q[field]=val;self.assertTrue(list(v.iter_errors(q)),field)

 def test_mm05_replay_requires_three_typed_not_measured_arms(self):
  s=load('schemas/mastermind_mm05_replay_payload.schema.json');v=Draft202012Validator(s)
  p={'schema_version':'PS-MM05-E3-REPLAY-PAYLOAD-2.5-1','learned_proposal':metric(),'random_admissible':metric(),'no_change_equal_compute':metric(),'comparison_status':'NOT_MEASURED','comparison_reason':'not run','self_promotion':False}
  self.assertEqual(list(v.iter_errors(p)),[])
  q=json.loads(json.dumps(p));q['learned_proposal']['value']=0;self.assertTrue(list(v.iter_errors(q)))

 def test_mm04_replay_nonvacuity_requires_checks(self):
  s=load('schemas/mastermind_mm04_replay_payload.schema.json');v=Draft202012Validator(s)
  p={'schema_version':'PS-MM04-REPLAY-PAYLOAD-2.5-1','architecture_result':metric(),'evaluator_execution_status':'NOT_EXECUTED','architecture_checks':['a'],'nonvacuity_checks':['n'],'provenance_checks':['p'],'self_promotion':False}
  self.assertEqual(list(v.iter_errors(p)),[])
  q=dict(p);q['architecture_checks']=[];self.assertTrue(list(v.iter_errors(q)))

 def test_mf02_e1_fresh_schema_requires_all_arms(self):
  s=load('schemas/math_foundry_e1_payload.schema.json');v=Draft202012Validator(s);cost={'wall_seconds':1,'cpu_seconds':1,'model_tokens':1,'tool_calls':1,'storage_bytes':1};arm={'route_availability':'AVAILABLE','recommended_action':'r','executed_action':'r','raw_outcome_ref':'o','complete_cost':cost}
  p={'schema_version':'PS-MF02-E1-PAYLOAD-2.5-1','experiment_id':'E','source_identity':'s','evaluator_identity':'e','model_tools_identity':'m','same_total_budget_identity':'b','seed_set':[1],'arms':{x:arm for x in ['BASE','SBS','VBS_SINGLE','AUTO','VBS_SCHEDULE']},'ranking_only_change_zero_credit':True,'origin_task_promotion':False}
  self.assertEqual(list(v.iter_errors(p)),[]);q=json.loads(json.dumps(p));q['arms'].pop('AUTO');self.assertTrue(list(v.iter_errors(q)))

 def test_typed_validator_requires_fresh_assignment_manifest_and_mm01_train_scope(self):
  m=mod();payload={'schema_version':'PS-MM01-REACT-PROPOSAL-2.5-1','proposal_id':'p','proposal_class':'BOUNDED_MECHANISM_PROPOSAL','authority':'PRE_REVIEW_ONLY','source_role':'MM01','source_task_id':'t','assignment_evidence':{'assignment_id':'A','cohort_id':'C','fresh_allowed':True,'stage0_train_only':True},'preservation_controls':['p'],'observer_contract':{'observed_inputs':[],'forbidden_hidden_inputs':['h'],'observation_timing_preserved':True},'contract_controls':{'producer_obligations':['p'],'consumer_obligations':['c'],'invariants':['i'],'failure_semantics':'f'},'contamination_controls':{'origin_task_excluded_from_promotion':True,'protected_eval_not_read':True,'source_versions_frozen':True,'cross_task_leakage_check':'PASS'},'mutation_controls':{'mutation_surface':['x'],'bounded_change':True,'rollback_defined':True,'security_envelope':'s','forbidden_surfaces':['z']},'execution_envelope':{'execution_status':'NOT_EXECUTED','executable_artifact_ref':None,'complete_cost_accounting_required':True,'equal_compute_control_required':True},'evaluator_envelope':{'self_grading_forbidden':True,'independent_evaluator_required':True,'evaluator_ref':None},'provenance':{'source_refs':['s'],'artifact_digests':[],'model_binding_status':'PARTIAL_UNVERIFIED'},'negative_controls':[{'control_id':'n','purpose':'p'}],'claim_scope':'c','self_promotion_requested':False,'next_action':'n'}
  r={'mode':'FRESH_EXECUTION','worker_id':'MM01','private_manifest_id':'M','private_manifest_git_identity':'a'*40,'role_payload':payload};self.assertEqual(m.typed_role_payload_errors(r,assignment()),[])
  q=json.loads(json.dumps(r));q['role_payload']['assignment_evidence']['assignment_id']='WRONG';self.assertTrue(m.typed_role_payload_errors(q,assignment()))
  self.assertTrue(m.typed_role_payload_errors(r,assignment(pool='CALIBRATION')))
  bad=assignment();bad['workers']['MM01']['fresh_allowed']=False;self.assertTrue(m.typed_role_payload_errors(r,bad))

 def test_verified_binding_requires_real_frozen_attestation_and_exact_blob(self):
  m=mod();old=m.ROOT
  try:
   t=pathlib.Path(tempfile.mkdtemp());m.ROOT=t;(t/'schemas').mkdir();(t/'runtime/model_bindings').mkdir(parents=True)
   (t/'schemas/model_binding_attestation.schema.json').write_text((ROOT/'schemas/model_binding_attestation.schema.json').read_text())
   att={'schema_version':'PS-MODEL-BINDING-ATTESTATION-2.5-1','status':'VALIDATED','task_network_plan_id':m.PLAN,'runtime_state_id':'runtime-X','model_target':'GPT-5.6 Sol','reasoning_effort_target':'EXTRA_HIGH','observed_model_id':'GPT-5.6 Sol','observed_reasoning_effort':'EXTRA_HIGH','model_match':True,'reasoning_match':True,'environment_sha256':'a'*64,'attestor_kind':'RUNTIME_OBSERVED','created_pre_outcome':True,'attestation_id':'A1'}
   p=t/'runtime/model_bindings/A1.json';p.write_text(json.dumps(att,separators=(',',':'))+'\n');report={'runtime_state_id':'runtime-X','session_header':{'model_binding_status':'VERIFIED','model_target':'GPT-5.6 Sol','reasoning_effort_target':'EXTRA_HIGH'},'model_binding_attestation_path':'runtime/model_bindings/A1.json','model_binding_attestation_git_identity':m.blob(p)};control={'required_control_paths':['runtime/model_bindings/A1.json']}
   self.assertEqual(m.model_binding_errors(report,control),[]);q=dict(report);q['model_binding_attestation_git_identity']='b'*40;self.assertTrue(m.model_binding_errors(q,control))
  finally:m.ROOT=old
if __name__=='__main__':unittest.main()
