import math
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import strict_json  # noqa: E402


class StrictJsonContractTests(unittest.TestCase):
    def test_rejects_nonfinite_constants(self):
        for raw in ('{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_json.loads(raw)

    def test_rejects_duplicate_object_keys(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON object key forbidden'):
            strict_json.loads('{"x":1,"x":2}')

    def test_encoder_rejects_nonfinite_numbers(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                strict_json.dumps({'x': value})

    def test_canonical_and_pretty_serialization_are_deterministic(self):
        obj = {'b': 2, 'a': 1}
        self.assertEqual(strict_json.canonical_dumps(obj), '{"a":1,"b":2}')
        self.assertEqual(strict_json.pretty_dumps(obj), '{\n  "a": 1,\n  "b": 2\n}\n')
        self.assertFalse(any(math.isnan(v) for v in obj.values() if isinstance(v, float)))

    def test_active_authority_parsers_use_strict_json(self):
        required = (
            'scripts/validate_bus.py',
            'scripts/validate_branch_bus_v251.py',
            'scripts/reconcile_open_prs.py',
            'scripts/reconcile_v25_admission.py',
            'scripts/reconcile_branch_statuses.py',
            'scripts/liveness_contract_guard.py',
            'scripts/check_lane_liveness.py',
        )
        for path in required:
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding='utf-8')
                self.assertIn('strict_json', text)


if __name__ == '__main__':
    unittest.main()
