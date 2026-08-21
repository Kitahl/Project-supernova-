#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, pathlib, subprocess, sys
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
HMAC2='PS-HMAC-SHA256-CANONICAL-REPORT-2'
SESS={'MF01':'PS-MF-W01 | Representation Lab','MF02':'PS-MF-W02 | E1 Solver Routing','MF03':'PS-MF-W03 | Lemma & Operator Lab','MF04':'PS-MF-W04 | Adversarial Falsifier','MF05':'PS-MF-W05 | Product Closure','MM01':'PS-MM-W01 | React Mechanisms','MM02':'PS-MM-W02 | DeepSWE Mechanisms','MM03':'PS-MM-W03 | SlopCode Contracts','MM04':'PS-MM-W04 | Senior SWE Architecture','MM05':'PS-MM-W05 | E3 Mechanism Controls','MM07':'PS-MM-W07 | Before/After Self-Bench','EXT01':'PS-JOINT-A01 | Runtime & Transport Audit'}
WORKERS=set(SESS)
def git(*a):
 p=subprocess.run(['git','-C',str(ROOT),*a],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);return p.returncode,p.stdout.strip(),p.stderr.strip()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def blob(p):
 b=p.read_bytes();return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def kind(branch):
 parts=branch.split('/')
 if len(parts)>=3 and parts[0]=='ps':
  if parts[1]=='gen':return 'generation','/'.join(parts[2:]),None
  if parts[1]=='work' and len(parts)>=4:return 'worker',parts[2],parts[3]
  if parts[1] in ('verify','integrate','consolidate'):return parts[1],parts[2],None
 return None,None,None
def sch(p):return load(ROOT/p)
def parse_time(s):
 try:
  x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00'))
  if x.tzinfo is None:return None
  return x.astimezone(dt.timezone.utc)
 except Exception:return None
def execution_mode_errors(report,assignment):
 e=[];h=report.get('session_header',{});hm=h.get('execution_mode');rm=report.get('mode')
 if hm!=rm:e.append('session_header.execution_mode != report.mode')
 if assignment.get('network_mode')=='GITHUB_BRANCH_CALIBRATION':
  if hm!='SAFE_REPLAY_ONLY':e.append('calibration session execution_mode != SAFE_REPLAY_ONLY')
  if rm!='SAFE_REPLAY_ONLY':e.append('calibration report mode != SAFE_REPLAY_ONLY')
 return e
def mm01_role_payload_errors(report):
 e=[]
 if report.get('worker_id')!='MM01' or report.get('mode')!='FRESH_EXECUTION':return e
 payload=report.get('role_payload')
 if not isinstance(payload,dict):return ['MM01 FRESH_EXECUTION requires typed role_payload']
 try:
  schema=sch('schemas/mastermind_react_proposal.schema.json');Draft202012Validator.check_schema(schema)
  for x in Draft202012Validator(schema).iter_errors(payload):e.append('MM01 React proposal schema: '+x.message)
 except Exception as x:e.append('MM01 React proposal schema execution failed: '+repr(x))
 return e
def issue_ledger_errors(report):
 e=[];ledger=report.get('issue_ledger')
 if not isinstance(ledger,list):return e
 ids=[]
 for rec in ledger:
  if isinstance(rec,dict) and isinstance(rec.get('issue_id'),str):ids.append(rec['issue_id'])
 seen=set()
 for issue_id in ids:
  if issue_id in seen:e.append('duplicate issue_ledger issue_id '+issue_id)
  seen.add(issue_id)
 if not ledger and 'ZERO_DELTA' not in str(report.get('executive_status','')):e.append('empty issue_ledger requires explicit ZERO_DELTA executive_status')
 if ledger and 'ZERO_DELTA' in str(report.get('executive_status','')):e.append('ZERO_DELTA executive_status requires empty issue_ledger')
 return e
def liveness_contract_errors(contract,control,assignment,control_blob,assignment_blob):
 e=[]
 try:
  schema=sch('schemas/cohort_liveness_contract.schema.json');Draft202012Validator.check_schema(schema)
  for x in Draft202012Validator(schema).iter_errors(contract):e.append('liveness schema: '+x.message)
 except Exception as x:return ['liveness schema execution failed: '+repr(x)]
 expected={
  'cohort_id':assignment.get('cohort_id'),
  'generation_root_sha':assignment.get('generation_root_sha'),
  'control_manifest_id':assignment.get('control_manifest_id'),
  'control_manifest_git_identity':control_blob,
  'assignment_id':assignment.get('assignment_id'),
  'assignment_git_identity':assignment_blob,
 }
 for key,val in expected.items():
  if contract.get(key)!=val:e.append('liveness binding mismatch '+key)
 lanes=contract.get('lanes')
 if not isinstance(lanes,list):return e+['liveness lanes not array']
 ids=[x.get('lane_id') for x in lanes if isinstance(x,dict)]
 if len(ids)!=12 or set(ids)!=WORKERS or len(set(ids))!=12:e.append('liveness lane set != exact 12 workers')
 by_id={x.get('lane_id'):x for x in lanes if isinstance(x,dict)}
 for w in sorted(WORKERS):
  lane=by_id.get(w);aw=(assignment.get('workers') or {}).get(w,{})
  if not lane:continue
  if lane.get('branch')!=aw.get('worker_branch'):e.append('liveness branch mismatch '+w)
  if lane.get('path')!=f"reports/{assignment.get('cohort_id')}/{w}.json":e.append('liveness path mismatch '+w)
  start=parse_time(lane.get('expected_window_start_utc'));deadline=parse_time(lane.get('deadline_utc'))
  if start is None or deadline is None:e.append('liveness timestamp invalid '+w)
  elif deadline<start:e.append('liveness deadline precedes start '+w)
 return e
def verification_liveness_errors(v,c,G):
 e=[];lp=ROOT/f'liveness/{c}.json'
 if not lp.exists():return ['verification missing frozen liveness contract at generation']
 if v.get('liveness_contract_path')!=f'liveness/{c}.json':e.append('verification liveness_contract_path mismatch')
 if v.get('liveness_contract_git_identity')!=blob(lp):e.append('verification liveness contract blob mismatch')
 if v.get('liveness_contract_binding_verified') is not True:e.append('verification liveness contract binding not verified')
 contract=load(lp);lanes={x['lane_id']:x for x in contract.get('lanes',[]) if isinstance(x,dict) and 'lane_id' in x}
 obs=v.get('lane_liveness_observations')
 if not isinstance(obs,list) or len(obs)!=12:return e+['verification liveness observations != 12']
 seen=set()
 for o in obs:
  wid=o.get('lane_id');seen.add(wid);lane=lanes.get(wid)
  if lane is None:e.append('verification unknown liveness lane '+str(wid));continue
  if o.get('expected_window_start')!=lane.get('expected_window_start_utc'):e.append('verification liveness start mismatch '+wid)
  if o.get('expected_window_end')!=lane.get('deadline_utc'):e.append('verification liveness deadline mismatch '+wid)
  if o.get('receipt_status') in ('RUN_OBSERVED','ZERO_DELTA_RECEIPT_OBSERVED','RUN_LATE'):
   expected=f"{lane.get('branch')}:{lane.get('path')}"
   if o.get('receipt_ref')!=expected:e.append('verification liveness receipt ref mismatch '+wid)
 if seen!=WORKERS:e.append('verification liveness observation lane set mismatch')
 return e
def validate(branch,G):
 e=[];k,c,w=kind(branch)
 if not k:return [f'unsupported branch {branch}']
 cp=ROOT/f'control/{c}.json';ap=ROOT/f'assignments/{c}.json'
 if not cp.exists() or not ap.exists():return ['missing control/assignment']
 co=load(cp);a=load(ap)
 for obj,path in [(co,'schemas/control.schema.json'),(a,'schemas/assignment.schema.json')]:
  for x in Draft202012Validator(sch(path)).iter_errors(obj):e.append(f'{path}: {x.message}')
 if co.get('task_network_plan_id')!=PLAN or a.get('task_network_plan_id')!=PLAN:e.append('plan mismatch')
 auth=sch('config/worker_auth.json')
 if auth.get('scheme')!=HMAC2:e.append('worker auth metadata scheme != PS-HMAC-SHA256-CANONICAL-REPORT-2')
 if co.get('worker_auth_scheme')!=HMAC2:e.append('control worker_auth_scheme mismatch')
 root=co.get('control_release_commit_sha')
 if a.get('generation_root_sha')!=root:e.append('assignment generation root != frozen control-release commit')
 rc,tree,_=git('rev-parse',f'{root}^{{tree}}')
 if rc or tree!=co.get('control_release_tree_sha'):e.append('control-release tree mismatch')
 for rel in co.get('required_control_paths',[]):
  r1,x,_=git('rev-parse',f'{root}:{rel}');r2,y,_=git('rev-parse',f'HEAD:{rel}')
  if r1 or r2 or x!=y:e.append(f'frozen control drift {rel}')
 rc,_,_=git('merge-base','--is-ancestor',G,'HEAD')
 if rc:e.append('branch does not descend from final generation head')
 if k=='generation':
  rc,h,_=git('rev-parse','HEAD')
  if h!=G:e.append('generation moved after freeze')
  rc,out,_=git('diff','--name-only',root,'HEAD');changed=[x for x in out.splitlines() if x]
  expected={f'control/{c}.json',f'assignments/{c}.json'}
  if co.get('calibration_countable') is True:
   lp=ROOT/f'liveness/{c}.json';expected.add(f'liveness/{c}.json')
   if not lp.exists():e.append('countable generation missing frozen liveness contract')
   else:e.extend(liveness_contract_errors(load(lp),co,a,blob(cp),blob(ap)))
  if set(changed)!=expected:e.append('generation root->G changed paths '+repr(changed)+' expected '+repr(sorted(expected)))
 if k=='worker':
  aw=a.get('workers',{}).get(w,{})
  if aw.get('worker_branch')!=branch:e.append('assigned worker branch mismatch')
  rc,out,_=git('diff','--name-only',G,'HEAD');changed=[x for x in out.splitlines() if x];p=f'reports/{c}/{w}.json'
  if changed!=[p]:e.append(f'worker diff {changed} != [{p}]')
  rp=ROOT/p
  if not rp.exists():e.append('report missing')
  else:
   r=load(rp)
   for x in Draft202012Validator(sch('schemas/branch_report.schema.json')).iter_errors(r):e.append(f'report schema: {x.message}')
   e.extend(mm01_role_payload_errors(r));e.extend(issue_ledger_errors(r))
   h=r.get('session_header',{});exact={'session_name':SESS.get(w),'target_program':aw.get('target_program'),'phase':a.get('phase'),'iteration_id':c,'iteration_number':a.get('generation_seq'),'role_id':w,'goal':aw.get('goal'),'plan_id':PLAN,'runtime_state_id':a.get('runtime_state_id'),'model_target':'GPT-5.6 Sol','reasoning_effort_target':'EXTRA_HIGH'}
   for key,val in exact.items():
    if h.get(key)!=val:e.append(f'strict session mismatch {key}')
   e.extend(execution_mode_errors(r,a))
   bindings={'task_network_plan_id':PLAN,'cohort_id':c,'worker_id':w,'generation_seq':a.get('generation_seq'),'generation_head_sha':G,'worker_branch':branch,'assignment_id':a.get('assignment_id'),'assignment_git_identity':blob(ap),'parent_state_git_identity':a.get('parent_state_git_identity'),'control_manifest_id':a.get('control_manifest_id'),'control_manifest_git_identity':blob(cp),'network_checkpoint_id':a.get('network_checkpoint_id'),'runtime_state_id':a.get('runtime_state_id'),'visibility_token':aw.get('visibility_token'),'worker_auth_scheme':HMAC2,'status':'VALID_ASSIGNED_REPORT','public_safety_status':'PASS','origin_reread_claim':False}
   for key,val in bindings.items():
    if r.get(key)!=val:e.append(f'report binding mismatch {key}')
   if a.get('network_mode')=='GITHUB_BRANCH_CALIBRATION':
    led=r.get('cost_ledger',{})
    if r.get('fresh_evidence_ids')!=[] or r.get('private_manifest_id') is not None:e.append('fresh/private calibration data')
    for key in ('fresh_evidence_units_consumed','protected_manifest_reads','benchmark_executions','deep_research_runs'):
     if led.get(key)!=0:e.append(f'nonzero calibration cost {key}')
 if k=='verify':
  rc,out,_=git('diff','--name-only',G,'HEAD');p=f'verification/{c}.json';changed=[x for x in out.splitlines() if x]
  if changed!=[p]:e.append(f'verifier diff invalid {changed}')
  elif (ROOT/p).exists():
   v=load(ROOT/p)
   for x in Draft202012Validator(sch('schemas/branch_verification.schema.json')).iter_errors(v):e.append(f'verification schema: {x.message}')
   e.extend(verification_liveness_errors(v,c,G))
 if k=='integrate':
  rc,out,_=git('diff','--name-only',G,'HEAD');p=f'integration/{c}.json';changed=[x for x in out.splitlines() if x]
  if changed!=[p]:e.append(f'integrator diff invalid {changed}')
  elif (ROOT/p).exists():
   for x in Draft202012Validator(sch('schemas/branch_integration.schema.json')).iter_errors(load(ROOT/p)):e.append(f'integration schema: {x.message}')
 return e
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--branch',required=True);q.add_argument('--generation-head',required=True);z=q.parse_args();E=validate(z.branch,z.generation_head)
 if E:
  print('BRANCH VALIDATION FAILED');[print('-',x) for x in E];sys.exit(1)
 print('BRANCH VALIDATION PASS')
