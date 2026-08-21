#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, re, shutil, subprocess, tempfile, urllib.request

ROOT=pathlib.Path.cwd().resolve()
REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-')
TOKEN=os.environ.get('GITHUB_TOKEN','')
API='https://api.github.com/repos/'+REPO
OWNER=REPO.split('/',1)[0]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
HEX40=re.compile(r'^[0-9a-f]{40}$')
POLICY_PATH='config/root_rotation_seed_v25.json'


def api(path,method='GET',data=None):
 req=urllib.request.Request(API+path,data=(json.dumps(data).encode() if data is not None else None),method=method)
 req.add_header('Accept','application/vnd.github+json');req.add_header('X-GitHub-Api-Version','2022-11-28')
 if TOKEN:req.add_header('Authorization','Bearer '+TOKEN)
 with urllib.request.urlopen(req,timeout=30) as r:
  raw=r.read();return json.loads(raw) if raw else None

def run(cmd,cwd=ROOT):
 p=subprocess.run(cmd,cwd=str(cwd),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False);return p.returncode,p.stdout

def load(root,path):return json.loads((root/path).read_text(encoding='utf-8'))
def git_blob(path):
 rc,out=run(['git','rev-parse','HEAD:'+path]);return out.strip() if rc==0 else None

def post(sha,ctx,state,desc):
 target=f"https://github.com/{REPO}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}"
 api('/statuses/'+sha,'POST',{'state':state,'context':ctx,'description':desc[:140],'target_url':target})

def fail(sha,reason,policy):
 if isinstance(sha,str) and HEX40.fullmatch(sha):
  post(sha,policy['seed_context'],'failure','root seed refused: '+reason)
  for ctx in policy['required_status_contexts']:post(sha,ctx,'failure','root seed refused: '+reason)
 print('ROOT SEED REFUSED:',reason);return 1

def main():
 policy=load(ROOT,POLICY_PATH)
 try:number=int(os.environ.get('PR_NUMBER','0'))
 except ValueError:number=0
 if number<=0:return 1
 pr=api(f'/pulls/{number}');head=pr.get('head') or {};base=pr.get('base') or {};sha=head.get('sha')
 if os.environ.get('CANDIDATE_DIAGNOSTICS_RESULT')!='success':return fail(sha,'read-only candidate diagnostics did not succeed',policy)
 diagnosed_head=os.environ.get('DIAGNOSED_HEAD_SHA');diagnosed_base=os.environ.get('DIAGNOSED_BASE_SHA')
 if sha!=diagnosed_head or base.get('sha')!=diagnosed_base:return fail(sha,'diagnosed head/base no longer match PR',policy)
 rc,out=run(['git','rev-parse','HEAD']);trusted=out.strip()
 if rc or trusted!=diagnosed_base:return fail(sha,'diagnosed base is not exact accepted main',policy)
 if base.get('ref')!='main' or (head.get('repo') or {}).get('full_name')!=REPO or (pr.get('user') or {}).get('login')!=OWNER:return fail(sha,'same-repo owner PR to main required',policy)
 if not str(head.get('ref','')).startswith(policy['head_prefix_required']):return fail(sha,'head prefix not root-rotation eligible',policy)
 state=load(ROOT,'state/CURRENT.json')
 if state.get('calibration_streak')!=0 or state.get('fresh_allowed_globally') is not False:return fail(sha,'streak must be zero and fresh disabled',policy)
 if (ROOT/policy['one_shot_marker_path']).exists():return fail(sha,'root epoch marker already exists; seed is permanently inert',policy)
 run(['git','fetch','--no-tags','origin',f'pull/{number}/head'])
 rc,_=run(['git','merge-base','--is-ancestor',trusted,sha])
 if rc:return fail(sha,'candidate does not descend from exact accepted main',policy)
 rc,out=run(['git','diff','--name-only',trusted+'...'+sha]);changed=[x for x in out.splitlines() if x]
 if rc or not changed:return fail(sha,'cannot enumerate nonempty candidate diff',policy)
 allowed=set(policy['allowed_root_candidate_paths']);required=set(policy['required_root_candidate_paths']);seed=set(policy['seed_paths'])
 if seed.intersection(changed):return fail(sha,'seed self-modification forbidden',policy)
 if any(p not in allowed for p in changed):return fail(sha,'candidate path outside root rotation allowlist',policy)
 if not required.issubset(changed):return fail(sha,'root candidate missing required repair path',policy)
 for prefix in policy['forbidden_candidate_prefixes']:
  if any(p.startswith(prefix) for p in changed):return fail(sha,'forbidden runtime/scientific path changed',policy)
 for p in changed:
  rc,tree=run(['git','ls-tree',sha,'--',p])
  if rc or (tree.strip() and tree.split(None,1)[0]!='100644'):return fail(sha,'non-regular changed path '+p,policy)
 tmp=pathlib.Path(tempfile.mkdtemp(prefix='supernova-root-seed-'))
 try:
  rc,out=run(['git','worktree','add','--detach',str(tmp),sha])
  if rc:return fail(sha,'cannot create candidate data worktree',policy)
  plan=load(tmp,'plan/PLAN.json');candidate_state=load(tmp,'state/CURRENT.json')
  if plan.get('task_network_plan_id')!=PLAN or plan.get('protocol_version')!='2.5' or plan.get('specification_revision')!=4:return fail(sha,'plan/protocol/revision drift',policy)
  if candidate_state!=state:return fail(sha,'state changed in root rotation candidate',policy)
  epoch=load(tmp,'config/root_tcb_epoch_v25.json')
  if epoch.get('schema_version')!='PS-ROOT-TCB-EPOCH-2.5-2' or epoch.get('epoch')!=2:return fail(sha,'invalid root epoch marker',policy)
  for k,p in [('seed_policy_blob','config/root_rotation_seed_v25.json'),('seed_reconciler_blob','scripts/reconcile_root_rotation_seed.py'),('seed_workflow_blob','.github/workflows/supernova-root-rotation-seed.yml')]:
   if epoch.get(k)!=git_blob(p):return fail(sha,'root epoch does not bind accepted seed '+k,policy)
  adm=load(tmp,'config/admission_authority.json')
  if adm.get('bootstrap_status_provenance')!='DESIGNATED_WORKFLOW_RUN_EXACT_PR_BINDING_REQUIRED':return fail(sha,'bootstrap provenance rule not installed',policy)
  helpers=set(adm.get('trusted_authority_helpers') or [])
  if not set(policy['seed_paths'][:3]).issubset(helpers):return fail(sha,'new TCB does not protect installed seed',policy)
  if adm.get('bootstrap_completion_workflow')!='.github/workflows/supernova-bootstrap-completion-reconcile.yml':return fail(sha,'completion reconciler not designated',policy)
 finally:
  run(['git','worktree','remove','--force',str(tmp)]);shutil.rmtree(tmp,ignore_errors=True)
 post(sha,policy['seed_context'],'success','one-shot accepted-main root seed PASS; exact head/base')
 for ctx in policy['required_status_contexts']:post(sha,ctx,'success','one-shot root seed exact-head PASS/N-A non-state transition')
 print('ROOT ROTATION SEED PASS',number,sha);return 0

if __name__=='__main__':raise SystemExit(main())
