import importlib.util, json, pathlib, unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/assert_validator_environment.py'
CONFIG=ROOT/'config/validator_environment_v25.json'
PLAN=ROOT/'plan/PLAN.json'
WORKFLOWS=[
 '.github/workflows/supernova-v25-admission.yml',
 '.github/workflows/supernova-authority-bootstrap.yml',
 '.github/workflows/supernova-bootstrap-completion-reconcile.yml',
 '.github/workflows/supernova-branch-reconciler.yml',
 '.github/workflows/supernova-liveness-monitor.yml',
]


def load_module():
 spec=importlib.util.spec_from_file_location('validator_environment_test',SCRIPT);m=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(m);return m


class ValidatorEnvironmentContractTests(unittest.TestCase):
 def setUp(self):self.mod=load_module();self.contract=json.loads(CONFIG.read_text())
 def test_frozen_contract_classifies_runtime_and_provenance(self):
  self.assertEqual(self.contract['runner_image'],'ubuntu-24.04')
  self.assertEqual(self.contract['runner_image_version'],'20260816.277.1')
  self.assertEqual(self.contract['python_version'],'3.13.15')
  self.assertEqual(self.contract['git_version'],'2.55.0')
  self.assertEqual(self.contract['enforced_runtime_fields'],['runner_image','python_version','git_version'])
  self.assertEqual(self.contract['provenance_only_fields'],['runner_image_version'])
  self.assertFalse(self.contract['enforced_runtime_drift_is_pass'])
  self.assertTrue(self.contract['provenance_only_drift_is_pass'])
  self.assertFalse(self.contract['missing_provenance_is_pass'])
 def test_exact_observation_passes(self):
  obs={k:self.contract[k] for k in ('runner_image','runner_image_version','python_version','git_version')}
  self.assertEqual(self.mod.errors(self.contract,obs),[])
  self.assertEqual(self.mod.provenance_drift(self.contract,obs),{})
 def test_each_enforced_runtime_drift_fails(self):
  base={k:self.contract[k] for k in ('runner_image','runner_image_version','python_version','git_version')}
  for key in self.contract['enforced_runtime_fields']:
   with self.subTest(key=key):
    x=dict(base);x[key]='WRONG';self.assertTrue(self.mod.errors(self.contract,x))
 def test_hosted_runner_build_rotation_is_recorded_not_rejected(self):
  obs={k:self.contract[k] for k in ('runner_image','runner_image_version','python_version','git_version')}
  obs['runner_image_version']='20260823.283.1'
  self.assertEqual(self.mod.errors(self.contract,obs),[])
  self.assertEqual(self.mod.provenance_drift(self.contract,obs),{
   'runner_image_version':{'reference':'20260816.277.1','observed':'20260823.283.1'}
  })
 def test_missing_observation_or_field_classification_drift_fails(self):
  obs={k:self.contract[k] for k in ('runner_image','runner_image_version','python_version','git_version')}
  for key in obs:
   with self.subTest(missing=key):
    x=dict(obs);x[key]='';self.assertTrue(self.mod.errors(self.contract,x))
  changed=dict(self.contract);changed['enforced_runtime_fields']=['runner_image']
  self.assertTrue(self.mod.errors(changed,obs))
  changed=dict(self.contract);changed['provenance_only_fields']=[]
  self.assertTrue(self.mod.errors(changed,obs))
 def test_plan_matches_runtime_provenance_separation(self):
  invariant=json.loads(PLAN.read_text())['control_plane_single_source_invariants']['validator_environment']
  self.assertIn('GITHUB_HOSTED_RUNNER_BUILD_VERSION_IS_REQUIRED_NON_GATING_PROVENANCE',invariant)
  self.assertIn('MISSING_PROVENANCE_FAILS_CLOSED',invariant)
  self.assertNotIn('FROZEN_RUNNER_IMAGE_IMAGE_VERSION',invariant)
 def test_github_env_normalization(self):
  with mock.patch.dict('os.environ',{'ImageOS':'ubuntu24','ImageVersion':'20260816.277.1','SUPERNOVA_PYTHON_VERSION':'3.13.15','SUPERNOVA_GIT_VERSION':'2.55.0'},clear=True):
   self.assertEqual(self.mod.observe(),{'runner_image':'ubuntu-24.04','runner_image_version':'20260816.277.1','python_version':'3.13.15','git_version':'2.55.0'})
 def test_all_changed_countable_or_privileged_workflows_assert_environment(self):
  for rel in WORKFLOWS:
   with self.subTest(path=rel):
    text=(ROOT/rel).read_text();self.assertIn('scripts/assert_validator_environment.py',text);self.assertIn('ubuntu-24.04',text);self.assertIn("3.13.15",text)

if __name__=='__main__':unittest.main()
