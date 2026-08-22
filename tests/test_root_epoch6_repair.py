import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
DURABLE='PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED'
EPOCH6_BLOB='5a087dead0572390565bfe8bfb8f2ce69a80fc7c'
EPOCH7_SEED_INSTALL='f14cfdae019f2692867353fea53ca50c4e163278'
EPOCH7_SEED_POLICY='80302d1c078ccb3cb40995b9e0809f07257f284c'
EPOCH7_SEED_RECONCILER='3110fc027173dbe5483bff6dcf32b04e49621c55'
EPOCH7_SEED_WORKFLOW='3cd9481fd185f3c1db94e78983bb5687fa7ad73e'


def load(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))


class RootEpoch6RepairTests(unittest.TestCase):
 def test_epoch7_binds_exact_epoch6_predecessor_and_epoch7_seed(self):
  epoch=load('config/root_tcb_epoch_v25.json')
  self.assertEqual(epoch['schema_version'],'PS-ROOT-TCB-EPOCH-2.5-7')
  self.assertEqual(epoch['protocol_version'],'2.5');self.assertEqual(epoch['task_network_plan_id'],PLAN);self.assertEqual(epoch['epoch'],7)
  self.assertEqual(epoch['previous_epoch_blob'],EPOCH6_BLOB)
  self.assertEqual(epoch['root_epoch7_repair_seed_install_commit_sha'],EPOCH7_SEED_INSTALL)
  self.assertEqual(epoch['root_epoch7_repair_seed_policy_blob'],EPOCH7_SEED_POLICY)
  self.assertEqual(epoch['root_epoch7_repair_seed_reconciler_blob'],EPOCH7_SEED_RECONCILER)
  self.assertEqual(epoch['root_epoch7_repair_seed_workflow_blob'],EPOCH7_SEED_WORKFLOW)
  self.assertEqual(epoch['bootstrap_provenance'],DURABLE)

 def test_epoch6_and_epoch7_markers_have_zero_runtime_science_and_credit_effect(self):
  old=load('config/root_epoch6_repair_epoch_v25.json');new=load('config/root_epoch7_repair_epoch_v25.json')
  self.assertEqual(old['schema_version'],'PS-ROOT-EPOCH6-REPAIR-EPOCH-2.5-1')
  self.assertEqual(old['previous_root_epoch'],5);self.assertEqual(old['new_root_epoch'],6)
  self.assertEqual(old['calibration_credit_effect'],0)
  self.assertEqual(old['fresh_science_effect'],'NONE');self.assertEqual(old['runtime_effect'],'NONE');self.assertEqual(old['scientific_state_effect'],'NONE')
  self.assertEqual(new['schema_version'],'PS-ROOT-EPOCH7-REPAIR-EPOCH-2.5-1')
  self.assertEqual(new['previous_root_epoch'],6);self.assertEqual(new['new_root_epoch'],7)
  self.assertEqual(new['root_epoch7_repair_seed_install_commit_sha'],EPOCH7_SEED_INSTALL)
  self.assertEqual(new['root_epoch7_repair_seed_policy_blob'],EPOCH7_SEED_POLICY)
  self.assertEqual(new['calibration_credit_effect'],0)
  self.assertEqual(new['fresh_science_effect'],'NONE');self.assertEqual(new['runtime_effect'],'NONE');self.assertEqual(new['scientific_state_effect'],'NONE')
  self.assertIn('GEN10_ZERO_CREDIT_TERMINAL_SUCCESSOR_ADMISSION',new['repair_scope'])
  self.assertIn('GEN9_COMPATIBILITY_REGRESSION_MIGRATED_THROUGH_ROOT_EPOCH7',new['repair_scope'])

 def test_seed_is_consumed_exactly_once_and_future_root_changes_still_need_independent_seed(self):
  seed=load('config/root_epoch7_repair_seed_v25.json');epoch=load('config/root_tcb_epoch_v25.json')
  self.assertEqual(seed['one_shot_marker_path'],'config/root_epoch7_repair_epoch_v25.json')
  self.assertTrue((ROOT/seed['one_shot_marker_path']).is_file())
  self.assertEqual(seed['target_root_epoch'],7)
  self.assertEqual(len(seed['required_root_candidate_paths']),8)
  self.assertEqual(epoch['root_change_rule'],'NO_AUTOMATED_BOOTSTRAP_SELF_AMENDMENT; FUTURE_ROOT_CHANGE_REQUIRES_A_NEW_INDEPENDENTLY_INSTALLED_SEED')

 def test_terminal_nonclean_receipts_are_evidence_not_calibration_pass(self):
  admission=(ROOT/'scripts/reconcile_v25_admission.py').read_text(encoding='utf-8')
  self.assertIn("TERMINAL_VERDICTS={'VERIFIED_COMPLETE','VERIFIED_WITH_QUARANTINES','INCOMPLETE','INVALID'}",admission)
  self.assertIn("if v.get('calibration_pass') is not False",admission)
  self.assertIn('diagnostic integration must force calibration pass false',admission)
  verifier=load('schemas/branch_verification.schema.json');integration=load('schemas/branch_integration.schema.json')
  self.assertIn('VERIFIED_WITH_QUARANTINES',verifier['properties']['verdict']['enum'])
  self.assertIn('VERIFIED_WITH_QUARANTINES',integration['properties']['verification_verdict']['enum'])
  vq=next(x for x in verifier['allOf'] if x.get('if',{}).get('properties',{}).get('verdict',{}).get('const')=='VERIFIED_WITH_QUARANTINES')
  iq=next(x for x in integration['allOf'] if x.get('if',{}).get('properties',{}).get('verification_verdict',{}).get('const')=='VERIFIED_WITH_QUARANTINES')
  self.assertEqual(vq['then']['properties']['calibration_pass'],{'const':False});self.assertEqual(iq['then']['properties']['calibration_pass'],{'const':False})

 def test_durable_bootstrap_rederivation_does_not_depend_on_transient_completion_env(self):
  text=(ROOT/'scripts/reconcile_open_prs.py').read_text(encoding='utf-8')
  self.assertIn(DURABLE,text);self.assertIn('/actions/runs/',text)
  self.assertIn('if completed and not completed.isdigit():return False',text)
  self.assertIn('if completed and rid!=completed:continue',text)
  self.assertNotIn('if not completed.isdigit():return False',text)
  authority=load('config/admission_authority.json');bootstrap=load('config/authority_bootstrap_v25.json')
  self.assertEqual(authority['bootstrap_status_provenance'],DURABLE)
  self.assertEqual(bootstrap['bootstrap_success_consumption'],DURABLE)

 def test_diagnostic_replay_binds_current_pr_head_and_base(self):
  text=(ROOT/'scripts/diagnose_authority_bootstrap.py').read_text(encoding='utf-8')
  self.assertIn('os.environ["DIAGNOSED_HEAD_SHA"] = sha',text)
  self.assertIn('os.environ["DIAGNOSED_BASE_SHA"] = base_sha',text)

 def test_countable_control_v22_freezes_epoch6_and_epoch7_repair_surfaces(self):
  control=load('config/countable_control_set_v25.json');paths=set(control['required_control_paths'])
  self.assertEqual(control['schema_version'],'PS-COUNTABLE-CONTROL-SET-2.5-22')
  required={'config/root_epoch6_repair_seed_v25.json','config/root_epoch6_repair_epoch_v25.json','scripts/reconcile_root_epoch6_repair_seed.py','tests/test_root_epoch6_repair_seed.py','tests/test_root_epoch6_repair.py','tests/test_gen9_reset_compat_root.py','config/root_epoch7_repair_seed_v25.json','config/root_epoch7_repair_epoch_v25.json','scripts/reconcile_root_epoch7_repair_seed.py','tests/test_root_epoch7_repair_seed.py','tests/test_gen10_zero_credit_terminal_transition.py','.github/workflows/supernova-root-epoch7-repair-seed.yml','scripts/reconcile_v25_admission.py','scripts/reconcile_open_prs.py','scripts/reconcile_authority_bootstrap.py','scripts/diagnose_authority_bootstrap.py'}
  self.assertTrue(required.issubset(paths),sorted(required-paths))

if __name__=='__main__':unittest.main()
