#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,pathlib,re,subprocess,tempfile,shutil,urllib.request
ROOT=pathlib.Path.cwd().resolve();REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-');TOKEN=os.environ.get('GITHUB_TOKEN','');API='https://api.github.com/repos/'+REPO;OWNER=REPO.split('/',1)[0]
HEX40=re.compile(r'^[0-9a-f]{40}$')

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
  post(sha,p['seed_context'],'failure','repair-reset seed refused: '+why)
  for ctx in p['required_normal_contexts']:post(sha,ctx,'failure','repair-reset seed refused: '+why)
 print('REPAIR RESET SEED REFUSED',why);return 1

def main():
 p=load(ROOT,'config/gen7_repair_reset_seed_v25.json')
 try:n=int(os.environ.get('PR_NUMBER','0'))
 except ValueError:n=0
 if n<=0:return 1
 pr=api(f'/pulls/{n}');head=pr.get('head') or {};base=pr.get('base') or {};sha=head.get('sha')
 if os.environ.get('CANDIDATE_DIAGNOSTICS_RESULT')!='success':return fail(sha,'candidate diagnostics failed',p)
 if sha!=os.environ.get('DIAGNOSED_HEAD_SHA') or base.get('sha')!=os.environ.get('DIAGNOSED_BASE_SHA'):return fail(sha,'diagnosed head/base mismatch',p)
 rc,out=run(['git','rev-parse','HEAD']);trusted=out.strip()
 if rc or trusted!=base.get('sha'):return fail(sha,'base is not exact accepted main',p)
 if base.get('ref')!='main' or (head.get('repo') or {}).get('full_name')!=REPO or (pr.get('user') or {}).get('login')!=OWNER:return fail(sha,'same-repo owner PR to main required',p)
 if not str(head.get('ref','')).startswith(p['head_prefix_required']):return fail(sha,'wrong repair-reset head prefix',p)
 state=load(ROOT,'state/CURRENT.json');rc,sblob=run(['git','rev-parse','HEAD:state/CURRENT.json'])
 if rc or sblob.strip()!=p['exact_invalidated_state_blob']:return fail(sha,'accepted main is not exact invalidated Gen7 state',p)
 if state.get('active_cohort_id')!=p['exact_invalidated_cohort'] or state.get('generation_head_sha')!=p['exact_invalidated_generation_head'] or state.get('calibration_streak')!=0 or state.get('fresh_allowed_globally') is not False:return fail(sha,'Gen7 repair preconditions no longer hold',p)
 if (ROOT/p['one_shot_marker_path']).exists():return fail(sha,'repair-reset marker already accepted; seed inert',p)
 run(['git','fetch','--no-tags','origin',f'pull/{n}/head']);rc,_=run(['git','merge-base','--is-ancestor',trusted,sha])
 if rc:return fail(sha,'candidate not descendant of exact main',p)
 rc,out=run(['git','diff','--name-only',trusted+'...'+sha]);changed=set(out.splitlines()) if not rc else set()
 required=set(p['required_candidate_paths'])
 if changed!=required:return fail(sha,'candidate diff is not exact repair-reset root set',p)
 if set(p['seed_paths']).intersection(changed):return fail(sha,'seed self-modification forbidden',p)
 for pref in p['forbidden_candidate_prefixes']:
  if any(x.startswith(pref) for x in changed):return fail(sha,'forbidden candidate path',p)
 tmp=pathlib.Path(tempfile.mkdtemp(prefix='gen7-repair-reset-seed-'))
 try:
  rc,_=run(['git','worktree','add','--detach',str(tmp),sha])
  if rc:return fail(sha,'cannot inspect candidate',p)
  if load(tmp,'state/CURRENT.json')!=state:return fail(sha,'root candidate changes state',p)
  epoch=load(tmp,'config/gen7_repair_reset_epoch_v25.json')
  if epoch.get('schema_version')!='PS-GEN7-REPAIR-RESET-EPOCH-2.5-1' or epoch.get('invalidated_state_blob')!=p['exact_invalidated_state_blob']:return fail(sha,'invalid repair-reset epoch marker',p)
  for key,path in [('seed_policy_blob','config/gen7_repair_reset_seed_v25.json'),('seed_reconciler_blob','scripts/reconcile_gen7_repair_reset_seed.py'),('seed_workflow_blob','.github/workflows/supernova-gen7-repair-reset-seed.yml')]:
   if epoch.get(key)!=blob(path):return fail(sha,'repair-reset epoch does not bind accepted seed '+key,p)
  text=(tmp/'scripts/reconcile_open_prs.py').read_text(encoding='utf-8')
  for needle in ('exact_invalidated_gen7_repair_parent','INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS','superseded/CAL-BR-007-v25-c13b6ee4.json'):
   if needle not in text:return fail(sha,'repair-reset root logic missing '+needle,p)
 finally:
  run(['git','worktree','remove','--force',str(tmp)]);shutil.rmtree(tmp,ignore_errors=True)
 post(sha,p['seed_context'],'success','exact Gen7 one-shot repair-reset seed PASS')
 for ctx in p['required_normal_contexts']:post(sha,ctx,'success','exact Gen7 repair-reset root seed PASS/N-A non-state transition')
 return 0
if __name__=='__main__':raise SystemExit(main())
