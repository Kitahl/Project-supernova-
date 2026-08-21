#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,pathlib,re,shutil,subprocess,tempfile,urllib.request
ROOT=pathlib.Path.cwd().resolve();REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-');TOKEN=os.environ.get('GITHUB_TOKEN','');API='https://api.github.com/repos/'+REPO;OWNER=REPO.split('/',1)[0];HEX40=re.compile(r'^[0-9a-f]{40}$')
POLICY='config/substrate_staging_completion_seed_v25.json'

def api(path,method='GET',data=None):
 r=urllib.request.Request(API+path,data=(json.dumps(data).encode() if data is not None else None),method=method);r.add_header('Accept','application/vnd.github+json');r.add_header('X-GitHub-Api-Version','2022-11-28')
 if TOKEN:r.add_header('Authorization','Bearer '+TOKEN)
 with urllib.request.urlopen(r,timeout=30) as z:
  raw=z.read();return json.loads(raw) if raw else None
def run(cmd,cwd=ROOT):
 p=subprocess.run(cmd,cwd=str(cwd),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False);return p.returncode,p.stdout
def load(root,path):return json.loads((root/path).read_text(encoding='utf-8'))
def blob(path):
 b=(ROOT/path).read_bytes();return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def post(sha,ctx,state,desc):
 body={'state':state,'context':ctx,'description':desc[:140],'target_url':f"https://github.com/{REPO}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}"};api('/statuses/'+sha,'POST',body)
def fail(sha,why,p):
 if isinstance(sha,str) and HEX40.fullmatch(sha):
  post(sha,p['seed_context'],'failure','staging-completion seed refused: '+why)
  for ctx in p['required_normal_contexts']:post(sha,ctx,'failure','staging-completion seed refused: '+why)
 print('STAGING COMPLETION SEED REFUSED',why);return 1

def main():
 p=load(ROOT,POLICY)
 try:n=int(os.environ.get('PR_NUMBER','0'))
 except ValueError:n=0
 if n<=0:return 1
 pr=api(f'/pulls/{n}');head=pr.get('head') or {};base=pr.get('base') or {};sha=head.get('sha')
 if os.environ.get('CANDIDATE_DIAGNOSTICS_RESULT')!='success':return fail(sha,'candidate diagnostics failed',p)
 if sha!=os.environ.get('DIAGNOSED_HEAD_SHA') or base.get('sha')!=os.environ.get('DIAGNOSED_BASE_SHA'):return fail(sha,'diagnosed head/base mismatch',p)
 rc,out=run(['git','rev-parse','HEAD']);trusted=out.strip()
 if rc or trusted!=base.get('sha'):return fail(sha,'base is not exact accepted main',p)
 if base.get('ref')!='main' or (head.get('repo') or {}).get('full_name')!=REPO or (pr.get('user') or {}).get('login')!=OWNER:return fail(sha,'same-repo owner PR to main required',p)
 if not str(head.get('ref','')).startswith(p['head_prefix_required']):return fail(sha,'wrong seed candidate prefix',p)
 state=load(ROOT,'state/CURRENT.json')
 if not (state.get('generation_seq')==7 and state.get('active_cohort_id')=='CAL-BR-007-v25-c13b6ee4' and state.get('calibration_streak')==0 and state.get('fresh_allowed_globally') is False):return fail(sha,'seed install is only legal while exact invalidated Gen7 remains canonical',p)
 if (ROOT/p['one_shot_marker_path']).exists():return fail(sha,'staging-completion epoch already accepted; seed inert',p)
 run(['git','fetch','--no-tags','origin',f'pull/{n}/head']);rc,_=run(['git','merge-base','--is-ancestor',trusted,sha])
 if rc:return fail(sha,'candidate does not descend from exact main',p)
 rc,out=run(['git','diff','--name-only',trusted+'...'+sha]);changed=set(out.splitlines()) if not rc else set()
 required=set(p['required_candidate_paths'])
 if changed!=required:return fail(sha,'candidate diff is not exact staging-completion root set',p)
 if set(p['seed_paths']).intersection(changed):return fail(sha,'seed self-modification forbidden',p)
 tmp=pathlib.Path(tempfile.mkdtemp(prefix='substrate-staging-seed-'))
 try:
  rc,_=run(['git','worktree','add','--detach',str(tmp),sha])
  if rc:return fail(sha,'cannot inspect candidate',p)
  if load(tmp,'state/CURRENT.json')!=state:return fail(sha,'root candidate changes state',p)
  epoch=load(tmp,p['one_shot_marker_path'])
  if epoch.get('schema_version')!='PS-SUBSTRATE-STAGING-COMPLETION-EPOCH-2.5-1':return fail(sha,'bad staging-completion epoch marker',p)
  for key,path in [('seed_policy_blob',POLICY),('seed_reconciler_blob','scripts/reconcile_substrate_staging_completion_seed.py'),('seed_workflow_blob','.github/workflows/supernova-substrate-staging-completion-seed.yml')]:
   if epoch.get(key)!=blob(path):return fail(sha,'epoch does not bind accepted seed '+key,p)
  text=(tmp/'scripts/reconcile_open_prs.py').read_text(encoding='utf-8')
  for needle in ('exact_noncountable_substrate_staging_parent',p['target_foundry_sha256'],p['staging_cohort_id'],p['runtime_update_receipt_path']):
   if needle not in text:return fail(sha,'staging-completion logic missing '+needle,p)
 finally:
  run(['git','worktree','remove','--force',str(tmp)]);shutil.rmtree(tmp,ignore_errors=True)
 post(sha,p['seed_context'],'success','one-shot substrate staging completion seed PASS')
 for ctx in p['required_normal_contexts']:post(sha,ctx,'success','substrate staging completion seed exact-head PASS/N-A')
 return 0
if __name__=='__main__':raise SystemExit(main())
