#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, re, subprocess, sys
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
WORKERS={'MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01'}
SESS={'MF01':'PS-MF-W01 | Representation Lab','MF02':'PS-MF-W02 | E1 Solver Routing','MF03':'PS-MF-W03 | Lemma & Operator Lab','MF04':'PS-MF-W04 | Adversarial Falsifier','MF05':'PS-MF-W05 | Product Closure','MM01':'PS-MM-W01 | React Mechanisms','MM02':'PS-MM-W02 | DeepSWE Mechanisms','MM03':'PS-MM-W03 | SlopCode Contracts','MM04':'PS-MM-W04 | Senior SWE Architecture','MM05':'PS-MM-W05 | E3 Mechanism Controls','MM07':'PS-MM-W07 | Before/After Self-Bench','EXT01':'PS-JOINT-A01 | Runtime & Transport Audit'}
BAD={'hidden_task_name','hidden_task_id','protected_task_id','benchmark_item_id','raw_hidden_prompt','private_manifest_payload','private_manifest_content','worker_auth_secret','worker_auth_secret_hex','secret','credential','api_key','access_token','password'}
HEX40=re.compile(r'^[0-9a-f]{40}$')
def git(*a):
 p=subprocess.run(['git','-C',str(ROOT),*a],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);return p.returncode,p.stdout.strip(),p.stderr.strip()
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def blob(path):
 b=path.read_bytes();return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def context(branch):
 m=re.fullmatch(r'ps/work/([^/]+)/([^/]+)',branch)
 if m:return 'worker',m.group(1),m.group(2)
 for kind in ('verify','integrate','consolidate'):
  m=re.fullmatch(rf'ps/{kind}/([^/]+)',branch)
  if m:return kind,m.group(1),None
 m=re.fullmatch(r'ps/gen/(.+)',branch)
 return ('generation',m.group(1),None) if m else (None,None,None)
def walk_public(o,path,errors):
 if isinstance(o,dict):
  for k,v in o.items():
   if k.lower() in BAD:errors.append(f'{path}: forbidden public key {k}')
   walk_public(v,path,errors)
 elif isinstance(o,list):
  for v in o:walk_public(v,path,errors)
def schema(path):
 s=load(ROOT/path);Draft202012Validator.check_schema(s);return s
def validate(branch,generation_head):
 errors=[];kind,cohort,worker=context(branch)
 if not kind:return [f'unsupported branch {branch}']
 cp=ROOT/'control'/f'{cohort}.json';ap=ROOT/'assignments'/f'{cohort}.json'
 if not cp.exists() or not ap.exists():return [f'{cohort}: control/assignment missing']
 c=load(cp);a=load(ap)
 for obj,sp,label in [(c,'schemas/control.schema.json','control'),(a,'schemas/assignment.schema.json','assignment')]:
  for e in Draft202012Validator(schema(sp)).iter_errors(obj):errors.append(f'{label}: {e.message}')
 if c.get('task_network_plan_id')!=PLAN or a.get('task_network_plan_id')!=PLAN:errors.append('plan mismatch')
 if c.get('cohort_id')!=cohort or a.get('cohort_id')!=cohort:errors.append('cohort mismatch')
 if a.get('control_manifest_git_identity')!=blob(cp):errors.append('assignment control blob mismatch')
 if a.get('generation_base_head')!=generation_head:errors.append('assignment generation head mismatch')
 release=c.get('control_release_commit_sha');tree=c.get('control_release_tree_sha')
 if not isinstance(release,str) or not HEX40.fullmatch(release):errors.append('bad control release commit')
 else:
  rc,out,_=git('rev-parse',f'{release}^{{tree}}')
  if rc or out!=tree:errors.append('control release tree mismatch')
  for rel in c.get('required_control_paths',[]):
   rc,expected,_=git('rev-parse',f'{release}:{rel}')
   rc2,observed,_=git('rev-parse',f'HEAD:{rel}')
   if rc or rc2 or expected!=observed:errors.append(f'frozen control drift {rel}')
 rc,_,_=git('merge-base','--is-ancestor',generation_head,'HEAD')
 if rc:errors.append('branch does not descend from generation head')
 if kind=='generation':
  rc,out,_=git('rev-parse','HEAD')
  if rc or out!=generation_head:errors.append('generation branch moved after freeze')
 if kind=='worker' and worker:
  if worker not in WORKERS:errors.append('unknown worker')
  if a.get('workers',{}).get(worker,{}).get('worker_branch')!=branch:errors.append('worker branch assignment mismatch')
  rc,out,_=git('diff','--name-only',generation_head,'HEAD');changed=[x for x in out.splitlines() if x]
  expected=f'reports/{cohort}/{worker}.json'
  if changed!=[expected]:errors.append(f'worker diff must be exactly {expected}; got {changed}')
  rp=ROOT/expected
  if not rp.exists():errors.append('assigned report missing')
  else:
   r=load(rp);walk_public(r,expected,errors)
   for e in Draft202012Validator(schema('schemas/branch_report.schema.json')).iter_errors(r):errors.append(f'report schema: {e.message}')
   aw=a.get('workers',{}).get(worker,{})
   h=r.get('session_header',{})
   exact={'session_name':SESS.get(worker),'target_program':aw.get('target_program'),'phase':a.get('phase'),'iteration_id':cohort,'iteration_number':a.get('generation_seq'),'role_id':worker,'goal':aw.get('goal'),'plan_id':PLAN,'runtime_state_id':a.get('runtime_state_id'),'model_target':'GPT-5.6 Sol','reasoning_effort_target':'EXTRA_HIGH'}
   for k,v in exact.items():
    if h.get(k)!=v:errors.append(f'strict session mismatch {k}')
   ex={'task_network_plan_id':PLAN,'cohort_id':cohort,'worker_id':worker,'generation_seq':a.get('generation_seq'),'generation_head_sha':generation_head,'worker_branch':branch,'assignment_id':a.get('assignment_id'),'assignment_git_identity':blob(ap),'parent_state_git_identity':a.get('parent_state_git_identity'),'control_manifest_id':a.get('control_manifest_id'),'control_manifest_git_identity':blob(cp),'network_checkpoint_id':a.get('network_checkpoint_id'),'runtime_state_id':a.get('runtime_state_id'),'visibility_token':aw.get('visibility_token'),'worker_auth_scheme':'PS-HMAC-SHA256-CANONICAL-REPORT-2','status':'VALID_ASSIGNED_REPORT','public_safety_status':'PASS','origin_reread_claim':False}
   for k,v in ex.items():
    if r.get(k)!=v:errors.append(f'report binding mismatch {k}')
   if a.get('network_mode')=='GITHUB_BRANCH_CALIBRATION':
    led=r.get('cost_ledger',{})
    if r.get('mode')!='SAFE_REPLAY_ONLY':errors.append('calibration report not replay-only')
    if r.get('fresh_evidence_ids')!=[] or r.get('private_manifest_id') is not None:errors.append('fresh/private evidence in calibration')
    for k in ('fresh_evidence_units_consumed','protected_manifest_reads','benchmark_executions','deep_research_runs'):
     if led.get(k)!=0:errors.append(f'nonzero calibration cost {k}')
 if kind=='verify':
  rc,out,_=git('diff','--name-only',generation_head,'HEAD');changed=[x for x in out.splitlines() if x];expected=f'verification/{cohort}.json'
  if changed!=[expected]:errors.append(f'verifier diff must be exactly {expected}; got {changed}')
  p=ROOT/expected
  if p.exists():
   for e in Draft202012Validator(schema('schemas/branch_verification.schema.json')).iter_errors(load(p)):errors.append(f'verification schema: {e.message}')
  else:errors.append('verification missing')
 if kind=='integrate':
  rc,out,_=git('diff','--name-only',generation_head,'HEAD');changed=[x for x in out.splitlines() if x];expected=f'integration/{cohort}.json'
  if changed!=[expected]:errors.append(f'integrator diff must be exactly {expected}; got {changed}')
  p=ROOT/expected
  if p.exists():
   for e in Draft202012Validator(schema('schemas/branch_integration.schema.json')).iter_errors(load(p)):errors.append(f'integration schema: {e.message}')
  else:errors.append('integration missing')
 return errors
if __name__=='__main__':
 pa=argparse.ArgumentParser();pa.add_argument('--branch',required=True);pa.add_argument('--generation-head',required=True);z=pa.parse_args();E=validate(z.branch,z.generation_head)
 if E:
  print('BRANCH STRUCTURAL VALIDATION FAILED');[print('-',x) for x in E];sys.exit(1)
 print(f'BRANCH STRUCTURAL VALIDATION PASS branch={z.branch}')
