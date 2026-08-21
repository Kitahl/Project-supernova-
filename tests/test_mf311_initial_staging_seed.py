import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('mf311_stage_seed',ROOT/'scripts/reconcile_mf311_initial_staging_seed.py')
MOD=importlib.util.module_from_spec(SPEC);assert SPEC.loader is not None;SPEC.loader.exec_module(MOD)

class MF311InitialStagingSeedTests(unittest.TestCase):
    def test_seed_is_exact_one_shot_and_zero_credit(self):
        policy=json.loads((ROOT/'config/mf311_initial_staging_seed_v25.json').read_text())
        self.assertEqual(policy['status'],'ONE_SHOT_INDEPENDENT_SEED')
        self.assertEqual(policy['candidate_cohort_id'],MOD.STAGE)
        self.assertEqual(policy['candidate_generation_seq'],8)
        self.assertFalse(policy['candidate_countable'])
        self.assertEqual(policy['candidate_network_mode'],'BENCHMARK_DISCOVERY_WAIT')
        self.assertEqual(policy['math_foundry_sha256'],MOD.MF311)
        self.assertEqual(policy['mastermind_sha256'],MOD.MM4410)
        self.assertEqual(policy['runtime_receipt_path'],MOD.RECEIPT)
        self.assertEqual(set(policy['required_candidate_paths']),MOD.EXPECTED_PATHS)
        self.assertEqual(policy['scientific_credit'],0)
        self.assertEqual(policy['calibration_credit'],0)
        self.assertEqual(policy['fresh_evidence_credit'],0)
        self.assertFalse(policy['seed_may_merge'])
        self.assertFalse(policy['seed_may_bypass'])

    def test_exact_gen7_supersession_shape_only(self):
        good={
          'schema_version':'PS-COHORT-SUPERSESSION-1','cohort_id':MOD.OLD_COHORT,'generation_head_sha':MOD.OLD_G,
          'state_blob_sha':MOD.OLD_STATE_BLOB,'disposition':'INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS',
          'calibration_credit':0,'fresh_evidence_consumed':False,'replacement_generation_seq':8,'replacement_countable':False}
        self.assertTrue(MOD.exact_supersession(good))
        for key,value in [('calibration_credit',1),('fresh_evidence_consumed',True),('replacement_countable',True),('generation_head_sha','0'*40)]:
            bad=dict(good);bad[key]=value
            self.assertFalse(MOD.exact_supersession(bad),key)

    def test_required_candidate_path_set_contains_no_wildcard_authority(self):
        self.assertEqual(len(MOD.EXPECTED_PATHS),7)
        self.assertIn('state/CURRENT.json',MOD.EXPECTED_PATHS)
        self.assertIn('config/substrate_epoch_v25.json',MOD.EXPECTED_PATHS)
        self.assertIn(MOD.RECEIPT,MOD.EXPECTED_PATHS)
        self.assertNotIn('scripts/reconcile_open_prs.py',MOD.EXPECTED_PATHS)
        self.assertFalse(any(p.startswith('.github/workflows/') for p in MOD.EXPECTED_PATHS))

    def test_workflow_is_candidate_read_only_then_trusted_status_only(self):
        text=(ROOT/'.github/workflows/supernova-mf311-initial-staging-seed.yml').read_text()
        self.assertIn("startsWith(github.event.pull_request.head.ref, 'mf311-staging/')",text)
        self.assertIn('persist-credentials: false',text)
        self.assertIn('GITHUB_TOKEN: ""',text)
        self.assertIn('statuses: write',text)
        self.assertIn('reconcile_mf311_initial_staging_seed.py',text)
        self.assertNotIn('gh pr merge',text)
        self.assertNotIn('--admin',text)

if __name__=='__main__':unittest.main()
