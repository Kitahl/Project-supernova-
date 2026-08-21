import copy,json,pathlib,unittest
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]

def load(path):return json.loads((ROOT/path).read_text())

class Gen9ZeroCreditRepairTests(unittest.TestCase):
 def test_assignment_fresh_scope_is_required_when_fresh_allowed(self):
  full=load('schemas/assignment.schema.json');schema=copy.deepcopy(full['$defs']['worker']);schema['$defs']={'fresh_scope':full['$defs']['fresh_scope']};v=Draft202012Validator(schema)
  base={'worker_branch':'b','fresh_allowed':False,'role':'r','goal':'g','target_program':'MASTERMIND','visibility_token':'a'*32,'opaque_evidence_ids':[],'private_manifest_id':None,'private_manifest_git_identity':None,'constraints':[]}
  self.assertEqual(list(v.iter_errors(base)),[])
  fresh=dict(base);fresh.update(fresh_allowed=True,private_manifest_id='M',private_manifest_git_identity='b'*40,fresh_scope={'pool':'TRAIN','stage':'STAGE0_LOOP','purpose_id':'P'})
  self.assertEqual(list(v.iter_errors(fresh)),[])
  bad=dict(fresh);bad.pop('fresh_scope');self.assertTrue(list(v.iter_errors(bad)))
  bad=dict(fresh);bad['private_manifest_id']=None;self.assertTrue(list(v.iter_errors(bad)))

 def test_verifier_assurance_empty_requires_explicit_transport_only_disposition(self):
  schema=load('schemas/branch_verification.schema.json');props=schema['properties']
  self.assertIn('verifier_assurance_disposition',schema['required']);self.assertIn('RUN_TIMING_UNKNOWN',schema['$defs']['liveness']['properties']['receipt_status']['enum']);self.assertIn('NOT_APPLICABLE_TRANSPORT_ONLY',props['verifier_assurance_disposition']['enum']);self.assertIn('ASSURANCE_RECORDS_PRESENT',props['verifier_assurance_disposition']['enum'])

 def test_issue_exact_failure_and_required_test_are_mandatory(self):
  issue=load('schemas/branch_report.schema.json')['$defs']['issue_record'];self.assertIn('exact_failure',issue['required']);self.assertIn('required_test',issue['required'])

 def test_mm03_payload_is_closed(self):
  schema=load('schemas/branch_report.schema.json');rule=[r for r in schema['allOf'] if r.get('if',{}).get('properties',{}).get('worker_id',{}).get('const')=='MM03'][0];self.assertFalse(rule['then']['properties']['role_payload']['additionalProperties'])

 def test_report_transport_contract_is_required(self):
  schema=load('schemas/branch_report.schema.json');self.assertIn('transport_serialization',schema['required']);self.assertEqual(schema['properties']['transport_serialization']['const'],'PRETTY_SORTED_UTF8_JSON_V1')

if __name__=='__main__':unittest.main()
