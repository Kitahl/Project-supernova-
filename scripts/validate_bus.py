#!/usr/bin/env python3
import hashlib,json,pathlib,re,sys
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN="0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
WORKERS={'MF01', 'EXT01', 'MM04', 'MF04', 'MM05', 'MM01', 'MM02', 'MF02', 'MM03', 'MF03', 'MM07', 'MF05'}
SESSION_NAMES={'MF01': 'PS-MF-W01 | Representation Lab', 'MF02': 'PS-MF-W02 | E1 Solver Routing', 'MF03': 'PS-MF-W03 | Lemma & Operator Lab', 'MF04': 'PS-MF-W04 | Adversarial Falsifier', 'MF05': 'PS-MF-W05 | Product Closure', 'MM01': 'PS-MM-W01 | React Mechanisms', 'MM02': 'PS-MM-W02 | DeepSWE Mechanisms', 'MM03': 'PS-MM-W03 | SlopCode Contracts', 'MM04': 'PS-MM-W04 | Senior SWE Architecture', 'MM05': 'PS-MM-W05 | E3 Mechanism Controls', 'MM07': 'PS-MM-W07 | Before/After Self-Bench', 'EXT01': 'PS-JOINT-A01 | Runtime & Transport Audit'}
BAD_KEYS={"hidden_task_name","hidden_task_id","protected_task_id","benchmark_item_id","raw_hidden_prompt","private_manifest_payload","private_manifest_content","worker_auth_secret","worker_auth_secret_hex","secret","credential","api_key","access_token","password"}
HEX40=re.compile(r"^[0-9a-f]{40}$");HEX64=re.compile(r"^[0-9a-f]{64}$");E=[]
def err(p,m):E.append(f"{p}: {m}")
def load(p):
 try:return json.loads(p.read_text(encoding="utf-8"))
 except Exception as x:err(str(p.relative_to(ROOT)) if p.exists() else str(p),f"invalid JSON: {x}");return None
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def walk(o,p):
 if isinstance(o,dict):
  for k,v in o.items():
   if k.lower() in BAD_KEYS:err(p,f"forbidden public key {k}")
   walk(v,p)
 elif isinstance(o,list):
  for v in o:walk(v,p)
def schema(n):
 p=ROOT/f"schemas/{n}.schema.json";s=load(p)
 if s is not None:
  try:Draft202012Validator.check_schema(s)
  except Exception as x:err(str(p.relative_to(ROOT)),f"invalid Draft2020-12 schema: {x}")
 return s
def validate(o,s,p):
 if o is None or s is None:return
 for x in sorted(Draft202012Validator(s).iter_errors(o),key=lambda z:list(z.path)):
  err(p,"schema:"+"/".join(map(str,x.path))+": "+x.message)
for p in ROOT.rglob("*.json"):
 if ".git" in p.parts:continue
 o=load(p)
 if o is not None:walk(o,str(p.relative_to(ROOT)))
names=["control","state","assignment","report","verification","integration","director","research","benchmark_registry","benchmark_completion","private_manifest_contract","transition","runtime_update"]
S={n:schema(n) for n in names}
state=load(ROOT/"state/CURRENT.json");plan=load(ROOT/"plan/PLAN.json");auth=load(ROOT/"config/worker_auth.json");registry=load(ROOT/"benchmark/registry.json");policy=load(ROOT/"config/repo_policy.json")
validate(state,S["state"],"state/CURRENT.json");validate(registry,S["benchmark_registry"],"benchmark/registry.json")
if not all([state,plan,auth,registry,policy]):err("root","missing state/plan/auth/registry/policy")
if state and plan and auth and registry and policy:
 if plan.get("task_network_plan_id")!=PLAN or state.get("task_network_plan_id")!=PLAN:err("plan/state","plan ID mismatch")
 if plan.get("protocol_version")!="2.4" or state.get("protocol_version")!="2.4":err("plan/state","protocol != 2.4")
 if set(auth.get("commitments",{}))!=WORKERS:err("config/worker_auth.json","worker commitment set mismatch")
 if state.get("fresh_allowed_globally") and state.get("repo_policy_status")!="VERIFIED_PROTECTED":err("state/CURRENT.json","fresh globally while repo policy unverified")
 if state.get("calibration_countable_current") and state.get("repo_policy_status")!="VERIFIED_PROTECTED":err("state/CURRENT.json","countable calibration while repo policy unverified")
 if state.get("required_ci_contexts")!=policy.get("required_status_contexts"):err("state/policy","required contexts mismatch")
 if state.get("benchmark_registry_git_identity")!=blob(ROOT/"benchmark/registry.json"):err("state/CURRENT.json","benchmark registry blob mismatch")
 cp=ROOT/state.get("active_control_manifest_path","");ap=ROOT/state.get("active_assignment_path","");c=load(cp) if cp.exists() else None;a=load(ap) if ap.exists() else None
 validate(c,S["control"],str(cp.relative_to(ROOT)) if cp.exists() else "active-control");validate(a,S["assignment"],str(ap.relative_to(ROOT)) if ap.exists() else "active-assignment")
 if not c:err("state/CURRENT.json","active control missing")
 if not a:err("state/CURRENT.json","active assignment missing")
 if c:
  if blob(cp)!=state.get("active_control_manifest_git_identity"):err(str(cp.relative_to(ROOT)),"control blob != state")
  for rel,sha in c.get("files",{}).items():
   fp=ROOT/rel
   if not fp.exists():err(str(cp.relative_to(ROOT)),f"missing frozen {rel}")
   elif blob(fp)!=sha:err(str(cp.relative_to(ROOT)),f"frozen file drift {rel}")
 if a:
  if blob(ap)!=state.get("active_assignment_git_identity"):err(str(ap.relative_to(ROOT)),"assignment blob != state")
  if set(a.get("workers",{}))!=WORKERS:err(str(ap.relative_to(ROOT)),"worker set mismatch")
  if a.get("network_mode")=="GITHUB_BUS_CALIBRATION":
   for w,x in a.get("workers",{}).items():
    if x.get("fresh_allowed") is not False or x.get("opaque_evidence_ids")!=[] or x.get("private_manifest_id") is not None or x.get("private_manifest_git_identity") is not None:err(str(ap.relative_to(ROOT)),f"{w} not replay-only")
cohort=state.get("active_cohort_id") if state else None
if cohort:
 d=ROOT/"reports"/cohort
 if d.exists():
  for p in d.glob("*.json"):
   r=load(p);validate(r,S["report"],str(p.relative_to(ROOT)))
   if r:
    w=r.get("worker_id")
    if w not in WORKERS or p.stem!=w:err(str(p.relative_to(ROOT)),"report path/worker mismatch")
    led=r.get("cost_ledger",{})
    if state.get("network_mode")=="GITHUB_BUS_CALIBRATION" and any(led.get(k)!=0 for k in ["fresh_evidence_units_consumed","protected_manifest_reads","benchmark_executions","deep_research_runs"]):err(str(p.relative_to(ROOT)),"nonzero calibration protected/benchmark/research cost")
for folder,key in [("verification","verification"),("integration","integration"),("director","director")]:
 p=ROOT/folder/f"{cohort}.json" if cohort else None
 if p and p.exists():validate(load(p),S[key],str(p.relative_to(ROOT)))
if E:
 print("BUS VALIDATION FAILED");[print("-",x) for x in E];sys.exit(1)
print("BUS VALIDATION PASS")
