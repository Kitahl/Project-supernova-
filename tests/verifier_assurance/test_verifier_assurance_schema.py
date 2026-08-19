import json, pathlib, unittest
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[2]

class VerifierAssuranceTests(unittest.TestCase):
    def schema(self): return json.loads((ROOT/'schemas/verifier_assurance.schema.json').read_text())
    def base(self): return {"checker_id":"lean-replay","exact_version_or_commit":"abc123","assurance_type":"SAME_KERNEL_FRESH_REPLAY","implementation_family":"lean-kernel","shared_tcb":["lean-kernel"],"statement_identity_scope":"challenge identity","independence_status":"SHARED_KERNEL","known_advisories":[],"exploit_regression_digest":"sha256:x","mutation_fuzz_digest":"sha256:y","last_security_review":"2026-08-19","scope":"fresh-environment replay"}

    def test_same_kernel_replay_is_not_external(self):
        o=self.base(); self.assertEqual(list(Draft202012Validator(self.schema()).iter_errors(o)),[])
        self.assertEqual(o['assurance_type'],'SAME_KERNEL_FRESH_REPLAY')
        self.assertNotEqual(o['assurance_type'],'EXTERNAL_KERNEL_IMPLEMENTATION')

    def test_default_no_independence_claim_is_valid(self):
        o=self.base(); o['independence_status']='NO_INDEPENDENCE_CLAIM'
        self.assertEqual(list(Draft202012Validator(self.schema()).iter_errors(o)),[])

if __name__=='__main__': unittest.main()
