#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.error,urllib.parse,urllib.request
TOKEN=os.environ.get('GITHUB_TOKEN','');REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-');API='https://api.github.com/repos/'+REPO
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
WORKERS=('MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01')
SESS={'MF01':'PS-MF-W01 | Representation Lab','MF02':'PS-MF-W02 | E1 Solver Routing','MF03':'PS-MF-W03 | Lemma & Operator Lab','MF04':'PS-MF-W04 | Adversarial Falsifier','MF05':'PS-MF-W05 | Product Closure','MM01':'PS-MM-W01 | React Mechanisms','MM02':'PS-MM-W02 | DeepSWE Mechanisms','MM03':'PS-MM-W03 | SlopCode Contracts','MM04':'PS-MM-W04 | Senior SWE Architecture','MM05':'PS-MM-W05 | E3 Mechanism Controls','MM07':'PS-MM-W07 | Before/After Self-Bench','EXT01':'PS-JOINT-A01 | Runtime & Transport Audit'}
HEX40=re.compile(r'^[0-9a-f]{40}$');HEX64=re.compile(r'^[0-9a-f]{64}$');BAD={'hidden_task_name','hidden_task_id','protected_task_id','benchmark_item_id','raw_hidden_prompt','private_manifest_payload','private_manifest_content','worker_auth_secret','worker_auth_secret_hex','secret','credential','api_key','access_token','password'}
def api(path,method='GET',body=None):
 r=urllib.request.Request(API+path,data=(json.dumps(body).encode() if body is not None else None),method=method);r.add_header('Accept','application/vnd.github+json');r.add_header('X-GitHub-Api-Version','2022-11-28');
 if TOKEN:r.add_header('Authorization','Bearer '+TOKEN)
 with urllib.request.urlopen(r,timeout=30) as z:
  raw=z.read();return json.loads(raw) if raw else None
def file_text(path,ref):
 o=api('/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(ref,safe=''));return o,base64.b64decode(o.get('content','')).decode('utf-8')
def file_json(path,ref):
 o,t=file_text(path,ref);return o,json.loads(t)
def head(branch):
 try:return api('/branches/'+urllib.parse.quote(branch,safe=''))['commit']['sha']
 except urllib.error.HTTPError as e:
  if e.code==404:return None
  raise
def compare(base,h):return api('/compare/'+base+'...'+h)
def status(sha,ctx,state,desc):api('/statuses/'+sha,'POST',{'state':state,'context':ctx,'description':desc[:140]})
def safe(o):
 if isinstance(o,dict):return all(str(k).lower() not in BAD and safe(v) for k,v in o.items())
 if isinstance(o,list):return all(safe(x) for x in o)
 return True
def paths(base,h):return [f['filename'] for f in compare(base,h).get('files',[]) if f.get('status')!='unchanged']
def envelope(obj,sch):
 if not isinstance(obj,dict):return False,'not object'
 miss=[x for x in sch.get('required',[]) if x not in obj]
 if miss:return False,'missing '+','.join(miss[:3])
 if sch.get('additionalProperties') is False:
  extra=set(obj)-set(sch.get('properties',{}))
  if extra:return False,'extra '+','.join(sorted(extra)[:3])
 return True,'envelope ok'
def main():
 _,state=file_json('state/CURRENT.json','main')
 if state.get('task_network_plan_id')!=PLAN or state.get('transport_mode')!='BRANCH_GITOPS':return 0
 C=state['active_cohort_id'];G=state['generation_head_sha'];gen=state['generation_branch'];errs=[]
 try:
  if head(gen)!=G:errs.append('generation ref moved/missing')
  cm,control=file_json(state['active_control_manifest_path'],G);am,a=file_json(state['active_assignment_path'],G)
  if cm.get('sha')!=state['active_control_manifest_git_identity']:errs.append('control blob mismatch')
  if am.get('sha')!=state['active_assignment_git_identity']:errs.append('assignment blob mismatch')
  root=control.get('control_release_commit_sha')
  if not isinstance(root,str) or not HEX40.fullmatch(root):errs.append('bad generation root')
  if a.get('generation_root_sha')!=root:errs.append('assignment root mismatch')
  if a.get('control_manifest_git_identity')!=cm.get('sha'):errs.append('assignment control binding')
  if set(paths(root,G))!={state['active_control_manifest_path'],state['active_assignment_path']}:errs.append('generation root->head paths invalid')
  for p in control.get('required_control_paths',[]):
   x,_=file_text(p,root);y,_=file_text(p,G)
   if x.get('sha')!=y.get('sha'):errs.append('frozen drift '+p)
 except Exception as e:errs.append('exception '+str(e))
 status(G,'supernova/branch-generation-v252','failure' if errs else 'success',('FAIL '+errs[0]) if errs else 'immutable generation/control/assignment PASS')
 if errs:
  print('generation FAIL',errs);return 1
 _,rs=file_json('schemas/branch_report.schema.json',G)
 for w in WORKERS:
  b=state['worker_branches'][w];H=head(b)
  if H is None:
   status(G,'supernova/branch-worker','failure',w+': branch missing');continue
  if H==G:
   status(H,'supernova/branch-worker','pending',w+': awaiting report');continue
  e=[]
  try:
   p=f'reports/{C}/{w}.json'
   if paths(G,H)!=[p]:e.append('worker diff invalid')
   _,r=file_json(p,H);ok,msg=envelope(r,rs)
   if not ok:e.append(msg)
   aw=a['workers'][w];bind={'task_network_plan_id':PLAN,'cohort_id':C,'worker_id':w,'generation_seq':a['generation_seq'],'generation_head_sha':G,'worker_branch':b,'assignment_id':a['assignment_id'],'assignment_git_identity':am['sha'],'parent_state_git_identity':a['parent_state_git_identity'],'control_manifest_id':a['control_manifest_id'],'control_manifest_git_identity':cm['sha'],'network_checkpoint_id':a['network_checkpoint_id'],'runtime_state_id':a['runtime_state_id'],'visibility_token':aw['visibility_token'],'worker_auth_scheme':'PS-HMAC-SHA256-CANONICAL-REPORT-2','status':'VALID_ASSIGNED_REPORT','public_safety_status':'PASS','origin_reread_claim':False}
   for k,v in bind.items():
    if r.get(k)!=v:e.append('binding '+k)
   sh=r.get('session_header',{});se={'session_name':SESS[w],'target_program':aw['target_program'],'phase':a['phase'],'iteration_id':C,'iteration_number':a['generation_seq'],'role_id':w,'goal':aw['goal'],'plan_id':PLAN,'runtime_state_id':a['runtime_state_id'],'model_target':'GPT-5.6 Sol','reasoning_effort_target':'EXTRA_HIGH'}
   for k,v in se.items():
    if sh.get(k)!=v:e.append('session '+k)
   if not HEX64.fullmatch(str(r.get('worker_auth_proof',''))):e.append('auth proof format')
   if not safe(r):e.append('public safety')
   if a.get('network_mode')=='GITHUB_BRANCH_CALIBRATION':
    led=r.get('cost_ledger',{})
    if r.get('mode')!='SAFE_REPLAY_ONLY' or r.get('fresh_evidence_ids')!=[] or r.get('private_manifest_id') is not None:e.append('fresh/private calibration data')
    if any(led.get(k)!=0 for k in ('fresh_evidence_units_consumed','protected_manifest_reads','benchmark_executions','deep_research_runs')):e.append('nonzero calibration cost')
  except Exception as x:e.append(str(x))
  status(H,'supernova/branch-worker','failure' if e else 'success',w+(': FAIL '+e[0] if e else ': structural PASS; HMAC by MM06'))
 for key,ctx,p,sp in [('verifier_branch','supernova/branch-verify',f'verification/{C}.json','schemas/branch_verification.schema.json'),('integrator_branch','supernova/branch-integrate',f'integration/{C}.json','schemas/branch_integration.schema.json')]:
  b=state[key];H=head(b)
  if H is None:continue
  if H==G:
   status(H,ctx,'pending',key+': awaiting receipt');continue
  e=[]
  try:
   if paths(G,H)!=[p]:e.append('diff invalid')
   _,o=file_json(p,H);_,s=file_json(sp,G);ok,msg=envelope(o,s)
   if not ok:e.append(msg)
   if o.get('task_network_plan_id')!=PLAN or o.get('cohort_id')!=C or o.get('generation_head_sha')!=G:e.append('identity binding')
  except Exception as x:e.append(str(x))
  status(H,ctx,'failure' if e else 'success',key+(': FAIL '+e[0] if e else ': structural PASS'))
 cb=state.get('consolidation_branch');H=head(cb) if cb else None
 if H:
  p=f'history/{C}/CONSOLIDATION.json'
  try:
   _,r=file_json(p,H);B=r.get('expected_main_head');M=head('main');fs=paths(B,H);allowed=all(x.startswith(f'history/{C}/') or x=='state/CURRENT.json' or x=='benchmark/registry.json' or x.startswith('control/') or x.startswith('assignments/') or x.startswith('superseded/') or x.startswith('transitions/') for x in fs);ok=bool(B and HEX40.fullmatch(B) and M==B and allowed and 'state/CURRENT.json' in fs);status(H,'supernova/branch-consolidate','success' if ok else 'failure','consolidation CAS/diff '+('PASS' if ok else 'FAIL'))
  except urllib.error.HTTPError as x:
   if x.code==404:status(H,'supernova/branch-consolidate','pending','awaiting consolidation receipt')
   else:raise
  except Exception as x:status(H,'supernova/branch-consolidate','failure','consolidation error '+str(x)[:100])
 print('v2.5.2 REST reconciliation complete',C);return 0
if __name__=='__main__':raise SystemExit(main())
