#!/usr/bin/env python3
import hashlib, json, pathlib, re, sys
from jsonschema import Draft202012Validator

ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN="61fbe7206e43ec538f310acf875e72865daf8fbb0e4ccbe27dcd6d1a072ff8a0"
WORKERS={"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
SESSION_NAMES={
 "MF01":"PS-MF-W01 | Representation Lab","MF02":"PS-MF-W02 | E1 Solver Routing","MF03":"PS-MF-W03 | Lemma & Operator Lab","MF04":"PS-MF-W04 | Adversarial Falsifier","MF05":"PS-MF-W05 | Product Closure",
 "MM01":"PS-MM-W01 | React Mechanisms","MM02":"PS-MM-W02 | DeepSWE Mechanisms","MM03":"PS-MM-W03 | SlopCode Contracts","MM04":"PS-MM-W04 | Senior SWE Architecture","MM05":"PS-MM-W05 | E3 Mechanism Controls","MM07":"PS-MM-W07 | Before/After Self-Bench","EXT01":"PS-JOINT-A01 | Runtime & Transport Audit"}
SEALED={"SEALED_ORACLE_SLOT_A","SEALED_ORACLE_SLOT_B"}
CONTROL={"PROTOCOL.md","WORKER_PROTOCOL.md","SESSION_STANDARD.md","plan/PLAN.json","config/roles.json","config/worker_auth.json","benchmark/registry.json","requirements-validation.txt","schemas/control.schema.json","schemas/state.schema.json","schemas/assignment.schema.json","schemas/report.schema.json","schemas/verification.schema.json","schemas/integration.schema.json","schemas/director.schema.json","schemas/research.schema.json","schemas/benchmark_registry.schema.json","schemas/benchmark_completion.schema.json","scripts/validate_bus.py",".github/workflows/validate-bus.yml"}
BAD_KEYS={"hidden_task_name","hidden_task_id","protected_task_id","benchmark_item_id","raw_hidden_prompt","private_manifest_payload","private_manifest_content","worker_auth_secret","worker_auth_secret_hex","secret","credential","api_key","access_token","password"}
TEST_RE=re.compile(r"\bTEST-\d{3}\b",re.I)
HEX40=re.compile(r"^[0-9a-f]{40}$"); HEX64=re.compile(r"^[0-9a-f]{64}$")
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
def schema(path):
 s=load(ROOT/path)
 if s is not None:
  try: Draft202012Validator.check_schema(s)
  except Exception as x: err(path,f"invalid Draft2020-12 schema: {x}")
 return s
def validate_obj(obj,sch,path):
 if obj is None or sch is None:return
 for x in sorted(Draft202012Validator(sch).iter_errors(obj),key=lambda z:list(z.path)):
  loc="/".join(map(str,x.path));err(path,f"schema:{loc}: {x.message}")

# public safety for every JSON artifact
for p in ROOT.rglob('*.json'):
 if '.git' in p.parts:continue
 o=load(p)
 if o is not None:walk_public(o,str(p.relative_to(ROOT)))

schemas={name:schema('schemas/'+name+'.schema.json') for name in ['control','state','assignment','report','verification','integration','director','research','benchmark_registry','benchmark_completion']}
state=load(ROOT/'state/CURRENT.json'); plan=load(ROOT/'plan/PLAN.json'); auth=load(ROOT/'config/worker_auth.json'); registry=load(ROOT/'benchmark/registry.json')
validate_obj(state,schemas['state'],'state/CURRENT.json'); validate_obj(registry,schemas['benchmark_registry'],'benchmark/registry.json')
if not state or not plan or not auth or not registry:err('root','missing state/plan/auth/registry')

sup=set(); sd=ROOT/'superseded'
if sd.exists():
 for p in sd.glob('*.json'):
  s=load(p)
  if s and s.get('cohort_id'):sup.add(s['cohort_id'])

if state and plan and auth and registry:
 if plan.get('task_network_plan_id')!=PLAN or state.get('task_network_plan_id')!=PLAN:err('plan/state','plan ID mismatch')
 if plan.get('protocol_version')!='2.3' or state.get('protocol_version')!='2.3':err('plan/state','protocol != 2.3')
 if state.get('active_cohort_id') in sup:err('state/CURRENT.json','active cohort is superseded')
 if set(auth.get('commitments',{}))!=WORKERS:err('config/worker_auth.json','worker commitment set mismatch')
 for w,c in auth.get('commitments',{}).items():
  if not isinstance(c,str) or not HEX64.match(c):err('config/worker_auth.json',f'bad commitment {w}')
 if state.get('benchmark_registry_path')!='benchmark/registry.json' or state.get('benchmark_registry_git_identity')!=blob(ROOT/'benchmark/registry.json'):err('state/CURRENT.json','benchmark registry identity mismatch')
 if state.get('fresh_allowed_globally') and state.get('network_mode')!='FRESH_ENABLED':err('state/CURRENT.json','fresh globally outside FRESH_ENABLED')
 if state.get('deep_research_owner')!='BIL00' or state.get('deep_research_times_vancouver')!=['00:58','12:58']:err('state/CURRENT.json','deep research owner/schedule mismatch')
 cp=ROOT/state.get('active_control_manifest_path',''); ap=ROOT/state.get('active_assignment_path','')
 c=load(cp) if cp.exists() else None; a=load(ap) if ap.exists() else None
 validate_obj(c,schemas['control'],str(cp.relative_to(ROOT)) if cp.exists() else 'active-control')
 validate_obj(a,schemas['assignment'],str(ap.relative_to(ROOT)) if ap.exists() else 'active-assignment')
 if not c:err('state/CURRENT.json','active control missing')
 if not a:err('state/CURRENT.json','active assignment missing')
 if c:
  if blob(cp)!=state.get('active_control_manifest_git_identity'):err(str(cp.relative_to(ROOT)),'control blob != state')
  if c.get('task_network_plan_id')!=PLAN or c.get('cohort_id')!=state.get('active_cohort_id'):err(str(cp.relative_to(ROOT)),'control plan/cohort mismatch')
  if c.get('generation_seq')!=state.get('generation_seq') or c.get('parent_state_git_identity')!=state.get('active_parent_state_git_identity'):err(str(cp.relative_to(ROOT)),'control lineage mismatch')
  if set(c.get('files',{}))!=CONTROL:err(str(cp.relative_to(ROOT)),'frozen control file set mismatch')
  for rel,sha in c.get('files',{}).items():
   fp=ROOT/rel
   if not fp.exists():err(str(cp.relative_to(ROOT)),f'missing frozen {rel}')
   elif blob(fp)!=sha:err(str(cp.relative_to(ROOT)),f'frozen file drift {rel}')
 if a:
  if blob(ap)!=state.get('active_assignment_git_identity'):err(str(ap.relative_to(ROOT)),'assignment blob != state')
  pairs={'task_network_plan_id':PLAN,'cohort_id':state.get('active_cohort_id'),'generation_seq':state.get('generation_seq'),'parent_state_git_identity':state.get('active_parent_state_git_identity'),'control_manifest_path':state.get('active_control_manifest_path'),'control_manifest_git_identity':state.get('active_control_manifest_git_identity'),'network_checkpoint_id':state.get('accepted_network_checkpoint_id'),'runtime_state_id':state.get('runtime_state_id'),'network_mode':state.get('network_mode')}
  for k,v in pairs.items():
   if a.get(k)!=v:err(str(ap.relative_to(ROOT)),f'{k} mismatch')
  if set(a.get('workers',{}))!=WORKERS:err(str(ap.relative_to(ROOT)),'worker set mismatch')
  if set(a.get('sealed_slots',[]))!=SEALED:err(str(ap.relative_to(ROOT)),'sealed slot set mismatch')
  if a.get('network_mode')=='GITHUB_BUS_CALIBRATION':
   for w,x in a.get('workers',{}).items():
    if x.get('fresh_allowed') is not False or x.get('opaque_evidence_ids')!=[] or x.get('private_manifest_id') is not None or x.get('private_manifest_git_identity') is not None:err(str(ap.relative_to(ROOT)),f'{w} not replay-only in calibration')

# benchmark successor graph integrity
for program,pdata in (registry or {}).get('programs',{}).items():
 suites=pdata.get('suites',[]); ids={s.get('suite_id') for s in suites}
 if pdata.get('active_suite_id') not in ids:err('benchmark/registry.json',f'{program} active suite missing')
 for s in suites:
  nxt=s.get('successor')
  if nxt is not None and nxt not in ids:err('benchmark/registry.json',f'{program} unknown successor {nxt}')

# validate non-superseded worker reports using the frozen cohort assignment
rr=ROOT/'reports'
if rr.exists():
 for p in rr.rglob('*.json'):
  r=load(p)
  if not r or r.get('cohort_id') in sup:continue
  validate_obj(r,schemas['report'],str(p.relative_to(ROOT)))
  w=r.get('worker_id'); cohort=r.get('cohort_id')
  if w not in WORKERS or p.stem!=w or p.parent.name!=cohort:err(str(p.relative_to(ROOT)),'report path/worker mismatch');continue
  cap=ROOT/'assignments'/f'{cohort}.json'; a=load(cap) if cap.exists() else None
  if not a:err(str(p.relative_to(ROOT)),'missing assignment');continue
  cpath=ROOT/a.get('control_manifest_path',''); c=load(cpath) if cpath.exists() else None
  if not c:err(str(p.relative_to(ROOT)),'missing control');continue
  expect={'task_network_plan_id':PLAN,'cohort_id':cohort,'assignment_id':a.get('assignment_id'),'assignment_git_identity':blob(cap),'generation_seq':a.get('generation_seq'),'parent_state_git_identity':a.get('parent_state_git_identity'),'control_manifest_id':a.get('control_manifest_id'),'control_manifest_git_identity':a.get('control_manifest_git_identity'),'network_checkpoint_id':a.get('network_checkpoint_id'),'runtime_state_id':a.get('runtime_state_id'),'visibility_token':a.get('workers',{}).get(w,{}).get('visibility_token'),'worker_auth_scheme':'PS-HMAC-SHA256-WORKER-PROOF-1','worker_auth_commitment':auth.get('commitments',{}).get(w),'status':'VALID_ASSIGNED_REPORT','public_safety_status':'PASS'}
  for k,v in expect.items():
   if r.get(k)!=v:err(str(p.relative_to(ROOT)),f'{k} mismatch')
  h=r.get('session_header',{})
  if h.get('session_name')!=SESSION_NAMES.get(w):err(str(p.relative_to(ROOT)),'session name mismatch')
  if h.get('iteration_id')!=cohort or h.get('iteration_number')!=a.get('generation_seq') or h.get('role_id')!=w:err(str(p.relative_to(ROOT)),'session iteration/role mismatch')
  if h.get('target_program')!=a.get('workers',{}).get(w,{}).get('target_program'):err(str(p.relative_to(ROOT)),'session target program mismatch')
  if h.get('goal')!=a.get('workers',{}).get(w,{}).get('goal'):err(str(p.relative_to(ROOT)),'session goal mismatch')
  if h.get('runtime_state_id')!=a.get('runtime_state_id'):err(str(p.relative_to(ROOT)),'session runtime mismatch')
  if h.get('execution_mode')!=r.get('mode'):err(str(p.relative_to(ROOT)),'session execution mode mismatch')
  if not HEX64.match(str(r.get('worker_auth_proof',''))):err(str(p.relative_to(ROOT)),'bad HMAC proof format')
  if r.get('ci_status') not in {'PASS','FAIL','PENDING','CI_NOT_OBSERVED'}:err(str(p.relative_to(ROOT)),'bad CI status')
  led=r.get('cost_ledger',{})
  if a.get('network_mode')=='GITHUB_BUS_CALIBRATION':
   if r.get('mode')!='SAFE_REPLAY_ONLY' or r.get('fresh_evidence_ids')!=[] or r.get('private_manifest_id') is not None or r.get('private_manifest_git_identity') is not None:err(str(p.relative_to(ROOT)),'fresh/private data in calibration report')
   if any(led.get(k)!=0 for k in ['fresh_evidence_units_consumed','protected_manifest_reads','benchmark_executions','deep_research_runs']):err(str(p.relative_to(ROOT)),'nonzero protected/benchmark/research cost in calibration')

# terminal artifacts under the current plan
for folder,key in [('verification','verification'),('integration','integration'),('director','director')]:
 d=ROOT/folder
 if d.exists():
  for p in d.glob('*.json'):
   if p.stem in sup:continue
   o=load(p);validate_obj(o,schemas[key],str(p.relative_to(ROOT)))
rd=ROOT/'research/results'
if rd.exists():
 for p in rd.glob('*.json'):
  o=load(p);validate_obj(o,schemas['research'],str(p.relative_to(ROOT)))
bd=ROOT/'benchmark/completion'
if bd.exists():
 for p in bd.rglob('*.json'):
  o=load(p);validate_obj(o,schemas['benchmark_completion'],str(p.relative_to(ROOT)))

# superseded cohorts can never count
for cohort in sup:
 p=ROOT/'director'/f'{cohort}.json'
 if p.exists():
  o=load(p)
  if o and o.get('calibration_counted'):err(str(p.relative_to(ROOT)),'superseded cohort counted')

if E:
 print('BUS VALIDATION FAILED')
 for x in E:print('-',x)
 sys.exit(1)
print('BUS VALIDATION PASS')
