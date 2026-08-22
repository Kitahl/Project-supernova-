import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
DURABLE='PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED'
EPOCH6_BLOB='5a087dead0572390565bfe8bfb8f2ce69a80fc7c'
SEED_INSTALL='d96054746af2b2138f28c668bbea1153c9835752'
SEED_POLICY_BLOB='987e289a6be45ffe9de33dbe1e6b04e400a2ece4'
SEED_RECONCILER_BLOB='31e2f8f47fcef1887237269b056691053720405d'
SEED_WORKFLOW_BLOB='0967b8e76adbab26221c85eee10ca18c8e3f7fa0'


def load(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))


class RootEpoch6RepairTests(unittest.TestCase):
 def test_current_epoch7_binds_exact_epoch6_predecessor(self):
  current=load('config/root_tcb_epoch_v25.json')
  self.assertEqual(current['schema_version'],'PS-ROOT-TCB-EPOCH-2.5-7')
  self.assertEqual(current['epoch'],7)
  self.assertEqual(current['previous_epoch_blob'],EPOCH6_BLOB)
  self.assertEqual(current['bootstrap_provenance'],DURABLE)

 def test_epoch6_marker_preserves_exact_seed_and_zero_effects(self):
  marker=load('config/root_epoch6_repair_epoch_v25.json')
  self.assertEqual(marker['schema_version'],'PS-ROOT-EPOCH6-REPAIR-EPOCH-2.5-1')
  self.assertEqual(marker['previous_root_epoch'],5);self.assertEqual(marker['new_root_epoch'],6)
  self.assertEqual(marker['root_epoch6_repair_seed_install_commit_sha'],SEED_INSTALL)
  self.assertEqual(marker['root_epoch6_repair_seed_policy_blob'],SEED_POLICY_BLOB)
  self.assertEqual(marker['calibration_credit_effect'],0)
  self.assertEqual(marker['fresh_science_effect'],'NONE');self.assertEqual(marker['runtime_effect'],'NONE');self.assertEqual(marker['scientific_state_effect'],'NONE')
  self.assertIn('GEN9_COMPATIBILITY_REGRESSION_MIGRATED_THROUGH_ROOT_EPOCH6',marker['repair_scope'])

 def test_epoch6_seed_remains_consumed_historical_evidence(self):
  seed=load('config/root_epoch6_repair_seed_v25.json')
  self.assertEqual(seed['one_shot_marker_path'],'config/root_epoch6_repair_epoch_v25.json')
  self.assertTrue((ROOT/seed['one_shot_marker_path']).is_file())
  self.assertEqual(seed['target_root_epoch'],6)
  self.assertEqual(len(seed['required_root_candidate_paths']),17)
  current=load('config/root_tcb_epoch_v25.json')
  self.assertEqual(current['root_change_rule'],'NO_AUTOMATED_BOOTSTRAP_SELF_AMENDMENT; FUTURE_ROOT_CHANGE_REQUIRES_A_NEW_INDEPENDENTLY_INSTALLED_SEED')

 def test_terminal_nonclean_receipts_remain_evidence_not_calibration_pass(self):
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

 def test_durable_bootstrap_rederivation_remains_active(self):
  text=(ROOT/'scripts/reconcile_open_prs.py').read_text(encoding='utf-8')
  self.assertIn(DURABLE,text);self.assertIn('/actions/runs/',text)
  self.assertIn('if completed and not completed.isdigit():return False',text)
  self.assertIn('if completed and rid!=completed:continue',text)
  self.assertNotIn('if not completed.isdigit():return False',text)
  authority=load('config/admission_authority.json');bootstrap=load('config/authority_bootstrap_v25.json')
  self.assertEqual(authority['bootstrap_status_provenance'],DURABLE)
  self.assertEqual(bootstrap['bootstrap_success_consumption'],DURABLE)

 def test_diagnostic_replay_still_binds_current_pr_head_and_base(self):
  text=(ROOT/'scripts/diagnose_authority_bootstrap.py').read_text(encoding='utf-8')
  self.assertIn('os.environ["DIAGNOSED_HEAD_SHA"] = sha',text)
  self.assertIn('os.environ["DIAGNOSED_BASE_SHA"] = base_sha',text)

 def test_countable_control_v22_preserves_epoch6_and_adds_epoch7_repair_surface(self):
  control=load('config/countable_control_set_v25.json');paths=set(control['required_control_paths'])
  self.assertEqual(control['schema_version'],'PS-COUNTABLE-CONTROL-SET-2.5-22')
  required={
   'config/root_epoch6_repair_seed_v25.json','config/root_epoch6_repair_epoch_v25.json','scripts/reconcile_root_epoch6_repair_seed.py','tests/test_root_epoch6_repair_seed.py','tests/test_root_epoch6_repair.py',
   'config/root_epoch7_repair_seed_v25.json','config/root_epoch7_repair_epoch_v25.json','scripts/reconcile_root_epoch7_repair_seed.py','tests/test_root_epoch7_repair_seed.py','tests/test_gen10_zero_credit_terminal_transition.py',
   'tests/test_gen9_reset_compat_root.py','scripts/reconcile_v25_admission.py','scripts/reconcile_open_prs.py','scripts/reconcile_authority_bootstrap.py','scripts/diagnose_authority_bootstrap.py'
  }
  self.assertTrue(required.issubset(paths),sorted(required-paths))

if __name__=='__main__':unittest.main()
