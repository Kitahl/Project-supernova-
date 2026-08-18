#!/usr/bin/env python3
import argparse, copy, hashlib, json, os, pathlib, re, sys
from jsonschema import Draft202012Validator

ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN="61fbe7206e43ec538f310acf875e72865daf8fbb0e4ccbe27dcd6d1a072ff8a0"
OVERLAY="78eaafc34bcf56a6c0898d2085ba1462f687c95d9cf0d5d6a46a357d8c2d6f96"
AUTH_SCHEME="PS-HMAC-SHA256-CANONICAL-REPORT-2"; MODEL="GPT-5.6 Sol"; EFFORT="EXTRA_HIGH"
WORKERS={"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
SESSION_NAMES={"MF01":"PS-MF-W01 | Representation Lab","MF02":"PS-MF-W02 | E1 Solver Routing","MF03":"PS-MF-W03 | Lemma & Operator Lab","MF04":"PS-MF-W04 | Adversarial Falsifier","MF05":"PS-MF-W05 | Product Closure","MM01":"PS-MM-W01 | React Mechanisms","MM02":"PS-MM-W02 | DeepSWE Mechanisms","MM03":"PS-MM-W03 | SlopCode Contracts","MM04":"PS-MM-W04 | Senior SWE Architecture","MM05":"PS-MM-W05 | E3 Mechanism Controls","MM07":"PS-MM-W07 | Before/After Self-Bench","EXT01":"PS-JOINT-A01 | Runtime & Transport Audit"}
BASE_CONTROL={"PROTOCOL.md","WORKER_PROTOCOL.md","SESSION_STANDARD.md","plan/PLAN.json","config/roles.json","config/worker_auth.json","benchmark/registry.json","requirements-validation.txt","schemas/control.schema.json","schemas/state.schema.json","schemas/assignment.schema.json","schemas/report.schema.json","schemas/verification.schema.json","schemas/integration.schema.json","schemas/director.schema.json","schemas/research.schema.json","schemas/benchmark_registry.schema.json","schemas/benchmark_completion.schema.json","schemas/private_manifest_contract.schema.json","scripts/validate_bus.py",".github/workflows/validate-bus.yml"}
OVERLAY_CONTROL={"BRANCH_PROTOCOL.md","BRANCH_WORKER_PROTOCOL.md","branch/CONFIG.json","schemas/branch_generation.schema.json","schemas/branch_consolidation.schema.json","scripts/validate_branch_bus.py",".github/workflows/validate-branch-bus.yml"}; CONTROL=BASE_CONTROL|OVERLAY_CONTROL
BAD_KEYS={"hidden_task_name","hidden_task_id","protected_task_id","benchmark_item_id","raw_hidden_prompt","private_manifest_payload","private_manifest_content","worker_auth_secret","worker_auth_secret_hex","secret","credential","api_key","access_token","password"}
TEST_RE=re.compile(r"\bTEST-\d{3}\b",re.I); HEX64=re.compile(r"^[0-9a-f]{64}$"); E=[]
def err(p,m):E.append(f"{p}: {m}")
def load(p):
 try:return json.loads(p.read_text(encoding="utf-8"))
 except Exception as x:err(str(p.relative_to(ROOT)),f"invalid JSON: {x}");return None
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def walk(o,p):
 if isinstance(o,dict):
  for k,v in o.items():
   if k.lower() in BAD_KEYS:err(p,f"forbidden public key {k}")
   walk(v,p)
 elif isinstance(o,list):
  for v in o:walk(v,p)
 elif isinstance(o,str) and TEST_RE.search(o):err(p,"raw TEST-NNN identifier forbidden in public bus")
def sch(n):
 p=ROOT/f"schemas/{n}.schema.json";s=load(p)
 if s is not None:
  try:Draft202012Validator.check_schema(s)
  except Exception as x:err(str(p.relative_to(ROOT)),f"bad schema: {x}")
 return s
def serr(o,s):return list(Draft202012Validator(s).iter_errors(o)) if o is not None and s is not None else []
def val(o,s,p):
 for x in sorted(serr(o,s),key=lambda z:list(z.path)):err(p,f"schema:{'/'.join(map(str,x.path))}: {x.message}")
def ctx(ref):
 m=re.match(r"^ps/work/([^/]+)/([^/]+)$",ref)
 if m:return "worker",m.group(1),m.group(2)
 for k in ("verify","integrate","consolidate"):
  m=re.match(rf"^ps/{k}/([^/]+)$",ref)
  if m:return k,m.group(1),None
 m=re.match(r"^ps/gen/(.+)$",ref)
 return ("generation",m.group(1),None) if m else (None,None,None)
def sm(r,a,w):
 h=(r or {}).get("session_header",{});aw=(a or {}).get("workers",{}).get(w,{})
 ex={"session_name":SESSION_NAMES.get(w),"target_program":aw.get("target_program"),"phase":(a or {}).get("phase"),"iteration_id":(a or {}).get("cohort_id"),"iteration_number":(a or {}).get("generation_seq"),"role_id":w,"goal":aw.get("goal"),"plan_id":PLAN,"runtime_state_id":(a or {}).get("runtime_state_id"),"model_target":MODEL,"reasoning_effort_target":EFFORT}
 out=[f"session_header.{k}" for k,v in ex.items() if h.get(k)!=v]
 if (a or {}).get("network_mode")=="GITHUB_BUS_CALIBRATION" and h.get("execution_mode")!="SAFE_REPLAY_ONLY":out.append("session_header.execution_mode")
 return out

pa=argparse.ArgumentParser();pa.add_argument("--branch");pa.add_argument("--cohort");z=pa.parse_args();ref=z.branch or os.environ.get("GITHUB_REF_NAME","");kind,cohort,worker=ctx(ref);cohort=z.cohort or cohort
if not cohort:err("branch",f"cannot derive cohort from {ref!r}")
for p in ROOT.rglob("*.json"):
 if ".git" not in p.parts:
  o=load(p)
  if o is not None:walk(o,str(p.relative_to(ROOT)))
S={n:sch(n) for n in ["control","assignment","report","verification","integration","director","research","benchmark_registry","benchmark_completion","private_manifest_contract","branch_generation","branch_consolidation"]}
plan=load(ROOT/"plan/PLAN.json");cfg=load(ROOT/"branch/CONFIG.json");auth=load(ROOT/"config/worker_auth.json");reg=load(ROOT/"benchmark/registry.json")
if (plan or {}).get("task_network_plan_id")!=PLAN:err("plan/PLAN.json","plan ID mismatch")
if (cfg or {}).get("overlay_id")!=OVERLAY or (cfg or {}).get("base_task_network_plan_id")!=PLAN:err("branch/CONFIG.json","overlay/base-plan mismatch")
if (cfg or {}).get("branch_worker_protocol")!="BRANCH_WORKER_PROTOCOL.md" or (cfg or {}).get("branch_worker_protocol_precedence")!="AUTHORITATIVE_FOR_BRANCH_STATE_DESTINATION_AUTH_REREAD_VALIDATION":err("branch/CONFIG.json","branch worker protocol precedence not frozen")
if set((cfg or {}).get("overlay_control_files",[]))!=OVERLAY_CONTROL:err("branch/CONFIG.json","overlay control set mismatch")
if (cfg or {}).get("base_control_file_count")!=21 or (cfg or {}).get("overlay_control_file_count")!=7 or (cfg or {}).get("branch_control_file_count")!=28:err("branch/CONFIG.json","declared control counts mismatch")
if (cfg or {}).get("worker_auth_scheme")!=AUTH_SCHEME or not (cfg or {}).get("strict_session_equality"):err("branch/CONFIG.json","auth/session contract mismatch")
if set((auth or {}).get("commitments",{}))!=WORKERS:err("config/worker_auth.json","worker commitment set mismatch")
if not (ROOT/"BRANCH_WORKER_PROTOCOL.md").exists():err("BRANCH_WORKER_PROTOCOL.md","missing authoritative branch worker protocol")
val(reg,S["benchmark_registry"],"benchmark/registry.json")
if cohort:
 cp=ROOT/"control"/f"{cohort}.json";ap=ROOT/"assignments"/f"{cohort}.json";c=load(cp) if cp.exists() else None;a=load(ap) if ap.exists() else None
 val(c,S["control"],str(cp.relative_to(ROOT)) if cp.exists() else "control");val(a,S["assignment"],str(ap.relative_to(ROOT)) if ap.exists() else "assignment")
 if not c:err("control",f"missing control for {cohort}")
 if not a:err("assignment",f"missing assignment for {cohort}")
 if c:
  if c.get("task_network_plan_id")!=PLAN or c.get("cohort_id")!=cohort:err(str(cp.relative_to(ROOT)),"plan/cohort mismatch")
  if set(c.get("files",{}))!=CONTROL:err(str(cp.relative_to(ROOT)),f"frozen control set must be exact 21+7 union; got {len(c.get('files',{}))}")
  for rel,sha in c.get("files",{}).items():
   fp=ROOT/rel
   if not fp.exists():err(str(cp.relative_to(ROOT)),f"missing frozen {rel}")
   elif blob(fp)!=sha:err(str(cp.relative_to(ROOT)),f"frozen file drift {rel}")
 if a:
  if a.get("task_network_plan_id")!=PLAN or a.get("cohort_id")!=cohort:err(str(ap.relative_to(ROOT)),"plan/cohort mismatch")
  if set(a.get("workers",{}))!=WORKERS:err(str(ap.relative_to(ROOT)),"worker set mismatch")
  if c and (a.get("control_manifest_path")!=str(cp.relative_to(ROOT)) or a.get("control_manifest_git_identity")!=blob(cp)):err(str(ap.relative_to(ROOT)),"control binding mismatch")
  if a.get("network_mode")=="GITHUB_BUS_CALIBRATION":
   for w,x in a.get("workers",{}).items():
    if x.get("fresh_allowed") is not False or x.get("opaque_evidence_ids")!=[] or x.get("private_manifest_id") is not None or x.get("private_manifest_git_identity") is not None:err(str(ap.relative_to(ROOT)),f"{w} not replay-only")
 if kind=="worker" and worker:
  rp=ROOT/"reports"/cohort/f"{worker}.json";r=load(rp) if rp.exists() else None
  if not r:err(str(rp.relative_to(ROOT)),"worker report missing")
  else:
   val(r,S["report"],str(rp.relative_to(ROOT)))
   ex={"task_network_plan_id":PLAN,"cohort_id":cohort,"worker_id":worker,"assignment_id":a.get("assignment_id") if a else None,"assignment_git_identity":blob(ap) if a else None,"control_manifest_id":a.get("control_manifest_id") if a else None,"control_manifest_git_identity":blob(cp) if c else None,"network_checkpoint_id":a.get("network_checkpoint_id") if a else None,"runtime_state_id":a.get("runtime_state_id") if a else None,"visibility_token":a.get("workers",{}).get(worker,{}).get("visibility_token") if a else None,"worker_auth_scheme":AUTH_SCHEME,"worker_auth_commitment":(auth or {}).get("commitments",{}).get(worker),"status":"VALID_ASSIGNED_REPORT","public_safety_status":"PASS","origin_reread_claim":False}
   for k,v in ex.items():
    if r.get(k)!=v:err(str(rp.relative_to(ROOT)),f"{k} mismatch")
   for x in sm(r,a,worker):err(str(rp.relative_to(ROOT)),f"strict session mismatch {x}")
   if not HEX64.match(str(r.get("worker_auth_proof",""))):err(str(rp.relative_to(ROOT)),"bad canonical-report HMAC format")
   if a and a.get("network_mode")=="GITHUB_BUS_CALIBRATION":
    led=r.get("cost_ledger",{})
    if r.get("mode")!="SAFE_REPLAY_ONLY" or r.get("fresh_evidence_ids")!=[] or r.get("private_manifest_id") is not None:err(str(rp.relative_to(ROOT)),"fresh/private data in calibration")
    if any(led.get(k)!=0 for k in ["fresh_evidence_units_consumed","protected_manifest_reads","benchmark_executions","deep_research_runs"]):err(str(rp.relative_to(ROOT)),"nonzero prohibited cost in calibration")
   m=copy.deepcopy(r);m.pop("task_network_plan_id",None)
   if not serr(m,S["report"]):err(str(rp.relative_to(ROOT)),"negative probe: missing field accepted")
   x=copy.deepcopy(r);x["unexpected_top_level"]="x"
   if not serr(x,S["report"]):err(str(rp.relative_to(ROOT)),"negative probe: extra field accepted")
   x=copy.deepcopy(r);x["session_header"]["phase"]="__WRONG_PHASE__"
   if not sm(x,a,worker):err(str(rp.relative_to(ROOT)),"negative probe: wrong phase accepted")
 if kind=="verify":
  p=ROOT/"verification"/f"{cohort}.json"
  if p.exists():val(load(p),S["verification"],str(p.relative_to(ROOT)))
 if kind=="integrate":
  p=ROOT/"integration"/f"{cohort}.json"
  if p.exists():val(load(p),S["integration"],str(p.relative_to(ROOT)))
 if kind=="consolidate":
  p=ROOT/"history"/cohort/"CONSOLIDATION.json"
  if p.exists():val(load(p),S["branch_consolidation"],str(p.relative_to(ROOT)))
if E:
 print("BRANCH BUS VALIDATION FAILED")
 for x in E:print("-",x)
 sys.exit(1)
print(f"BRANCH BUS VALIDATION PASS ref={ref} cohort={cohort} kind={kind} auth={AUTH_SCHEME} controls=21+7")
