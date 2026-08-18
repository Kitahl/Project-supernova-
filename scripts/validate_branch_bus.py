#!/usr/bin/env python3
import argparse, hashlib, json, os, pathlib, re, sys
from jsonschema import Draft202012Validator

ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN="61fbe7206e43ec538f310acf875e72865daf8fbb0e4ccbe27dcd6d1a072ff8a0"
OVERLAY="78eaafc34bcf56a6c0898d2085ba1462f687c95d9cf0d5d6a46a357d8c2d6f96"
WORKERS={"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
SESSION_NAMES={"MF01":"PS-MF-W01 | Representation Lab","MF02":"PS-MF-W02 | E1 Solver Routing","MF03":"PS-MF-W03 | Lemma & Operator Lab","MF04":"PS-MF-W04 | Adversarial Falsifier","MF05":"PS-MF-W05 | Product Closure","MM01":"PS-MM-W01 | React Mechanisms","MM02":"PS-MM-W02 | DeepSWE Mechanisms","MM03":"PS-MM-W03 | SlopCode Contracts","MM04":"PS-MM-W04 | Senior SWE Architecture","MM05":"PS-MM-W05 | E3 Mechanism Controls","MM07":"PS-MM-W07 | Before/After Self-Bench","EXT01":"PS-JOINT-A01 | Runtime & Transport Audit"}
BASE_CONTROL={"PROTOCOL.md","WORKER_PROTOCOL.md","SESSION_STANDARD.md","plan/PLAN.json","config/roles.json","config/worker_auth.json","benchmark/registry.json","requirements-validation.txt","schemas/control.schema.json","schemas/state.schema.json","schemas/assignment.schema.json","schemas/report.schema.json","schemas/verification.schema.json","schemas/integration.schema.json","schemas/director.schema.json","schemas/research.schema.json","schemas/benchmark_registry.schema.json","schemas/benchmark_completion.schema.json","schemas/private_manifest_contract.schema.json","scripts/validate_bus.py",".github/workflows/validate-bus.yml"}
OVERLAY_CONTROL={"BRANCH_PROTOCOL.md","branch/CONFIG.json","schemas/branch_generation.schema.json","schemas/branch_consolidation.schema.json","scripts/validate_branch_bus.py",".github/workflows/validate-branch-bus.yml"}
CONTROL=BASE_CONTROL|OVERLAY_CONTROL
BAD_KEYS={"hidden_task_name","hidden_task_id","protected_task_id","benchmark_item_id","raw_hidden_prompt","private_manifest_payload","private_manifest_content","worker_auth_secret","worker_auth_secret_hex","secret","credential","api_key","access_token","password"}
TEST_RE=re.compile(r"\bTEST-\d{3}\b",re.I); HEX40=re.compile(r"^[0-9a-f]{40}$"); HEX64=re.compile(r"^[0-9a-f]{64}$")
E=[]
def err(p,m): E.append(f"{p}: {m}")
def load(p):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception as x:err(str(p.relative_to(ROOT)),f"invalid JSON: {x}");return None
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def walk_public(o,p):
 if isinstance(o,dict):
  for k,v in o.items():
   if k.lower() in BAD_KEYS:err(p,f"forbidden public key {k}")
   walk_public(v,p)
 elif isinstance(o,list):
  for v in o:walk_public(v,p)
 elif isinstance(o,str) and TEST_RE.search(o):err(p,"raw TEST-NNN identifier forbidden in public bus")
def schema(name):
 p=ROOT/f"schemas/{name}.schema.json";s=load(p)
 if s is not None:
  try:Draft202012Validator.check_schema(s)
  except Exception as x:err(str(p.relative_to(ROOT)),f"invalid Draft2020-12 schema: {x}")
 return s
def validate(o,s,p):
 if o is None or s is None:return
 for x in sorted(Draft202012Validator(s).iter_errors(o),key=lambda z:list(z.path)):
  loc='/'.join(map(str,x.path));err(p,f"schema:{loc}: {x.message}")
def branch_context(ref):
 pats=[(r"^ps/work/([^/]+)/([^/]+)$","worker"),(r"^ps/(verify)/([^/]+)$","verify"),(r"^ps/(integrate)/([^/]+)$","integrate"),(r"^ps/(consolidate)/([^/]+)$","consolidate"),(r"^ps/gen/(.+)$","generation")]
 m=re.match(pats[0][0],ref)
 if m:return "worker",m.group(1),m.group(2)
 for pat,kind in pats[1:4]:
  m=re.match(pat,ref)
  if m:return kind,m.group(2),None
 m=re.match(pats[4][0],ref)
 if m:return "generation",m.group(1),None
 return None,None,None

ap=argparse.ArgumentParser();ap.add_argument('--branch');ap.add_argument('--cohort');args=ap.parse_args()
ref=args.branch or os.environ.get('GITHUB_REF_NAME','')
kind,cohort,worker=branch_context(ref)
if args.cohort:cohort=args.cohort
if not cohort:err('branch',f'cannot derive cohort from ref {ref!r}; use --cohort')

for p in ROOT.rglob('*.json'):
 if '.git' in p.parts:continue
 o=load(p)
 if o is not None:walk_public(o,str(p.relative_to(ROOT)))

schemas={n:schema(n) for n in ['control','assignment','report','verification','integration','director','research','benchmark_registry','benchmark_completion','private_manifest_contract','branch_generation','branch_consolidation']}
plan=load(ROOT/'plan/PLAN.json');config=load(ROOT/'branch/CONFIG.json');auth=load(ROOT/'config/worker_auth.json');registry=load(ROOT/'benchmark/registry.json')
if not plan or not config or not auth or not registry:err('root','missing plan/config/auth/registry')
if plan and plan.get('task_network_plan_id')!=PLAN:err('plan/PLAN.json','plan ID mismatch')
if config:
 if config.get('overlay_id')!=OVERLAY or config.get('base_task_network_plan_id')!=PLAN:err('branch/CONFIG.json','overlay/base plan mismatch')
 if set(config.get('overlay_control_files',[]))!=OVERLAY_CONTROL:err('branch/CONFIG.json','overlay_control_files mismatch')
if set((auth or {}).get('commitments',{}))!=WORKERS:err('config/worker_auth.json','worker commitment set mismatch')
validate(registry,schemas['benchmark_registry'],'benchmark/registry.json')

if cohort:
 cp=ROOT/'control'/f'{cohort}.json';asp=ROOT/'assignments'/f'{cohort}.json'
 c=load(cp) if cp.exists() else None;a=load(asp) if asp.exists() else None
 validate(c,schemas['control'],str(cp.relative_to(ROOT)) if cp.exists() else 'control')
 validate(a,schemas['assignment'],str(asp.relative_to(ROOT)) if asp.exists() else 'assignment')
 if not c:err('control',f'missing control for {cohort}')
 if not a:err('assignment',f'missing assignment for {cohort}')
 if c:
  if c.get('task_network_plan_id')!=PLAN or c.get('cohort_id')!=cohort:err(str(cp.relative_to(ROOT)),'plan/cohort mismatch')
  if set(c.get('files',{}))!=CONTROL:err(str(cp.relative_to(ROOT)),f'frozen control file set mismatch expected={len(CONTROL)} got={len(c.get("files",{}))}')
  for rel,sha in c.get('files',{}).items():
   fp=ROOT/rel
   if not fp.exists():err(str(cp.relative_to(ROOT)),f'missing frozen {rel}')
   elif blob(fp)!=sha:err(str(cp.relative_to(ROOT)),f'frozen file drift {rel}')
 if a:
  if a.get('task_network_plan_id')!=PLAN or a.get('cohort_id')!=cohort:err(str(asp.relative_to(ROOT)),'plan/cohort mismatch')
  if set(a.get('workers',{}))!=WORKERS:err(str(asp.relative_to(ROOT)),'worker set mismatch')
  if c and (a.get('control_manifest_path')!=str(cp.relative_to(ROOT)) or a.get('control_manifest_git_identity')!=blob(cp)):err(str(asp.relative_to(ROOT)),'control binding mismatch')
  if a.get('network_mode')=='GITHUB_BUS_CALIBRATION':
   for w,x in a.get('workers',{}).items():
    if x.get('fresh_allowed') is not False or x.get('opaque_evidence_ids')!=[] or x.get('private_manifest_id') is not None or x.get('private_manifest_git_identity') is not None:err(str(asp.relative_to(ROOT)),f'{w} not replay-only')
 if kind=='worker' and worker:
  rp=ROOT/'reports'/cohort/f'{worker}.json';r=load(rp) if rp.exists() else None
  if not r:err(str(rp.relative_to(ROOT)),'worker report missing')
  else:
   validate(r,schemas['report'],str(rp.relative_to(ROOT)))
   expect={'task_network_plan_id':PLAN,'cohort_id':cohort,'worker_id':worker,'assignment_id':a.get('assignment_id') if a else None,'assignment_git_identity':blob(asp) if a else None,'control_manifest_id':a.get('control_manifest_id') if a else None,'control_manifest_git_identity':blob(cp) if c else None,'network_checkpoint_id':a.get('network_checkpoint_id') if a else None,'runtime_state_id':a.get('runtime_state_id') if a else None,'visibility_token':a.get('workers',{}).get(worker,{}).get('visibility_token') if a else None,'worker_auth_scheme':'PS-HMAC-SHA256-WORKER-PROOF-1','worker_auth_commitment':auth.get('commitments',{}).get(worker),'status':'VALID_ASSIGNED_REPORT','public_safety_status':'PASS','origin_reread_claim':False}
   for k,v in expect.items():
    if r.get(k)!=v:err(str(rp.relative_to(ROOT)),f'{k} mismatch')
   h=r.get('session_header',{})
   if h.get('session_name')!=SESSION_NAMES.get(worker) or h.get('iteration_id')!=cohort or h.get('role_id')!=worker:err(str(rp.relative_to(ROOT)),'session identity mismatch')
   if a and (h.get('target_program')!=a.get('workers',{}).get(worker,{}).get('target_program') or h.get('goal')!=a.get('workers',{}).get(worker,{}).get('goal')):err(str(rp.relative_to(ROOT)),'session target/goal mismatch')
   if not HEX64.match(str(r.get('worker_auth_proof',''))):err(str(rp.relative_to(ROOT)),'bad HMAC proof format')
   if a and a.get('network_mode')=='GITHUB_BUS_CALIBRATION':
    led=r.get('cost_ledger',{})
    if r.get('mode')!='SAFE_REPLAY_ONLY' or r.get('fresh_evidence_ids')!=[] or r.get('private_manifest_id') is not None:err(str(rp.relative_to(ROOT)),'fresh/private data in calibration')
    if any(led.get(k)!=0 for k in ['fresh_evidence_units_consumed','protected_manifest_reads','benchmark_executions','deep_research_runs']):err(str(rp.relative_to(ROOT)),'nonzero prohibited cost in calibration')
 if kind=='verify':
  p=ROOT/'verification'/f'{cohort}.json'
  if p.exists():validate(load(p),schemas['verification'],str(p.relative_to(ROOT)))
 if kind=='integrate':
  p=ROOT/'integration'/f'{cohort}.json'
  if p.exists():validate(load(p),schemas['integration'],str(p.relative_to(ROOT)))
 if kind=='consolidate':
  for p in (ROOT/'history'/cohort).rglob('*.json') if (ROOT/'history'/cohort).exists() else []:walk_public(load(p),str(p.relative_to(ROOT)))
  p=ROOT/'history'/cohort/'CONSOLIDATION.json'
  if p.exists():validate(load(p),schemas['branch_consolidation'],str(p.relative_to(ROOT)))

if E:
 print('BRANCH BUS VALIDATION FAILED')
 for x in E:print('-',x)
 sys.exit(1)
print(f'BRANCH BUS VALIDATION PASS ref={ref} cohort={cohort} kind={kind}')
