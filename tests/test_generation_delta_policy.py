import json, pathlib, unittest
from scripts.generation_delta_guard import expected_paths, validate_names

ROOT=pathlib.Path(__file__).resolve().parents[1]

class GenerationDeltaPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy=json.loads((ROOT/'config/generation_delta_policy_v25.json').read_text())
        self.cohort='CAL-TEST'

    def test_countable_exact_four_passes(self):
        names=[f'control/{self.cohort}.json',f'assignments/{self.cohort}.json',f'liveness/{self.cohort}.json',f'scheduler/{self.cohort}.json']
        self.assertEqual(validate_names(names,self.cohort,True,self.policy),[])

    def test_countable_missing_liveness_fails(self):
        names=[f'control/{self.cohort}.json',f'assignments/{self.cohort}.json',f'scheduler/{self.cohort}.json']
        self.assertTrue(validate_names(names,self.cohort,True,self.policy))

    def test_countable_missing_scheduler_manifest_fails(self):
        names=[f'control/{self.cohort}.json',f'assignments/{self.cohort}.json',f'liveness/{self.cohort}.json']
        self.assertTrue(validate_names(names,self.cohort,True,self.policy))

    def test_countable_extra_fifth_path_fails(self):
        names=expected_paths(self.cohort,True,self.policy)+['README.md']
        self.assertTrue(validate_names(names,self.cohort,True,self.policy))

    def test_wrong_cohort_path_fails(self):
        names=[f'control/{self.cohort}.json',f'assignments/{self.cohort}.json','liveness/OTHER.json',f'scheduler/{self.cohort}.json']
        self.assertTrue(validate_names(names,self.cohort,True,self.policy))

    def test_noncountable_exact_two_passes(self):
        names=[f'control/{self.cohort}.json',f'assignments/{self.cohort}.json']
        self.assertEqual(validate_names(names,self.cohort,False,self.policy),[])

    def test_machine_policy_freezes_scheduler_manifest(self):
        self.assertEqual(self.policy['countable']['exact_cardinality'],4)
        self.assertEqual(self.policy['non_countable']['exact_cardinality'],2)
        self.assertIn('scheduler/{cohort}.json',self.policy['countable']['exact_path_templates'])
        self.assertTrue(self.policy['countable']['scheduler_admission_required_before_promotion'])
        self.assertEqual(self.policy['stage_admit_promote'],'THREE_DISTINCT_TRANSACTIONS')

if __name__=='__main__': unittest.main()
