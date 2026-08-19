from __future__ import annotations
import copy, hashlib, hmac, json, pathlib, unittest
from scripts.validate_branch_bus_v251 import execution_mode_errors

ROOT = pathlib.Path(__file__).resolve().parents[2]

def canonical_payload(report: dict) -> bytes:
    x = copy.deepcopy(report)
    x.pop('worker_auth_proof', None)
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

def sign(report: dict, secret: bytes) -> str:
    return hmac.new(secret, canonical_payload(report), hashlib.sha256).hexdigest()

class T0AuthAndModeTests(unittest.TestCase):
    def test_auth_metadata_is_hmac2(self):
        auth = json.loads((ROOT/'config'/'worker_auth.json').read_text())
        self.assertEqual(auth['scheme'], 'PS-HMAC-SHA256-CANONICAL-REPORT-2')
        self.assertTrue(auth['raw_secrets_forbidden_in_repo'])

    def test_any_signed_field_mutation_invalidates_proof(self):
        secret = bytes.fromhex('11' * 32)
        report = {
            'session_header': {'execution_mode': 'SAFE_REPLAY_ONLY', 'goal': 'g'},
            'mode': 'SAFE_REPLAY_ONLY',
            'task_network_plan_id': 'p',
            'issue_ledger': [{'issue_id': 'I-1', 'status': 'OPEN'}],
            'cost_ledger': {'benchmark_executions': 0},
            'worker_auth_proof': ''
        }
        report['worker_auth_proof'] = sign(report, secret)
        self.assertTrue(hmac.compare_digest(report['worker_auth_proof'], sign(report, secret)))
        mutations = [
            ('identity', lambda r: r.__setitem__('task_network_plan_id', 'q')),
            ('execution mode', lambda r: r['session_header'].__setitem__('execution_mode', 'FRESH_EXECUTION')),
            ('report mode', lambda r: r.__setitem__('mode', 'FRESH_EXECUTION')),
            ('issue', lambda r: r['issue_ledger'][0].__setitem__('status', 'CLOSED')),
            ('cost', lambda r: r['cost_ledger'].__setitem__('benchmark_executions', 1)),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                changed = copy.deepcopy(report)
                mutate(changed)
                self.assertFalse(hmac.compare_digest(report['worker_auth_proof'], sign(changed, secret)))

    def test_execution_mode_match_passes(self):
        report = {'session_header': {'execution_mode': 'SAFE_REPLAY_ONLY'}, 'mode': 'SAFE_REPLAY_ONLY'}
        assignment = {'network_mode': 'GITHUB_BRANCH_CALIBRATION'}
        self.assertEqual(execution_mode_errors(report, assignment), [])

    def test_execution_mode_mismatch_fails(self):
        report = {'session_header': {'execution_mode': 'SAFE_REPLAY_ONLY'}, 'mode': 'FRESH_EXECUTION'}
        assignment = {'network_mode': 'GITHUB_BRANCH_CALIBRATION'}
        errors = execution_mode_errors(report, assignment)
        self.assertIn('session_header.execution_mode != report.mode', errors)
        self.assertIn('calibration report mode != SAFE_REPLAY_ONLY', errors)

    def test_calibration_header_cannot_claim_fresh(self):
        report = {'session_header': {'execution_mode': 'FRESH_EXECUTION'}, 'mode': 'FRESH_EXECUTION'}
        assignment = {'network_mode': 'GITHUB_BRANCH_CALIBRATION'}
        errors = execution_mode_errors(report, assignment)
        self.assertIn('calibration session execution_mode != SAFE_REPLAY_ONLY', errors)
        self.assertIn('calibration report mode != SAFE_REPLAY_ONLY', errors)

if __name__ == '__main__':
    unittest.main()
