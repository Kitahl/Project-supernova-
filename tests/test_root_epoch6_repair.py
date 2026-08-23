import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
DURABLE='PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED'
EPOCH8_BLOB='b98b3378ad90e9c35fd02017ea3a4a0f21320c52'
EPOCH7_SEED_INSTALL='7af2eba8687b17fe8a3be4569dba02024b3e1d2b'
EPOCH7_SEED_POLICY='795a325cc22ea4d5142d4d2e171e66360e75358e'
EPOCH7_SEED_RECONCILER='1104237e8df009b4bec73056afacac671d3ea719'
EPOCH7_SEED_WORKFLOW='3cd9481fd185f3c1db94e78983bb5687fa7ad73e'
EPOCH8_SEED_INSTALL='1e4967a8783b9d2fdc0d76080aba3e7acc31a0cf'
EPOCH8_SEED_POLICY='62a68682380741ed2a32e97b0412cbbd6f20f217'
EPOCH8_SEED_RECONCILER='e46611a9e6085d53d8e4f4ec53ea6b7f4291ae35'
EPOCH8_SEED_WORKFLOW='5b7999063894a491f122d232639c4bc4d8855f32'
EPOCH9_SEED_INSTALL='7c6cca62c51afd28c0554353331abe172dbee389'
EPOCH9_SEED_POLICY='46b2f26e6a52c4d9051f7642a8cbaf7f45a1f259'
EPOCH9_SEED_RECONCILER='89593976839aaaf12bf0e7406a98f30223905829'
EPOCH9_SEED_WORKFLOW='08d12d85073b048748964c09f8ce14940c7b1106'
EPOCH9_BLOB='9a45b2098cd5870b53f9faa92e52409fa3204c81'


def load(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))


class RootEpoch6RepairTests(unittest.TestCase):
 def test_root11_binds_epoch10_predecessor_and_preserves_epoch7_through_epoch10_history(self):
  epoch=load('config/root_tcb_epoch_v25.json')
  self.assertEqual(epoch['schema_version'],'PS-ROOT-TCB-EPOCH-2.5-11')
  self.assertEqual(epoch['protocol_version'],'2.5');self.assertEqual(epoch['task_network_plan_id'],PLAN);self.assertEqual(epoch['epoch'],11)
  self.assertEqual(epoch['previous_epoch_blob'],'cf74b9c17bf1d763e7d89dc07f9bb74c334f8b59')
  self.assertEqual(epoch['root_epoch7_repair_seed_install_commit_sha'],EPOCH7_SEED_INSTALL)
  self.assertEqual(epoch['root_epoch7_repair_seed_policy_blob'],EPOCH7_SEED_POLICY)
  self.assertEqual(epoch['root_epoch7_repair_seed_reconciler_blob'],EPOCH7_SEED_RECONCILER)
  self.assertEqual(epoch['root_epoch7_repair_seed_workflow_blob'],EPOCH7_SEED_WORKFLOW)
  self.assertEqual(epoch['root_epoch8_status_writer_repair_seed_install_commit_sha'],EPOCH8_SEED_INSTALL)
  self.assertEqual(epoch['root_epoch8_status_writer_repair_seed_policy_blob'],EPOCH8_SEED_POLICY)
  self.assertEqual(epoch['root_epoch8_status_writer_repair_seed_reconciler_blob'],EPOCH8_SEED_RECONCILER)
  self.assertEqual(epoch['root_epoch8_status_writer_repair_seed_workflow_blob'],EPOCH8_SEED_WORKFLOW)
  self.assertEqual(epoch['root_epoch9_integrity_repair_seed_install_commit_sha'],EPOCH9_SEED_INSTALL)
  self.assertEqual(epoch['root_epoch9_integrity_repair_seed_policy_blob'],EPOCH9_SEED_POLICY)
  self.assertEqual(epoch['root_epoch9_integrity_repair_seed_reconciler_blob'],EPOCH9_SEED_RECONCILER)
  self.assertEqual(epoch['root_epoch9_integrity_repair_seed_workflow_blob'],EPOCH9_SEED_WORKFLOW)
  self.assertEqual(epoch['root_epoch10_scheduler_admission_seed_install_commit_sha'],'7bc97d2bed9fb285feb2e9ae1c31fb4331919d00')
  self.assertEqual(epoch['root_epoch10_scheduler_admission_seed_amendment_install_commit_sha'],'cff3368586764248f4658603d5278eeb86c375ee')
  self.assertEqual(epoch['bootstrap_provenance'],DURABLE)

 def test_epoch6_through_root11_markers_have_zero_runtime_science_and_credit_effect(self):
  old=load('config/root_epoch6_repair_epoch_v25.json');mid=load('config/root_epoch7_repair_epoch_v25.json');eight=load('config/root_epoch8_status_writer_repair_epoch_v25.json');nine=load('config/root_epoch9_integrity_repair_epoch_v25.json');ten=load('config/root_epoch10_scheduler_admission_epoch_v25.json');eleven=load('config/root_epoch11_stageability_repair_epoch_v25.json')
  self.assertEqual(old['previous_root_epoch'],5);self.assertEqual(old['new_root_epoch'],6)
  self.assertEqual(mid['previous_root_epoch'],6);self.assertEqual(mid['new_root_epoch'],7)
  self.assertEqual(eight['previous_root_epoch'],7);self.assertEqual(eight['new_root_epoch'],8)
  self.assertEqual(nine['previous_root_epoch'],8);self.assertEqual(nine['new_root_epoch'],9)
  self.assertEqual(ten['previous_root_epoch'],9);self.assertEqual(ten['new_root_epoch'],10)
  self.assertEqual(eleven['previous_root_epoch'],10);self.assertEqual(eleven['new_root_epoch'],11)
  for marker in (old,mid,eight,nine,ten):
   self.assertEqual(marker['calibration_credit_effect'],0)
   self.assertEqual(marker['fresh_science_effect'],'NONE');self.assertEqual(marker['runtime_effect'],'NONE')
  self.assertEqual(eleven['calibration_credit_effect'],0)
  self.assertEqual(eleven['calibration_streak_effect'],0)
  self.assertFalse(eleven['fresh_allowed'])
  self.assertIn('STRUCTURAL_BRANCH_STATUS_SINGLE_WRITER_RESTORED',eight['repair_scope'])
  self.assertIn('STRICT_FINITE_DUPLICATE_FREE_JSON',nine['repair_scope'])

 def test_epoch7_epoch8_epoch9_seeds_are_consumed_once_and_future_root_changes_need_new_seed(self):
  seeds=[load('config/root_epoch7_repair_seed_v25.json'),load('config/root_epoch8_status_writer_repair_seed_v25.json'),load('config/root_epoch9_integrity_repair_seed_v25.json')]
  expected_epochs=[7,8,9]
  for seed,epoch_number in zip(seeds,expected_epochs):
   self.assertTrue((ROOT/seed['one_shot_marker_path']).is_file())
   self.assertEqual(seed['target_root_epoch'],epoch_number)
   self.assertEqual(set(seed['required_root_candidate_paths']),set(seed['allowed_root_candidate_paths']))
  epoch=load('config/root_tcb_epoch_v25.json')
  self.assertEqual(epoch['root_change_rule'],'NO_AUTOMATED_BOOTSTRAP_SELF_AMENDMENT; FUTURE_ROOT_CHANGE_REQUIRES_A_NEW_INDEPENDENTLY_INSTALLED_SEED')

 def test_terminal_nonclean_receipts_are_evidence_not_calibration_pass(self):
  admission=(ROOT/'scripts/reconcile_v25_admission.py').read_text(encoding='utf-8')
  self.assertIn("TERMINAL_VERDICTS={'VERIFIED_COMPLETE','VERIFIED_WITH_QUARANTINES','INCOMPLETE','INVALID'}",admission)
  self.assertIn("if v.get('calibration_pass') is not False",admission)
  self.assertIn('diagnostic integration must force calibration pass false',admission)
  verifier=load('schemas/branch_verification.schema.json');integration=load('schemas/branch_integration.schema.json')
  self.assertIn('VERIFIED_WITH_QUARANTINES',verifier['properties']['verdict']['enum'])
  self.assertIn('VERIFIED_WITH_QUARANTINES',integration['properties']['verification_verdict']['enum'])

 def test_durable_bootstrap_rederivation_remains_bound(self):
  text=(ROOT/'scripts/reconcile_open_prs.py').read_text(encoding='utf-8')
  self.assertIn(DURABLE,text);self.assertIn('/actions/runs/',text)
  authority=load('config/admission_authority.json');bootstrap=load('config/authority_bootstrap_v25.json')
  self.assertEqual(authority['bootstrap_status_provenance'],DURABLE)
  self.assertEqual(bootstrap['bootstrap_success_consumption'],DURABLE)

 def test_diagnostic_replay_binds_current_pr_head_and_base(self):
  text=(ROOT/'scripts/diagnose_authority_bootstrap.py').read_text(encoding='utf-8')
  self.assertIn('os.environ["DIAGNOSED_HEAD_SHA"] = sha',text)
  self.assertIn('os.environ["DIAGNOSED_BASE_SHA"] = base_sha',text)

 def test_countable_control_v25_freezes_root11_and_historical_integrity_surface(self):
  control=load('config/countable_control_set_v25.json');paths=set(control['required_control_paths'])
  self.assertEqual(control['schema_version'],'PS-COUNTABLE-CONTROL-SET-2.5-26')
  required={'config/root_epoch9_integrity_repair_seed_v25.json','config/root_epoch9_integrity_repair_epoch_v25.json','scripts/reconcile_root_epoch9_integrity_repair_seed.py','.github/workflows/supernova-root-epoch9-integrity-repair-seed.yml','config/root_epoch10_scheduler_admission_seed_v25.json','config/root_epoch10_scheduler_admission_seed_amendment_v25.json','config/root_epoch10_scheduler_admission_epoch_v25.json','scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py','.github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml','config/root_epoch11_stageability_repair_seed_v25.json','config/root_epoch11_stageability_repair_seed_amendment_v25.json','config/root_epoch11_stageability_repair_epoch_v25.json','scripts/reconcile_root_epoch11_stageability_repair_seed.py','scripts/reconcile_root_epoch11_stageability_repair_seed_amendment.py','.github/workflows/supernova-root-epoch11-stageability-repair-seed.yml','.github/workflows/supernova-root-epoch11-stageability-repair-seed-amendment.yml','tests/test_root_epoch11_stageability_repair_seed_amendment.py','scripts/strict_json.py','tests/test_root_epoch9_integrity_repair.py','tests/test_strict_json_contract.py','tests/test_gen11_zero_credit_terminal_transition.py','scripts/reconcile_v25_admission.py','scripts/reconcile_open_prs.py','scripts/reconcile_authority_bootstrap.py','tests/test_structural_status_single_writer.py'}
  self.assertTrue(required.issubset(paths),sorted(required-paths))
  self.assertGreaterEqual(control['minimum_worker_liveness_window_minutes'],45)

if __name__=='__main__':unittest.main()
