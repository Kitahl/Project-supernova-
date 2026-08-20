#!/usr/bin/env python3
import hashlib,json,os,pathlib,re,sys
from jsonschema import Draft202012Validator

TRUSTED_ROOT=pathlib.Path(__file__).resolve().parents[1]
ROOT=pathlib.Path(os.environ.get('SUPERNOVA_VALIDATE_ROOT',str(TRUSTED_ROOT))).resolve()
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
WORKERS={'MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01'}
REQ_CTX=['supernova/static-control','supernova/report-admission','supernova/transition-admission']
BAD={'hidden_task_name','hidden_task_id','protected_task_id','benchmark_item_id','raw_hidden_prompt','private_manifest_payload','private_manifest_content','worker_auth_secret','worker_auth_secret_hex','secret','credential','api_key','access_token','password'}
E=[]
def err(x):E.append(x)
def load(p):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception as e:
  try: label=str(p.relative_to(ROOT))
  except Exception: label=str(p)
  err(f'{label} invalid JSON: {e}');return None
def blob(p):
 b=p.read_bytes();return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def walk(o,p):
 if isinstance(o,dict):
  for k,v in o.items():
   if k.lower() in BAD:err(f'{p}: forbidden public key {k}')
   walk(v,p)
 elif isinstance(o,list):
  for v in o:walk(v,p)
if not ROOT.is_dir():
 err(f'validation root is not a directory: {ROOT}')
else:
 for p in ROOT.rglob('*.json'):
  if '.git' in p.parts:continue
  o=load(p)
  if o is not None:walk(o,str(p.relative_to(ROOT)))
state=load(ROOT/'state/CURRENT.json');plan=load(ROOT/'plan/PLAN.json');auth=load(ROOT/'config/worker_auth.json');reg=load(ROOT/'benchmark/registry.json');policy=load(ROOT/'config/repo_policy.json');cfg=load(ROOT/'branch/CONFIG.json');freeze=load(ROOT/'config/protocol_freeze.json');pools=load(ROOT/'benchmark/pool_disposition.json');lanes=load(ROOT/'research/open_lanes.json')
substrate=load(ROOT/'config/substrate_epoch_v25.json') if (ROOT/'config/substrate_epoch_v25.json').is_file() else None
parallel=load(ROOT/'config/read_only_probe_parallelism_v25.json') if (ROOT/'config/read_only_probe_parallelism_v25.json').is_file() else None
if not all([state,plan,auth,reg,policy,cfg,freeze,pools,lanes]):err('missing canonical v2.5 state/plan/auth/registry/policy/freeze/pools/research gate/branch config')
if state:
 try:
  s=json.loads((ROOT/'schemas/state.schema.json').read_text());Draft202012Validator.check_schema(s)
  for e in Draft202012Validator(s).iter_errors(state):err(f'state schema: {e.message}')
 except Exception as e:err(f'state schema execution failed: {e}')
if plan and plan.get('task_network_plan_id')!=PLAN:err('plan ID mismatch')
if plan and plan.get('protocol_version')!='2.5':err('plan protocol != 2.5')
if state and state.get('task_network_plan_id')!=PLAN:err('state plan ID mismatch')
if state and state.get('protocol_version')!='2.5':err('state protocol != 2.5')
if state and state.get('transport_mode')!='BRANCH_GITOPS':err('state transport != BRANCH_GITOPS')
if set((auth or {}).get('commitments',{}))!=WORKERS:err('worker commitment set mismatch')
if (auth or {}).get('scheme')!='PS-HMAC-SHA256-CANONICAL-REPORT-2':err('worker auth metadata scheme mismatch')
if (cfg or {}).get('task_network_plan_id')!=PLAN or (cfg or {}).get('worker_auth_scheme')!='PS-HMAC-SHA256-CANONICAL-REPORT-2':err('branch config plan/auth mismatch')
if freeze:
 if freeze.get('frozen_protocol_version')!='2.5':err('protocol freeze != 2.5')
 if freeze.get('status')!='FROZEN_UNTIL_TWO_CLEAN_COUNTABLE_COHORTS':err('protocol freeze status mismatch')
if pools:
 if pools.get('task_network_plan_id')!=PLAN or pools.get('protocol_version')!='2.5':err('benchmark pool disposition identity mismatch')
 mapped=set((pools.get('programs',{}).get('MASTERMIND',{}) or {}).keys())|set((pools.get('programs',{}).get('MATH_FOUNDRY',{}) or {}).keys())
 registry_ids={s.get('suite_id') for p in (reg or {}).get('programs',{}).values() for s in p.get('suites',[])}
 if registry_ids-mapped:err('benchmark suites missing Stage-1 pool disposition: '+repr(sorted(registry_ids-mapped)))
if policy:
 if policy.get('required_main_status_contexts')!=REQ_CTX:err('repo policy required contexts mismatch')
 if policy.get('fresh_gate')!='BLOCK':err('fresh gate must remain BLOCK before T0')
if lanes:
 if lanes.get('t0_qualified') is False:
  bad=[x for x in lanes.get('open_lanes',[]) if x.get('lane_id')!='T0-TRANSPORT-CLOSURE' and x.get('allowed_at_research_slots')]
  if bad:err('non-T0 research lane open while T0 unqualified')
if substrate:
 if substrate.get('task_network_plan_id')!=PLAN or substrate.get('protocol_version')!='2.5':err('substrate epoch identity mismatch')
 if substrate.get('status')!='FROZEN_FOR_COUNTABLE_CALIBRATION':err('substrate epoch is not frozen for countable calibration')
 if not (substrate.get('countable_freeze') or {}).get('ready'):err('substrate epoch countable freeze not ready')
if parallel:
 if parallel.get('task_network_plan_id')!=PLAN or parallel.get('protocol_version')!='2.5':err('read-only parallelism identity mismatch')
 if parallel.get('currently_enabled') is not False:err('read-only probe parallelism must remain disabled during T0 calibration')
for wf in (ROOT/'.github/workflows').glob('*.yml'):
 for line in wf.read_text(encoding='utf-8').splitlines():
  if re.search(r'^\s*-\s+uses:',line):
   ref=line.split('@',1)[1].split()[0] if '@' in line else ''
   if not re.fullmatch(r'[0-9a-f]{40}',ref):err(f'{wf.relative_to(ROOT)} mutable action ref: {line.strip()}')
if state:
 if state.get('fresh_allowed_globally') and state.get('repo_policy_status')!='VERIFIED_PROTECTED_SOURCE_BOUND':err('fresh enabled while source-bound repo policy unverified')
 if state.get('calibration_countable_current') and state.get('repo_policy_status')!='VERIFIED_PROTECTED_SOURCE_BOUND':err('countable calibration while source-bound repo policy unverified')
 if state.get('benchmark_registry_git_identity')!=blob(ROOT/'benchmark/registry.json'):err('benchmark registry blob mismatch')
 if state.get('worker_auth_scheme')!='PS-HMAC-SHA256-CANONICAL-REPORT-2':err('state worker auth scheme mismatch')
 if state.get('calibration_countable_current'):
  if not substrate:err('countable calibration missing frozen substrate epoch')
  else:
   mf=(substrate.get('math_foundry') or {}).get('source_archive_sha256')
   mm=(substrate.get('mastermind') or {}).get('sha256')
   if state.get('foundry_sha256')!=mf:err('countable state Foundry hash does not match frozen substrate epoch')
   if state.get('mastermind_sha256')!=mm:err('countable state Mastermind hash does not match frozen substrate epoch')
  if not parallel:err('countable calibration missing read-only parallelism policy')
if E:
 print('CANONICAL BUS VALIDATION FAILED');[print('-',e) for e in E];sys.exit(1)
print('CANONICAL BUS VALIDATION PASS')
