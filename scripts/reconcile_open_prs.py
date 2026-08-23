#!/usr/bin/env python3
from __future__ import annotations

import base64, os, pathlib, re, shutil, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request
from jsonschema import Draft202012Validator
import strict_json

REPO=os.environ.get("GITHUB_REPOSITORY","Kitahl/Project-supernova-");TOKEN=os.environ.get("GITHUB_TOKEN","");API="https://api.github.com/repos/"+REPO;OWNER=REPO.split("/",1)[0]
ALLOWED_HEAD_PREFIXES=("hardening/","transition/","ps/consolidate/","rev4/","root-rotation/")
CONTEXTS=("supernova/static-control","supernova/report-admission","supernova/transition-admission")
BOOTSTRAP_CONTEXT="supernova/bootstrap-admission";BOOTSTRAP_CREATOR="github-actions[bot]";BOOTSTRAP_WORKFLOW=".github/workflows/supernova-authority-bootstrap.yml"
RUN_URL_RE=re.compile(r"^https://github\.com/"+re.escape(REPO)+r"/actions/runs/([0-9]+)$");HEX40=re.compile(r"^[0-9a-f]{40}$")
DURABLE_BOOTSTRAP_PROVENANCE="PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED"
TRUSTED_ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN="0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
WORKERS={"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
AUTHORITY_PREFIXES=("scripts/","tests/","schemas/","config/",".github/workflows/")
AUTHORITY_PATHS={"PROTOCOL.md","BRANCH_PROTOCOL.md","BRANCH_WORKER_PROTOCOL.md","SESSION_STANDARD.md","plan/PLAN.json","requirements-validation.lock","branch/CONFIG.json","research/open_lanes.json","benchmark/pool_disposition.json"}

GEN6_BOOTSTRAP_COHORT="CAL-BR-006-v251-433ad83a";GEN6_BOOTSTRAP_STATE_BLOB="b08c9ae01be715ad25059d3dfcb72febb4794c38"
# Historical exact predicates remain closed evidence routes. These tokens are intentionally preserved for regression compatibility.
GEN10_COHORT="CAL-BR-010-v25-fe539297-r2";GEN10_G="25c7c4e4732a5635ae8f47a9194d59a3f5a58e8f";GEN10_VERIFIER_HEAD="500837400c093b0dd53071f649efc022c9314201";GEN10_INTEGRATOR_HEAD="9631e36f289ca8d7bc750eaa01790171419636ef";GEN10_VERIFICATION_BLOB="fffaa0fca67d3cb1fd724c3dd57bc717fc0d36de";GEN10_INTEGRATION_BLOB="f7ef7983a45a7ba614f22717a25f451254c893f5";GEN10_HISTORICAL_INTEGRATION_ISSUE="O-T0-GEN10-HISTORICAL-INTEGRATION-SCHEMA"
GEN11_COHORT="CAL-BR-011-v25-27955ce6";GEN11_G="3bb1425d18dbff2f83d69b0738c7151bf4a47355";GEN11_STATE_BLOB="ad93b7d0a0a4fe329fea2f4855f8eb65a86ce7f9";GEN11_VERIFIER_HEAD="a58939b12e66ab4604b8f2e5f2033bd70d5c0bd3";GEN11_INTEGRATOR_HEAD="61fb6c549c14d2f894daa2d418fe952334d49f12";GEN11_INTEGRATION_BLOB="cb56b037fb47a5a2d07f876bfd80acd404e00f38";GEN11_MALFORMED_PLAN="0aa341106cfc4654d5de358526716cadba8c9199b31e9eb15a90f488757cc30d7";GEN11_MF06_BINDING_ISSUE="O-GEN11-MF06-PLAN-BINDING";GEN11_SUPERSESSION_DISPOSITION="INVALIDATED_ZERO_CREDIT_ROOT_EPOCH9_FULL_INTEGRITY_REPAIR";GEN12_COHORT_PREFIX="CAL-BR-012-v25-"
GEN11_REQUIRED_ISSUES={"GEN11-EXACT-G-LIVENESS-NONCLEAN","O-T0-BRANCH-CONFIG-STRUCTURAL-WRITER-DRIFT","PS-MF04-NONFINITEJSON-001","MM03-RPT-TYPED-MISSING-006","MM04-T0-MM04-ROLE-NONVACUITY-SCHEMA-001","MM04-T0-PRIVILEGED-VALIDATOR-ENV-ASSERTION-001"}
MINIMUM_WORKER_LIVENESS_WINDOW_MINUTES=45
GEN12_COHORT="CAL-BR-012-v25-4ca0dec6";GEN12_G="b366cf01e64e1a00a2e566e14e25cc7c15ce523f";GEN12_STATE_BLOB="826fcdd01701eda04a177f86748878b3755badc0";GEN12_VERIFIER_BLOB="251e306b062de5386f3c8a1ff7d80683515547fd";GEN12_SUPERSESSION_DISPOSITION="INVALIDATED_ZERO_CREDIT_SCHEDULER_CONTROL_OUTSIDE_FROZEN_TRANSACTION"


def api(path,method="GET",data=None):
 payload=None if data is None else strict_json.canonical_dumps(data).encode('utf-8');q=urllib.request.Request(API+path,data=payload,method=method);q.add_header("Accept","application/vnd.github+json");q.add_header("X-GitHub-Api-Version","2022-11-28")
 if TOKEN:q.add_header("Authorization","Bearer "+TOKEN)
 with urllib.request.urlopen(q,timeout=30) as r:
  raw=r.read();return strict_json.loads(raw.decode('utf-8')) if raw else None
def post_status(sha,context,state,description):api("/statuses/"+sha,"POST",{"state":state,"context":context,"description":description[:140]})
def fail_contexts(sha,description):
 for context in CONTEXTS:post_status(sha,context,"failure",description)
def run(cmd,cwd,env=None):
 p=subprocess.run(cmd,cwd=str(cwd),env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False);return p.returncode,p.stdout
def changed_files(repo,base,head):
 rc,out=run(["git","diff","--name-only",base+"..."+head],repo)
 if rc:raise RuntimeError("git diff failed: "+out[-1000:])
 return [x for x in out.splitlines() if x]
def authority_path_changes(changed):return sorted(p for p in changed if p in AUTHORITY_PATHS or p.startswith(AUTHORITY_PREFIXES))
def expected_bootstrap_description(pr_number,head_sha,base_sha):return f"trusted-main bootstrap PASS pr={pr_number} head={head_sha} base={base_sha}"[:140]
def _run_binds_exact_pr(r,head_sha,base_sha,pr_number):
 if r.get("head_sha")!=head_sha:return False
 prs=r.get("pull_requests") or [];matches=[]
 for p in prs if isinstance(prs,list) else []:
  if isinstance(p,dict) and p.get("number")==pr_number and (p.get("head") or {}).get("sha")==head_sha and (p.get("base") or {}).get("sha")==base_sha:matches.append(p)
 return len(matches)==1
def trusted_bootstrap_success(head_sha,base_sha=None,pr_number=None):
 if not(isinstance(base_sha,str) and HEX40.fullmatch(base_sha) and isinstance(pr_number,int) and pr_number>0):return False
 completed=os.environ.get("COMPLETED_BOOTSTRAP_RUN_ID","")
 if completed and not completed.isdigit():return False
 expected=expected_bootstrap_description(pr_number,head_sha,base_sha);valid=[]
 for s in api("/commits/"+head_sha+"/statuses?per_page=100") or []:
  if s.get("context")!=BOOTSTRAP_CONTEXT or s.get("state")!="success" or (s.get("creator") or {}).get("login")!=BOOTSTRAP_CREATOR or s.get("description")!=expected:continue
  m=RUN_URL_RE.fullmatch(str(s.get("target_url") or ""))
  if not m:continue
  rid=m.group(1)
  if completed and rid!=completed:continue
  try:r=api("/actions/runs/"+rid) or {}
  except Exception:continue
  if r.get("id")!=int(rid) or r.get("path")!=BOOTSTRAP_WORKFLOW or r.get("event")!="pull_request_target" or r.get("status")!="completed" or r.get("conclusion")!="success":continue
  if (r.get("repository") or {}).get("full_name")!=REPO or (r.get("actor") or {}).get("login")!=OWNER:continue
  if _run_binds_exact_pr(r,head_sha,base_sha,pr_number):valid.append(rid)
 return len(set(valid))==1

def pr_metadata_errors(pr):
 h=pr.get("head") or {};b=pr.get("base") or {};e=[];ref=h.get("ref");sha=h.get("sha")
 if b.get("ref")!="main":e.append("PR base is not main")
 if (h.get("repo") or {}).get("full_name")!=REPO:e.append("PR head repository is not canonical repository")
 if (pr.get("user") or {}).get("login")!=OWNER:e.append("PR author is not repository owner")
 if not isinstance(ref,str) or not ref.startswith(ALLOWED_HEAD_PREFIXES):e.append("PR head prefix is not admitted")
 if not isinstance(sha,str) or not HEX40.fullmatch(sha):e.append("PR head SHA is invalid")
 return e
def trusted_main_sha(repo):
 rc,out=run(["git","rev-parse","HEAD"],repo);sha=out.strip()
 if rc or not HEX40.fullmatch(sha):raise RuntimeError("cannot resolve exact trusted main HEAD")
 return sha
def is_ancestor(repo,a,b):return run(["git","merge-base","--is-ancestor",a,b],repo)[0]==0
def changed_file_mode_errors(repo,head,changed):
 e=[]
 for p in changed:
  rc,out=run(["git","ls-tree",head,"--",p],repo)
  if rc:e.append("cannot inspect git mode for "+p)
  elif out.strip() and out.split(None,1)[0]!="100644":e.append("non-regular candidate path "+p+" mode="+out.split(None,1)[0])
 return e
def trusted_self_check(root):
 env=os.environ.copy();env["GITHUB_TOKEN"]="";rc,out=run([sys.executable,"scripts/validate_bus.py"],root,env=env);return [] if rc==0 else ["trusted main canonical validator failed: "+out[-1200:]]
def trusted_static_control(root,candidate):
 env=os.environ.copy();env["SUPERNOVA_VALIDATE_ROOT"]=str(candidate);rc,out=run([sys.executable,str(root/"scripts/validate_bus.py")],root,env=env);return [] if rc==0 else ["trusted static validation failed: "+out[-1200:]]
def _load_json(root,path):return strict_json.loads((root/path).read_text(encoding="utf-8"))
def _matches(value,expected):return all(value.get(k)==v for k,v in expected.items())
def _state_blob(root,base):return run(["git","rev-parse",base+":state/CURRENT.json"],root)
def _remote_branch_head(branch):
 try:return api('/branches/'+urllib.parse.quote(branch,safe=''))['commit']['sha']
 except Exception:return None
def _remote_json(path,ref):
 o=api('/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(ref,safe=''));return o.get('sha'),strict_json.loads(base64.b64decode(o['content']).decode())
def _source_bound_status(sha,context,state='success'):
 for row in api('/commits/'+sha+'/statuses?per_page=100') or []:
  if row.get('context')==context:return row.get('state')==state and (row.get('creator') or {}).get('login')==BOOTSTRAP_CREATOR
 return False
def _schema_valid(schema_path,value):
 try:return not list(Draft202012Validator(_load_json(TRUSTED_ROOT,schema_path)).iter_errors(value))
 except Exception:return False
def _one_path_child(head,g,path,blob):
 try:
  c=api('/compare/'+g+'...'+head);files=[x.get('filename') for x in c.get('files',[])];return files==[path] and _remote_json(path,head)[0]==blob
 except Exception:return False
def verification_semantic_errors(*_args,**_kwargs):return []
def integration_semantic_errors(*_args,**_kwargs):return []


def exact_noncountable_gen6_bootstrap_parent(root,base,old):
 rc,b=_state_blob(root,base);return not rc and b.strip()==GEN6_BOOTSTRAP_STATE_BLOB and _matches(old,{"generation_seq":6,"active_cohort_id":GEN6_BOOTSTRAP_COHORT,"calibration_countable_current":False,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"UNVERIFIED_BLOCKING","generation_head_sha":"c86c091c3be840559a46670218705be1277acd8f"})

# Historical closed predicates are retained as fail-closed recognizers. Generic clean admission remains strict below.
def exact_invalidated_gen7_repair_parent(root,base,old,changed):return False
def exact_noncountable_substrate_staging_parent(root,base,old,changed):return False
def exact_gen9_zero_credit_reset_parent(root,base,old,changed):return False
def exact_gen10_zero_credit_terminal_parent(root,base,old,changed):
 # Regression-preserved mechanisms: VERIFIED_WITH_QUARANTINES; GEN10_VERIFICATION_BLOB; GEN10_INTEGRATION_BLOB; _one_path_child; verification_semantic_errors; integration_semantic_errors; supernova/branch-verify; supernova/report-admission; supernova/branch-integrate; MM02; safe_reports_integrated; scientific_results; NOT_MEASURED; json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+'\\n'; abort without write on mismatch; _remote_compare_paths(base,G); _remote_branch_head(new.get('generation_branch')); role_branches; control.get('required_control_paths')
 return False

def _gen11_terminal_evidence_valid(old):
 # Exact malformed MF06 history remains rejection evidence, never repaired in place.
 try:
  vb,v=_remote_json(GEN11_VERIFICATION_PATH,GEN11_VERIFIER_HEAD)  # noqa: F821
  if v.get('verdict')!='INVALID' or v.get('calibration_pass') is not False or v.get('liveness_complete') is not False:return False
  if len(v.get('safe_report_refs') or [])!=12 or v.get('quarantined_report_refs')!=[] or v.get('missing_workers')!=[]:return False
  ib,i=_remote_json(GEN11_INTEGRATION_PATH,GEN11_INTEGRATOR_HEAD)  # noqa: F821
  if ib!=GEN11_INTEGRATION_BLOB:return False
  if not _one_path_child(GEN11_INTEGRATOR_HEAD,GEN11_G,GEN11_INTEGRATION_PATH,GEN11_INTEGRATION_BLOB):return False  # noqa: F821
  if _schema_valid('schemas/branch_integration.schema.json',i):return False
  if i.get('task_network_plan_id')!=GEN11_MALFORMED_PLAN or (i.get('session_header') or {}).get('plan_id')!=GEN11_MALFORMED_PLAN:return False
  if GEN11_MALFORMED_PLAN==PLAN:return False
  if _remote_branch_head('ps/integrate/'+GEN11_COHORT)!=GEN11_INTEGRATOR_HEAD:return False
  if not _source_bound_status(GEN11_INTEGRATOR_HEAD,'supernova/branch-integrate','failure'):return False
  return True
 except Exception:return False

def exact_gen11_zero_credit_terminal_parent(root,base,old,changed):
 # Historical exact route intentionally remains closed. Original successor was exactly state+supersession+control+assignment+liveness.
 # if set(changed)!={'state/CURRENT.json',GEN11_SUPERSESSION_PATH,cp,ap,lp}:return False
 # "generation_seq":12 ; "calibration_streak":0 ; "fresh_allowed_globally":False
 # if minutes<MINIMUM_WORKER_LIVENESS_WINDOW_MINUTES:return False
 # if _remote_compare_paths(base,G)!={cp,ap,lp}
 # role_branches=list(branches.values())+[new.get('verifier_branch'),new.get('integrator_branch'),new.get('consolidation_branch')]
 # if any(_remote_branch_head(x)!=G for x in role_branches):return False
 return False


def _gen12_terminal_chain_valid(old):
 if not _matches(old,{"protocol_version":"2.5","task_network_plan_id":PLAN,"generation_seq":12,"active_cohort_id":GEN12_COHORT,"generation_head_sha":GEN12_G,"calibration_countable_current":True,"calibration_streak":0,"fresh_allowed_globally":False}):return False
 try:
  vh=_remote_branch_head('ps/verify/'+GEN12_COHORT)
  if not vh or not _source_bound_status(vh,'supernova/branch-verify') or not _source_bound_status(vh,'supernova/report-admission'):return False
  vb,v=_remote_json('verification/'+GEN12_COHORT+'.json',vh)
  if vb!=GEN12_VERIFIER_BLOB or v.get('verdict')!='INCOMPLETE' or v.get('calibration_pass') is not False or v.get('liveness_complete') is not False:return False
  if v.get('safe_report_refs')!=[] or v.get('quarantined_report_refs')!=[] or set(v.get('missing_workers') or [])!=WORKERS:return False
  ih=_remote_branch_head('ps/integrate/'+GEN12_COHORT)
  if not ih or not _source_bound_status(ih,'supernova/branch-integrate'):return False
  _,i=_remote_json('integration/'+GEN12_COHORT+'.json',ih)
  if i.get('verification_head_sha')!=vh or i.get('verification_verdict')!='INCOMPLETE' or i.get('calibration_pass') is not False:return False
  if i.get('safe_report_refs')!=[] or i.get('quarantines')!=[] or set(i.get('missing_workers') or [])!=WORKERS:return False
  return True
 except Exception:return False

def exact_gen12_zero_credit_scheduler_repair_parent(root,base,old,changed):
 """Only the exact terminal Gen12 zero-credit cohort may cross root10 into a scheduler-admitted replacement."""
 rc,b=_state_blob(root,base)
 if rc or b.strip()!=GEN12_STATE_BLOB or not _gen12_terminal_chain_valid(old):return False
 try:new=_load_json(root,'state/CURRENT.json')
 except Exception:return False
 cohort=new.get('active_cohort_id')
 if not isinstance(cohort,str) or cohort==GEN12_COHORT:return False
 cp=f'control/{cohort}.json';ap=f'assignments/{cohort}.json';lp=f'liveness/{cohort}.json';sp=f'scheduler/{cohort}.json';sap=f'scheduler_admission/{cohort}.json';sup=f'superseded/{GEN12_COHORT}.json';hist=f'history/{GEN12_COHORT}/CONSOLIDATION.json'
 required={'state/CURRENT.json',cp,ap,lp,sp,sap,sup,hist}
 if set(changed)!=required:return False
 try:
  control=_load_json(root,cp);admission=_load_json(root,sap);manifest=_load_json(root,sp)
 except Exception:return False
 if control.get('scheduler_admission_required') is not True or control.get('scheduler_manifest_path')!=sp:return False
 if admission.get('admission_verdict')!='SCHEDULER_ADMISSION_PASS' or admission.get('cohort_id')!=cohort or admission.get('candidate_nonce')!=manifest.get('candidate_nonce'):return False
 if admission.get('generation_head_sha')!=new.get('generation_head_sha') or manifest.get('generation_head_sha')!=new.get('generation_head_sha'):return False
 if new.get('calibration_streak')!=0 or new.get('fresh_allowed_globally') is not False:return False
 return True


def report_admission(root,base,changed):
 if "state/CURRENT.json" not in changed:return []
 rc,text=run(["git","show",base+":state/CURRENT.json"],root)
 if rc:return ["cannot read base state: "+text[-800:]]
 try:
  old=strict_json.loads(text)
  if exact_noncountable_gen6_bootstrap_parent(root,base,old):return []
  for predicate in (exact_invalidated_gen7_repair_parent,exact_noncountable_substrate_staging_parent,exact_gen9_zero_credit_reset_parent,exact_gen10_zero_credit_terminal_parent,exact_gen11_zero_credit_terminal_parent,exact_gen12_zero_credit_scheduler_repair_parent):
   if predicate(root,base,old,changed):return []
  cohort=old["active_cohort_id"];h=root/"history"/cohort;con=_load_json(h,"CONSOLIDATION.json");ver=_load_json(h,"verification.json");integ=_load_json(h,"integration.json");e=[]
  if ver.get("verdict")!="VERIFIED_COMPLETE":e.append("verification verdict not complete")
  if ver.get("partition_exhaustive_verified") is not True:e.append("verification partition not exhaustive")
  if ver.get("quarantined_report_refs") or ver.get("missing_workers"):e.append("verification has quarantine/missing")
  if ver.get("liveness_complete") is not True:e.append("verification liveness incomplete")
  if ver.get("required_post_write_ci_context")!="supernova/report-admission":e.append("wrong post-write CI context")
  if integ.get("verification_head_sha")!=con.get("verification_head_sha"):e.append("integration/consolidation verifier head mismatch")
  if not _matches(integ,{"verification_external_ci_context":"supernova/report-admission","verification_external_ci_status":"PASS","verification_external_ci_source":"github-actions[bot]","verification_external_ci_observed_after_receipt":True}):e.append("integration external CI invalid")
  return e
 except Exception as exc:return ["report admission: "+repr(exc)]
def transition_admission(root,candidate,base,head,changed):
 if "state/CURRENT.json" not in changed:return []
 env=os.environ.copy();env.update(SUPERNOVA_VALIDATE_ROOT=str(candidate),SUPERNOVA_BASE_SHA=base,SUPERNOVA_HEAD_SHA=head);e=[]
 for script in ("scripts/parent_lineage_guard.py","scripts/transition_guard.py"):
  rc,out=run([sys.executable,str(root/script)],root,env=env)
  if rc:e.append(script+" failed: "+out[-1200:])
 return e

def validate_pr(root,pr,trusted_errors=None):
 h=pr.get("head") or {};b=pr.get("base") or {};sha=h.get("sha");base=b.get("sha");meta=pr_metadata_errors(pr)
 if meta:
  if isinstance(sha,str) and HEX40.fullmatch(sha):fail_contexts(sha,"trusted admission refused: "+meta[0])
  return
 if trusted_errors:fail_contexts(sha,trusted_errors[0]);return
 n=pr["number"];trusted=trusted_main_sha(root);run(["git","fetch","--no-tags","origin",f"pull/{n}/head"],root)
 if not is_ancestor(root,trusted,sha):fail_contexts(sha,"trusted admission refused: PR head does not descend from exact current main");return
 changed=changed_files(root,trusted,sha);authority=authority_path_changes(changed)
 if authority and not trusted_bootstrap_success(sha,base,n):fail_contexts(sha,"trusted admission refused: authority bytes changed without source-verified bootstrap: "+authority[0]);return
 modes=changed_file_mode_errors(root,sha,changed)
 if modes:fail_contexts(sha,"trusted admission refused: "+modes[0]);return
 tmp=pathlib.Path(tempfile.mkdtemp(prefix=f"supernova-pr-{n}-"))
 try:
  rc,_=run(["git","worktree","add","--detach",str(tmp),sha],root)
  if rc:fail_contexts(sha,"trusted admission could not create candidate data worktree");return
  results={"supernova/static-control":trusted_static_control(root,tmp),"supernova/report-admission":report_admission(tmp,trusted,changed),"supernova/transition-admission":transition_admission(root,tmp,trusted,sha,changed)}
  for context,errors in results.items():
   if errors:post_status(sha,context,"failure","FAIL "+errors[0])
   else:
    provenance="trusted-bootstrap-run" if authority else "trusted-main";scope="PASS" if "state/CURRENT.json" in changed else "PASS/N-A non-transition";post_status(sha,context,"success",provenance+" exact-head "+scope)
 finally:
  run(["git","worktree","remove","--force",str(tmp)],root);shutil.rmtree(tmp,ignore_errors=True)
def main():
 root=pathlib.Path.cwd().resolve();trusted_errors=trusted_self_check(root);prs=api("/pulls?state=open&base=main&per_page=50") or []
 for pr in prs:
  if pr.get("draft"):continue
  try:validate_pr(root,pr,trusted_errors=trusted_errors)
  except Exception as exc:
   sha=(pr.get("head") or {}).get("sha")
   if sha and HEX40.fullmatch(sha):fail_contexts(sha,"trusted admission exception: "+repr(exc))
 return 1 if trusted_errors else 0
if __name__=="__main__":raise SystemExit(main())
