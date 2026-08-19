#!/usr/bin/env python3
import hashlib,json,pathlib,sys
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
WORKERS={'MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01'}
BAD={'hidden_task_name','hidden_task_id','protected_task_id','benchmark_item_id','raw_hidden_prompt','private_manifest_payload','private_manifest_content','worker_auth_secret','worker_auth_secret_hex','secret','credential','api_key','access_token','password'}
E=[]
def err(x):E.append(x)
def load(p):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception as e:err(f'{p.relative_to(ROOT)} invalid JSON: {e}');return None
def blob(p):
 b=p.read_bytes();return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def walk(o,p):
 if isinstance(o,dict):
  for k,v in o.items():
   if k.lower() in BAD:err(f'{p}: forbidden public key {k}')
   walk(v,p)
 elif isinstance(o,list):
  for v in o:walk(v,p)
for p in ROOT.rglob('*.json'):
 if '.git' in p.parts:continue
 o=load(p)
 if o is not None:walk(o,str(p.relative_to(ROOT)))
state=load(ROOT/'state/CURRENT.json');plan=load(ROOT/'plan/PLAN.json');auth=load(ROOT/'config/worker_auth.json');reg=load(ROOT/'benchmark/registry.json');policy=load(ROOT/'config/repo_policy.json');cfg=load(ROOT/'branch/CONFIG.json')
if not all([state,plan,auth,reg,policy,cfg]):err('missing state/plan/auth/registry/policy/branch config')
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
if (cfg or {}).get('task_network_plan_id')!=PLAN or (cfg or {}).get('worker_auth_scheme')!='PS-HMAC-SHA256-CANONICAL-REPORT-2':err('branch config plan/auth mismatch')
if state:
 if state.get('fresh_allowed_globally') and state.get('repo_policy_status')!='VERIFIED_PROTECTED':err('fresh enabled while repo policy unverified')
 if state.get('calibration_countable_current') and state.get('repo_policy_status')!='VERIFIED_PROTECTED':err('countable calibration while repo policy unverified')
 if state.get('benchmark_registry_git_identity')!=blob(ROOT/'benchmark/registry.json'):err('benchmark registry blob mismatch')
 if state.get('worker_auth_scheme')!='PS-HMAC-SHA256-CANONICAL-REPORT-2':err('state worker auth scheme mismatch')
if E:
 print('CANONICAL BUS VALIDATION FAILED');[print('-',e) for e in E];sys.exit(1)
print('CANONICAL BUS VALIDATION PASS')
