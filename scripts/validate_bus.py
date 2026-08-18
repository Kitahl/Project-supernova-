#!/usr/bin/env python3
import hashlib, json, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; E=[]
PLAN="ec86c19d38aec9a8a5f8f6c88169d7b4d770897e44b2aad82e02c0afba40545f"
WORKERS={"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
SEALED={"SEALED_ORACLE_SLOT_A","SEALED_ORACLE_SLOT_B"}
CONTROL={"PROTOCOL.md","WORKER_PROTOCOL.md","plan/PLAN.json","config/roles.json","config/worker_auth.json","schemas/control.schema.json","schemas/state.schema.json","schemas/assignment.schema.json","schemas/report.schema.json","schemas/verification.schema.json","schemas/integration.schema.json","schemas/director.schema.json","schemas/research.schema.json","scripts/validate_bus.py",".github/workflows/validate-bus.yml"}
BAD_KEYS={"hidden_task_name","hidden_task_id","protected_task_id","benchmark_item_id","raw_hidden_prompt","private_manifest_payload","private_manifest_content","worker_auth_secret","worker_auth_secret_hex","secret","credential","api_key","access_token","password"}
TEST=re.compile(r"\bTEST-\d{3}\b",re.I); HEX40=re.compile(r"^[0-9a-f]{40}$"); HEX64=re.compile(r"^[0-9a-f]{64}$")
def err(p,m): E.append(f"{p}: {m}")
def load(p):
 try:return json.loads(p.read_text())
 except Exception as x:err(p.relative_to(ROOT),f"invalid JSON: {x}");return None
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def walk(o,p):
 if isinstance(o,dict):
  for k,v in o.items():
   if k.lower() in BAD_KEYS:err(p,f"forbidden public key {k}")
   walk(v,p)
 elif isinstance(o,list):
  for v in o:walk(v,p)
 elif isinstance(o,str) and TEST.search(o):err(p,"raw TEST-NNN forbidden in public bus")
for p in ROOT.rglob("*.json"):
 if ".git" not in p.parts:
  o=load(p)
  if o is not None:walk(o,str(p.relative_to(ROOT)))
# superseded
sup=set(); sd=ROOT/"superseded"
if sd.exists():
 for p in sd.glob("*.json"):
  o=load(p)
  if o and o.get("cohort_id"):sup.add(o["cohort_id"])
state=load(ROOT/"state/CURRENT.json"); plan=load(ROOT/"plan/PLAN.json"); auth=load(ROOT/"config/worker_auth.json")
if not state or not plan or not auth:err("root","missing state/plan/auth")
if state and plan and auth:
 if state.get("task_network_plan_id")!=PLAN or plan.get("task_network_plan_id")!=PLAN:err("plan/state","plan ID mismatch")
 if state.get("protocol_version")!="2.2" or plan.get("protocol_version")!="2.2":err("plan/state","protocol != 2.2")
 if set(auth.get("commitments",{}))!=WORKERS:err("config/worker_auth.json","worker commitment set mismatch")
 for w,c in auth.get("commitments",{}).items():
  if not isinstance(c,str) or not HEX64.match(c):err("config/worker_auth.json",f"bad commitment {w}")
 if state.get("active_cohort_id") in sup:err("state/CURRENT.json","active cohort superseded")
 if state.get("fresh_allowed_globally") and state.get("network_mode")!="FRESH_ENABLED":err("state/CURRENT.json","fresh globally outside FRESH_ENABLED")
 if state.get("deep_research_owner")!="BIL00" or state.get("deep_research_times_vancouver")!=["00:58","12:58"]:err("state/CURRENT.json","deep research owner/schedule mismatch")
 if not isinstance(state.get("generation_seq"),int) or state["generation_seq"]<1:err("state/CURRENT.json","bad generation_seq")
 if not HEX40.match(str(state.get("active_parent_state_git_identity",""))):err("state/CURRENT.json","bad active parent state identity")
 cp=ROOT/state.get("active_control_manifest_path",""); ap=ROOT/state.get("active_assignment_path","")
 c=load(cp) if cp.exists() else None; a=load(ap) if ap.exists() else None
 if not c:err("state/CURRENT.json","active control missing")
 if not a:err("state/CURRENT.json","active assignment missing")
 if c:
  if blob(cp)!=state.get("active_control_manifest_git_identity"):err(cp.relative_to(ROOT),"control blob != state")
  if c.get("task_network_plan_id")!=PLAN or c.get("cohort_id")!=state.get("active_cohort_id"):err(cp.relative_to(ROOT),"control plan/cohort mismatch")
  if c.get("generation_seq")!=state.get("generation_seq") or c.get("parent_state_git_identity")!=state.get("active_parent_state_git_identity"):err(cp.relative_to(ROOT),"control lineage mismatch")
  files=c.get("files",{})
  if set(files)!=CONTROL:err(cp.relative_to(ROOT),"frozen control file set mismatch")
  for rel,sha in files.items():
   fp=ROOT/rel
   if not fp.exists():err(cp.relative_to(ROOT),f"missing frozen {rel}")
   elif blob(fp)!=sha:err(cp.relative_to(ROOT),f"frozen file drift {rel}")
 if a:
  if blob(ap)!=state.get("active_assignment_git_identity"):err(ap.relative_to(ROOT),"assignment blob != state")
  pairs={"task_network_plan_id":PLAN,"cohort_id":state.get("active_cohort_id"),"generation_seq":state.get("generation_seq"),"parent_state_git_identity":state.get("active_parent_state_git_identity"),"control_manifest_path":state.get("active_control_manifest_path"),"control_manifest_git_identity":state.get("active_control_manifest_git_identity"),"network_checkpoint_id":state.get("accepted_network_checkpoint_id"),"runtime_state_id":state.get("runtime_state_id"),"network_mode":state.get("network_mode")}
  for k,v in pairs.items():
   if a.get(k)!=v:err(ap.relative_to(ROOT),f"{k} mismatch")
  if set(a.get("workers",{}))!=WORKERS:err(ap.relative_to(ROOT),"worker set mismatch")
  if set(a.get("sealed_slots",[]))!=SEALED:err(ap.relative_to(ROOT),"sealed set mismatch")
  if a.get("network_mode")=="GITHUB_BUS_CALIBRATION":
   for w,x in a.get("workers",{}).items():
    if x.get("fresh_allowed") is not False or x.get("opaque_evidence_ids")!=[] or x.get("private_manifest_id") is not None or x.get("private_manifest_git_identity") is not None:err(ap.relative_to(ROOT),f"{w} not replay-only in calibration")
# active/non-superseded reports
rr=ROOT/"reports"
if rr.exists():
 for p in rr.rglob("*.json"):
  r=load(p)
  if not r or r.get("cohort_id") in sup:continue
  w=r.get("worker_id"); cohort=r.get("cohort_id")
  if w not in WORKERS or p.stem!=w or p.parent.name!=cohort:err(p.relative_to(ROOT),"report path/worker mismatch");continue
  ap=ROOT/"assignments"/f"{cohort}.json"; a=load(ap) if ap.exists() else None
  if not a:err(p.relative_to(ROOT),"missing assignment");continue
  cp=ROOT/a.get("control_manifest_path",""); c=load(cp) if cp.exists() else None
  if not c:err(p.relative_to(ROOT),"missing control");continue
  expect={"task_network_plan_id":PLAN,"cohort_id":cohort,"assignment_id":a.get("assignment_id"),"assignment_git_identity":blob(ap),"generation_seq":a.get("generation_seq"),"parent_state_git_identity":a.get("parent_state_git_identity"),"control_manifest_id":a.get("control_manifest_id"),"control_manifest_git_identity":a.get("control_manifest_git_identity"),"network_checkpoint_id":a.get("network_checkpoint_id"),"runtime_state_id":a.get("runtime_state_id"),"visibility_token":a.get("workers",{}).get(w,{}).get("visibility_token"),"worker_auth_scheme":"PS-HMAC-SHA256-WORKER-PROOF-1","worker_auth_commitment":auth.get("commitments",{}).get(w),"status":"VALID_ASSIGNED_REPORT","public_safety_status":"PASS","git_reread_verified":True}
  for k,v in expect.items():
   if r.get(k)!=v:err(p.relative_to(ROOT),f"{k} mismatch")
  if not HEX64.match(str(r.get("worker_auth_proof",""))):err(p.relative_to(ROOT),"bad worker auth proof format")
  if r.get("mode") not in {"SAFE_REPLAY_ONLY","FRESH_EXECUTION"}:err(p.relative_to(ROOT),"bad mode")
  if r.get("ci_status") not in {"PASS","FAIL","PENDING","CI_NOT_OBSERVED"}:err(p.relative_to(ROOT),"bad ci_status")
  led=r.get("cost_ledger",{})
  for k in ["fresh_evidence_units_consumed","protected_manifest_reads","benchmark_executions","deep_research_runs"]:
   if not isinstance(led.get(k),int) or led[k]<0:err(p.relative_to(ROOT),f"bad cost {k}")
  if led.get("deep_research_runs")!=0:err(p.relative_to(ROOT),"worker deep research forbidden")
  if a.get("network_mode")=="GITHUB_BUS_CALIBRATION":
   if r.get("mode")!="SAFE_REPLAY_ONLY" or r.get("fresh_evidence_ids")!=[] or r.get("private_manifest_id") is not None or r.get("private_manifest_git_identity") is not None:err(p.relative_to(ROOT),"fresh/private data in calibration report")
   if any(led.get(k)!=0 for k in ["fresh_evidence_units_consumed","protected_manifest_reads","benchmark_executions"]):err(p.relative_to(ROOT),"nonzero fresh/protected costs in calibration")
# terminal artifacts must never make superseded cohort count
for cohort in sup:
 dp=ROOT/"director"/f"{cohort}.json"
 if dp.exists():
  d=load(dp)
  if d and d.get("calibration_counted"):err(dp.relative_to(ROOT),"superseded cohort counted")
if E:
 print("BUS VALIDATION FAILED")
 for x in E:print("-",x)
 sys.exit(1)
print("BUS VALIDATION PASS")
