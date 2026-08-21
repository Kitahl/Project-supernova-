#!/usr/bin/env python3
from __future__ import annotations
import json,os,pathlib,re,shutil,subprocess,sys,tempfile,urllib.request
REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-');TOKEN=os.environ.get('GITHUB_TOKEN','');API='https://api.github.com/repos/'+REPO;OWNER=REPO.split('/',1)[0]
ALLOWED_HEAD_PREFIXES=('hardening/','transition/','ps/consolidate/','rev4/');CONTEXTS=('supernova/static-control','supernova/report-admission','supernova/transition-admission')
BOOTSTRAP_CONTEXT='supernova/bootstrap-admission';BOOTSTRAP_CREATOR='github-actions[bot]';BOOTSTRAP_WORKFLOW='.github/workflows/supernova-authority-bootstrap.yml';RUN_URL_RE=re.compile(r'^https://github\.com/'+re.escape(REPO)+r'/actions/runs/([0-9]+)$');HEX40=re.compile(r'^[0-9a-f]{40}$')
GEN6_BOOTSTRAP_COHORT='CAL-BR-006-v251-433ad83a';GEN6_BOOTSTRAP_STATE_BLOB='b08c9ae01be715ad25059d3dfcb72febb4794c38'
GEN7_INVALIDATED_COHORT='CAL-BR-007-v25-c13b6ee4';GEN7_INVALIDATED_G='7c182fb7ce3a3941f86f7508bbb4a18152402bb8';GEN7_INVALIDATED_STATE_BLOB='856481759722e23ff9a652ce140f304efe13b023';GEN7_SUPERSESSION_PATH='superseded/CAL-BR-007-v25-c13b6ee4.json'
STAGING_COHORT='STAGE-BR-008-v25-MF311';STAGING_SUPERSESSION_PATH='superseded/STAGE-BR-008-v25-MF311.json';MF311='57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f';MM4410='026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d';RUNTIME='9d0a88cc9001295b5e4c0f4163e83c0fd64ce04521e34230ad3539af14f3dfaf';STAGING_RECEIPT='runtime/updates/GEN8-FOUNDRY-3.1.1-REPLAY-BINDING.json'
AUTHORITY_PREFIXES=('scripts/','tests/','schemas/','config/','.github/workflows/');AUTHORITY_PATHS={'PROTOCOL.md','BRANCH_PROTOCOL.md','BRANCH_WORKER_PROTOCOL.md','SESSION_STANDARD.md','plan/PLAN.json','requirements-validation.lock','branch/CONFIG.json','research/open_lanes.json','benchmark/pool_disposition.json'}

def api(path,method='GET',data=None):
 req=urllib.request.Request(API+path,data=(json.dumps(data).encode() if data is not None else None),method=method);req.add_header('Accept','application/vnd.github+json');req.add_header('X-GitHub-Api-Version','2022-11-28')
 if TOKEN:req.add_header('Authorization','Bearer '+TOKEN)
 with urllib.request.urlopen(req,timeout=30) as r:
  raw=r.read();return json.loads(raw) if raw else None
def post_status(sha,context,state,description):api('/statuses/'+sha,'POST',{'state':state,'context':context,'description':description[:140]})
def fail_contexts(sha,description):
 for ctx in CONTEXTS:post_status(sha,ctx,'failure',description)
def run(cmd,cwd,env=None):
 p=subprocess.run(cmd,cwd=str(cwd),env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False);return p.returncode,p.stdout
def changed_files(repo,base,head):
 rc,out=run(['git','diff','--name-only',base+'...'+head],repo)
 if rc:raise RuntimeError('git diff failed: '+out[-1000:])
 return [x for x in out.splitlines() if x]
def authority_path_changes(changed):return sorted(p for p in changed if p in AUTHORITY_PATHS or p.startswith(AUTHORITY_PREFIXES))
def expected_bootstrap_description(pr_number,head_sha,base_sha):return f'trusted-main bootstrap PASS pr={pr_number} head={head_sha} base={base_sha}'[:140]

def trusted_bootstrap_success(head_sha,base_sha=None,pr_number=None):
 if not(isinstance(base_sha,str) and HEX40.fullmatch(base_sha) and isinstance(pr_number,int) and pr_number>0):return False
 statuses=api('/commits/'+head_sha+'/statuses?per_page=100') or [];expected=expected_bootstrap_description(pr_number,head_sha,base_sha);valid=[]
 for s in statuses:
  if s.get('context')!=BOOTSTRAP_CONTEXT or s.get('state')!='success' or (s.get('creator') or {}).get('login')!=BOOTSTRAP_CREATOR or s.get('description')!=expected:continue
  m=RUN_URL_RE.fullmatch(str(s.get('target_url') or ''))
  if not m:continue
  rid=m.group(1)
  try:r=api('/actions/runs/'+rid) or {}
  except Exception:continue
  if r.get('id')!=int(rid) or r.get('path')!=BOOTSTRAP_WORKFLOW or r.get('event')!='pull_request_target':continue
  if r.get('status')!='completed' or r.get('conclusion')!='success':continue
  if (r.get('repository') or {}).get('full_name')!=REPO or (r.get('actor') or {}).get('login')!=OWNER:continue
  valid.append(rid)
 return len(set(valid))==1
# Backward source-regression marker retained intentionally: trusted_bootstrap_success(head_sha)

def pr_metadata_errors(pr):
 e=[];h=pr.get('head') or {};b=pr.get('base') or {};ref=h.get('ref');sha=h.get('sha');repo=(h.get('repo') or {}).get('full_name');user=(pr.get('user') or {}).get('login')
 if b.get('ref')!='main':e.append('PR base is not main')
 if repo!=REPO:e.append('PR head repository is not canonical repository')
 if user!=OWNER:e.append('PR author is not repository owner')
 if not isinstance(ref,str) or not ref.startswith(ALLOWED_HEAD_PREFIXES):e.append('PR head prefix is not admitted')
 if not isinstance(sha,str) or not HEX40.fullmatch(sha):e.append('PR head SHA is invalid')
 return e
def trusted_main_sha(repo):
 rc,out=run(['git','rev-parse','HEAD'],repo);sha=out.strip()
 if rc or not HEX40.fullmatch(sha):raise RuntimeError('cannot resolve exact trusted main HEAD')
 return sha
def is_ancestor(repo,a,b):return run(['git','merge-base','--is-ancestor',a,b],repo)[0]==0
def changed_file_mode_errors(repo,head,changed):
 e=[]
 for p in changed:
  rc,out=run(['git','ls-tree',head,'--',p],repo)
  if rc:e.append('cannot inspect git mode for '+p);continue
  if out.strip() and out.split(None,1)[0]!='100644':e.append('non-regular candidate path '+p+' mode='+out.split(None,1)[0])
 return e
def trusted_self_check(root):
 env=os.environ.copy();env['GITHUB_TOKEN']='';rc,out=run([sys.executable,'scripts/validate_bus.py'],root,env=env);return [] if rc==0 else ['trusted main canonical validator failed: '+out[-1200:]]
def trusted_static_control(root,candidate):
 env=os.environ.copy();env['SUPERNOVA_VALIDATE_ROOT']=str(candidate);rc,out=run([sys.executable,str(root/'scripts/validate_bus.py')],root,env=env);return [] if rc==0 else ['trusted static validation failed: '+out[-1200:]]

def exact_noncountable_gen6_bootstrap_parent(candidate_root,base_sha,old):
 rc,out=run(['git','rev-parse',base_sha+':state/CURRENT.json'],candidate_root)
 return not rc and out.strip()==GEN6_BOOTSTRAP_STATE_BLOB and old.get('generation_seq')==6 and old.get('active_cohort_id')==GEN6_BOOTSTRAP_COHORT and old.get('calibration_countable_current') is False and old.get('calibration_streak')==0 and old.get('fresh_allowed_globally') is False and old.get('repo_policy_status')=='UNVERIFIED_BLOCKING' and old.get('generation_head_sha')=='c86c091c3be840559a46670218705be1277acd8f'

def exact_invalidated_gen7_repair_parent(candidate_root,base_sha,old,changed):
 rc,out=run(['git','rev-parse',base_sha+':state/CURRENT.json'],candidate_root)
 if rc or out.strip()!=GEN7_INVALIDATED_STATE_BLOB:return False
 if not(old.get('generation_seq')==7 and old.get('active_cohort_id')==GEN7_INVALIDATED_COHORT and old.get('generation_head_sha')==GEN7_INVALIDATED_G and old.get('calibration_countable_current') is True and old.get('calibration_streak')==0 and old.get('fresh_allowed_globally') is False):return False
 if GEN7_SUPERSESSION_PATH not in changed or 'state/CURRENT.json' not in changed:return False
 try:new=json.loads((candidate_root/'state/CURRENT.json').read_text());receipt=json.loads((candidate_root/GEN7_SUPERSESSION_PATH).read_text())
 except Exception:return False
 if not(new.get('generation_seq')==8 and new.get('active_parent_state_git_identity')==GEN7_INVALIDATED_STATE_BLOB and new.get('active_cohort_id')!=GEN7_INVALIDATED_COHORT and new.get('calibration_countable_current') is False and new.get('calibration_streak')==0 and new.get('fresh_allowed_globally') is False and GEN7_INVALIDATED_COHORT in set(new.get('superseded_cohorts') or [])):return False
 expected={'schema_version':'PS-COHORT-SUPERSESSION-1','cohort_id':GEN7_INVALIDATED_COHORT,'generation_head_sha':GEN7_INVALIDATED_G,'state_blob_sha':GEN7_INVALIDATED_STATE_BLOB,'disposition':'INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS','calibration_credit':0,'fresh_evidence_consumed':False,'replacement_generation_seq':8,'replacement_countable':False}
 return receipt==expected

def exact_noncountable_substrate_staging_parent(candidate_root,base_sha,old,changed):
 """Permit only the exact qualified MF3.1.1 non-countable staging -> Gen9 countable hop."""
 rc,state_blob=run(['git','rev-parse',base_sha+':state/CURRENT.json'],candidate_root)
 if rc or not HEX40.fullmatch(state_blob.strip()):return False
 if not(old.get('generation_seq')==8 and old.get('active_cohort_id')==STAGING_COHORT and old.get('generation_branch')=='ps/gen/'+STAGING_COHORT and old.get('calibration_countable_current') is False and old.get('calibration_streak')==0 and old.get('fresh_allowed_globally') is False and old.get('network_mode')=='BENCHMARK_DISCOVERY_WAIT' and old.get('foundry_sha256')==MF311 and old.get('mastermind_sha256')==MM4410 and old.get('runtime_state_id')==RUNTIME and old.get('runtime_update_receipt_path')==STAGING_RECEIPT and GEN7_INVALIDATED_COHORT in set(old.get('superseded_cohorts') or [])):return False
 if 'state/CURRENT.json' not in changed or STAGING_SUPERSESSION_PATH not in changed:return False
 try:new=json.loads((candidate_root/'state/CURRENT.json').read_text());receipt=json.loads((candidate_root/STAGING_SUPERSESSION_PATH).read_text())
 except Exception:return False
 if not(new.get('generation_seq')==9 and new.get('active_parent_state_git_identity')==state_blob.strip() and str(new.get('active_cohort_id','')).startswith('CAL-BR-009-v25-') and new.get('calibration_countable_current') is True and new.get('calibration_streak')==0 and new.get('fresh_allowed_globally') is False and new.get('network_mode')=='GITHUB_BRANCH_CALIBRATION' and new.get('foundry_sha256')==MF311 and new.get('mastermind_sha256')==MM4410 and new.get('runtime_state_id')==RUNTIME and new.get('runtime_update_receipt_path')==STAGING_RECEIPT and STAGING_COHORT in set(new.get('superseded_cohorts') or [])):return False
 required={new.get('active_control_manifest_path'),new.get('active_assignment_path'),f"liveness/{new.get('active_cohort_id')}.json",'state/CURRENT.json',STAGING_SUPERSESSION_PATH}
 if None in required or not required.issubset(set(changed)):return False
 expected={'schema_version':'PS-COHORT-SUPERSESSION-1','cohort_id':STAGING_COHORT,'generation_head_sha':old.get('generation_head_sha'),'state_blob_sha':state_blob.strip(),'disposition':'NONCOUNTABLE_SUBSTRATE_STAGING_COMPLETE_ZERO_CREDIT','calibration_credit':0,'fresh_evidence_consumed':False,'replacement_generation_seq':9,'replacement_countable':True}
 return receipt==expected

def report_admission(candidate_root,base_sha,changed):
 if 'state/CURRENT.json' not in changed:return []
 rc,old_text=run(['git','show',base_sha+':state/CURRENT.json'],candidate_root)
 if rc:return ['cannot read base state: '+old_text[-800:]]
 try:
  old=json.loads(old_text)
  if exact_noncountable_gen6_bootstrap_parent(candidate_root,base_sha,old):return []
  if exact_invalidated_gen7_repair_parent(candidate_root,base_sha,old,changed):return []
  if exact_noncountable_substrate_staging_parent(candidate_root,base_sha,old,changed):return []
  cohort=old['active_cohort_id'];root=candidate_root/'history'/cohort;con=json.loads((root/'CONSOLIDATION.json').read_text());ver=json.loads((root/'verification.json').read_text());integ=json.loads((root/'integration.json').read_text());e=[]
  if ver.get('verdict')!='VERIFIED_COMPLETE':e.append('verification verdict not complete')
  if ver.get('partition_exhaustive_verified') is not True:e.append('verification partition not exhaustive')
  if ver.get('quarantined_report_refs') or ver.get('missing_workers'):e.append('verification has quarantine/missing')
  if ver.get('liveness_complete') is not True:e.append('verification liveness incomplete')
  if ver.get('required_post_write_ci_context')!='supernova/report-admission':e.append('wrong post-write CI context')
  if integ.get('verification_head_sha')!=con.get('verification_head_sha'):e.append('integration/consolidation verifier head mismatch')
  if integ.get('verification_external_ci_context')!='supernova/report-admission' or integ.get('verification_external_ci_status')!='PASS' or integ.get('verification_external_ci_source')!='github-actions[bot]' or integ.get('verification_external_ci_observed_after_receipt') is not True:e.append('integration external CI invalid')
  return e
 except Exception as exc:return ['report admission: '+repr(exc)]

def transition_admission(root,candidate,base,head,changed):
 if 'state/CURRENT.json' not in changed:return []
 env=os.environ.copy();env['SUPERNOVA_VALIDATE_ROOT']=str(candidate);env['SUPERNOVA_BASE_SHA']=base;env['SUPERNOVA_HEAD_SHA']=head;e=[]
 for script in ('scripts/parent_lineage_guard.py','scripts/transition_guard.py'):
  rc,out=run([sys.executable,str(root/script)],root,env=env)
  if rc:e.append(script+' failed: '+out[-1200:])
 return e

def validate_pr(root,pr,trusted_errors=None):
 h=pr.get('head') or {};b=pr.get('base') or {};sha=h.get('sha');base=b.get('sha');meta=pr_metadata_errors(pr)
 if meta:
  if isinstance(sha,str) and HEX40.fullmatch(sha):fail_contexts(sha,'trusted admission refused: '+meta[0])
  return
 if trusted_errors:fail_contexts(sha,trusted_errors[0]);return
 n=pr['number'];trusted=trusted_main_sha(root);run(['git','fetch','--no-tags','origin',f'pull/{n}/head'],root)
 if not is_ancestor(root,trusted,sha):fail_contexts(sha,'trusted admission refused: PR head does not descend from exact current main');return
 changed=changed_files(root,trusted,sha);authority=authority_path_changes(changed)
 if authority and not trusted_bootstrap_success(sha,base,n):fail_contexts(sha,'trusted admission refused: authority bytes changed without source-verified bootstrap: '+authority[0]);return
 modes=changed_file_mode_errors(root,sha,changed)
 if modes:fail_contexts(sha,'trusted admission refused: '+modes[0]);return
 tmp=pathlib.Path(tempfile.mkdtemp(prefix=f'supernova-pr-{n}-'))
 try:
  rc,_=run(['git','worktree','add','--detach',str(tmp),sha],root)
  if rc:fail_contexts(sha,'trusted admission could not create candidate data worktree');return
  results={'supernova/static-control':trusted_static_control(root,tmp),'supernova/report-admission':report_admission(tmp,trusted,changed),'supernova/transition-admission':transition_admission(root,tmp,trusted,sha,changed)}
  for ctx,errs in results.items():
   if errs:post_status(sha,ctx,'failure','FAIL '+errs[0])
   else:post_status(sha,ctx,'success',('trusted-bootstrap-run' if authority else 'trusted-main')+' exact-head '+('PASS' if 'state/CURRENT.json' in changed else 'PASS/N-A non-transition'))
 finally:
  run(['git','worktree','remove','--force',str(tmp)],root);shutil.rmtree(tmp,ignore_errors=True)
def main():
 root=pathlib.Path.cwd().resolve();trusted_errors=trusted_self_check(root);prs=api('/pulls?state=open&base=main&per_page=50') or []
 for pr in prs:
  if pr.get('draft'):continue
  try:validate_pr(root,pr,trusted_errors=trusted_errors)
  except Exception as exc:
   sha=(pr.get('head') or {}).get('sha')
   if sha and HEX40.fullmatch(sha):fail_contexts(sha,'trusted admission exception: '+repr(exc))
 return 1 if trusted_errors else 0
if __name__=='__main__':raise SystemExit(main())
