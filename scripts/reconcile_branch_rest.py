#!/usr/bin/env python3
"""REST-only diagnostics for the branch bus.

This helper is intentionally NON-AUTHORITATIVE for structural admission. The
checkout-based `scripts/reconcile_branch_statuses.py` is the only writer of the
required structural contexts. REST diagnostics publish only `supernova/rest-*`
contexts so a weaker/partial predicate can never overwrite authoritative PASS/FAIL.
"""
from __future__ import annotations
import base64,json,os,re,urllib.error,urllib.parse,urllib.request
TOKEN=os.environ.get('GITHUB_TOKEN','');REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-');API='https://api.github.com/repos/'+REPO
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa';WORKERS=('MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01');HEX40=re.compile(r'^[0-9a-f]{40}$')
GEN_CTX='supernova/rest-branch-generation-diagnostic';WORKER_CTX='supernova/rest-branch-worker-diagnostic';VERIFY_CTX='supernova/rest-branch-verify-diagnostic';INTEGRATE_CTX='supernova/rest-branch-integrate-diagnostic';CONSOLIDATE_CTX='supernova/rest-branch-consolidate-diagnostic'

def req(path,method='GET',data=None):
 r=urllib.request.Request(API+path,data=(json.dumps(data).encode() if data is not None else None),method=method);r.add_header('Accept','application/vnd.github+json');r.add_header('X-GitHub-Api-Version','2022-11-28')
 if TOKEN:r.add_header('Authorization','Bearer '+TOKEN)
 with urllib.request.urlopen(r,timeout=30) as z:
  raw=z.read();return json.loads(raw) if raw else None

def file_text(path,ref):
 o=req('/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(ref,safe=''))
 if not isinstance(o,dict) or o.get('type')!='file':raise RuntimeError(f'{path}@{ref}: not a file')
 return o,base64.b64decode(o.get('content','')).decode('utf-8')
def content(path,ref):
 o,t=file_text(path,ref);return o,json.loads(t)
def branch_head(branch):
 try:return req('/branches/'+urllib.parse.quote(branch,safe=''))['commit']['sha']
 except urllib.error.HTTPError as e:
  if e.code==404:return None
  raise
def changed_files(base,head):
 c=req('/compare/'+base+'...'+head);return [f['filename'] for f in c.get('files',[]) if f.get('status')!='unchanged']
def status(sha,ctx,state,desc):req('/statuses/'+sha,'POST',{'state':state,'context':ctx,'description':desc[:140]})

def expected_generation_paths(state,control):
 paths={state['active_control_manifest_path'],state['active_assignment_path']}
 if state.get('calibration_countable_current') is True:
  paths.add(f"liveness/{state['active_cohort_id']}.json")
 return paths

def generation_errors(state,G):
 errors=[];gen=state['generation_branch'];gh=branch_head(gen)
 if gh!=G:errors.append(f'generation ref {gh} != {G}')
 try:
  cm,control=content(state['active_control_manifest_path'],G);am,assignment=content(state['active_assignment_path'],G)
  if cm['sha']!=state['active_control_manifest_git_identity']:errors.append('state control blob mismatch')
  if am['sha']!=state['active_assignment_git_identity']:errors.append('state assignment blob mismatch')
  if control.get('task_network_plan_id')!=PLAN or assignment.get('task_network_plan_id')!=PLAN:errors.append('generation plan mismatch')
  root=control.get('control_release_commit_sha')
  if not isinstance(root,str) or not HEX40.fullmatch(root):errors.append('bad generation root')
  elif assignment.get('generation_root_sha')!=root:errors.append('assignment root mismatch')
  files=changed_files(root,G) if isinstance(root,str) and HEX40.fullmatch(root) else []
  expected=expected_generation_paths(state,control)
  if set(files)!=expected:errors.append('generation root->G changed paths '+repr(files)+' expected '+repr(sorted(expected)))
  if isinstance(root,str) and HEX40.fullmatch(root):
   for p in control.get('required_control_paths',[]):
    a,_=file_text(p,root);b,_=file_text(p,G)
    if a['sha']!=b['sha']:errors.append('frozen control drift '+p)
  if state.get('calibration_countable_current') is True:
   lp=f"liveness/{state['active_cohort_id']}.json"
   try:lm,live=content(lp,G)
   except Exception as exc:errors.append('countable liveness missing: '+str(exc))
   else:
    if live.get('cohort_id')!=state['active_cohort_id']:errors.append('liveness cohort mismatch')
    if live.get('generation_seq')!=state.get('generation_seq'):errors.append('liveness generation mismatch')
    if live.get('generation_root_sha')!=root:errors.append('liveness root mismatch')
    if live.get('control_manifest_git_identity')!=cm.get('sha'):errors.append('liveness control blob mismatch')
    if live.get('assignment_git_identity')!=am.get('sha'):errors.append('liveness assignment blob mismatch')
 except Exception as exc:errors.append('generation exception: '+repr(exc))
 return errors

def main():
 _,state=content('state/CURRENT.json','main')
 if state.get('task_network_plan_id')!=PLAN or state.get('transport_mode')!='BRANCH_GITOPS':return 0
 cohort=state['active_cohort_id'];G=state['generation_head_sha'];errs=generation_errors(state,G)
 status(G,GEN_CTX,'failure' if errs else 'success',('DIAGNOSTIC FAIL: '+errs[0]) if errs else 'REST diagnostic generation PASS; non-authoritative')
 try:_,assignment=content(state['active_assignment_path'],G)
 except Exception:return 0
 for w in WORKERS:
  branch=state['worker_branches'][w];H=branch_head(branch)
  if H is None:status(G,WORKER_CTX,'failure',w+': diagnostic assigned branch missing');continue
  if H==G:status(H,WORKER_CTX,'pending',w+': diagnostic awaiting receipt');continue
  path=f'reports/{cohort}/{w}.json';e=[]
  try:
   files=changed_files(G,H)
   if files!=[path]:e.append('diff != exactly assigned report')
   _,r=content(path,H)
   if r.get('cohort_id')!=cohort or r.get('worker_id')!=w or r.get('generation_head_sha')!=G:e.append('identity binding mismatch')
   if r.get('worker_branch')!=branch:e.append('branch binding mismatch')
  except Exception as exc:e.append(str(exc))
  status(H,WORKER_CTX,'failure' if e else 'success',w+(': diagnostic FAIL '+e[0] if e else ': REST diagnostic PASS; non-authoritative'))
 for key,ctx,path in (('verifier_branch',VERIFY_CTX,f'verification/{cohort}.json'),('integrator_branch',INTEGRATE_CTX,f'integration/{cohort}.json')):
  H=branch_head(state[key])
  if H is None:continue
  if H==G:status(H,ctx,'pending',key+': diagnostic awaiting receipt');continue
  try:files=changed_files(G,H);ok=files==[path];status(H,ctx,'success' if ok else 'failure',key+(': REST diagnostic PASS' if ok else ': REST diagnostic path mismatch'))
  except Exception as exc:status(H,ctx,'failure',key+': diagnostic '+str(exc)[:100])
 cb=state.get('consolidation_branch');H=branch_head(cb) if cb else None
 if H:status(H,CONSOLIDATE_CTX,'pending','REST consolidation diagnostic is informational only')
 print('REST diagnostic reconciliation complete for',cohort);return 0
if __name__=='__main__':raise SystemExit(main())
