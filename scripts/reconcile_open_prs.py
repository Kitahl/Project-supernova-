#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, re, shutil, subprocess, sys, tempfile, urllib.request

REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-');TOKEN=os.environ.get('GITHUB_TOKEN','');API='https://api.github.com/repos/'+REPO;OWNER=REPO.split('/',1)[0]
ALLOWED_HEAD_PREFIXES=('hardening/','transition/','ps/consolidate/','rev4/')
CONTEXTS=('supernova/static-control','supernova/report-admission','supernova/transition-admission')
BOOTSTRAP_CONTEXT='supernova/bootstrap-admission';BOOTSTRAP_CREATOR='github-actions[bot]';BOOTSTRAP_WORKFLOW='.github/workflows/supernova-authority-bootstrap.yml'
RUN_URL_RE=re.compile(r'^https://github\.com/'+re.escape(REPO)+r'/actions/runs/([0-9]+)$');HEX40=re.compile(r'^[0-9a-f]{40}$')
GEN6_BOOTSTRAP_COHORT='CAL-BR-006-v251-433ad83a';GEN6_BOOTSTRAP_STATE_BLOB='b08c9ae01be715ad25059d3dfcb72febb4794c38'
AUTHORITY_PREFIXES=('scripts/','tests/','schemas/','config/','.github/workflows/')
AUTHORITY_PATHS={'PROTOCOL.md','BRANCH_PROTOCOL.md','BRANCH_WORKER_PROTOCOL.md','SESSION_STANDARD.md','plan/PLAN.json','requirements-validation.lock','branch/CONFIG.json','research/open_lanes.json','benchmark/pool_disposition.json'}

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
 if not (isinstance(base_sha,str) and HEX40.fullmatch(base_sha) and isinstance(pr_number,int) and pr_number>0):return False
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
 e=[];head=pr.get('head') or {};base=pr.get('base') or {};ref=head.get('ref');sha=head.get('sha');repo=(head.get('repo') or {}).get('full_name');user=(pr.get('user') or {}).get('login')
 if base.get('ref')!='main':e.append('PR base is not main')
 if repo!=REPO:e.append('PR head repository is not canonical repository')
 if user!=OWNER:e.append('PR author is not repository owner')
 if not isinstance(ref,str) or not ref.startswith(ALLOWED_HEAD_PREFIXES):e.append('PR head prefix is not admitted')
 if not isinstance(sha,str) or not HEX40.fullmatch(sha):e.append('PR head SHA is invalid')
 return e
def trusted_main_sha(repo):
 rc,out=run(['git','rev-parse','HEAD'],repo);sha=out.strip()
 if rc or not HEX40.fullmatch(sha):raise RuntimeError('cannot resolve exact trusted main HEAD')
 return sha
def is_ancestor(repo,ancestor,descendant):return run(['git','merge-base','--is-ancestor',ancestor,descendant],repo)[0]==0
def changed_file_mode_errors(repo,head_sha,changed):
 e=[]
 for path in changed:
  rc,out=run(['git','ls-tree',head_sha,'--',path],repo)
  if rc:e.append('cannot inspect git mode for '+path);continue
  if not out.strip():continue
  mode=out.split(None,1)[0]
  if mode!='100644':e.append(f'non-regular candidate path {path} mode={mode}')
 return e

def trusted_self_check(trusted_root):
 # Never execute the mutable accepted-main unit-test corpus while holding a status-write token.
 # Candidate tests already run in the separate read-only diagnostics job. The privileged path
 # executes only the root-protected canonical validator here.
 env=os.environ.copy();env['GITHUB_TOKEN']=''
 rc,out=run([sys.executable,'scripts/validate_bus.py'],trusted_root,env=env)
 return [] if rc==0 else ['trusted main canonical validator failed: '+out[-1200:]]

def trusted_static_control(trusted_root,candidate_root):
 env=os.environ.copy();env['SUPERNOVA_VALIDATE_ROOT']=str(candidate_root)
 rc,out=run([sys.executable,str(trusted_root/'scripts/validate_bus.py')],trusted_root,env=env);return [] if rc==0 else ['trusted static validation failed: '+out[-1200:]]
def exact_noncountable_gen6_bootstrap_parent(candidate_root,base_sha,old):
 rc,out=run(['git','rev-parse',base_sha+':state/CURRENT.json'],candidate_root)
 return not rc and out.strip()==GEN6_BOOTSTRAP_STATE_BLOB and old.get('generation_seq')==6 and old.get('active_cohort_id')==GEN6_BOOTSTRAP_COHORT and old.get('calibration_countable_current') is False and old.get('calibration_streak')==0 and old.get('fresh_allowed_globally') is False and old.get('repo_policy_status')=='UNVERIFIED_BLOCKING' and old.get('generation_head_sha')=='c86c091c3be840559a46670218705be1277acd8f'
def report_admission(candidate_root,base_sha,changed):
 if 'state/CURRENT.json' not in changed:return []
 errors=[];rc,old_text=run(['git','show',base_sha+':state/CURRENT.json'],candidate_root)
 if rc:return ['cannot read base state: '+old_text[-800:]]
 try:
  old=json.loads(old_text)
  if exact_noncountable_gen6_bootstrap_parent(candidate_root,base_sha,old):return []
  cohort=old['active_cohort_id'];root=candidate_root/'history'/cohort;con=json.loads((root/'CONSOLIDATION.json').read_text());ver=json.loads((root/'verification.json').read_text());integ=json.loads((root/'integration.json').read_text())
  if ver.get('verdict')!='VERIFIED_COMPLETE':errors.append('verification verdict not complete')
  if ver.get('partition_exhaustive_verified') is not True:errors.append('verification partition not exhaustive')
  if ver.get('quarantined_report_refs') or ver.get('missing_workers'):errors.append('verification has quarantine/missing')
  if ver.get('liveness_complete') is not True:errors.append('verification liveness incomplete')
  if ver.get('required_post_write_ci_context')!='supernova/report-admission':errors.append('wrong post-write CI context')
  if integ.get('verification_head_sha')!=con.get('verification_head_sha'):errors.append('integration/consolidation verifier head mismatch')
  if integ.get('verification_external_ci_context')!='supernova/report-admission':errors.append('integration wrong external CI context')
  if integ.get('verification_external_ci_status')!='PASS':errors.append('integration external CI not PASS')
  if integ.get('verification_external_ci_source')!='github-actions[bot]':errors.append('integration CI source not github-actions[bot]')
  if integ.get('verification_external_ci_observed_after_receipt') is not True:errors.append('integration CI not observed after receipt')
 except Exception as exc:errors.append('report admission: '+repr(exc))
 return errors
def transition_admission(trusted_root,candidate_root,base_sha,head_sha,changed):
 if 'state/CURRENT.json' not in changed:return []
 env=os.environ.copy();env['SUPERNOVA_VALIDATE_ROOT']=str(candidate_root);env['SUPERNOVA_BASE_SHA']=base_sha;env['SUPERNOVA_HEAD_SHA']=head_sha;e=[]
 for script in ('scripts/parent_lineage_guard.py','scripts/transition_guard.py'):
  rc,out=run([sys.executable,str(trusted_root/script)],trusted_root,env=env)
  if rc:e.append(script+' failed: '+out[-1200:])
 return e

def validate_pr(repo_root,pr,trusted_errors=None):
 head=pr.get('head') or {};base=pr.get('base') or {};head_sha=head.get('sha');base_sha=base.get('sha');meta=pr_metadata_errors(pr)
 if meta:
  if isinstance(head_sha,str) and HEX40.fullmatch(head_sha):fail_contexts(head_sha,'trusted admission refused: '+meta[0])
  return
 if trusted_errors:fail_contexts(head_sha,trusted_errors[0]);return
 number=pr['number'];trusted=trusted_main_sha(repo_root);run(['git','fetch','--no-tags','origin',f'pull/{number}/head'],repo_root)
 if not is_ancestor(repo_root,trusted,head_sha):fail_contexts(head_sha,'trusted admission refused: PR head does not descend from exact current main');return
 changed=changed_files(repo_root,trusted,head_sha);authority=authority_path_changes(changed)
 if authority and not trusted_bootstrap_success(head_sha,base_sha,number):fail_contexts(head_sha,'trusted admission refused: authority bytes changed without source-verified bootstrap: '+authority[0]);return
 modes=changed_file_mode_errors(repo_root,head_sha,changed)
 if modes:fail_contexts(head_sha,'trusted admission refused: '+modes[0]);return
 tmp=pathlib.Path(tempfile.mkdtemp(prefix=f'supernova-pr-{number}-'))
 try:
  rc,_=run(['git','worktree','add','--detach',str(tmp),head_sha],repo_root)
  if rc:fail_contexts(head_sha,'trusted admission could not create candidate data worktree');return
  results={'supernova/static-control':trusted_static_control(repo_root,tmp),'supernova/report-admission':report_admission(tmp,trusted,changed),'supernova/transition-admission':transition_admission(repo_root,tmp,trusted,head_sha,changed)}
  for ctx,errs in results.items():
   if errs:post_status(head_sha,ctx,'failure','FAIL '+errs[0])
   else:
    label='PASS' if 'state/CURRENT.json' in changed else 'PASS/N-A non-transition';prefix='trusted-bootstrap-run' if authority else 'trusted-main';post_status(head_sha,ctx,'success',prefix+' exact-head '+label)
 finally:
  run(['git','worktree','remove','--force',str(tmp)],repo_root);shutil.rmtree(tmp,ignore_errors=True)
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
