#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-')
TOKEN=os.environ.get('GITHUB_TOKEN','')
API='https://api.github.com/repos/'+REPO
OWNER=REPO.split('/',1)[0]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
HEX40=re.compile(r'^[0-9a-f]{40}$')
OLD_COHORT='CAL-BR-007-v25-c13b6ee4'
OLD_G='7c182fb7ce3a3941f86f7508bbb4a18152402bb8'
OLD_STATE_BLOB='856481759722e23ff9a652ce140f304efe13b023'
STAGE='STAGE-BR-008-v25-MF311'
GEN_BRANCH='ps/gen/'+STAGE
MF311='57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f'
MM4410='026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d'
RUNTIME='9d0a88cc9001295b5e4c0f4163e83c0fd64ce04521e34230ad3539af14f3dfaf'
RECEIPT='runtime/updates/GEN8-FOUNDRY-3.1.1-REPLAY-BINDING.json'
EPOCH='config/mf311_initial_staging_epoch_v25.json'
CONTEXTS=('supernova/static-control','supernova/report-admission','supernova/transition-admission')
EXPECTED_PATHS={
 'config/substrate_epoch_v25.json',RECEIPT,EPOCH,
 f'control/{STAGE}.json',f'assignments/{STAGE}.json',
 f'superseded/{OLD_COHORT}.json','state/CURRENT.json'
}

def api(path,method='GET',data=None):
 req=urllib.request.Request(API+path,data=(json.dumps(data).encode() if data is not None else None),method=method)
 req.add_header('Accept','application/vnd.github+json');req.add_header('X-GitHub-Api-Version','2022-11-28')
 if TOKEN:req.add_header('Authorization','Bearer '+TOKEN)
 with urllib.request.urlopen(req,timeout=30) as r:
  raw=r.read();return json.loads(raw) if raw else None

def post(sha,context,state,description):
 body={'state':state,'context':context,'description':description[:140]}
 rid=os.environ.get('GITHUB_RUN_ID','')
 if rid.isdigit():body['target_url']=f'https://github.com/{REPO}/actions/runs/{rid}'
 api('/statuses/'+sha,'POST',body)

def fail(sha,reason):
 if isinstance(sha,str) and HEX40.fullmatch(sha):
  for c in CONTEXTS:post(sha,c,'failure','MF311 staging seed refused: '+reason)
 print('MF311 STAGING SEED REFUSED',reason);return 1

def run(cmd,cwd,env=None):
 p=subprocess.run(cmd,cwd=str(cwd),env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
 return p.returncode,p.stdout

def load(root,path):return json.loads((root/path).read_text(encoding='utf-8'))

def exact_supersession(obj):
 return obj=={
  'schema_version':'PS-COHORT-SUPERSESSION-1','cohort_id':OLD_COHORT,'generation_head_sha':OLD_G,
  'state_blob_sha':OLD_STATE_BLOB,'disposition':'INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS',
  'calibration_credit':0,'fresh_evidence_consumed':False,'replacement_generation_seq':8,'replacement_countable':False
 }

def validate_candidate(trusted,candidate,base,head):
 e=[]
 state=load(candidate,'state/CURRENT.json');control=load(candidate,f'control/{STAGE}.json');assignment=load(candidate,f'assignments/{STAGE}.json')
 epoch=load(candidate,EPOCH);substrate=load(candidate,'config/substrate_epoch_v25.json');receipt=load(candidate,RECEIPT)
 sup=load(candidate,f'superseded/{OLD_COHORT}.json')
 if not exact_supersession(sup):e.append('Gen7 supersession receipt is not exact zero-credit receipt')
 if not(
  state.get('generation_seq')==8 and state.get('active_parent_state_git_identity')==OLD_STATE_BLOB and
  state.get('active_cohort_id')==STAGE and state.get('generation_branch')==GEN_BRANCH and
  state.get('calibration_countable_current') is False and state.get('calibration_streak')==0 and
  state.get('fresh_allowed_globally') is False and state.get('network_mode')=='BENCHMARK_DISCOVERY_WAIT' and
  state.get('foundry_sha256')==MF311 and state.get('mastermind_sha256')==MM4410 and
  state.get('runtime_state_id')==RUNTIME and state.get('runtime_update_receipt_path')==RECEIPT and
  state.get('expected_base_head')==base and OLD_COHORT in set(state.get('superseded_cohorts') or [])
 ):e.append('staging state binding mismatch')
 for obj,label in ((control,'control'),(assignment,'assignment')):
  if not(obj.get('cohort_id')==STAGE and obj.get('generation_seq')==8 and obj.get('parent_state_git_identity')==OLD_STATE_BLOB and obj.get('expected_base_head')==base and obj.get('calibration_countable') is False):e.append(label+' staging binding mismatch')
 if assignment.get('generation_branch')!=GEN_BRANCH or assignment.get('network_mode')!='BENCHMARK_DISCOVERY_WAIT':e.append('assignment staging mode/branch mismatch')
 mf=substrate.get('math_foundry') or {};mm=substrate.get('mastermind') or {}
 if mf.get('source_archive_sha256')!=MF311 or mf.get('semantic_version')!='3.1.1':e.append('substrate epoch not exact MF3.1.1')
 if mm.get('sha256')!=MM4410:e.append('Mastermind substrate drift')
 if receipt.get('status')!='VALIDATED' or receipt.get('runtime_before')!=RUNTIME or receipt.get('runtime_after')!=RUNTIME:e.append('runtime receipt status/runtime mismatch')
 if (receipt.get('artifact_hashes') or {}).get('foundry_sha256')!=MF311:e.append('runtime receipt Foundry hash mismatch')
 if receipt.get('fresh_prospective_evidence_refs')!=[]:e.append('runtime receipt consumed fresh evidence')
 if epoch.get('schema_version')!='PS-MF311-INITIAL-STAGING-EPOCH-2.5-1' or epoch.get('seed_install_main_commit_sha')!=base or epoch.get('staging_cohort_id')!=STAGE:e.append('staging epoch marker mismatch')
 # Trusted accepted-main validators run on the candidate tree.
 env=os.environ.copy();env['SUPERNOVA_VALIDATE_ROOT']=str(candidate);env['SUPERNOVA_BASE_SHA']=base;env['SUPERNOVA_HEAD_SHA']=head;env['GITHUB_TOKEN']=''
 for script in ('scripts/validate_bus.py','scripts/parent_lineage_guard.py','scripts/transition_guard.py'):
  rc,out=run([sys.executable,str(trusted/script)],trusted,env=env)
  if rc:e.append(script+' failed: '+out[-800:])
 return e

def validate_generation(trusted,state,candidate):
 e=[];g=state.get('generation_head_sha');control=load(candidate,f'control/{STAGE}.json');root=control.get('control_release_commit_sha')
 if not isinstance(g,str) or not HEX40.fullmatch(g):return ['invalid staging generation head']
 if not isinstance(root,str) or not HEX40.fullmatch(root):return ['invalid staging control-release root']
 run(['git','fetch','--no-tags','origin',f'+refs/heads/{GEN_BRANCH}:refs/remotes/origin/{GEN_BRANCH}'],trusted)
 rc,out=run(['git','rev-parse',f'refs/remotes/origin/{GEN_BRANCH}'],trusted)
 if rc or out.strip()!=g:e.append('staging generation branch/head mismatch');return e
 rc,_=run(['git','merge-base','--is-ancestor',root,g],trusted)
 if rc:e.append('staging generation does not descend from control release root')
 rc,out=run(['git','diff','--name-only',root,g],trusted)
 if rc or set(x for x in out.splitlines() if x)!={f'control/{STAGE}.json',f'assignments/{STAGE}.json'}:e.append('staging root->G diff is not exactly control+assignment')
 # G must contain the same immutable control/assignment blobs as the transition candidate.
 for path in (f'control/{STAGE}.json',f'assignments/{STAGE}.json'):
  rc,a=run(['git','rev-parse',f'{g}:{path}'],trusted);rc2,b=run(['git','hash-object',str(candidate/path)],trusted)
  if rc or rc2 or a.strip()!=b.strip():e.append('staging generation '+path+' blob mismatch')
 return e

def main():
 root=pathlib.Path.cwd().resolve()
 try:n=int(os.environ.get('PR_NUMBER','0'))
 except ValueError:n=0
 if n<=0:return 1
 pr=api(f'/pulls/{n}');h=pr.get('head') or {};b=pr.get('base') or {};sha=h.get('sha');base=b.get('sha')
 if os.environ.get('CANDIDATE_DIAGNOSTICS_RESULT')!='success':return fail(sha,'candidate diagnostics not success')
 if os.environ.get('DIAGNOSED_HEAD_SHA')!=sha or os.environ.get('DIAGNOSED_BASE_SHA')!=base:return fail(sha,'diagnosed head/base mismatch')
 if b.get('ref')!='main' or (h.get('repo') or {}).get('full_name')!=REPO or (pr.get('user') or {}).get('login')!=OWNER:return fail(sha,'owner/same-repo/main required')
 if not str(h.get('ref','')).startswith('mf311-staging/'):return fail(sha,'wrong staging branch prefix')
 if not HEX40.fullmatch(str(sha or '')) or not HEX40.fullmatch(str(base or '')):return fail(sha,'invalid SHA')
 if (root/EPOCH).exists():return fail(sha,'one-shot seed already consumed')
 current=load(root,'state/CURRENT.json')
 rc,state_blob=run(['git','rev-parse','HEAD:state/CURRENT.json'],root)
 if rc or state_blob.strip()!=OLD_STATE_BLOB:return fail(sha,'canonical state blob is not exact invalidated Gen7')
 if not(current.get('generation_seq')==7 and current.get('active_cohort_id')==OLD_COHORT and current.get('generation_head_sha')==OLD_G and current.get('calibration_streak')==0 and current.get('fresh_allowed_globally') is False):return fail(sha,'current Gen7 state is not exact eligible parent')
 rc,main=run(['git','rev-parse','HEAD'],root)
 if rc or main.strip()!=base:return fail(sha,'base is not exact accepted main')
 run(['git','fetch','--no-tags','origin',f'pull/{n}/head'],root)
 rc,_=run(['git','merge-base','--is-ancestor',base,sha],root)
 if rc:return fail(sha,'candidate does not descend exact main')
 rc,out=run(['git','diff','--name-only',base+'...'+sha],root);changed=set(x for x in out.splitlines() if x)
 if rc or changed!=EXPECTED_PATHS:return fail(sha,'candidate path set mismatch: '+','.join(sorted(changed)))
 tmp=pathlib.Path(tempfile.mkdtemp(prefix='mf311-stage-'))
 try:
  rc,_=run(['git','worktree','add','--detach',str(tmp),sha],root)
  if rc:return fail(sha,'cannot create candidate worktree')
  errors=validate_candidate(root,tmp,base,sha)
  if not errors:errors.extend(validate_generation(root,load(tmp,'state/CURRENT.json'),tmp))
  if errors:return fail(sha,errors[0])
 finally:
  run(['git','worktree','remove','--force',str(tmp)],root);shutil.rmtree(tmp,ignore_errors=True)
 for c in CONTEXTS:post(sha,c,'success','one-shot MF311 staging seed exact candidate PASS')
 print('MF311 INITIAL STAGING SEED PASS',n,sha);return 0

if __name__=='__main__':raise SystemExit(main())
