import json, pathlib, unittest
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[2]

class VerifierAssuranceTests(unittest.TestCase):
    def schema(self): return json.loads((ROOT/'schemas/verifier_assurance.schema.json').read_text())
    def branch_verification_schema(self): return json.loads((ROOT/'schemas/branch_verification.schema.json').read_text())
    def embedded_schema(self): return self.branch_verification_schema()['$defs']['verifier_assurance']
    def base(self): return {"checker_id":"lean-replay","exact_version_or_commit":"abc123","assurance_type":"SAME_KERNEL_FRESH_REPLAY","implementation_family":"lean-kernel","shared_tcb":["lean-kernel"],"statement_identity_scope":"challenge identity","independence_status":"SHARED_KERNEL","known_advisories":[],"exploit_regression_digest":"sha256:x","mutation_fuzz_digest":"sha256:y","last_security_review":"2026-08-19","scope":"fresh-environment replay"}

    def test_same_kernel_replay_is_not_external(self):
        o=self.base(); self.assertEqual(list(Draft202012Validator(self.schema()).iter_errors(o)),[])
        self.assertEqual(o['assurance_type'],'SAME_KERNEL_FRESH_REPLAY')
        self.assertNotEqual(o['assurance_type'],'EXTERNAL_KERNEL_IMPLEMENTATION')

    def test_default_no_independence_claim_is_valid(self):
        o=self.base(); o['independence_status']='NO_INDEPENDENCE_CLAIM'
        self.assertEqual(list(Draft202012Validator(self.schema()).iter_errors(o)),[])

    def test_branch_verification_embeds_closed_assurance_contract(self):
        o=self.base()
        self.assertEqual(list(Draft202012Validator(self.embedded_schema()).iter_errors(o)), [])
        embedded = self.embedded_schema()
        self.assertFalse(embedded['additionalProperties'])
        for required in self.schema()['required']:
            self.assertIn(required, embedded['required'])

    def test_branch_verification_rejects_malformed_assurance_record(self):
        malformed=self.base(); malformed.pop('independence_status')
        self.assertTrue(list(Draft202012Validator(self.embedded_schema()).iter_errors(malformed)))
        extra=self.base(); extra['self_reported_confidence']=0.99
        self.assertTrue(list(Draft202012Validator(self.embedded_schema()).iter_errors(extra)))

    def test_branch_verification_items_are_not_generic_objects(self):
        branch=self.branch_verification_schema()
        items=branch['properties']['verifier_assurance_records']['items']
        self.assertEqual(items, {'$ref':'#/$defs/verifier_assurance'})
        self.assertNotEqual(items, {'type':'object'})

if __name__=='__main__': unittest.main()
