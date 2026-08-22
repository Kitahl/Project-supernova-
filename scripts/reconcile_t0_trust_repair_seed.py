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
POLICY_PATH='config/t0_trust_repair_seed_v25.json'
EXPECTED_ENV={
 'runner_image':'ubuntu-24.04',
 'runner_image_version':'20260816.277.1',
 'python_version':'3.13.15',
 'git_version':'2.55.0'
}
STRONG_BOOTSTRAP_PROVENANCE='DESIGNATED_COMPLETED_WORKFLOW_RUN_ID_AND_EXACT_PR_HEAD_BASE_REQUIRED'


def api(path,method='GET',data=None):
 req=urllib.request.Request(API+path,data=(json.dumps(data).encode() if data is not None else None),method=method)
 req.add_header('Accept','application/vnd.github+json');req.add_header('X-GitHub-Api-Version','2022-11-28')
 if TOKEN:req.add_header('Authorization','Bearer '+TOKEN)
 with urllib.request.urlopen(req,timeout=30) as r:
  raw=r.read();return json.loads(raw) if raw else None


def run(cmd,cwd=ROOT):
 p=subprocess.run(cmd,cwd=str(cwd),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False);return p.returncode,p.stdout


def load(root,path):return json.loads((root/path).read_text(encoding='utf-8'))
def blob_at(ref,path):
 rc,out=run(['git','rev-parse',f'{ref}:{path}']);return out.strip() if rc==0 else None


def post(sha,ctx,state,desc):
 target=f"https://github.com/{REPO}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}"
 api('/statuses/'+sha,'POST',{'state':state,'context':ctx,'description':desc[:140],'target_url':target})


def fail(sha,reason,policy):
 if isinstance(sha,str) and HEX40.fullmatch(sha):
  post(sha,policy['seed_context'],'failure','trust seed refused: '+reason)
  for ctx in policy['required_status_contexts']:post(sha,ctx,'failure','trust seed refused: '+reason)
 print('T0 TRUST SEED REFUSED:',reason);return 1


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
 if not str(head.get('ref','')).startswith(policy['head_prefix_required']):return fail(sha,'head prefix not trust-repair eligible',policy)
 state=load(ROOT,'state/CURRENT.json')
 if state.get('calibration_streak')!=policy['calibration_streak_required'] or state.get('fresh_allowed_globally') is not policy['fresh_allowed_globally_required']:return fail(sha,'streak must be zero and fresh disabled',policy)
 current_epoch=load(ROOT,'config/root_tcb_epoch_v25.json')
 if current_epoch.get('epoch')!=policy['required_current_root_epoch']:return fail(sha,'one-shot seed is inert outside root epoch 4',policy)
 run(['git','fetch','--no-tags','origin',f'pull/{number}/head'])
 rc,_=run(['git','merge-base','--is-ancestor',trusted,sha])
 if rc:return fail(sha,'candidate does not descend from exact accepted main',policy)
 rc,out=run(['git','diff','--name-only',trusted+'...'+sha]);changed=[x for x in out.splitlines() if x]
 if rc or not changed:return fail(sha,'cannot enumerate nonempty candidate diff',policy)
 allowed=set(policy['allowed_root_candidate_paths']);required=set(policy['required_root_candidate_paths']);seed=set(policy['seed_paths'])
 if seed.intersection(changed):return fail(sha,'seed self-modification forbidden',policy)
 if set(changed)!=required:return fail(sha,'root candidate diff is not exact required repair set',policy)
 if any(p not in allowed for p in changed):return fail(sha,'candidate path outside trust-repair allowlist',policy)
 for prefix in policy['forbidden_candidate_prefixes']:
  if any(p.startswith(prefix) for p in changed):return fail(sha,'forbidden runtime/scientific path changed',policy)
 for p in changed:
  rc,tree=run(['git','ls-tree',sha,'--',p])
  if rc or (tree.strip() and tree.split(None,1)[0]!='100644'):return fail(sha,'non-regular changed path '+p,policy)
 tmp=pathlib.Path(tempfile.mkdtemp(prefix='supernova-t0-trust-seed-'))
 try:
  rc,out=run(['git','worktree','add','--detach',str(tmp),sha])
  if rc:return fail(sha,'cannot create candidate data worktree',policy)
  if load(tmp,'state/CURRENT.json')!=state:return fail(sha,'state changed in trust-repair candidate',policy)
  plan=load(tmp,'plan/PLAN.json')
  if plan.get('task_network_plan_id')!=PLAN or plan.get('protocol_version')!='2.5' or plan.get('specification_revision')!=4:return fail(sha,'plan/protocol/revision drift',policy)
  epoch=load(tmp,'config/root_tcb_epoch_v25.json')
  expected_seed={
   't0_trust_repair_seed_install_commit_sha':trusted,
   't0_trust_repair_seed_policy_blob':blob_at('HEAD',policy['seed_paths'][0]),
   't0_trust_repair_seed_reconciler_blob':blob_at('HEAD',policy['seed_paths'][1]),
   't0_trust_repair_seed_workflow_blob':blob_at('HEAD',policy['seed_paths'][2]),
  }
  if epoch.get('schema_version')!='PS-ROOT-TCB-EPOCH-2.5-5' or epoch.get('epoch')!=5:return fail(sha,'invalid target root epoch marker',policy)
  if epoch.get('previous_epoch_blob')!=blob_at('HEAD','config/root_tcb_epoch_v25.json'):return fail(sha,'epoch5 does not bind accepted epoch4 blob',policy)
  for k,v in expected_seed.items():
   if not isinstance(v,str) or epoch.get(k)!=v:return fail(sha,'epoch5 does not bind accepted seed '+k,policy)
  adm=load(tmp,'config/admission_authority.json')
  if adm.get('root_tcb_epoch')!=5:return fail(sha,'admission authority root epoch not 5',policy)
  if adm.get('bootstrap_status_provenance')!=STRONG_BOOTSTRAP_PROVENANCE:return fail(sha,'bootstrap provenance strengthening missing',policy)
  if adm.get('validator_environment_contract')!='config/validator_environment_v25.json':return fail(sha,'validator environment contract not designated',policy)
  envc=load(tmp,'config/validator_environment_v25.json')
  for k,v in EXPECTED_ENV.items():
   if envc.get(k)!=v:return fail(sha,'validator environment mismatch '+k,policy)
  gd=load(tmp,'config/generation_delta_policy_v25.json')
  if gd.get('countable',{}).get('exact_cardinality')!=3 or gd.get('non_countable',{}).get('exact_cardinality')!=2:return fail(sha,'generation delta policy invalid',policy)
  schema=load(tmp,'schemas/branch_report.schema.json')
  nzo=((schema.get('properties') or {}).get('negative_zero_outcomes') or {})
  if not isinstance(nzo.get('items'),dict):return fail(sha,'negative_zero_outcomes remains untyped',policy)
  reconciler=(tmp/'scripts/reconcile_open_prs.py').read_text(encoding='utf-8')
  if 'COMPLETED_BOOTSTRAP_RUN_ID' not in reconciler:return fail(sha,'completion run id is not consumed by bootstrap verifier',policy)
  bootstrap_checker=(tmp/'scripts/reconcile_authority_bootstrap.py').read_text(encoding='utf-8')
  if STRONG_BOOTSTRAP_PROVENANCE not in bootstrap_checker:return fail(sha,'bootstrap invariant checker does not accept strengthened provenance contract',policy)
  if 'config/validator_environment_v25.json' not in bootstrap_checker:return fail(sha,'bootstrap invariant checker does not protect validator environment contract',policy)
  for wf in policy['required_root_candidate_paths']:
   if wf.startswith('.github/workflows/'):
    text=(tmp/wf).read_text(encoding='utf-8')
    if 'scripts/assert_validator_environment.py' not in text:return fail(sha,'privileged/countable workflow lacks environment assertion '+wf,policy)
 finally:
  run(['git','worktree','remove','--force',str(tmp)]);shutil.rmtree(tmp,ignore_errors=True)
 post(sha,policy['seed_context'],'success','one-shot accepted-main T0 trust seed PASS; exact head/base/repair set')
 for ctx in policy['required_status_contexts']:post(sha,ctx,'success','one-shot T0 trust seed exact-head PASS/N-A non-state transition')
 print('T0 TRUST REPAIR SEED PASS',number,sha);return 0

if __name__=='__main__':raise SystemExit(main())
