import copy
import json
import pathlib
import tempfile
import unittest

from jsonschema import Draft202012Validator
import scripts.validate_branch_bus_v251 as v


class LivenessContractTests(unittest.TestCase):
    def setUp(self):
        self.original_root = v.ROOT
        self.liveness_schema = json.loads((self.original_root / 'schemas/cohort_liveness_contract.schema.json').read_text())
        self.report_schema = json.loads((self.original_root / 'schemas/branch_report.schema.json').read_text())
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / 'schemas').mkdir(parents=True)
        (self.root / 'control').mkdir()
        (self.root / 'assignments').mkdir()
        (self.root / 'liveness').mkdir()
        (self.root / 'schemas/cohort_liveness_contract.schema.json').write_text(json.dumps(self.liveness_schema))
        self.co = {'calibration_countable': True, 'control_manifest_id': 'CTRL-C'}
        self.a = {
            'generation_seq': 8,
            'assignment_id': 'ASSIGN-C',
            'workers': {wid: {'worker_branch': f'ps/work/c/{wid}'} for wid in v.WORKERS},
        }
        self.cp = self.root / 'control/c.json'
        self.ap = self.root / 'assignments/c.json'
        self.cp.write_text(json.dumps(self.co, sort_keys=True))
        self.ap.write_text(json.dumps(self.a, sort_keys=True))
        v.ROOT = self.root

    def tearDown(self):
        v.ROOT = self.original_root
        self.tmp.cleanup()

    def contract(self):
        return {
            'schema_version': 'PS-COHORT-LIVENESS-2.5-2',
            'protocol_version': '2.5',
            'task_network_plan_id': v.PLAN,
            'cohort_id': 'c',
            'generation_seq': 8,
            'generation_root_sha': 'a' * 40,
            'control_manifest_id': 'CTRL-C',
            'control_manifest_git_identity': v.blob(self.cp),
            'assignment_id': 'ASSIGN-C',
            'assignment_git_identity': v.blob(self.ap),
            'lanes': [
                {
                    'lane_id': wid,
                    'branch': f'ps/work/c/{wid}',
                    'path': f'reports/c/{wid}.json',
                    'expected_window_start_utc': f'2026-08-21T08:{i:02d}:00Z',
                    'deadline_utc': f'2026-08-21T09:{i:02d}:00Z',
                    'eligible_before_deadline': True,
                }
                for i, wid in enumerate(v.WORKERS)
            ],
        }

    def write(self, contract):
        (self.root / 'liveness/c.json').write_text(json.dumps(contract))

    def errors(self, contract):
        self.write(contract)
        return v.liveness_contract_errors('c', self.co, self.a, self.cp, self.ap, 'a' * 40)

    def test_schema_has_no_self_referential_generation_head(self):
        self.assertNotIn('generation_head_sha', self.liveness_schema['required'])
        self.assertNotIn('generation_head_sha', self.liveness_schema['properties'])
        self.assertIn('generation_root_sha', self.liveness_schema['required'])

    def test_valid_contract_passes(self):
        self.assertEqual(self.errors(self.contract()), [])

    def test_wrong_root_fails(self):
        c = self.contract(); c['generation_root_sha'] = 'b' * 40
        self.assertTrue(any('generation_root_sha' in x for x in self.errors(c)))

    def test_wrong_control_or_assignment_identity_fails(self):
        c = self.contract(); c['control_manifest_git_identity'] = 'b' * 40
        self.assertTrue(any('control_manifest_git_identity' in x for x in self.errors(c)))
        c = self.contract(); c['assignment_git_identity'] = 'b' * 40
        self.assertTrue(any('assignment_git_identity' in x for x in self.errors(c)))

    def test_missing_extra_duplicate_lane_fails(self):
        c = self.contract(); c['lanes'] = c['lanes'][:-1]
        self.assertTrue(self.errors(c))
        c = self.contract(); c['lanes'].append(copy.deepcopy(c['lanes'][0]))
        c['lanes'][-1]['lane_id'] = 'MF01'
        self.assertTrue(any('duplicate liveness lane_id' in x or 'liveness schema' in x for x in self.errors(c)))

    def test_branch_path_and_window_mismatch_fail(self):
        c = self.contract(); c['lanes'][0]['branch'] = 'wrong'
        self.assertTrue(any('liveness branch mismatch' in x for x in self.errors(c)))
        c = self.contract(); c['lanes'][0]['path'] = 'wrong'
        self.assertTrue(any('liveness report path mismatch' in x for x in self.errors(c)))
        c = self.contract(); c['lanes'][0]['deadline_utc'] = c['lanes'][0]['expected_window_start_utc']
        self.assertTrue(any('deadline not after start' in x for x in self.errors(c)))


class ReportSemanticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((v.ROOT / 'schemas/branch_report.schema.json').read_text())
        cls.metric = Draft202012Validator(cls.schema['$defs']['metric_result'])
        cls.issue = Draft202012Validator(cls.schema['$defs']['issue_record'])

    def test_metric_missing_is_null_not_zero(self):
        good = {'metric_id':'m','status':'NOT_MEASURED','value':None,'unit':None,'reason':'not observed','evidence_refs':[]}
        self.assertEqual(list(self.metric.iter_errors(good)), [])
        bad = dict(good, value=0)
        self.assertTrue(list(self.metric.iter_errors(bad)))
        bad = dict(good, status='UNKNOWN', value=1)
        self.assertTrue(list(self.metric.iter_errors(bad)))

    def test_measured_requires_numeric_value(self):
        good = {'metric_id':'m','status':'MEASURED','value':1.5,'unit':'score','reason':'measured','evidence_refs':['r']}
        self.assertEqual(list(self.metric.iter_errors(good)), [])
        bad = dict(good, value=None)
        self.assertTrue(list(self.metric.iter_errors(bad)))

    def test_issue_record_is_closed_and_required(self):
        good = {
            'issue_id':'X-1','severity':'HIGH','component':'schema','status':'FIX_NOW_V25',
            'evidence_refs':['ref'],'blocker':'gap','proposed_fix_or_falsifier':'fix','required_test':'negative',
            'owner':'BIL00','authoritative_control_change':True,'next_action':'repair'
        }
        self.assertEqual(list(self.issue.iter_errors(good)), [])
        missing = dict(good); missing.pop('required_test')
        self.assertTrue(list(self.issue.iter_errors(missing)))
        unknown = dict(good, self_attested_pass=True)
        self.assertTrue(list(self.issue.iter_errors(unknown)))

    def test_duplicate_issue_ids_and_untyped_empty_ledger_fail(self):
        row = {'issue_id':'X-1'}
        self.assertTrue(v.issue_ledger_errors({'issue_ledger':[row, dict(row)], 'executive_status':'BLOCKED'}))
        self.assertTrue(v.issue_ledger_errors({'issue_ledger':[], 'executive_status':'PASS'}))
        self.assertEqual(v.issue_ledger_errors({'issue_ledger':[], 'executive_status':'ZERO_DELTA'}), [])


if __name__ == '__main__':
    unittest.main()
