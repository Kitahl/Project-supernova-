import importlib.util,json,pathlib,subprocess,tempfile,unittest
SCRIPT=pathlib.Path(__file__).resolve().parents[1]/"scripts"/"parent_lineage_guard.py";S=importlib.util.spec_from_file_location("p",SCRIPT);p=importlib.util.module_from_spec(S);S.loader.exec_module(p)
def git(r,*a):return subprocess.run(["git","-C",str(r),*a],check=True,text=True,stdout=subprocess.PIPE).stdout.strip()
def w(q,o):q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(o))
class T(unittest.TestCase):
 def setUp(self):
  self.x=tempfile.TemporaryDirectory();self.r=pathlib.Path(self.x.name);git(self.r,"init");git(self.r,"config","user.email","x@y");git(self.r,"config","user.name","x")
  self.base={"generation_seq":1,"active_cohort_id":"A","superseded_cohorts":[],"base_runtime_state_id":"r","runtime_state_id":"r","foundry_sha256":"f","mastermind_sha256":"m","actual_runtime_plan_id":"p","canonical_bus_repo":"R","private_vault_repo":"V"};w(self.r/"state/CURRENT.json",self.base);git(self.r,"add",".");git(self.r,"commit","-m","p");self.blob=git(self.r,"rev-parse","HEAD:state/CURRENT.json")
 def tearDown(self):self.x.cleanup()
 def make(self,parent=None,g=2):
  s=dict(self.base,generation_seq=g,active_cohort_id="B",active_parent_state_git_identity=parent or self.blob,superseded_cohorts=["A"],active_control_manifest_path="control/B.json",active_assignment_path="assignments/B.json");w(self.r/"state/CURRENT.json",s);w(self.r/"control/B.json",{"parent_state_git_identity":s["active_parent_state_git_identity"],"generation_seq":g,"cohort_id":"B"});w(self.r/"assignments/B.json",{"parent_state_git_identity":s["active_parent_state_git_identity"],"generation_seq":g,"cohort_id":"B"});return s
 def test_valid(self):self.make();self.assertEqual(p.validate(self.r),[])
 def test_nonexistent(self):self.make("0"*40);self.assertTrue(p.validate(self.r))
 def test_skip_generation(self):self.make(g=3);self.assertTrue(any("generation" in x for x in p.validate(self.r)))
if __name__=="__main__":unittest.main()
