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
scheduler_attestation=load(ROOT/'config/scheduler_attestation_authority_v25.json') if (ROOT/'config/scheduler_attestation_authority_v25.json').is_file() else None

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

# Root11 is prospective. Immutable Gen12 remains root9 evidence and does not
# acquire nonce/scheduler fields retroactively.
if root_epoch and root_epoch.get('epoch')==11:
 if root_epoch.get('schema_version')!='PS-ROOT-TCB-EPOCH-2.5-11':err('root11 schema/version mismatch')
 if root_epoch.get('scheduler_task_cardinality')!=15 or root_epoch.get('scheduler_sixteenth_lane')!='FORBIDDEN':err('root11 exact 15-lane scheduler invariant mismatch')
 if root_epoch.get('scheduler_admission_guard')!='scripts/scheduler_admission_guard.py':err('root11 scheduler admission guard missing')
 if root_epoch.get('generation_identity_dag')!='CONTROL_TO_ASSIGNMENT_TO_LIVENESS_TO_SCHEDULER':err('root11 generation DAG mismatch')
 for path,title in (('schemas/scheduler_manifest.schema.json','PS-SCHEDULER-MANIFEST-2.5-2'),('schemas/preactivation_receipt.schema.json','PS-PREACTIVATION-RECEIPT-2.5-3'),('schemas/scheduler_admission.schema.json','PS-SCHEDULER-ADMISSION-2.5-3'),('schemas/scheduler_admission_copy.schema.json','PS-SCHEDULER-ADMISSION-COPY-2.5-1'),('schemas/scheduler_inventory_attestation.schema.json','PS-SCHEDULER-INVENTORY-ATTESTATION-2.5-1'),('schemas/staged_candidate.schema.json','PS-STAGED-CANDIDATE-2.5-1')):
  s=check_schema(path)
  if s and s.get('title')!=title:err(path+' identity mismatch')
 if not task_registry or task_registry.get('active_task_count')!=15 or task_registry.get('no_sixteenth_lane') is not True or task_registry.get('same_task_session_each_run') is not True:err('root11 task registry does not preserve exact 15 same sessions')
 else:
  roles=[x.get('role_id') for x in task_registry.get('tasks',[]) if isinstance(x,dict)]
  if len(roles)!=15 or set(roles)!=ROLES or len(set(roles))!=15:err('root11 task registry role partition mismatch')
  task_ids=[x.get('scheduler_task_id') for x in task_registry.get('tasks',[]) if isinstance(x,dict)]
  if len(task_ids)!=15 or len(set(task_ids))!=15 or any(not re.fullmatch(r'[0-9a-f]{32}',str(x)) for x in task_ids):err('root11 frozen scheduler task identities invalid')
 if not scheduler_attestation or scheduler_attestation.get('trusted_workflow')!='.github/workflows/supernova-preactivation-admission.yml' or scheduler_attestation.get('trusted_script')!='scripts/reconcile_preactivation_admission.py' or scheduler_attestation.get('exact_existing_task_count')!=15 or scheduler_attestation.get('worker_hmac_recomputation_required') is not True or scheduler_attestation.get('max_attempt_duration_seconds')!=600 or scheduler_attestation.get('scheduler_jitter_budget_seconds')!=60 or scheduler_attestation.get('retry_budget_authority')!='ACCEPTED_MAIN_EXACT_VALUES_CANDIDATE_OVERRIDE_FORBIDDEN':err('root11 scheduler attestation authority missing or weakened')
 for path in ('scripts/reconcile_preactivation_admission.py','scripts/preactivation_publication_state.py','.github/workflows/supernova-preactivation-admission.yml'):
  if not (ROOT/path).is_file():err('root11 trusted preactivation surface missing: '+path)
 expected_preactivation_outcomes=['WAITING_FOR_CHALLENGE','RECEIPT_COMMITTED_PR_MISSING','PR_OPEN_STATUS_PENDING','ADMITTED','REJECTED','BLOCKED']
 if not task_semantics or task_semantics.get('same_task_session_rule')!='SAME_TASK_SESSION' or task_semantics.get('scheduler_readback_rule')!='NORMALIZED_SCHEDULER_READBACK' or task_semantics.get('active_cohort_repair_rule')!='NO_POST_ACTIVATION_CONSTRUCTIVE_REPAIR' or task_semantics.get('preactivation_completion_rule')!='RECEIPT_COMMIT_ALONE_IS_NOT_SUCCESS' or task_semantics.get('preactivation_retry_rule')!='RESUME_FROM_FIRST_MISSING_TRANSITION_AND_NEVER_CREATE_A_SECOND_RECEIPT_COMMIT' or task_semantics.get('preactivation_state_classifier')!='scripts/preactivation_publication_state.py' or task_semantics.get('preactivation_outcomes')!=expected_preactivation_outcomes:err('root11 task semantics weakened')
 if task_registry and (task_registry.get('preactivation_outcomes')!=expected_preactivation_outcomes or 'EXACTLY_ONE_NON_DRAFT_PR' not in str(task_registry.get('preactivation_publication_rule')) or 'RECEIPT_COMMIT_ALONE_IS_NOT_SUCCESS' not in str(task_registry.get('preactivation_publication_rule')) or 'NEVER_CREATE_A_SECOND_RECEIPT_COMMIT' not in str(task_registry.get('preactivation_retry_rule'))):err('root11 task registry preactivation publication contract missing')
 preactivation_workflow=(ROOT/'.github/workflows/supernova-preactivation-admission.yml').read_text(encoding='utf-8') if (ROOT/'.github/workflows/supernova-preactivation-admission.yml').is_file() else ''
 for token in ('pull_request_target:','github.event.pull_request.draft == false','github.event.pull_request.head.repo.full_name == github.repository',"startsWith(github.event.pull_request.base.ref, 'ps/gen/')","startsWith(github.event.pull_request.head.ref, 'ps/preactivate/')"):
  if token not in preactivation_workflow:err('root11 trusted preactivation workflow publication trigger weakened: '+token)
 if not delta_policy or (delta_policy.get('countable') or {}).get('exact_cardinality')!=4 or 'scheduler/{cohort}.json' not in set((delta_policy.get('countable') or {}).get('exact_path_templates') or []):err('root11 countable generation delta does not freeze scheduler manifest')
 if not countable_contract or countable_contract.get('scheduler_manifest_required_for_countable_generation') is not True or countable_contract.get('scheduler_admission_required_before_promotion') is not True:err('root11 countable scheduler admission contract missing')
 control_schema=check_schema('schemas/control.schema.json')
 if control_schema:
  properties=set((control_schema.get('properties') or {}).keys())
  conditional_required=set()
  for clause in control_schema.get('allOf') or []:
   if isinstance(clause,dict) and (clause.get('if') or {}).get('required')==['candidate_nonce']:
    conditional_required.update((clause.get('then') or {}).get('required') or [])
  for key in ('candidate_nonce','generation_root_sha','scheduler_manifest_path','scheduler_admission_required'):
   if key not in properties or key not in conditional_required:err('root11 control schema missing conditional '+key)
  if 'scheduler_manifest_git_identity' in set(control_schema.get('required') or []):err('root11 control schema requires impossible future scheduler blob')
  # Validate only prospective controls that declare scheduler admission. Old frozen controls remain historical evidence.
 if control_schema:
  for p in (ROOT/'control').glob('*.json'):
   c=load(p)
   if isinstance(c,dict) and c.get('scheduler_admission_required') is True:
     for e in Draft202012Validator(control_schema).iter_errors(c):err(f'{p.relative_to(ROOT)} root11 control schema: {e.message}')

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
 archive=state.get('active_staged_candidate_path')
 if archive:
  archive_path=ROOT/archive
  if archive!=f"staging/{state.get('active_cohort_id')}.json" or not archive_path.is_file():err('active root11 staged pointer archive missing/noncanonical')
  elif state.get('active_staged_candidate_git_identity')!=blob(archive_path):err('active root11 staged pointer archive blob mismatch')
  else:
   pointer=load(archive_path)
   if pointer.get('candidate_cohort_id')!=state.get('active_cohort_id') or pointer.get('generation_head_sha')!=state.get('generation_head_sha'):err('active root11 staged pointer/state identity mismatch')
   artifact_bindings=((state.get('active_control_manifest_path'),state.get('active_control_manifest_git_identity'),'control_path','control_git_identity'),(state.get('active_assignment_path'),state.get('active_assignment_git_identity'),'assignment_path','assignment_git_identity'),(pointer.get('liveness_path'),pointer.get('liveness_git_identity'),'liveness_path','liveness_git_identity'),(pointer.get('scheduler_manifest_path'),pointer.get('scheduler_manifest_git_identity'),'scheduler_manifest_path','scheduler_manifest_git_identity'))
   for path,state_identity,pointer_path_key,pointer_identity_key in artifact_bindings:
    if not isinstance(path,str) or path!=pointer.get(pointer_path_key):err('active root11 main-copy path differs from archived pointer '+pointer_path_key);continue
    artifact_path=ROOT/path
    if not artifact_path.is_file():err('active root11 main-copy artifact missing '+path);continue
    observed=blob(artifact_path)
    if observed!=pointer.get(pointer_identity_key):err('active root11 main-copy artifact blob differs from archived pointer '+path)
    if state_identity is not None and observed!=state_identity:err('active root11 state artifact identity mismatch '+path)
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
