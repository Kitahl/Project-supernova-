import json, pathlib, unittest
from scripts.generation_delta_guard import expected_paths, validate_names

ROOT=pathlib.Path(__file__).resolve().parents[1]

# Touch note: this test file intentionally participates in the authority-change
# regression surface so a fresh pull_request synchronize event re-runs the
# accepted-main bootstrap against the final consolidated repair head.
class GenerationDeltaPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy=json.loads((ROOT/'config/generation_delta_policy_v25.json').read_text())
        self.cohort='CAL-TEST'

    def test_countable_exact_three_passes(self):
        names=[f'control/{self.cohort}.json',f'assignments/{self.cohort}.json',f'liveness/{self.cohort}.json']
        self.assertEqual(validate_names(names,self.cohort,True,self.policy),[])

    def test_countable_missing_liveness_fails(self):
        names=[f'control/{self.cohort}.json',f'assignments/{self.cohort}.json']
        self.assertTrue(validate_names(names,self.cohort,True,self.policy))

    def test_countable_extra_fourth_path_fails(self):
        names=expected_paths(self.cohort,True,self.policy)+['README.md']
        self.assertTrue(validate_names(names,self.cohort,True,self.policy))

    def test_wrong_cohort_path_fails(self):
        names=[f'control/{self.cohort}.json',f'assignments/{self.cohort}.json','liveness/OTHER.json']
        self.assertTrue(validate_names(names,self.cohort,True,self.policy))

    def test_noncountable_exact_two_passes(self):
        names=[f'control/{self.cohort}.json',f'assignments/{self.cohort}.json']
        self.assertEqual(validate_names(names,self.cohort,False,self.policy),[])

    def test_protocol_and_machine_policy_agree(self):
        text=(ROOT/'BRANCH_PROTOCOL.md').read_text()
        self.assertIn('config/generation_delta_policy_v25.json',text)
        self.assertIn('control/<C>.json`, `assignments/<C>.json`, and `liveness/<C>.json',text)
        self.assertEqual(self.policy['countable']['exact_cardinality'],3)
        self.assertEqual(self.policy['non_countable']['exact_cardinality'],2)

if __name__=='__main__': unittest.main()
