import importlib.util,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]

def rest_module():
 p=ROOT/'scripts/reconcile_branch_rest.py';s=importlib.util.spec_from_file_location('rest_diag_test',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class StructuralStatusSingleWriterTests(unittest.TestCase):
 def test_rest_cannot_publish_authoritative_generation_or_worker_context(self):
  rest=(ROOT/'scripts/reconcile_branch_rest.py').read_text()
  self.assertNotIn("'supernova/branch-generation'",rest);self.assertNotIn('"supernova/branch-generation"',rest)
  self.assertNotIn("'supernova/branch-worker'",rest);self.assertNotIn('"supernova/branch-worker"',rest)
  self.assertIn('supernova/rest-branch-generation-diagnostic',rest);self.assertIn('supernova/rest-branch-worker-diagnostic',rest)

 def test_primary_structural_reconciler_owns_required_contexts(self):
  primary=(ROOT/'scripts/reconcile_branch_statuses.py').read_text()
  self.assertIn('supernova/branch-generation',primary);self.assertIn('supernova/branch-worker',primary)
  workflows=list((ROOT/'.github/workflows').glob('*.yml'))+list((ROOT/'.github/workflows').glob('*.yaml'))
  primary_invokers=[p.name for p in workflows if 'reconcile_branch_statuses.py' in p.read_text()]
  self.assertEqual(primary_invokers,['supernova-branch-reconciler.yml'])

 def test_countable_generation_rest_diagnostic_expects_control_assignment_liveness_exactly(self):
  m=rest_module();state={'active_control_manifest_path':'control/C.json','active_assignment_path':'assignments/C.json','active_cohort_id':'C','calibration_countable_current':True};control={}
  self.assertEqual(m.expected_generation_paths(state,control),{'control/C.json','assignments/C.json','liveness/C.json'})
  state['calibration_countable_current']=False
  self.assertEqual(m.expected_generation_paths(state,control),{'control/C.json','assignments/C.json'})

 def test_rest_workflow_names_diagnostics_and_never_mentions_required_structural_contexts(self):
  text=(ROOT/'.github/workflows/supernova-rest-branch-reconciler.yml').read_text()
  self.assertIn('REST Diagnostics + Admission Reconciler',text);self.assertIn('reconcile_branch_rest.py',text);self.assertIn('reconcile_v25_admission.py',text)
  self.assertNotIn('supernova/branch-generation',text);self.assertNotIn('supernova/branch-worker',text)

if __name__=='__main__':unittest.main()
