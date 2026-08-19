#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, subprocess, sys, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
TOKEN=os.environ.get('GITHUB_TOKEN','');REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-')
def git(*a):
 p=subprocess.run(['git','-C',str(ROOT),*a],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);return p.returncode,p.stdout.strip(),p.stderr.strip()
def post(sha,context,state,description):
 if not TOKEN:raise RuntimeError('GITHUB_TOKEN missing')
 body=json.dumps({'state':state,'context':context,'description':description[:140]}).encode();req=urllib.request.Request(f'https://api.github.com/repos/{REPO}/statuses/{sha}',data=body,method='POST');req.add_header('Authorization',f'Bearer {TOKEN}');req.add_header('Accept','application/vnd.github+json');req.add_header('X-GitHub-Api-Version','2022-11-28');urllib.request.urlopen(req).read()
def remote_head(branch):
 rc,out,_=git('rev-parse',f'refs/remotes/origin/{branch}');return out if rc==0 else None
def summarize_validator_output(output:str)->str:
 lines=[x.strip() for x in output.splitlines() if x.strip()]
 for line in lines:
  if line.startswith('- '):return line[2:]
 if lines:return lines[-1]
 return 'validator failed with no output'
def validate(branch,generation_head):
 rc,out,err=git('checkout','--detach',remote_head(branch) or generation_head)
 if rc:return False,f'checkout failed: {err or out}'
 p=subprocess.run([sys.executable,'scripts/validate_branch_bus_v251.py','--branch',branch,'--generation-head',generation_head],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
 raw=p.stdout.strip()
 print(f'::group::Supernova validator {branch} @ {generation_head}')
 print(raw or '<no validator output>')
 print('::endgroup::')
 return p.returncode==0,summarize_validator_output(raw)
def main():
 git('fetch','--prune','origin','+refs/heads/ps/*:refs/remotes/origin/ps/*')
 git('checkout','--detach','origin/main')
 state=json.loads((ROOT/'state/CURRENT.json').read_text())
 if state.get('transport_mode')!='BRANCH_GITOPS':
  print('No active branch-GitOps state; nothing to reconcile.');return 0
 cohort=state['active_cohort_id'];G=state['generation_head_sha'];gen=state['generation_branch']
 h=remote_head(gen)
 if h!=G:
  msg=f'generation branch missing or moved: observed={h} expected={G}'
  print(msg);post(G,'supernova/branch-generation','failure',msg)
 else:
  ok,msg=validate(gen,G);print(f'branch-generation {"PASS" if ok else "FAIL"}: {msg}');post(G,'supernova/branch-generation','success' if ok else 'failure',msg)
 for worker,branch in state['worker_branches'].items():
  h=remote_head(branch)
  if h is None:continue
  if h==G:post(h,'supernova/branch-worker','pending',f'{worker}: awaiting immutable report');continue
  ok,msg=validate(branch,G);post(h,'supernova/branch-worker','success' if ok else 'failure',f'{worker}: {msg}')
 for kind,key,context in [('verify','verifier_branch','supernova/branch-verify'),('integrate','integrator_branch','supernova/branch-integrate')]:
  branch=state[key];h=remote_head(branch)
  if h is None:continue
  if h==G:post(h,context,'pending',f'{kind}: awaiting receipt');continue
  ok,msg=validate(branch,G);post(h,context,'success' if ok else 'failure',msg)
 branch=state.get('consolidation_branch');h=remote_head(branch) if branch else None
 if h:
  git('checkout','--detach',h)
  receipt=ROOT/'history'/cohort/'CONSOLIDATION.json'
  if not receipt.exists():post(h,'supernova/branch-consolidate','pending','awaiting consolidation receipt')
  else:
   try:
    r=json.loads(receipt.read_text());expected=r.get('expected_main_head');rc,_,_=git('merge-base','--is-ancestor',expected,h) if expected else (1,'','');rc2,out,_=git('diff','--name-only',expected,h) if expected else (1,'','');names=[x for x in out.splitlines() if x];allowed=all(x.startswith(f'history/{cohort}/') or x=='state/CURRENT.json' or x=='benchmark/registry.json' or x.startswith('control/') or x.startswith('assignments/') or x.startswith('superseded/') or x.startswith('transitions/') for x in names);ok=rc==0 and rc2==0 and allowed and 'state/CURRENT.json' in names
    post(h,'supernova/branch-consolidate','success' if ok else 'failure','consolidation CAS/diff policy '+('PASS' if ok else 'FAIL'))
   except Exception as e:post(h,'supernova/branch-consolidate','failure',f'consolidation parse error {e}')
 git('checkout','--detach','origin/main')
 return 0
if __name__=='__main__':raise SystemExit(main())
