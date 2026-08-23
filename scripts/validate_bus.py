#!/usr/bin/env python3
import hashlib,os,pathlib,re,sys
from jsonschema import Draft202012Validator
import strict_json

TRUSTED_ROOT=pathlib.Path(__file__).resolve().parents[1]
ROOT=pathlib.Path(os.environ.get('SUPERNOVA_VALIDATE_ROOT',str(TRUSTED_ROOT))).resolve()
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
WORKERS={'MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01'}
ROLES=WORKERS|{'MM06','MF06','BIL00'}
REQ_CTX=['supernova/static-control','supernova/report-admission','supernova/transition-admission']
BAD={'hidden_task_name','hidden_task_id','protected_task_id','benchmark_item_id','raw_hidden_prompt','private_manifest_payload','private_manifest_content','worker_auth_secret','worker_auth_secret_hex','raw_auth_material','private_key','secret','credential','api_key','access_token','password'}
E=[]
def err(x):E.append(x)
def load(p):
 try:return strict_json.loads(p.read_text(encoding='utf-8'))
 except Exception as e:
  try:label=str(p.relative_to(ROOT))
  except Exception:label=str(p)
  err(f'{label} invalid strict JSON: {e}');return None
def blob(p):
 b=p.read_bytes();return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def walk(o,p):
 if isinstance(o,dict):
  for k,v in o.items():
   if k.lower() in BAD:err(f'{p}: forbidden public key {k}')
   walk(v,p)
 elif isinstance(o,list):
  for v in o:walk(v,p)
def check_schema(path):
 try:
  s=load(ROOT/path)
  if s is None:return None
  Draft202012Validator.check_schema(s);return s
 except Exception as e:err(f'{path} schema invalid: {e}');return None

if not ROOT.is_dir():err(f'validation root is not a directory: {ROOT}')
else:
 for p in ROOT.rglob('*.json'):
  if '.git' in p.parts:continue
  o=load(p)
  if o is not None:walk(o,str(p.relative_to(ROOT)))

state=load(ROOT/'state/CURRENT.json');plan=load(ROOT/'plan/PLAN.json');auth=load(ROOT/'config/worker_auth.json');reg=load(ROOT/'benchmark/registry.json');policy=load(ROOT/'config/repo_policy.json');cfg=load(ROOT/'branch/CONFIG.json');freeze=load(ROOT/'config/protocol_freeze.json');pools=load(ROOT/'benchmark/pool_disposition.json');lanes=load(ROOT/'research/open_lanes.json')
substrate=load(ROOT/'config/substrate_epoch_v25.json') if (ROOT/'config/substrate_epoch_v25.json').is_file() else None
parallel=load(ROOT/'config/read_only_probe_parallelism_v25.json') if (ROOT/'config/read_only_probe_parallelism_v25.json').is_file() else None
root_epoch=load(ROOT/'config/root_tcb_epoch_v25.json') if (ROOT/'config/root_tcb_epoch_v25.json').is_file() else None
task_registry=load(ROOT/'config/task_registry_v25.json') if (ROOT/'config/task_registry_v25.json').is_file() else None
task_semantics=load(ROOT/'config/task_registry_semantics_v25.json') if (ROOT/'config/task_registry_semantics_v25.json').is_file() else None
delta_policy=load(ROOT/'config/generation_delta_policy_v25.json') if (ROOT/'config/generation_delta_policy_v25.json').is_file() else None
countable_contract=load(ROOT/'config/countable_control_set_v25.json') if (ROOT/'config/countable_control_set_v25.json').is_file() else None

if not all([state,plan,auth,reg,policy,cfg,freeze,pools,lanes]):err('missing canonical v2.5 state/plan/auth/registry/policy/freeze/pools/research gate/branch config')
if state:
 s=check_schema('schemas/state.schema.json')
 if s:
  for e in Draft202012Validator(s).iter_errors(state):err(f'state schema: {e.message}')
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
if lanes and lanes.get('t0_qualified') is False:
 bad=[x for x in lanes.get('open_lanes',[]) if x.get('lane_id')!='T0-TRANSPORT-CLOSURE' and x.get('allowed_at_research_slots')]
 if bad:err('non-T0 research lane open while T0 unqualified')
if substrate:
 if substrate.get('task_network_plan_id')!=PLAN or substrate.get('protocol_version')!='2.5':err('substrate epoch identity mismatch')
 if substrate.get('status')!='FROZEN_FOR_COUNTABLE_CALIBRATION':err('substrate epoch is not frozen for countable calibration')
 if not (substrate.get('countable_freeze') or {}).get('ready'):err('substrate epoch countable freeze not ready')
if parallel:
 if parallel.get('task_network_plan_id')!=PLAN or parallel.get('protocol_version')!='2.5':err('read-only parallelism identity mismatch')
 if parallel.get('currently_enabled') is not False:err('read-only probe parallelism must remain disabled during T0 calibration')

# Root10 scheduler-admission control is prospective. Legacy active Gen12 is validated under its immutable frozen root9 control;
# no root10 validator may retroactively require scheduler fields in Gen12 control/assignment/liveness.
if root_epoch and root_epoch.get('epoch')==10:
 if root_epoch.get('schema_version')!='PS-ROOT-TCB-EPOCH-2.5-10':err('root10 schema/version mismatch')
 if root_epoch.get('scheduler_task_cardinality')!=15 or root_epoch.get('scheduler_sixteenth_lane')!='FORBIDDEN':err('root10 exact 15-lane scheduler invariant mismatch')
 if root_epoch.get('scheduler_admission_guard')!='scripts/scheduler_admission_guard.py':err('root10 scheduler admission guard missing')
 for path,title in (('schemas/scheduler_manifest.schema.json','PS-SCHEDULER-MANIFEST-2.5-1'),('schemas/preactivation_receipt.schema.json','PS-PREACTIVATION-RECEIPT-2.5-1'),('schemas/scheduler_admission.schema.json','PS-SCHEDULER-ADMISSION-2.5-1')):
  s=check_schema(path)
  if s and s.get('title')!=title:err(path+' identity mismatch')
 if not task_registry or task_registry.get('active_task_count')!=15 or task_registry.get('no_sixteenth_lane') is not True or task_registry.get('same_task_session_each_run') is not True:err('root10 task registry does not preserve exact 15 same sessions')
 else:
  roles=[x.get('role_id') for x in task_registry.get('tasks',[]) if isinstance(x,dict)]
  if len(roles)!=15 or set(roles)!=ROLES or len(set(roles))!=15:err('root10 task registry role partition mismatch')
 if not task_semantics or task_semantics.get('same_task_session_rule')!='SAME_TASK_SESSION' or task_semantics.get('scheduler_readback_rule')!='NORMALIZED_SCHEDULER_READBACK' or task_semantics.get('active_cohort_repair_rule')!='NO_POST_ACTIVATION_CONSTRUCTIVE_REPAIR':err('root10 task semantics weakened')
 if not delta_policy or (delta_policy.get('countable') or {}).get('exact_cardinality')!=4 or 'scheduler/{cohort}.json' not in set((delta_policy.get('countable') or {}).get('exact_path_templates') or []):err('root10 countable generation delta does not freeze scheduler manifest')
 if not countable_contract or countable_contract.get('scheduler_manifest_required_for_countable_generation') is not True or countable_contract.get('scheduler_admission_required_before_promotion') is not True:err('root10 countable scheduler admission contract missing')
 control_schema=check_schema('schemas/control.schema.json')
 if control_schema:
  required=set(control_schema.get('required') or [])
  for key in ('scheduler_manifest_path','scheduler_manifest_git_identity','scheduler_admission_required'):
   if key not in required:err('root10 control schema missing '+key)
 # Validate only root10/prospective controls that declare scheduler admission. Old frozen controls remain historical evidence.
 if control_schema:
  for p in (ROOT/'control').glob('*.json'):
   c=load(p)
   if isinstance(c,dict) and c.get('scheduler_admission_required') is True:
    for e in Draft202012Validator(control_schema).iter_errors(c):err(f'{p.relative_to(ROOT)} root10 control schema: {e.message}')

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
   mf=(substrate.get('math_foundry') or {}).get('source_archive_sha256');mm=(substrate.get('mastermind') or {}).get('sha256')
   if state.get('foundry_sha256')!=mf:err('countable state Foundry hash does not match frozen substrate epoch')
   if state.get('mastermind_sha256')!=mm:err('countable state Mastermind hash does not match frozen substrate epoch')
  if not parallel:err('countable calibration missing read-only parallelism policy')
if E:
 print('CANONICAL BUS VALIDATION FAILED');[print('-',e) for e in E];sys.exit(1)
print('CANONICAL BUS VALIDATION PASS')
