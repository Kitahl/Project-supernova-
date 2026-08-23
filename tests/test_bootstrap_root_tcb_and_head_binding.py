import importlib.util
import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
BOOT=ROOT/'scripts/reconcile_authority_bootstrap.py'
WF=ROOT/'.github/workflows/supernova-authority-bootstrap.yml'

def load_bootstrap_module():
 spec=importlib.util.spec_from_file_location('bootstrap_root_tcb_test',BOOT);m=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(m);return m

class BootstrapRootTcbAndHeadBindingTests(unittest.TestCase):
 def test_transitive_write_capable_admission_tcb_is_root_protected(self):
  mod=load_bootstrap_module();roots=mod.bootstrap_root_paths(ROOT)
  expected={
   'config/admission_authority.json','config/authority_bootstrap_v25.json','config/root_rotation_seed_v25.json','config/root_tcb_epoch_v25.json',
   'config/root_epoch9_integrity_repair_seed_v25.json','config/root_epoch9_integrity_repair_epoch_v25.json',
   'config/root_epoch10_scheduler_admission_seed_v25.json','config/root_epoch10_scheduler_admission_epoch_v25.json','config/validator_environment_v25.json','config/generation_delta_policy_v25.json',
   'schemas/scheduler_manifest.schema.json','schemas/preactivation_receipt.schema.json','schemas/scheduler_admission.schema.json',
   'scripts/assert_validator_environment.py','scripts/strict_json.py','scripts/generation_delta_guard.py','scripts/scheduler_admission_guard.py','scripts/reconcile_authority_bootstrap.py','scripts/reconcile_open_prs.py','scripts/reconcile_root_epoch10_scheduler_admission_seed.py','scripts/reconcile_branch_statuses.py','scripts/check_lane_liveness.py','scripts/validate_bus.py','scripts/parent_lineage_guard.py','scripts/transition_guard.py',
   '.github/workflows/supernova-authority-bootstrap.yml','.github/workflows/supernova-bootstrap-completion-reconcile.yml','.github/workflows/supernova-pr-target-admission.yml','.github/workflows/supernova-comment-admission.yml','.github/workflows/supernova-open-pr-reconciler.yml','.github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml','.github/workflows/supernova-branch-reconciler.yml','.github/workflows/supernova-liveness-monitor.yml','requirements-validation.lock'
  }
  self.assertTrue(expected.issubset(roots),sorted(expected-roots))

 def test_each_privileged_scheduler_class_is_rejected_as_root_drift(self):
  mod=load_bootstrap_module()
  for path in ('scripts/reconcile_open_prs.py','scripts/reconcile_authority_bootstrap.py','scripts/assert_validator_environment.py','scripts/strict_json.py','scripts/reconcile_root_epoch10_scheduler_admission_seed.py','scripts/scheduler_admission_guard.py','config/root_epoch10_scheduler_admission_seed_v25.json','config/root_epoch10_scheduler_admission_epoch_v25.json','schemas/scheduler_manifest.schema.json','schemas/preactivation_receipt.schema.json','schemas/scheduler_admission.schema.json','config/validator_environment_v25.json','config/generation_delta_policy_v25.json','.github/workflows/supernova-pr-target-admission.yml','.github/workflows/supernova-bootstrap-completion-reconcile.yml','.github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml','requirements-validation.lock'):
   with self.subTest(path=path):
    e=mod.bootstrap_invariant_errors(ROOT,ROOT,[path]);self.assertTrue(any('bootstrap root self-modification' in x for x in e),e)

 def test_non_tcb_support_path_is_not_rejected_as_root_drift(self):
  self.assertNotIn('docs/PROJECT_SUPERNOVA_REV5_CANDIDATE.md',load_bootstrap_module().bootstrap_root_paths(ROOT))

 def test_diagnostic_binding_accepts_only_exact_head_and_base(self):
  mod=load_bootstrap_module();a='a'*40;b='b'*40;c='c'*40;pr={'head':{'sha':a},'base':{'sha':b}}
  self.assertEqual(mod.diagnostic_binding_errors(pr,a,b),[])
  self.assertIn('diagnosed head SHA no longer matches current PR head',mod.diagnostic_binding_errors(pr,c,b))
  self.assertIn('diagnosed base SHA no longer matches current PR base',mod.diagnostic_binding_errors(pr,a,c))

 def test_epoch10_policy_is_current_and_epoch9_is_predecessor(self):
  mod=load_bootstrap_module();self.assertEqual(mod.DURABLE_BOOTSTRAP_PROVENANCE,'PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED')
  admission=json.loads((ROOT/'config/admission_authority.json').read_text());bootstrap=json.loads((ROOT/'config/authority_bootstrap_v25.json').read_text());epoch=json.loads((ROOT/'config/root_tcb_epoch_v25.json').read_text())
  self.assertEqual(admission['root_tcb_epoch'],10);self.assertEqual(bootstrap['root_tcb_epoch_required'],10);self.assertEqual(epoch['epoch'],10)
  self.assertEqual(epoch['previous_epoch_blob'],'9a45b2098cd5870b53f9faa92e52409fa3204c81')
  self.assertEqual(epoch['root_epoch9_integrity_repair_marker'],'config/root_epoch9_integrity_repair_epoch_v25.json')
  self.assertEqual(epoch['root_epoch10_scheduler_admission_marker'],'config/root_epoch10_scheduler_admission_epoch_v25.json')
  self.assertEqual(epoch['root_epoch10_scheduler_admission_seed_install_commit_sha'],'7bc97d2bed9fb285feb2e9ae1c31fb4331919d00')
  self.assertEqual(admission['scheduler_admission_guard'],'scripts/scheduler_admission_guard.py')
  self.assertEqual(admission['bootstrap_status_provenance'],mod.DURABLE_BOOTSTRAP_PROVENANCE)
  self.assertEqual(bootstrap['bootstrap_success_consumption'],mod.DURABLE_BOOTSTRAP_PROVENANCE)

 def test_privileged_workflow_passes_immutable_event_head_base_run_and_environment(self):
  text=WF.read_text()
  self.assertIn('DIAGNOSED_HEAD_SHA: ${{ github.event.pull_request.head.sha }}',text)
  self.assertIn('DIAGNOSED_BASE_SHA: ${{ github.event.pull_request.base.sha }}',text)
  self.assertIn('GITHUB_RUN_ID: ${{ github.run_id }}',text)
  self.assertIn('CANDIDATE_DIAGNOSTICS_RESULT: ${{ needs.candidate-diagnostics.result }}',text)
  self.assertIn('scripts/assert_validator_environment.py',text)
  self.assertIn('cancel-in-progress: false',text)
  self.assertNotIn('run: cd trusted && python3 scripts/reconcile_open_prs.py',text)

if __name__=='__main__':unittest.main()
