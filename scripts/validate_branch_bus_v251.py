#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, subprocess, sys
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
SESS={'MF01':'PS-MF-W01 | Representation Lab','MF02':'PS-MF-W02 | E1 Solver Routing','MF03':'PS-MF-W03 | Lemma & Operator Lab','MF04':'PS-MF-W04 | Adversarial Falsifier','MF05':'PS-MF-W05 | Product Closure','MM01':'PS-MM-W01 | React Mechanisms','MM02':'PS-MM-W02 | DeepSWE Mechanisms','MM03':'PS-MM-W03 | SlopCode Contracts','MM04':'PS-MM-W04 | Senior SWE Architecture','MM05':'PS-MM-W05 | E3 Mechanism Controls','MM07':'PS-MM-W07 | Before/After Self-Bench','EXT01':'PS-JOINT-A01 | Runtime & Transport Audit'}
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
def validate(branch,G):
 e=[];k,c,w=kind(branch)
 if not k:return [f'unsupported branch {branch}']
 cp=ROOT/f'control/{c}.json';ap=ROOT/f'assignments/{c}.json'
 if not cp.exists() or not ap.exists():return ['missing control/assignment']
 co=load(cp);a=load(ap)
 for obj,path in [(co,'schemas/control.schema.json'),(a,'schemas/assignment.schema.json')]:
  for x in Draft202012Validator(sch(path)).iter_errors(obj):e.append(f'{path}: {x.message}')
 if co.get('task_network_plan_id')!=PLAN or a.get('task_network_plan_id')!=PLAN:e.append('plan mismatch')
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
   h=r.get('session_header',{});exact={'session_name':SESS.get(w),'target_program':aw.get('target_program'),'phase':a.get('phase'),'iteration_id':c,'iteration_number':a.get('generation_seq'),'role_id':w,'goal':aw.get('goal'),'plan_id':PLAN,'runtime_state_id':a.get('runtime_state_id'),'model_target':'GPT-5.6 Sol','reasoning_effort_target':'EXTRA_HIGH'}
   for key,val in exact.items():
    if h.get(key)!=val:e.append(f'strict session mismatch {key}')
   bindings={'task_network_plan_id':PLAN,'cohort_id':c,'worker_id':w,'generation_seq':a.get('generation_seq'),'generation_head_sha':G,'worker_branch':branch,'assignment_id':a.get('assignment_id'),'assignment_git_identity':blob(ap),'parent_state_git_identity':a.get('parent_state_git_identity'),'control_manifest_id':a.get('control_manifest_id'),'control_manifest_git_identity':blob(cp),'network_checkpoint_id':a.get('network_checkpoint_id'),'runtime_state_id':a.get('runtime_state_id'),'visibility_token':aw.get('visibility_token'),'worker_auth_scheme':'PS-HMAC-SHA256-CANONICAL-REPORT-2','status':'VALID_ASSIGNED_REPORT','public_safety_status':'PASS','origin_reread_claim':False}
   for key,val in bindings.items():
    if r.get(key)!=val:e.append(f'report binding mismatch {key}')
   if a.get('network_mode')=='GITHUB_BRANCH_CALIBRATION':
    led=r.get('cost_ledger',{})
    if r.get('mode')!='SAFE_REPLAY_ONLY' or r.get('fresh_evidence_ids')!=[] or r.get('private_manifest_id') is not None:e.append('fresh/private calibration data')
    for key in ('fresh_evidence_units_consumed','protected_manifest_reads','benchmark_executions','deep_research_runs'):
     if led.get(key)!=0:e.append(f'nonzero calibration cost {key}')
 if k=='verify':
  rc,out,_=git('diff','--name-only',G,'HEAD');p=f'verification/{c}.json';changed=[x for x in out.splitlines() if x]
  if changed!=[p]:e.append(f'verifier diff invalid {changed}')
  elif (ROOT/p).exists():
   for x in Draft202012Validator(sch('schemas/branch_verification.schema.json')).iter_errors(load(ROOT/p)):e.append(f'verification schema: {x.message}')
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
