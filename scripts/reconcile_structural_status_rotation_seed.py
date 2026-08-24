#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, re, shutil, subprocess, tempfile, urllib.request

ROOT=pathlib.Path.cwd().resolve();REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-');TOKEN=os.environ.get('GITHUB_TOKEN','');API='https://api.github.com/repos/'+REPO;OWNER=REPO.split('/',1)[0]
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa';HEX40=re.compile(r'^[0-9a-f]{40}$');POLICY_PATH='config/structural_status_rotation_seed_v25.json'
ROOT_TCB_PATH='config/root_tcb_epoch_v25.json';EXPECTED_PREDECESSOR_ROOT_EPOCH=2
EXPECTED_ROOT_EPOCH2_IDENTITY={
 'schema_version':'PS-ROOT-TCB-EPOCH-2.5-2',
 'protocol_version':'2.5',
 'task_network_plan_id':'0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa',
 'epoch':2,
 'status':'ACTIVE_AFTER_ROOT_ROTATION',
 'root_rotation_seed_merge_commit_sha':'088139cca3fa308058dca72e2c67eb3f758624bc',
 'seed_policy_blob':'9698216426dba4121de444d1800936e196e64163',
 'seed_reconciler_blob':'7a7b1dc4cd88d98642f2ba933f004b09b36a1933',
 'seed_workflow_blob':'10cf188aa27a8d799d48052cef8347238be43385',
 'seed_one_shot_disposition':'PERMANENTLY_INERT_AFTER_THIS_MARKER_IS_ACCEPTED',
 'root_tcb_source':'ACCEPTED_MAIN_ADMISSION_AUTHORITY_PLUS_DEPENDENCY_LOCK_PLUS_STATIC_ROOTS',
 'bootstrap_provenance':'DESIGNATED_WORKFLOW_RUN_EXACT_PR_BINDING_REQUIRED',
 'root_change_rule':'NO_AUTOMATED_BOOTSTRAP_SELF_AMENDMENT; FUTURE_ROOT_CHANGE_REQUIRES_A_NEW_INDEPENDENTLY_INSTALLED_SEED',
 'fresh_science_effect':'NONE',
 'calibration_credit_effect':'NONE; REPLACEMENT COUNTABLE COHORT STARTS_AT_STREAK_ZERO',
}
GEN9_COHORT='CAL-BR-009-v25-b53ab205';GEN9_G='67bcfef1a5a1e65c9cc4adb1a2f308ec51c70c3f';GEN9_STATE_BLOB='31071464144bde197aca0e3f13153be2d85208d7'
FOUNDRY='57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f';MASTERMIND='026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d';RUNTIME='9d0a88cc9001295b5e4c0f4163e83c0fd64ce04521e34230ad3539af14f3dfaf'

def api(path,method='GET',data=None):
 req=urllib.request.Request(API+path,data=(json.dumps(data).encode() if data is not None else None),method=method);req.add_header('Accept','application/vnd.github+json');req.add_header('X-GitHub-Api-Version','2022-11-28')
 if TOKEN:req.add_header('Authorization','Bearer '+TOKEN)
 with urllib.request.urlopen(req,timeout=30) as r:
  raw=r.read();return json.loads(raw) if raw else None

def run(cmd,cwd=ROOT):
 p=subprocess.run(cmd,cwd=str(cwd),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False);return p.returncode,p.stdout

def load(root,path):return json.loads((root/path).read_text(encoding='utf-8'))
def accepted_predecessor_root_epoch():
 try:value=load(ROOT,ROOT_TCB_PATH)
 except (OSError,UnicodeError,json.JSONDecodeError):return None
 return EXPECTED_PREDECESSOR_ROOT_EPOCH if value==EXPECTED_ROOT_EPOCH2_IDENTITY else None
def git_blob(path):
 rc,out=run(['git','rev-parse','HEAD:'+path]);return out.strip() if rc==0 else None

def post(sha,ctx,state,desc):
 target=f"https://github.com/{REPO}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}";api('/statuses/'+sha,'POST',{'state':state,'context':ctx,'description':desc[:140],'target_url':target})

def fail(sha,reason,policy):
 if isinstance(sha,str) and HEX40.fullmatch(sha):
  post(sha,policy['seed_context'],'failure','structural root seed refused: '+reason)
 print('STRUCTURAL ROOT SEED REFUSED:',reason);return 1

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
 if not str(head.get('ref','')).startswith(policy['head_prefix_required']):return fail(sha,'head prefix not structural-rotation eligible',policy)
 state=load(ROOT,'state/CURRENT.json')
 if git_blob('state/CURRENT.json')!=GEN9_STATE_BLOB or state.get('active_cohort_id')!=GEN9_COHORT or state.get('generation_head_sha')!=GEN9_G:return fail(sha,'canonical state is not exact zero-credit Gen9 target',policy)
 if state.get('calibration_streak')!=0 or state.get('fresh_allowed_globally') is not False:return fail(sha,'streak must be zero and fresh disabled',policy)
 if state.get('foundry_sha256')!=FOUNDRY or state.get('mastermind_sha256')!=MASTERMIND or state.get('runtime_state_id')!=RUNTIME:return fail(sha,'Gen9 substrate/runtime identity drift',policy)
 if (ROOT/policy['one_shot_marker_path']).exists():return fail(sha,'structural-status epoch marker exists; seed permanently inert',policy)
 if accepted_predecessor_root_epoch()!=EXPECTED_PREDECESSOR_ROOT_EPOCH:return fail(sha,'structural seed is inert outside exact predecessor root epoch 2 identity',policy)
 run(['git','fetch','--no-tags','origin',f'pull/{number}/head']);rc,_=run(['git','merge-base','--is-ancestor',trusted,sha])
 if rc:return fail(sha,'candidate does not descend from exact accepted main',policy)
 rc,out=run(['git','diff','--name-only',trusted+'...'+sha]);changed=[x for x in out.splitlines() if x]
 if rc or not changed:return fail(sha,'cannot enumerate nonempty candidate diff',policy)
 allowed=set(policy['allowed_root_candidate_paths']);required=set(policy['required_root_candidate_paths']);seed=set(policy['seed_paths'])
 if seed.intersection(changed):return fail(sha,'seed self-modification forbidden',policy)
 if any(p not in allowed for p in changed):return fail(sha,'candidate path outside structural rotation allowlist',policy)
 if not required.issubset(changed):return fail(sha,'candidate missing required structural-root repair path',policy)
 for prefix in policy['forbidden_candidate_prefixes']:
  if any(p.startswith(prefix) for p in changed):return fail(sha,'forbidden state/runtime/scientific path changed',policy)
 for p in changed:
  rc,tree=run(['git','ls-tree',sha,'--',p])
  if rc or (tree.strip() and tree.split(None,1)[0]!='100644'):return fail(sha,'non-regular changed path '+p,policy)
 tmp=pathlib.Path(tempfile.mkdtemp(prefix='supernova-structural-root-seed-'))
 try:
  rc,_=run(['git','worktree','add','--detach',str(tmp),sha])
  if rc:return fail(sha,'cannot create candidate data worktree',policy)
  plan=load(tmp,'plan/PLAN.json');candidate_state=load(tmp,'state/CURRENT.json')
  if plan.get('task_network_plan_id')!=PLAN or plan.get('protocol_version')!='2.5' or plan.get('specification_revision')!=4:return fail(sha,'plan/protocol/revision drift',policy)
  if candidate_state!=state:return fail(sha,'state changed in structural root candidate',policy)
  marker=load(tmp,'config/structural_status_rotation_epoch_v25.json')
  if marker.get('schema_version')!='PS-STRUCTURAL-STATUS-ROTATION-EPOCH-2.5-1' or marker.get('epoch')!=1:return fail(sha,'invalid structural-status epoch marker',policy)
  for k,p in [('seed_policy_blob','config/structural_status_rotation_seed_v25.json'),('seed_reconciler_blob','scripts/reconcile_structural_status_rotation_seed.py'),('seed_workflow_blob','.github/workflows/supernova-structural-status-rotation-seed.yml')]:
   if marker.get(k)!=git_blob(p):return fail(sha,'structural epoch does not bind accepted seed '+k,policy)
  current_root_blob=git_blob('config/root_tcb_epoch_v25.json');root_epoch=load(tmp,'config/root_tcb_epoch_v25.json')
  if root_epoch.get('schema_version')!='PS-ROOT-TCB-EPOCH-2.5-3' or root_epoch.get('epoch')!=3:return fail(sha,'root TCB epoch 3 not installed',policy)
  if root_epoch.get('previous_epoch_blob')!=current_root_blob:return fail(sha,'root TCB epoch 3 does not bind previous accepted epoch',policy)
  if root_epoch.get('structural_status_rotation_epoch_path')!='config/structural_status_rotation_epoch_v25.json':return fail(sha,'root TCB does not bind structural rotation marker',policy)
  reset=load(tmp,'config/gen9_repair_reset_epoch_v25.json')
  expected={'schema_version':'PS-GEN9-REPAIR-RESET-EPOCH-2.5-1','old_state_blob':GEN9_STATE_BLOB,'old_cohort_id':GEN9_COHORT,'old_generation_head_sha':GEN9_G,'allowed_successor_generation_seq':10,'calibration_credit':0,'fresh_evidence_consumed':False,'foundry_sha256':FOUNDRY,'mastermind_sha256':MASTERMIND,'runtime_state_id':RUNTIME}
  for k,v in expected.items():
   if reset.get(k)!=v:return fail(sha,'invalid Gen9 zero-credit reset marker '+k,policy)
  adm=load(tmp,'config/admission_authority.json');helpers=set(adm.get('trusted_authority_helpers') or []);workflows=set(adm.get('authoritative_status_workflows') or [])
  if not set(policy['seed_paths'][:3]).issubset(helpers):return fail(sha,'new root TCB does not protect structural seed',policy)
  if '.github/workflows/supernova-structural-status-rotation-seed.yml' not in workflows:return fail(sha,'new root TCB does not inventory structural seed workflow',policy)
  rest=(tmp/'scripts/reconcile_branch_rest.py').read_text(encoding='utf-8')
  if "'supernova/branch-generation'" in rest or '"supernova/branch-generation"' in rest:return fail(sha,'REST reconciler still contains authoritative branch-generation context',policy)
  if "'supernova/branch-worker'" in rest or '"supernova/branch-worker"' in rest:return fail(sha,'REST reconciler still contains authoritative branch-worker context',policy)
  if 'supernova/rest-branch-generation-diagnostic' not in rest or 'supernova/rest-branch-worker-diagnostic' not in rest:return fail(sha,'distinct REST diagnostic contexts missing',policy)
  open_prs=(tmp/'scripts/reconcile_open_prs.py').read_text(encoding='utf-8')
  if 'GEN9_ZERO_CREDIT_RESET' not in open_prs or 'config/gen9_repair_reset_epoch_v25.json' not in open_prs:return fail(sha,'exact Gen9 repair-reset gate missing',policy)
 finally:
  run(['git','worktree','remove','--force',str(tmp)]);shutil.rmtree(tmp,ignore_errors=True)
 post(sha,policy['seed_context'],'success','accepted-main structural-status seed PASS; exact head/base')
 print('STRUCTURAL STATUS ROTATION SEED PASS',number,sha);return 0

if __name__=='__main__':raise SystemExit(main())
