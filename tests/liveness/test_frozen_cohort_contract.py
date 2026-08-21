import hashlib,json,pathlib,tempfile,unittest
from scripts.liveness_contract_guard import validate
ROOT=pathlib.Path(__file__).resolve().parents[2]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
WORKERS=['MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01']
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,separators=(',',':'))+'\n')
def blob(p):
 b=p.read_bytes();return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
class FrozenLivenessContractTests(unittest.TestCase):
 def fixture(self):
  t=pathlib.Path(tempfile.mkdtemp());(t/'schemas').mkdir();(t/'schemas/cohort_liveness_contract.schema.json').write_text((ROOT/'schemas/cohort_liveness_contract.schema.json').read_text())
  cohort='CAL-X';root='a'*40
  c={'control_manifest_id':'CTRL-X','cohort_id':cohort,'generation_seq':8,'control_release_commit_sha':root}
  a={'assignment_id':'ASSIGN-X','cohort_id':cohort,'generation_seq':8,'generation_root_sha':root,'workers':{w:{'worker_branch':f'ps/work/{cohort}/{w}'} for w in WORKERS}}
  cp=t/f'control/{cohort}.json';ap=t/f'assignments/{cohort}.json';write(cp,c);write(ap,a)
  l={'schema_version':'PS-COHORT-LIVENESS-2.5-2','protocol_version':'2.5','task_network_plan_id':PLAN,'cohort_id':cohort,'generation_seq':8,'generation_root_sha':root,'control_manifest_id':'CTRL-X','control_manifest_git_identity':blob(cp),'assignment_id':'ASSIGN-X','assignment_git_identity':blob(ap),'lanes':[{'lane_id':w,'branch':f'ps/work/{cohort}/{w}','path':f'reports/{cohort}/{w}.json','expected_window_start_utc':'2026-08-21T08:00:00Z','deadline_utc':'2026-08-21T09:00:00Z','eligible_before_deadline':True} for w in WORKERS]}
  write(t/f'liveness/{cohort}.json',l);return t,cohort,l
 def test_exact_contract_passes(self):
  t,c,_=self.fixture();self.assertEqual(validate(t,c),[])
 def test_no_generation_head_self_reference(self):
  schema=json.loads((ROOT/'schemas/cohort_liveness_contract.schema.json').read_text());self.assertNotIn('generation_head_sha',schema['properties'])
 def test_wrong_root_fails(self):
  t,c,l=self.fixture();l['generation_root_sha']='b'*40;write(t/f'liveness/{c}.json',l);self.assertTrue(validate(t,c))
 def test_wrong_assignment_binding_fails(self):
  t,c,l=self.fixture();l['assignment_git_identity']='b'*40;write(t/f'liveness/{c}.json',l);self.assertTrue(validate(t,c))
 def test_missing_duplicate_or_wrong_lane_fails(self):
  for mutate in ('missing','duplicate','path'):
   t,c,l=self.fixture()
   if mutate=='missing':l['lanes']=l['lanes'][:-1]
   elif mutate=='duplicate':l['lanes'][-1]=dict(l['lanes'][0])
   else:l['lanes'][0]['path']='wrong'
   write(t/f'liveness/{c}.json',l);self.assertTrue(validate(t,c),mutate)
 def test_bad_window_fails(self):
  t,c,l=self.fixture();l['lanes'][0]['deadline_utc']=l['lanes'][0]['expected_window_start_utc'];write(t/f'liveness/{c}.json',l);self.assertTrue(validate(t,c))
if __name__=='__main__':unittest.main()
