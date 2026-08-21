import importlib.util,json,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"ci_guard.py";SPEC=importlib.util.spec_from_file_location("ci",SCRIPT);ci=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(ci)
def git(root,*a):return subprocess.run(["git","-C",str(root),*a],check=True,text=True,stdout=subprocess.PIPE).stdout.strip()
def w(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o))
class T(unittest.TestCase):
 def setUp(self):
  self.x=tempfile.TemporaryDirectory();self.r=pathlib.Path(self.x.name);git(self.r,"init");git(self.r,"config","user.email","x@y");git(self.r,"config","user.name","x");self.c="C";self.w="MF01"
  w(self.r/"state/CURRENT.json",{"active_cohort_id":self.c});w(self.r/f"assignments/{self.c}.json",{"workers":{self.w:{}}});self.p=self.r/f"reports/{self.c}/{self.w}.json";w(self.p,{"cohort_id":self.c,"worker_id":self.w});git(self.r,"add",".");git(self.r,"commit","-m","r");self.commit=git(self.r,"rev-parse","HEAD");self.blob=ci.git_blob_sha(self.p)
 def tearDown(self):self.x.cleanup()
 def m(self):return {"cohort_id":self.c,"safe_report_refs":[{"worker_id":self.w,"path":f"reports/{self.c}/{self.w}.json","blob_sha":self.blob,"commit_sha":self.commit,"verifier_reread_verified":True,"schema_valid":True,"auth_valid":True,"public_safety_valid":True,"assignment_binding_valid":True,"control_binding_valid":True,"lineage_valid":True,"immutable_history_valid":True}],"quarantined_report_refs":[],"missing_workers":[],"worker_auth_verification":{self.w:"PASS"},"calibration_pass":True,"verdict":"VERIFIED_COMPLETE"}
 def test_ok(self):w(self.r/f"verification/{self.c}.json",self.m());self.assertEqual(ci.validate(self.r),[])
 def test_wrong_blob(self):m=self.m();m["safe_report_refs"][0]["blob_sha"]="0"*40;w(self.r/f"verification/{self.c}.json",m);self.assertTrue(any("blob mismatch" in x for x in ci.validate(self.r)))
 def test_mutation(self):w(self.p,{"cohort_id":self.c,"worker_id":self.w,"x":1});git(self.r,"add",".");git(self.r,"commit","-m","bad");m=self.m();m["safe_report_refs"][0]["blob_sha"]=ci.git_blob_sha(self.p);w(self.r/f"verification/{self.c}.json",m);self.assertTrue(any("create-once" in x for x in ci.validate(self.r)))
 def test_partition(self):m=self.m();m["safe_report_refs"]=[];m["missing_workers"]=[self.w];w(self.r/f"verification/{self.c}.json",m);self.assertTrue(any("complete/pass" in x for x in ci.validate(self.r)))
 def test_quarantine_closed(self):m=self.m();m["calibration_pass"]=False;m["verdict"]="VERIFIED_WITH_QUARANTINES";m["safe_report_refs"]=[];m["quarantined_report_refs"]=[{"worker_id":self.w,"reason_code":"x"}];w(self.r/f"verification/{self.c}.json",m);self.assertTrue(any("closed schema" in x for x in ci.validate(self.r)))
 def test_only_one_scheduled_structural_reconciler_writes_branch_contexts(self):
  workflows=list((ROOT/".github/workflows").glob("*.yml"))+list((ROOT/".github/workflows").glob("*.yaml"))
  rest_invokers=[p.name for p in workflows if "reconcile_branch_rest.py" in p.read_text()]
  primary_invokers=[p.name for p in workflows if "reconcile_branch_statuses.py" in p.read_text()]
  self.assertEqual(rest_invokers,[])
  self.assertEqual(primary_invokers,["supernova-branch-reconciler.yml"])
 def test_rest_admission_workflow_remains_admission_only(self):
  text=(ROOT/".github/workflows/supernova-rest-branch-reconciler.yml").read_text()
  self.assertIn("reconcile_v25_admission.py",text)
  self.assertNotIn("reconcile_branch_rest.py",text)
  self.assertNotIn("supernova/branch-generation",text)
if __name__=="__main__":unittest.main()
