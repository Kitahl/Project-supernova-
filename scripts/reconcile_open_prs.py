#!/usr/bin/env python3
from __future__ import annotations

import base64, importlib.util, os, pathlib, re, shutil, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request
from datetime import datetime
from jsonschema import Draft202012Validator

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import strict_json
from scheduler_admission_guard import candidate_fresh_gate_errors, validate_scheduler_admission, validate_scheduler_manifest

REPO=os.environ.get("GITHUB_REPOSITORY","Kitahl/Project-supernova-"); TOKEN=os.environ.get("GITHUB_TOKEN","")
API="https://api.github.com/repos/"+REPO; OWNER=REPO.split("/",1)[0]
ALLOWED_HEAD_PREFIXES=("hardening/","transition/","ps/consolidate/","ps/stage/","ps/admit/","rev4/","root-rotation/")
CONTEXTS=("supernova/static-control","supernova/report-admission","supernova/transition-admission")
BOOTSTRAP_CONTEXT = "supernova/bootstrap-admission"; BOOTSTRAP_CREATOR = "github-actions[bot]"
BOOTSTRAP_WORKFLOW=".github/workflows/supernova-authority-bootstrap.yml"
BRANCH_RECONCILER_WORKFLOW=".github/workflows/supernova-branch-reconciler.yml"
REST_RECONCILER_WORKFLOW=".github/workflows/supernova-rest-branch-reconciler.yml"
RUN_URL_RE=re.compile(r"^https://github\.com/"+re.escape(REPO)+r"/actions/runs/([0-9]+)$"); HEX40=re.compile(r"^[0-9a-f]{40}$")
DURABLE_BOOTSTRAP_PROVENANCE="PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED"
TRUSTED_ROOT=pathlib.Path(__file__).resolve().parents[1]

GEN6_BOOTSTRAP_COHORT="CAL-BR-006-v251-433ad83a"; GEN6_BOOTSTRAP_STATE_BLOB="b08c9ae01be715ad25059d3dfcb72febb4794c38"
GEN7_INVALIDATED_COHORT="CAL-BR-007-v25-c13b6ee4"; GEN7_INVALIDATED_G="7c182fb7ce3a3941f86f7508bbb4a18152402bb8"; GEN7_INVALIDATED_STATE_BLOB="856481759722e23ff9a652ce140f304efe13b023"
GEN7_SUPERSESSION_PATH=f"superseded/{GEN7_INVALIDATED_COHORT}.json"
STAGING_COHORT="STAGE-BR-008-v25-MF311"; STAGING_SUPERSESSION_PATH=f"superseded/{STAGING_COHORT}.json"
MF311="57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f"; MM4410="026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d"
RUNTIME="9d0a88cc9001295b5e4c0f4163e83c0fd64ce04521e34230ad3539af14f3dfaf"; STAGING_RECEIPT="runtime/updates/GEN8-FOUNDRY-3.1.1-REPLAY-BINDING.json"
GEN9_ZERO_CREDIT_RESET="config/gen9_repair_reset_epoch_v25.json"; GEN9_COHORT="CAL-BR-009-v25-b53ab205"; GEN9_G="67bcfef1a5a1e65c9cc4adb1a2f308ec51c70c3f"; GEN9_STATE_BLOB="31071464144bde197aca0e3f13153be2d85208d7"
GEN9_SUPERSESSION_PATH=f"superseded/{GEN9_COHORT}.json"; GEN9_SUPERSESSION_DISPOSITION="INVALIDATED_ZERO_CREDIT_MUTABLE_DUAL_WRITER_STRUCTURAL_STATUS"; GEN10_COHORT_PREFIX="CAL-BR-010-v25-"
GEN10_COHORT="CAL-BR-010-v25-fe539297-r2"; GEN10_G="25c7c4e4732a5635ae8f47a9194d59a3f5a58e8f"; GEN10_STATE_BLOB="72d5aa0c0f9144bb0cb2faa19ad8300bd38c8ad6"
GEN10_VERIFIER_HEAD="500837400c093b0dd53071f649efc022c9314201"; GEN10_INTEGRATOR_HEAD="9631e36f289ca8d7bc750eaa01790171419636ef"
GEN10_VERIFICATION_PATH=f"verification/{GEN10_COHORT}.json"; GEN10_INTEGRATION_PATH=f"integration/{GEN10_COHORT}.json"
GEN10_VERIFICATION_BLOB="fffaa0fca67d3cb1fd724c3dd57bc717fc0d36de"; GEN10_INTEGRATION_BLOB="f7ef7983a45a7ba614f22717a25f451254c893f5"
GEN10_CONSOLIDATION_PATH=f"history/{GEN10_COHORT}/CONSOLIDATION.json"; GEN10_SUPERSESSION_PATH=f"superseded/{GEN10_COHORT}.json"
GEN10_SUPERSESSION_DISPOSITION="INVALIDATED_ZERO_CREDIT_POST_START_AUTHORITATIVE_CONTROL_REPAIR"; GEN11_COHORT_PREFIX="CAL-BR-011-v25-"
GEN10_HISTORICAL_INTEGRATION_ISSUE="O-T0-GEN10-HISTORICAL-INTEGRATION-SCHEMA"

GEN11_COHORT="CAL-BR-011-v25-27955ce6"; GEN11_G="3bb1425d18dbff2f83d69b0738c7151bf4a47355"; GEN11_STATE_BLOB="ad93b7d0a0a4fe329fea2f4855f8eb65a86ce7f9"
GEN11_VERIFIER_HEAD="a58939b12e66ab4604b8f2e5f2033bd70d5c0bd3"; GEN11_VERIFICATION_PATH=f"verification/{GEN11_COHORT}.json"
GEN11_INTEGRATOR_HEAD="61fb6c549c14d2f894daa2d418fe952334d49f12"; GEN11_INTEGRATION_PATH=f"integration/{GEN11_COHORT}.json"; GEN11_INTEGRATION_BLOB="cb56b037fb47a5a2d07f876bfd80acd404e00f38"
GEN11_MALFORMED_PLAN="0aa341106cfc4654d5de358526716cadba8c9199b31e9eb15a90f488757cc30d7"; GEN11_MF06_BINDING_ISSUE="O-GEN11-MF06-PLAN-BINDING"
GEN11_SUPERSESSION_PATH=f"superseded/{GEN11_COHORT}.json"
GEN11_SUPERSESSION_DISPOSITION="INVALIDATED_ZERO_CREDIT_ROOT_EPOCH9_FULL_INTEGRITY_REPAIR"; GEN12_COHORT_PREFIX="CAL-BR-012-v25-"
GEN11_REQUIRED_ISSUES={"GEN11-EXACT-G-LIVENESS-NONCLEAN","O-T0-BRANCH-CONFIG-STRUCTURAL-WRITER-DRIFT","PS-MF04-NONFINITEJSON-001","MM03-RPT-TYPED-MISSING-006","MM04-T0-MM04-ROLE-NONVACUITY-SCHEMA-001","MM04-T0-PRIVILEGED-VALIDATOR-ENV-ASSERTION-001"}
MINIMUM_WORKER_LIVENESS_WINDOW_MINUTES=45

GEN12_COHORT="CAL-BR-012-v25-4ca0dec6"; GEN12_G="b366cf01e64e1a00a2e566e14e25cc7c15ce523f"
GEN12_STATE_BLOB="826fcdd01701eda04a177f86748878b3755badc0"; GEN12_VERIFIER_BLOB="251e306b062de5386f3c8a1ff7d80683515547fd"
GEN12_SUPERSESSION_DISPOSITION="INCOMPLETE_0_SAFE_0_QUARANTINED_12_MISSING_ZERO_CREDIT_ROOT11_SUCCESSOR"

AUTHORITY_PREFIXES=("scripts/","tests/","schemas/","config/",".github/workflows/")
AUTHORITY_PATHS={"PROTOCOL.md","BRANCH_PROTOCOL.md","BRANCH_WORKER_PROTOCOL.md","SESSION_STANDARD.md","plan/PLAN.json","requirements-validation.lock","branch/CONFIG.json","research/open_lanes.json","benchmark/pool_disposition.json"}
WORKERS={"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
PREACTIVATION_ROLES=WORKERS|{"MF06"}
PRODUCTION_ROLES=PREACTIVATION_ROLES|{"MM06","BIL00"}
PLAN="0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
ROOT11_CONSOLIDATION_SCHEMA="PS-BRANCH-CONSOLIDATION-2.5-ROOT11-1"

def api(path,method="GET",data=None):
    payload=None if data is None else strict_json.canonical_dumps(data).encode('utf-8')
    q=urllib.request.Request(API+path,data=payload,method=method);q.add_header("Accept","application/vnd.github+json");q.add_header("X-GitHub-Api-Version","2022-11-28")
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
def _exact_diff_name_status(repo,base,expected):
    rc,out=run(["git","diff","--name-status","--no-renames",base+"...HEAD"],repo)
    if rc:return False
    observed={}
    for line in out.splitlines():
        if not line:return False
        fields=line.split('\t')
        if len(fields)!=2 or fields[1] in observed:return False
        observed[fields[1]]=fields[0]
    return observed==expected
def _root11_promotion_paths_are_create_once(repo,base,R,created_paths):
    for path in created_paths:
        if run(['git','cat-file','-e',R+':'+path],repo)[0]==0:return False
        if run(['git','cat-file','-e',base+':'+path],repo)[0]==0:return False
    expected={'state/CURRENT.json':'M'}
    expected.update({path:'A' for path in created_paths})
    return _exact_diff_name_status(repo,base,expected)
def _root11_countable_control_contract_matches(control,frozen,accepted,candidate):
    required=accepted.get('required_control_paths') if isinstance(accepted,dict) else None
    return isinstance(required,list) and frozen==accepted==candidate and control.get('required_control_paths')==required
def authority_path_changes(changed):return sorted(p for p in changed if p in AUTHORITY_PATHS or p.startswith(AUTHORITY_PREFIXES))
def expected_bootstrap_description(pr_number,head_sha,base_sha):return f"trusted-main bootstrap PASS pr={pr_number} head={head_sha} base={base_sha}"[:140]
def _run_binds_exact_pr(r,head_sha,base_sha,pr_number):
    if r.get("head_sha")!=head_sha:return False
    # GitHub currently reports pull_requests=[] for pull_request_target runs in
    # this repository. Bind the run to the event head, then independently reread
    # the exact numbered PR instead of depending on that unavailable association.
    try:p=api("/pulls/"+str(pr_number)) or {}
    except Exception:return False
    ph=p.get("head") or {};pb=p.get("base") or {}
    if p.get("number")!=pr_number or ph.get("sha")!=head_sha or pb.get("sha")!=base_sha:return False
    if (ph.get("repo") or {}).get("full_name")!=REPO:return False
    if r.get("head_branch") not in (None,ph.get("ref")):return False
    head_repo=r.get("head_repository") or r.get("repository") or {}
    return head_repo.get("full_name")==REPO
def trusted_bootstrap_success(head_sha,base_sha=None,pr_number=None):
    # Frozen pre-root9 source-token compatibility only; authority still requires exact head+base+PR: trusted_bootstrap_success(head_sha)
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
        if not _run_binds_exact_pr(r,head_sha,base_sha,pr_number):continue
        valid.append(rid)
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
def trusted_ruleset_errors():
    try:
        path=TRUSTED_ROOT/'scripts/reconcile_ruleset_attestation.py';spec=importlib.util.spec_from_file_location('supernova_trusted_ruleset_attestation',path)
        if spec is None or spec.loader is None:return ['trusted ruleset attestor unavailable']
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        rules=mod.api(mod.API+'/rules/branches/main',auth=False);actions_app=mod.api('https://api.github.com/apps/github-actions',auth=False)
        result=mod.evaluate_rules(rules,actions_app)
        required=('pr_required','deletion_blocked','non_fast_forward_blocked','actions_app','static_bound','report_bound','transition_bound','strict_up_to_date','spoof_resistant')
        missing=[key for key in required if result.get(key) is not True]
        return [] if not missing else ['live main ruleset lacks required source-bound strict/up-to-date protection: '+','.join(missing)]
    except Exception as exc:return ['live main ruleset attestation failed closed: '+repr(exc)]
def trusted_static_control(root,candidate):
    env=os.environ.copy();env["SUPERNOVA_VALIDATE_ROOT"]=str(candidate);rc,out=run([sys.executable,str(root/"scripts/validate_bus.py")],root,env=env);return [] if rc==0 else ["trusted static validation failed: "+out[-1200:]]
def _load_json(root,path):return strict_json.loads((root/path).read_text(encoding="utf-8"))
def _matches(value,expected):return all(value.get(k)==v for k,v in expected.items())
def _state_blob(root,base):return run(["git","rev-parse",base+":state/CURRENT.json"],root)
def _receipt(cohort,g,blob,disposition,seq,countable):return {"schema_version":"PS-COHORT-SUPERSESSION-1","cohort_id":cohort,"generation_head_sha":g,"state_blob_sha":blob,"disposition":disposition,"calibration_credit":0,"fresh_evidence_consumed":False,"replacement_generation_seq":seq,"replacement_countable":countable}
def _parse_utc(value):return datetime.fromisoformat(str(value).replace('Z','+00:00'))

def exact_noncountable_gen6_bootstrap_parent(root,base,old):
    rc,b=_state_blob(root,base);return not rc and b.strip()==GEN6_BOOTSTRAP_STATE_BLOB and _matches(old,{"generation_seq":6,"active_cohort_id":GEN6_BOOTSTRAP_COHORT,"calibration_countable_current":False,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"UNVERIFIED_BLOCKING","generation_head_sha":"c86c091c3be840559a46670218705be1277acd8f"})
def exact_invalidated_gen7_repair_parent(root,base,old,changed):
    rc,b=_state_blob(root,base)
    if rc or b.strip()!=GEN7_INVALIDATED_STATE_BLOB or not _matches(old,{"generation_seq":7,"active_cohort_id":GEN7_INVALIDATED_COHORT,"generation_head_sha":GEN7_INVALIDATED_G,"calibration_countable_current":True,"calibration_streak":0,"fresh_allowed_globally":False}) or not {"state/CURRENT.json",GEN7_SUPERSESSION_PATH}.issubset(changed):return False
    try:new=_load_json(root,"state/CURRENT.json");receipt=_load_json(root,GEN7_SUPERSESSION_PATH)
    except Exception:return False
    return _matches(new,{"generation_seq":8,"active_parent_state_git_identity":GEN7_INVALIDATED_STATE_BLOB,"calibration_countable_current":False,"calibration_streak":0,"fresh_allowed_globally":False}) and new.get("active_cohort_id")!=GEN7_INVALIDATED_COHORT and GEN7_INVALIDATED_COHORT in set(new.get("superseded_cohorts") or []) and receipt==_receipt(GEN7_INVALIDATED_COHORT,GEN7_INVALIDATED_G,GEN7_INVALIDATED_STATE_BLOB,"INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS",8,False)
def exact_noncountable_substrate_staging_parent(root,base,old,changed):
    rc,b=_state_blob(root,base);blob=b.strip()
    if rc or not HEX40.fullmatch(blob) or not _matches(old,{"generation_seq":8,"active_cohort_id":STAGING_COHORT,"generation_branch":"ps/gen/"+STAGING_COHORT,"calibration_countable_current":False,"calibration_streak":0,"fresh_allowed_globally":False,"network_mode":"BENCHMARK_DISCOVERY_WAIT","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT}) or GEN7_INVALIDATED_COHORT not in set(old.get("superseded_cohorts") or []):return False
    try:new=_load_json(root,"state/CURRENT.json");receipt=_load_json(root,STAGING_SUPERSESSION_PATH)
    except Exception:return False
    cohort=str(new.get("active_cohort_id",""));required={"state/CURRENT.json",STAGING_SUPERSESSION_PATH,new.get("active_control_manifest_path"),new.get("active_assignment_path"),f"liveness/{cohort}.json"}
    return None not in required and required.issubset(changed) and cohort.startswith("CAL-BR-009-v25-") and _matches(new,{"generation_seq":9,"active_parent_state_git_identity":blob,"calibration_countable_current":True,"calibration_streak":0,"fresh_allowed_globally":False,"network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT}) and STAGING_COHORT in set(new.get("superseded_cohorts") or []) and receipt==_receipt(STAGING_COHORT,old.get("generation_head_sha"),blob,"NONCOUNTABLE_SUBSTRATE_STAGING_COMPLETE_ZERO_CREDIT",9,True)
def exact_gen9_zero_credit_reset_parent(root,base,old,changed):
    rc,b=_state_blob(root,base);old_expected={"protocol_version":"2.5","task_network_plan_id":PLAN,"generation_seq":9,"active_cohort_id":GEN9_COHORT,"generation_head_sha":GEN9_G,"calibration_countable_current":True,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND","network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT}
    if rc or b.strip()!=GEN9_STATE_BLOB or not _matches(old,old_expected) or GEN9_COHORT in set(old.get("superseded_cohorts") or []):return False
    try:marker=_load_json(root,GEN9_ZERO_CREDIT_RESET);new=_load_json(root,"state/CURRENT.json");receipt=_load_json(root,GEN9_SUPERSESSION_PATH)
    except Exception:return False
    marker_expected={"schema_version":"PS-GEN9-REPAIR-RESET-EPOCH-2.5-1","old_state_blob":GEN9_STATE_BLOB,"old_cohort_id":GEN9_COHORT,"old_generation_head_sha":GEN9_G,"allowed_successor_generation_seq":10,"allowed_successor_cohort_prefix":GEN10_COHORT_PREFIX,"supersession_disposition":GEN9_SUPERSESSION_DISPOSITION,"calibration_credit":0,"fresh_evidence_consumed":False,"foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"failure_semantics":"FAIL_CLOSED"};cohort=new.get("active_cohort_id")
    if not _matches(marker,marker_expected) or not isinstance(cohort,str) or not cohort.startswith(GEN10_COHORT_PREFIX):return False
    cp=f"control/{cohort}.json";ap=f"assignments/{cohort}.json";lp=f"liveness/{cohort}.json"
    if new.get("active_control_manifest_path")!=cp or new.get("active_assignment_path")!=ap or set(changed)!={"state/CURRENT.json",GEN9_SUPERSESSION_PATH,cp,ap,lp}:return False
    if set(new.get("superseded_cohorts") or [])!=set(old.get("superseded_cohorts") or [])|{GEN9_COHORT}:return False
    if not _matches(new,{"protocol_version":"2.5","task_network_plan_id":PLAN,"transport_mode":"BRANCH_GITOPS","generation_seq":10,"active_parent_state_git_identity":GEN9_STATE_BLOB,"generation_branch":f"ps/gen/{cohort}","calibration_countable_current":True,"calibration_required_clean_cohorts":2,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND","network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT,"expected_base_head":base,"current_runtime_blocker":"O-T0-TWO_CLEAN_COUNTABLE_V25_COHORTS","goal1_status":"BLOCKED_T0","goal2_status":"BLOCKED_BY_GOAL1","verifier_branch":f"ps/verify/{cohort}","integrator_branch":f"ps/integrate/{cohort}","consolidation_branch":f"ps/consolidate/{cohort}"}):return False
    branches=new.get("worker_branches") or {}
    if set(branches)!=WORKERS or any(branches[w]!=f"ps/work/{cohort}/{w}" for w in WORKERS):return False
    try:control=_load_json(root,cp);assignment=_load_json(root,ap);live=_load_json(root,lp)
    except Exception:return False
    rc_cb,control_blob=run(["git","rev-parse","HEAD:"+cp],root);rc_ab,assignment_blob=run(["git","rev-parse","HEAD:"+ap],root);control_blob=control_blob.strip();assignment_blob=assignment_blob.strip()
    if rc_cb or rc_ab or new.get("active_control_manifest_git_identity")!=control_blob or new.get("active_assignment_git_identity")!=assignment_blob:return False
    common={"task_network_plan_id":PLAN,"cohort_id":cohort,"generation_seq":10,"parent_state_git_identity":GEN9_STATE_BLOB,"expected_base_head":base,"calibration_countable":True};root_sha=control.get("control_release_commit_sha")
    return _matches(control,common) and _matches(assignment,common) and assignment.get("generation_branch")==new.get("generation_branch") and assignment.get("generation_root_sha")==root_sha and assignment.get("control_manifest_git_identity")==control_blob and _matches(live,{"cohort_id":cohort,"generation_seq":10,"generation_root_sha":root_sha,"control_manifest_id":control.get("control_manifest_id"),"control_manifest_git_identity":control_blob,"assignment_id":assignment.get("assignment_id"),"assignment_git_identity":assignment_blob}) and receipt==_receipt(GEN9_COHORT,GEN9_G,GEN9_STATE_BLOB,GEN9_SUPERSESSION_DISPOSITION,10,True)

def _remote_json(path,ref):
    obj=api('/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(ref,safe=''))
    if not isinstance(obj,dict) or obj.get('type')!='file':raise ValueError('remote object is not file: '+path)
    return obj.get('sha'),strict_json.loads(base64.b64decode(obj['content']).decode('utf-8'))
def _remote_branch_head(branch):
    try:return (api('/branches/'+urllib.parse.quote(branch,safe='')) or {}).get('commit',{}).get('sha')
    except urllib.error.HTTPError as exc:
        if exc.code==404:return None
        raise
def _source_bound_status(sha,context,state='success'):
    for row in api('/commits/'+sha+'/statuses?per_page=100') or []:
        if row.get('context')==context:return row.get('state')==state and (row.get('creator') or {}).get('login')==BOOTSTRAP_CREATOR
    return False
def _trusted_workflow_status_row(sha,context,workflow,events,state='success',description=None):
    rows=[row for row in api('/commits/'+sha+'/statuses?per_page=100') or [] if row.get('context')==context]
    if not rows:return None
    row=max(rows,key=lambda item:int(item.get('id') or 0))
    if row.get('state')!=state or (row.get('creator') or {}).get('login')!=BOOTSTRAP_CREATOR:return None
    if description is not None and row.get('description')!=description:return None
    m=RUN_URL_RE.fullmatch(str(row.get('target_url') or ''))
    if not m:return None
    try:r=api('/actions/runs/'+m.group(1)) or {}
    except Exception:return None
    return row if r.get('path')==workflow and r.get('event') in set(events) and r.get('status')=='completed' and r.get('conclusion')=='success' and (r.get('repository') or {}).get('full_name')==REPO and (r.get('actor') or {}).get('login')==OWNER else None
def _trusted_workflow_status(sha,context,workflow,events,state='success',description=None):
    return _trusted_workflow_status_row(sha,context,workflow,events,state,description) is not None

def _source_bound_generation_status(generation_head,pr):
    """Bind branch-generation success to this exact pointer PR workflow run."""
    head=(pr.get('head') or {}).get('sha');base=(pr.get('base') or {}).get('sha');number=pr.get('number')
    expected=f'stage-generation PASS pr={number} pointer={head} base={base} G={generation_head}'[:140]
    rows=[row for row in api('/commits/'+generation_head+'/statuses?per_page=100') or [] if row.get('context')=='supernova/branch-generation']
    if not rows:return False
    row=max(rows,key=lambda item:int(item.get('id') or 0))
    if row.get('state')!='success' or (row.get('creator') or {}).get('login')!=BOOTSTRAP_CREATOR or row.get('description')!=expected:return False
    m=RUN_URL_RE.fullmatch(str(row.get('target_url') or ''))
    if not m:return False
    rid=m.group(1)
    try:r=api('/actions/runs/'+rid) or {}
    except Exception:return False
    if r.get('path')!=BRANCH_RECONCILER_WORKFLOW or r.get('event')!='pull_request_target' or r.get('status')!='completed' or r.get('conclusion')!='success':return False
    if (r.get('repository') or {}).get('full_name')!=REPO or (r.get('actor') or {}).get('login')!=OWNER:return False
    return _run_binds_exact_pr(r,head,base,number)
def _one_path_child(head,parent,path,blob_sha=None):
    c=api('/commits/'+head) or {};parents=c.get('parents') or [];files=c.get('files') or []
    ok=len(parents)==1 and parents[0].get('sha')==parent and len(files)==1 and files[0].get('filename')==path and files[0].get('status')=='added'
    return ok and (blob_sha is None or files[0].get('sha')==blob_sha)
def _schema_valid(schema_path,obj):
    schema=_load_json(TRUSTED_ROOT,schema_path);Draft202012Validator.check_schema(schema);return not list(Draft202012Validator(schema).iter_errors(obj))
def _trusted_v25_module():
    path=TRUSTED_ROOT/'scripts/reconcile_v25_admission.py';spec=importlib.util.spec_from_file_location('supernova_trusted_v25_admission',path)
    if spec is None or spec.loader is None:raise RuntimeError('cannot load trusted reconcile_v25_admission')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def _trusted_branch_module():
    path=TRUSTED_ROOT/'scripts/reconcile_branch_statuses.py';spec=importlib.util.spec_from_file_location('supernova_trusted_branch_statuses',path)
    if spec is None or spec.loader is None:raise RuntimeError('cannot load trusted reconcile_branch_statuses')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def _trusted_preactivation_module():
    path=TRUSTED_ROOT/'scripts/reconcile_preactivation_admission.py';spec=importlib.util.spec_from_file_location('supernova_trusted_preactivation_admission',path)
    if spec is None or spec.loader is None:raise RuntimeError('cannot load trusted reconcile_preactivation_admission')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def _source_bound_preactivation_status(commit,role,cohort,generation_head,cutoff_utc):
    try:return bool(_trusted_preactivation_module().source_status_valid(commit,role,cohort,generation_head,cutoff_utc))
    except Exception:return False
def _remote_compare_paths(base,head):return {f.get('filename') for f in (api('/compare/'+base+'...'+head) or {}).get('files',[]) if f.get('status')!='unchanged'}

def _remote_inactive_production_snapshot(manifest,G):
    """Independently prove all 15 canonical production refs remain exactly at G."""
    cohort=manifest.get('cohort_id');tasks={row.get('role_id'):row for row in manifest.get('tasks',[]) if isinstance(row,dict)}
    if set(tasks)!=PRODUCTION_ROLES or len(tasks)!=15:return None
    snapshot={}
    for role in sorted(PRODUCTION_ROLES):
        branch=(f'ps/work/{cohort}/{role}' if role in WORKERS else f'ps/verify/{cohort}' if role=='MM06' else f'ps/integrate/{cohort}' if role=='MF06' else f'ps/consolidate/{cohort}')
        if (tasks.get(role) or {}).get('production_branch')!=branch:return None
        head=_remote_branch_head(branch)
        if head!=G:return None
        snapshot[role]=(branch,head)
    return snapshot

def _remote_worker_preactivation_errors(source,manifest,pointer):
    """Re-derive all 12 workers, MF06, and the BIL00 inventory before cutoff."""
    errors=[];cohort=source.get('cohort_id');G=source.get('generation_head_sha');cutoff=manifest.get('admission_cutoff_utc');results=source.get('preactivation_results') or []
    roles=[row.get('role_id') for row in results if isinstance(row,dict)]
    if len(results)!=13 or set(roles)!=PREACTIVATION_ROLES or len(roles)!=len(set(roles)):return ['MM06 source preactivation partition is not exact 12 workers plus MF06']
    tasks={row.get('role_id'):row for row in manifest.get('tasks',[]) if isinstance(row,dict)}
    authority=_load_json(TRUSTED_ROOT,'config/scheduler_attestation_authority_v25.json')
    for row in results:
        role=row.get('role_id');branch=row.get('preactivation_branch');path=row.get('preactivation_path');commit=row.get('receipt_creation_commit_sha');blob=row.get('receipt_blob_sha')
        if branch!=f'ps/preactivate/{cohort}/{role}' or path!=f'preactivation/{cohort}/{role}.json':errors.append(str(role)+' preactivation branch/path mismatch');continue
        if _remote_branch_head(branch)!=commit:errors.append(role+' preactivation branch moved');continue
        try:observed_blob,receipt=_remote_json(path,commit)
        except Exception as exc:errors.append(role+' preactivation receipt unavailable: '+repr(exc));continue
        if observed_blob!=blob or not _one_path_child(commit,G,path,blob):errors.append(role+' preactivation receipt is not exact one-path child/blob');continue
        if not _schema_valid('schemas/preactivation_receipt.schema.json',receipt):errors.append(role+' preactivation receipt schema invalid')
        task=tasks.get(role) or {};commitment=task.get('worker_auth_commitment') if role in WORKERS else authority.get('mf06_preactivation_key_commitment_sha256')
        expected={'protocol_version':source.get('protocol_version'),'task_network_plan_id':source.get('task_network_plan_id'),'candidate_nonce':source.get('candidate_nonce'),'cohort_id':cohort,'generation_root_sha':source.get('generation_root_sha'),'generation_head_sha':G,'staged_candidate_git_identity':source.get('staged_candidate_git_identity'),'scheduler_manifest_git_identity':source.get('scheduler_manifest_git_identity'),'role_id':role,'scheduler_task_id':task.get('scheduler_task_id'),'behavioral_config_sha256':task.get('behavioral_config_sha256'),'runtime_state_id':manifest.get('runtime_state_id'),'role_auth_scheme':'PS-HMAC-SHA256-PREACTIVATION-RECEIPT-1','role_auth_commitment':commitment,'production_not_before_utc':manifest.get('production_not_before_utc'),'normalized_first_production_utc':task.get('normalized_first_production_utc'),'production_branch':task.get('production_branch'),'production_path':task.get('production_path'),'preactivation_branch':branch,'preactivation_path':path}
        for key,value in expected.items():
            if receipt.get(key)!=value:errors.append(role+' preactivation semantic mismatch: '+key)
        if receipt.get('challenge_occurrence_utc') not in set(task.get('challenge_occurrences_utc') or []):errors.append(role+' preactivation challenge is not a frozen scheduled occurrence')
        if not _source_bound_preactivation_status(commit,role,cohort,G,cutoff):errors.append(role+' preactivation lacks exact-PR trusted success by admission cutoff')
    try:
        branch=source.get('scheduler_inventory_branch');path=source.get('scheduler_inventory_path');commit=source.get('scheduler_inventory_commit_sha');blob=source.get('scheduler_inventory_blob_sha')
        if branch!=f'ps/preactivate/{cohort}/BIL00' or path!=f'preactivation/{cohort}/BIL00.json':errors.append('BIL00 inventory branch/path mismatch')
        elif _remote_branch_head(branch)!=commit:errors.append('BIL00 inventory branch moved')
        else:
            observed_blob,inventory=_remote_json(path,commit)
            if observed_blob!=blob or not _one_path_child(commit,G,path,blob):errors.append('BIL00 inventory is not exact one-path child/blob')
            if not _schema_valid('schemas/scheduler_inventory_attestation.schema.json',inventory):errors.append('BIL00 inventory schema invalid')
            if not _source_bound_preactivation_status(commit,'BIL00',cohort,G,cutoff):errors.append('BIL00 inventory lacks exact-PR trusted success by admission cutoff')
    except Exception as exc:errors.append('BIL00 inventory unavailable: '+repr(exc))
    return errors

def _remote_production_worker_errors(verification,state):
    """Re-derive every clean-credit worker receipt and its trusted HMAC-validating status."""
    errors=[];cohort=state.get('active_cohort_id');G=state.get('generation_head_sha');refs=verification.get('safe_report_refs') or []
    roles=[row.get('worker_id') for row in refs if isinstance(row,dict)]
    if len(refs)!=12 or set(roles)!=WORKERS or len(roles)!=len(set(roles)):return ['production worker partition is not exact 12']
    branches=state.get('worker_branches') or {}
    for row in refs:
        role=row.get('worker_id');branch=row.get('branch');head=row.get('branch_head_sha');commit=row.get('report_creation_commit_sha');path=row.get('path');blob=row.get('blob_sha')
        expected_branch=branches.get(role);expected_path=f'reports/{cohort}/{role}.json'
        if branch!=expected_branch or branch!=f'ps/work/{cohort}/{role}' or path!=expected_path:errors.append(str(role)+' production branch/path mismatch');continue
        if head!=commit or _remote_branch_head(branch)!=head:errors.append(role+' production branch/head moved or creation commit mismatch');continue
        try:observed_blob,report=_remote_json(path,head)
        except Exception as exc:errors.append(role+' production report unavailable: '+repr(exc));continue
        if observed_blob!=blob or not _one_path_child(head,G,path,blob):errors.append(role+' production report is not an exact one-path child/blob of G');continue
        if not _schema_valid('schemas/branch_report.schema.json',report):errors.append(role+' production report schema invalid')
        expected={'task_network_plan_id':PLAN,'cohort_id':cohort,'worker_id':role,'generation_head_sha':G,'worker_branch':branch,'worker_auth_scheme':'PS-HMAC-SHA256-CANONICAL-REPORT-2','worker_auth_commitment':report.get('worker_auth_commitment'),'status':'VALID_ASSIGNED_REPORT','public_safety_status':'PASS','origin_reread_claim':False}
        for key,value in expected.items():
            if report.get(key)!=value:errors.append(role+' production report identity mismatch: '+key)
        if not _trusted_workflow_status(head,'supernova/branch-worker',BRANCH_RECONCILER_WORKFLOW,{'schedule','push','repository_dispatch'},description=role+': BRANCH VALIDATION PASS'):
            errors.append(role+' production report lacks trusted HMAC-validating branch-worker status')
    return errors

def _remote_production_liveness_errors(verification,state):
    """Derive the clean liveness partition only from frozen deadlines and GitHub server timestamps."""
    errors=[];cohort=state.get('active_cohort_id');G=state.get('generation_head_sha')
    try:_,contract=_remote_json(f'liveness/{cohort}.json',G)
    except Exception as exc:return ['frozen liveness contract unavailable: '+repr(exc)]
    if not _schema_valid('schemas/cohort_liveness_contract.schema.json',contract):return ['frozen liveness contract schema invalid']
    lanes={row.get('lane_id'):row for row in contract.get('lanes') or [] if isinstance(row,dict)}
    refs={row.get('worker_id'):row for row in verification.get('safe_report_refs') or [] if isinstance(row,dict)}
    if set(lanes)!=WORKERS or set(refs)!=WORKERS:return ['liveness/report partition is not exact 12']
    expected=[]
    for role in sorted(WORKERS):
        lane=lanes[role];ref=refs[role];head=ref.get('branch_head_sha')
        row=_trusted_workflow_status_row(head,'supernova/branch-worker',BRANCH_RECONCILER_WORKFLOW,{'schedule','push','repository_dispatch'},description=role+': BRANCH VALIDATION PASS')
        if row is None:return [role+' liveness lacks trusted exact-head branch-worker status']
        created=row.get('created_at')
        try:created_dt=_parse_utc(created);start=_parse_utc(lane.get('expected_window_start_utc'));deadline=_parse_utc(lane.get('deadline_utc'))
        except Exception:return [role+' liveness status/deadline timestamp invalid']
        if not(start<=created_dt<=deadline):return [role+' trusted branch-worker status is outside frozen production window']
        expected.append({'lane_id':role,'task_id':None,'associated_chat_ref':None,'expected_window_start':lane.get('expected_window_start_utc'),'expected_window_end':lane.get('deadline_utc'),'observation_time':created,'receipt_status':'RUN_OBSERVED','task_state':'TASK_STATE_UNKNOWN','observation_source':'GITHUB_RECEIPT_MONITOR','receipt_ref':lane.get('branch')+':'+lane.get('path'),'lateness_seconds':0,'notes':f"trusted branch-worker status id={row.get('id')} created_at={created}"})
    return [] if verification.get('lane_liveness_observations')==expected else ['MM06 liveness observations differ from trusted deadline/status rederivation']

def _gen10_terminal_evidence_valid(old):
    try:
        vb,v=_remote_json(GEN10_VERIFICATION_PATH,GEN10_VERIFIER_HEAD);ib,i=_remote_json(GEN10_INTEGRATION_PATH,GEN10_INTEGRATOR_HEAD)
        if vb!=GEN10_VERIFICATION_BLOB or ib!=GEN10_INTEGRATION_BLOB:return False
        if not _one_path_child(GEN10_VERIFIER_HEAD,GEN10_G,GEN10_VERIFICATION_PATH,GEN10_VERIFICATION_BLOB) or not _one_path_child(GEN10_INTEGRATOR_HEAD,GEN10_G,GEN10_INTEGRATION_PATH,GEN10_INTEGRATION_BLOB):return False
        if not _schema_valid('schemas/branch_verification.schema.json',v) or not _schema_valid('schemas/branch_integration.schema.json',i):return False
        sem=_trusted_v25_module()
        if sem.verification_semantic_errors(v,old) or sem.integration_semantic_errors(i,v,old):return False
        safe=v.get('safe_report_refs') or [];q=v.get('quarantined_report_refs') or [];missing=v.get('missing_workers') or []
        if v.get('verdict')!='VERIFIED_WITH_QUARANTINES' or v.get('calibration_pass') is not False or len(safe)!=11 or len(q)!=1 or missing:return False
        if q[0].get('worker_id')!='MM02' or q[0].get('reason_code')!='O-T0-GEN10-MM02-TRANSPORT-SERIALIZATION':return False
        if i.get('verification_head_sha')!=GEN10_VERIFIER_HEAD or i.get('safe_report_refs')!=safe or i.get('quarantines')!=q or i.get('missing_workers')!=missing or i.get('calibration_pass') is not False:return False
        costs=i.get('costs_regressions_unknowns') or {};expected_costs={"benchmark_executions":0,"calibration_credit":0,"calibration_streak_effect":0,"deep_research_runs":0,"fresh_evidence_units_consumed":0,"missing_workers":0,"protected_manifest_reads":0,"quarantined_reports_preserved":1,"safe_reports_integrated":11,"runtime_mutation":"NONE","scientific_promotion":"NONE","scientific_results":"NOT_MEASURED"}
        return _matches(costs,expected_costs) and _source_bound_status(GEN10_VERIFIER_HEAD,'supernova/branch-verify','success') and _source_bound_status(GEN10_VERIFIER_HEAD,'supernova/report-admission','success') and _source_bound_status(GEN10_INTEGRATOR_HEAD,'supernova/branch-integrate','failure')
    except Exception:return False

def exact_gen10_zero_credit_terminal_parent(root,base,old,changed):
    rc,b=_state_blob(root,base);old_expected={"protocol_version":"2.5","task_network_plan_id":PLAN,"generation_seq":10,"active_cohort_id":GEN10_COHORT,"generation_head_sha":GEN10_G,"calibration_countable_current":True,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND","network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT}
    if rc or b.strip()!=GEN10_STATE_BLOB or not _matches(old,old_expected) or GEN10_COHORT in set(old.get('superseded_cohorts') or []):return False
    try:new=_load_json(root,'state/CURRENT.json');con=_load_json(root,GEN10_CONSOLIDATION_PATH);receipt=_load_json(root,GEN10_SUPERSESSION_PATH)
    except Exception:return False
    cohort=new.get('active_cohort_id')
    if not isinstance(cohort,str) or not cohort.startswith(GEN11_COHORT_PREFIX):return False
    cp=f'control/{cohort}.json';ap=f'assignments/{cohort}.json';lp=f'liveness/{cohort}.json'
    if set(changed)!={'state/CURRENT.json',GEN10_CONSOLIDATION_PATH,GEN10_SUPERSESSION_PATH,cp,ap,lp}:return False
    if new.get('active_control_manifest_path')!=cp or new.get('active_assignment_path')!=ap:return False
    if set(new.get('superseded_cohorts') or [])!=set(old.get('superseded_cohorts') or [])|{GEN10_COHORT}:return False
    if not _matches(new,{"protocol_version":"2.5","task_network_plan_id":PLAN,"transport_mode":"BRANCH_GITOPS","generation_seq":11,"active_parent_state_git_identity":GEN10_STATE_BLOB,"generation_branch":f"ps/gen/{cohort}","calibration_countable_current":True,"calibration_required_clean_cohorts":2,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND","network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":old.get('foundry_sha256'),"mastermind_sha256":old.get('mastermind_sha256'),"runtime_state_id":old.get('runtime_state_id'),"base_runtime_state_id":old.get('base_runtime_state_id'),"actual_runtime_plan_id":old.get('actual_runtime_plan_id'),"accepted_network_checkpoint_id":old.get('accepted_network_checkpoint_id'),"benchmark_registry_path":old.get('benchmark_registry_path'),"benchmark_registry_git_identity":old.get('benchmark_registry_git_identity'),"runtime_update_receipt_path":old.get('runtime_update_receipt_path'),"expected_base_head":base,"current_runtime_blocker":"O-T0-TWO_CLEAN_COUNTABLE_V25_COHORTS","goal1_status":"BLOCKED_T0","goal2_status":"BLOCKED_BY_GOAL1","verifier_branch":f"ps/verify/{cohort}","integrator_branch":f"ps/integrate/{cohort}","consolidation_branch":f"ps/consolidate/{cohort}"}):return False
    G=new.get('generation_head_sha');branches=new.get('worker_branches') or {}
    if not isinstance(G,str) or not HEX40.fullmatch(G) or set(branches)!=WORKERS or any(branches[w]!=f'ps/work/{cohort}/{w}' for w in WORKERS):return False
    try:control=_load_json(root,cp);assignment=_load_json(root,ap);live=_load_json(root,lp);contract=_load_json(root,'config/countable_control_set_v25.json')
    except Exception:return False
    rc_cb,control_blob=run(['git','rev-parse','HEAD:'+cp],root);rc_ab,assignment_blob=run(['git','rev-parse','HEAD:'+ap],root);control_blob=control_blob.strip();assignment_blob=assignment_blob.strip()
    if rc_cb or rc_ab or new.get('active_control_manifest_git_identity')!=control_blob or new.get('active_assignment_git_identity')!=assignment_blob:return False
    common={"task_network_plan_id":PLAN,"cohort_id":cohort,"generation_seq":11,"parent_state_git_identity":GEN10_STATE_BLOB,"expected_base_head":base,"calibration_countable":True}
    if not _matches(control,common) or not _matches(assignment,common) or control.get('protocol_version')!='2.5' or control.get('control_release_commit_sha')!=base:return False
    if set(control.get('required_control_paths') or [])!=set(contract.get('required_control_paths') or []):return False
    if assignment.get('generation_branch')!=new.get('generation_branch') or assignment.get('generation_root_sha')!=base or assignment.get('control_manifest_git_identity')!=control_blob:return False
    if not _matches(live,{"cohort_id":cohort,"generation_seq":11,"generation_root_sha":base,"control_manifest_id":control.get('control_manifest_id'),"control_manifest_git_identity":control_blob,"assignment_id":assignment.get('assignment_id'),"assignment_git_identity":assignment_blob}):return False
    if _remote_compare_paths(base,G)!={cp,ap,lp} or _remote_branch_head(new.get('generation_branch'))!=G:return False
    role_branches=list(branches.values())+[new.get('verifier_branch'),new.get('integrator_branch'),new.get('consolidation_branch')]
    if any(_remote_branch_head(x)!=G for x in role_branches):return False
    workers=assignment.get('workers') or {}
    if set(workers)!=WORKERS:return False
    for wid in WORKERS:
        w=workers[wid];joined='\n'.join(str(x) for x in (w.get('constraints') or []))
        if w.get('fresh_allowed') is not False or w.get('private_manifest_id') is not None or w.get('benchmark_suite_id') is not None:return False
        if 'HMAC input contract is separate from committed-file byte contract' not in joined or "json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+'\\n'" not in joined or 'abort without write on mismatch' not in joined:return False
    if receipt!=_receipt(GEN10_COHORT,GEN10_G,GEN10_STATE_BLOB,GEN10_SUPERSESSION_DISPOSITION,11,True):return False
    if not _matches(con,{"cohort_id":GEN10_COHORT,"generation_head_sha":GEN10_G,"verification_head_sha":GEN10_VERIFIER_HEAD,"integration_head_sha":GEN10_INTEGRATOR_HEAD,"expected_main_head":base,"calibration_counted":False}):return False
    refs=set(con.get('safe_history_refs') or []);required_refs={f'{GEN10_VERIFICATION_PATH}@{GEN10_VERIFIER_HEAD}#{GEN10_VERIFICATION_BLOB}',f'{GEN10_INTEGRATION_PATH}@{GEN10_INTEGRATOR_HEAD}#{GEN10_INTEGRATION_BLOB}',f'github-status:{GEN10_VERIFIER_HEAD}:supernova/branch-verify=success',f'github-status:{GEN10_VERIFIER_HEAD}:supernova/report-admission=success',f'github-status:{GEN10_INTEGRATOR_HEAD}:supernova/branch-integrate=failure','issue:#209:'+GEN10_HISTORICAL_INTEGRATION_ISSUE}
    return required_refs.issubset(refs) and _matches(con.get('report_admission_context') or {},{"context":"supernova/report-admission","status":"PASS","verification_head_sha":GEN10_VERIFIER_HEAD}) and _gen10_terminal_evidence_valid(old)

def _gen11_terminal_evidence_valid(old):
    try:
        vb,v=_remote_json(GEN11_VERIFICATION_PATH,GEN11_VERIFIER_HEAD)
        if not isinstance(vb,str) or not HEX40.fullmatch(vb):return False
        if not _one_path_child(GEN11_VERIFIER_HEAD,GEN11_G,GEN11_VERIFICATION_PATH,vb):return False
        if not _schema_valid('schemas/branch_verification.schema.json',v):return False
        sem=_trusted_v25_module()
        if sem.verification_semantic_errors(v,old):return False
        if v.get('verdict')!='INVALID' or v.get('calibration_pass') is not False or v.get('partition_exhaustive_verified') is not True:return False
        if len(v.get('safe_report_refs') or [])!=12 or v.get('quarantined_report_refs')!=[] or v.get('missing_workers')!=[] or v.get('liveness_complete') is not False:return False
        issues=set()
        for row in v.get('issue_ledger') or []:
            if not isinstance(row,dict):continue
            if isinstance(row.get('issue_id'),str):issues.add(row['issue_id'])
            if isinstance(row.get('issue_ids'),list):issues.update(x for x in row['issue_ids'] if isinstance(x,str))
        if not GEN11_REQUIRED_ISSUES.issubset(issues):return False
        if _remote_branch_head('ps/verify/'+GEN11_COHORT)!=GEN11_VERIFIER_HEAD:return False
        if not _source_bound_status(GEN11_VERIFIER_HEAD,'supernova/branch-verify','success') or not _source_bound_status(GEN11_VERIFIER_HEAD,'supernova/report-admission','success'):return False
        ib,i=_remote_json(GEN11_INTEGRATION_PATH,GEN11_INTEGRATOR_HEAD)
        if ib!=GEN11_INTEGRATION_BLOB:return False
        if not _one_path_child(GEN11_INTEGRATOR_HEAD,GEN11_G,GEN11_INTEGRATION_PATH,GEN11_INTEGRATION_BLOB):return False
        if _schema_valid('schemas/branch_integration.schema.json',i):return False
        if i.get('task_network_plan_id')!=GEN11_MALFORMED_PLAN or (i.get('session_header') or {}).get('plan_id')!=GEN11_MALFORMED_PLAN:return False
        if GEN11_MALFORMED_PLAN==PLAN:return False
        if i.get('cohort_id')!=GEN11_COHORT or i.get('generation_head_sha')!=GEN11_G or i.get('runtime_state_id')!=RUNTIME or i.get('calibration_pass') is not False:return False
        if _remote_branch_head('ps/integrate/'+GEN11_COHORT)!=GEN11_INTEGRATOR_HEAD:return False
        if not _source_bound_status(GEN11_INTEGRATOR_HEAD,'supernova/branch-integrate','failure'):return False
        return True
    except Exception:return False

def exact_gen11_zero_credit_terminal_parent(root,base,old,changed):
    rc,b=_state_blob(root,base)
    old_expected={"protocol_version":"2.5","task_network_plan_id":PLAN,"generation_seq":11,"active_cohort_id":GEN11_COHORT,"generation_head_sha":GEN11_G,"calibration_countable_current":True,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND","network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT}
    if rc or b.strip()!=GEN11_STATE_BLOB or not _matches(old,old_expected) or GEN11_COHORT in set(old.get('superseded_cohorts') or []):return False
    if not _gen11_terminal_evidence_valid(old):return False
    try:new=_load_json(root,'state/CURRENT.json');receipt=_load_json(root,GEN11_SUPERSESSION_PATH);contract=_load_json(root,'config/countable_control_set_v25.json')
    except Exception:return False
    cohort=new.get('active_cohort_id')
    if not isinstance(cohort,str) or not cohort.startswith(GEN12_COHORT_PREFIX):return False
    cp=f'control/{cohort}.json';ap=f'assignments/{cohort}.json';lp=f'liveness/{cohort}.json'
    if set(changed)!={'state/CURRENT.json',GEN11_SUPERSESSION_PATH,cp,ap,lp}:return False
    if new.get('active_control_manifest_path')!=cp or new.get('active_assignment_path')!=ap:return False
    if set(new.get('superseded_cohorts') or [])!=set(old.get('superseded_cohorts') or [])|{GEN11_COHORT}:return False
    expected={"protocol_version":"2.5","task_network_plan_id":PLAN,"transport_mode":"BRANCH_GITOPS","generation_seq":12,"active_parent_state_git_identity":GEN11_STATE_BLOB,"generation_branch":f"ps/gen/{cohort}","calibration_countable_current":True,"calibration_required_clean_cohorts":2,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND","network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":old.get('foundry_sha256'),"mastermind_sha256":old.get('mastermind_sha256'),"runtime_state_id":old.get('runtime_state_id'),"base_runtime_state_id":old.get('base_runtime_state_id'),"actual_runtime_plan_id":old.get('actual_runtime_plan_id'),"accepted_network_checkpoint_id":old.get('accepted_network_checkpoint_id'),"benchmark_registry_path":old.get('benchmark_registry_path'),"benchmark_registry_git_identity":old.get('benchmark_registry_git_identity'),"runtime_update_receipt_path":old.get('runtime_update_receipt_path'),"expected_base_head":base,"current_runtime_blocker":"O-T0-TWO_CLEAN_COUNTABLE_V25_COHORTS","goal1_status":"BLOCKED_T0","goal2_status":"BLOCKED_BY_GOAL1","verifier_branch":f"ps/verify/{cohort}","integrator_branch":f"ps/integrate/{cohort}","consolidation_branch":f"ps/consolidate/{cohort}"}
    if not _matches(new,expected):return False
    G=new.get('generation_head_sha');branches=new.get('worker_branches') or {}
    if not isinstance(G,str) or not HEX40.fullmatch(G) or set(branches)!=WORKERS or any(branches[w]!=f'ps/work/{cohort}/{w}' for w in WORKERS):return False
    try:control=_load_json(root,cp);assignment=_load_json(root,ap);live=_load_json(root,lp)
    except Exception:return False
    rc_cb,control_blob=run(['git','rev-parse','HEAD:'+cp],root);rc_ab,assignment_blob=run(['git','rev-parse','HEAD:'+ap],root);control_blob=control_blob.strip();assignment_blob=assignment_blob.strip()
    if rc_cb or rc_ab or new.get('active_control_manifest_git_identity')!=control_blob or new.get('active_assignment_git_identity')!=assignment_blob:return False
    common={"task_network_plan_id":PLAN,"cohort_id":cohort,"generation_seq":12,"parent_state_git_identity":GEN11_STATE_BLOB,"expected_base_head":base,"calibration_countable":True}
    if not _matches(control,common) or not _matches(assignment,common) or control.get('protocol_version')!='2.5' or control.get('control_release_commit_sha')!=base:return False
    if set(control.get('required_control_paths') or [])!=set(contract.get('required_control_paths') or []):return False
    if assignment.get('generation_branch')!=new.get('generation_branch') or assignment.get('generation_root_sha')!=base or assignment.get('control_manifest_git_identity')!=control_blob:return False
    if not _matches(live,{"cohort_id":cohort,"generation_seq":12,"generation_root_sha":base,"control_manifest_id":control.get('control_manifest_id'),"control_manifest_git_identity":control_blob,"assignment_id":assignment.get('assignment_id'),"assignment_git_identity":assignment_blob}):return False
    lanes=live.get('lanes') or []
    if len(lanes)!=12:return False
    for lane in lanes:
        try:
            minutes=(_parse_utc(lane['deadline_utc'])-_parse_utc(lane['expected_window_start_utc'])).total_seconds()/60.0
            if minutes<MINIMUM_WORKER_LIVENESS_WINDOW_MINUTES:return False
        except Exception:return False
    if _remote_compare_paths(base,G)!={cp,ap,lp} or _remote_branch_head(new.get('generation_branch'))!=G:return False
    role_branches=list(branches.values())+[new.get('verifier_branch'),new.get('integrator_branch'),new.get('consolidation_branch')]
    if any(_remote_branch_head(x)!=G for x in role_branches):return False
    workers=assignment.get('workers') or {}
    if set(workers)!=WORKERS:return False
    for wid in WORKERS:
        w=workers[wid];joined='\n'.join(str(x) for x in (w.get('constraints') or []))
        if w.get('fresh_allowed') is not False or w.get('private_manifest_id') is not None or w.get('benchmark_suite_id') is not None:return False
        if 'HMAC input contract is separate from committed-file byte contract' not in joined or 'abort without write on mismatch' not in joined:return False
    return receipt==_receipt(GEN11_COHORT,GEN11_G,GEN11_STATE_BLOB,GEN11_SUPERSESSION_DISPOSITION,12,True)

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

def _root11_gen12_terminal(old):
    """Rebind frozen Gen12 terminal evidence to the trusted root11 status writers."""
    if not _gen12_terminal_chain_valid(old):return None
    try:
        G=old.get('generation_head_sha');cohort=old.get('active_cohort_id')
        vh=_remote_branch_head('ps/verify/'+cohort)
        vb,verification=_remote_json('verification/'+cohort+'.json',vh)
        ih=_remote_branch_head('ps/integrate/'+cohort)
        ib,integration=_remote_json('integration/'+cohort+'.json',ih)
        trusted_events={'schedule','push','repository_dispatch'}
        if not _trusted_workflow_status(G,'supernova/active-static-control',REST_RECONCILER_WORKFLOW,trusted_events):return None
        if not _trusted_workflow_status(vh,'supernova/branch-verify',BRANCH_RECONCILER_WORKFLOW,trusted_events):return None
        if not _trusted_workflow_status(vh,'supernova/branch-report-admission',REST_RECONCILER_WORKFLOW,trusted_events):return None
        if not _trusted_workflow_status(ih,'supernova/branch-integrate',BRANCH_RECONCILER_WORKFLOW,trusted_events):return None
        return {'verification_head':vh,'verification_blob':vb,'verification':verification,'integration_head':ih,'integration_blob':ib,'integration':integration}
    except Exception:return None

def exact_gen12_zero_credit_scheduler_repair_parent(root,base,old,changed):
    """Promote only a separately staged and admitted root11 successor."""
    rc,b=_state_blob(root,base)
    if rc or b.strip()!=GEN12_STATE_BLOB or not _gen12_terminal_chain_valid(old):return False
    try:new=_load_json(root,'state/CURRENT.json');pointer=_load_json(root,'state/STAGED.json')
    except Exception:return False
    cohort=new.get('active_cohort_id')
    if not isinstance(cohort,str) or cohort==GEN12_COHORT or pointer.get('candidate_cohort_id')!=cohort:return False
    cp=f'control/{cohort}.json';ap=f'assignments/{cohort}.json';lp=f'liveness/{cohort}.json';sp=f'scheduler/{cohort}.json';sap=f'scheduler_admission/{cohort}.json';sup=f'superseded/{GEN12_COHORT}.json';hist=f'history/{GEN12_COHORT}/CONSOLIDATION.json'
    if set(changed)!={'state/CURRENT.json',cp,ap,lp,sp,sup,hist}:return False
    try:
        control=_load_json(root,cp);assignment=_load_json(root,ap);live=_load_json(root,lp);admission=_load_json(root,sap);manifest=_load_json(root,sp);receipt=_load_json(root,sup)
    except Exception:return False
    R=pointer.get('generation_root_sha');G=pointer.get('generation_head_sha');nonce=pointer.get('candidate_nonce')
    if not _schema_valid('schemas/staged_candidate.schema.json',pointer) or pointer.get('stage_base_head')!=R or pointer.get('active_state_git_identity')!=GEN12_STATE_BLOB or pointer.get('active_cohort_id')!=GEN12_COHORT or pointer.get('active_generation_seq')!=12:return False
    if pointer.get('candidate_generation_seq')!=13 or pointer.get('generation_branch')!=f'ps/gen/{cohort}' or pointer.get('scheduler_admission_path')!=sap or G==R:return False
    if control.get('scheduler_admission_required') is not True or control.get('scheduler_manifest_path')!=sp or 'scheduler_manifest_git_identity' in control:return False
    if candidate_fresh_gate_errors(control,assignment) or validate_scheduler_manifest(root,control,assignment,live,manifest):return False
    if any(obj.get('candidate_nonce')!=nonce for obj in (control,assignment,live,manifest)):return False
    if any(obj.get('generation_root_sha')!=R for obj in (control,assignment,live,manifest)):return False
    if 'generation_head_sha' in manifest:return False
    rc_pb,pb=run(['git','rev-parse',base+':state/STAGED.json'],root);rc_ph,ph=run(['git','rev-parse','HEAD:state/STAGED.json'],root)
    rc_ab,ab=run(['git','rev-parse',base+':'+sap],root);rc_ah,ah=run(['git','rev-parse','HEAD:'+sap],root)
    if rc_pb or rc_ph or pb.strip()!=ph.strip() or rc_ab or rc_ah or ab.strip()!=ah.strip():return False
    if admission.get('staged_candidate_git_identity')!=pb.strip() or not _schema_valid('schemas/scheduler_admission_copy.schema.json',admission):return False
    artifacts=((cp,'control_git_identity'),(ap,'assignment_git_identity'),(lp,'liveness_git_identity'),(sp,'scheduler_manifest_git_identity'))
    for path,key in artifacts:
        rc_blob,observed=run(['git','rev-parse','HEAD:'+path],root)
        if rc_blob or observed.strip()!=pointer.get(key):return False
    if _remote_branch_head(pointer.get('generation_branch'))!=G or _remote_compare_paths(R,G)!=set(path for path,_ in artifacts):return False
    generation_commit=api('/commits/'+G) or {};generation_parents=generation_commit.get('parents') or [];generation_files=generation_commit.get('files') or []
    if len(generation_parents)!=1 or generation_parents[0].get('sha')!=R or len(generation_files)!=4:return False
    expected_generation_blobs={path:pointer.get(key) for path,key in artifacts}
    if {row.get('filename'):row.get('sha') for row in generation_files}!=expected_generation_blobs:return False
    if control.get('expected_base_head')!=R or assignment.get('expected_base_head')!=R:return False
    if new.get('expected_base_head')!=base or base==R or new.get('generation_head_sha')!=G or new.get('generation_branch')!=pointer.get('generation_branch'):return False
    if new.get('generation_seq')!=pointer.get('candidate_generation_seq') or new.get('calibration_countable_current') is not True:return False
    if new.get('active_parent_state_git_identity')!=GEN12_STATE_BLOB or new.get('active_control_manifest_path')!=cp or new.get('active_assignment_path')!=ap:return False
    if new.get('active_control_manifest_git_identity')!=pointer.get('control_git_identity') or new.get('active_assignment_git_identity')!=pointer.get('assignment_git_identity'):return False
    if new.get('calibration_streak')!=0 or new.get('fresh_allowed_globally') is not False or new.get('calibration_required_clean_cohorts')!=2:return False
    if set(new.get('superseded_cohorts') or [])!=set(old.get('superseded_cohorts') or [])|{GEN12_COHORT}:return False
    branches=new.get('worker_branches') or {}
    if set(branches)!=WORKERS or any(branches[role]!=f'ps/work/{cohort}/{role}' for role in WORKERS):return False
    if new.get('verifier_branch')!=f'ps/verify/{cohort}' or new.get('integrator_branch')!=f'ps/integrate/{cohort}' or new.get('consolidation_branch')!=f'ps/consolidate/{cohort}':return False
    for key in ('protocol_version','task_network_plan_id','transport_mode','base_runtime_state_id','runtime_state_id','foundry_sha256','mastermind_sha256','actual_runtime_plan_id','accepted_network_checkpoint_id','canonical_bus_repo','private_vault_repo','benchmark_registry_path','benchmark_registry_git_identity','repo_policy_status','network_mode','runtime_update_receipt_path','worker_auth_scheme'):
        if new.get(key)!=old.get(key):return False
    if receipt!=_receipt(GEN12_COHORT,GEN12_G,GEN12_STATE_BLOB,GEN12_SUPERSESSION_DISPOSITION,pointer.get('candidate_generation_seq'),True):return False
    try:
        source_branch=admission['source_preactivation_admission_branch'];source_commit=admission['source_preactivation_admission_commit_sha'];source_path=admission['source_preactivation_admission_path'];source_blob,source=_remote_json(source_path,source_commit)
        if _remote_branch_head(source_branch)!=source_commit or source_blob!=admission.get('source_preactivation_admission_blob_sha'):return False
        if not _one_path_child(source_commit,G,source_path,source_blob) or not _schema_valid('schemas/scheduler_admission.schema.json',source):return False
        if not _source_bound_preactivation_status(source_commit,'MM06',cohort,G,manifest.get('admission_cutoff_utc')):return False
        for key in ('protocol_version','task_network_plan_id','candidate_nonce','cohort_id','generation_root_sha','generation_head_sha','staged_candidate_git_identity','scheduler_manifest_git_identity','admission_verdict'):
            if admission.get(key)!=source.get(key):return False
        if admission.get('source_schema_version')!=source.get('schema_version'):return False
        rc_manifest_blob,manifest_blob=run(['git','rev-parse','HEAD:'+sp],root)
        if rc_manifest_blob or validate_scheduler_admission(root,manifest,admission,staged=pointer,source=source,observed_manifest_blob=manifest_blob.strip(),require_inactive_production_fence=True,expected_generation_head=pointer.get("generation_head_sha")):return False
        if _remote_worker_preactivation_errors(source,manifest,pointer):return False
    except Exception:return False
    return True

def _root11_clean_terminal(old):
    """Return immutable clean terminal heads/receipts for an already-active root11 cohort."""
    if old.get('generation_seq',0)<13 or old.get('calibration_countable_current') is not True:return None
    cohort=old.get('active_cohort_id');G=old.get('generation_head_sha')
    try:
        pointer_path=old.get('active_staged_candidate_path')
        if pointer_path!=f'staging/{cohort}.json':return None
        pointer_blob,pointer=_remote_json(pointer_path,'main')
        if pointer_blob!=old.get('active_staged_candidate_git_identity') or pointer.get('candidate_cohort_id')!=cohort or pointer.get('generation_head_sha')!=G:return None
        trusted_events={'schedule','push','repository_dispatch'}
        if not _trusted_workflow_status(G,'supernova/active-static-control',REST_RECONCILER_WORKFLOW,trusted_events):return None
        vh=_remote_branch_head(old.get('verifier_branch'))
        vb,verification=_remote_json(f'verification/{cohort}.json',vh)
        if not _one_path_child(vh,G,f'verification/{cohort}.json',vb):return None
        if not _schema_valid('schemas/branch_verification.schema.json',verification):return None
        sem=_trusted_v25_module()
        if sem.generation_check(old):return None
        if sem.verification_semantic_errors(verification,old):return None
        if verification.get('verdict')!='VERIFIED_COMPLETE' or verification.get('calibration_pass') is not True or verification.get('liveness_complete') is not True:return None
        if len(verification.get('safe_report_refs') or [])!=12 or verification.get('quarantined_report_refs') or verification.get('missing_workers'):return None
        if _remote_production_worker_errors(verification,old):return None
        if _remote_production_liveness_errors(verification,old):return None
        if not _trusted_workflow_status(vh,'supernova/branch-verify',BRANCH_RECONCILER_WORKFLOW,{'schedule','push','repository_dispatch'}):return None
        if not _trusted_workflow_status(vh,'supernova/branch-report-admission',REST_RECONCILER_WORKFLOW,{'schedule','push','repository_dispatch'}):return None
        ih=_remote_branch_head(old.get('integrator_branch'))
        ib,integration=_remote_json(f'integration/{cohort}.json',ih)
        if not _one_path_child(ih,G,f'integration/{cohort}.json',ib):return None
        if not _schema_valid('schemas/branch_integration.schema.json',integration):return None
        if sem.integration_semantic_errors(integration,verification,old):return None
        if integration.get('verification_head_sha')!=vh or integration.get('calibration_pass') is not True:return None
        if not _trusted_workflow_status(ih,'supernova/branch-integrate',BRANCH_RECONCILER_WORKFLOW,{'schedule','push','repository_dispatch'}):return None
        return {'verification_head':vh,'verification_blob':vb,'verification':verification,'integration_head':ih,'integration_blob':ib,'integration':integration}
    except Exception:return None

def _clean_supersession_receipt(cohort,generation_head,state_blob,replacement_seq):
    return {
        'schema_version':'PS-COHORT-SUPERSESSION-1','cohort_id':cohort,
        'generation_head_sha':generation_head,'state_blob_sha':state_blob,
        'disposition':'CLEAN_COUNTABLE_COHORT_COMPLETE_ROOT11_SUCCESSOR',
        'calibration_credit':1,'fresh_evidence_consumed':False,
        'replacement_generation_seq':replacement_seq,'replacement_countable':True,
    }

def _root11_next_streak(previous_streak, credit):
    """Pure, capped clean-cohort credit transition used by root11 promotion."""
    return min(2, int(previous_streak) + int(credit))

def _root11_consolidation_evidence_matches(consolidation,old,base,terminal):
    """Require the exact immutable terminal evidence set used by root11 promotion."""
    cohort=old.get('active_cohort_id');G=old.get('generation_head_sha')
    vh=terminal.get('verification_head');vb=terminal.get('verification_blob')
    ih=terminal.get('integration_head');ib=terminal.get('integration_blob')
    if not all(isinstance(value,str) and HEX40.fullmatch(value) for value in (G,base,vh,vb,ih,ib)):return False
    expected={
        'schema_version':ROOT11_CONSOLIDATION_SCHEMA,
        'task_network_plan_id':PLAN,
        'cohort_id':cohort,
        'generation_head_sha':G,
        'verification_branch':f'ps/verify/{cohort}',
        'verification_head_sha':vh,
        'integration_branch':f'ps/integrate/{cohort}',
        'integration_head_sha':ih,
        'expected_main_head':base,
        'next_state_path':'state/CURRENT.json',
        'repo_policy_observed_protected':True,
        'repo_policy_source_bound_contexts_verified':True,
        'static_control_context':{
            'context':'supernova/active-static-control',
            'status':'PASS',
            'generation_head_sha':G,
        },
        'report_admission_context':{
            'context':'supernova/branch-report-admission',
            'status':'PASS',
            'verification_head_sha':vh,
        },
        'transition_admission_context':{
            'context':'supernova/branch-transition-admission',
            'required_on_exact_consolidation_head':True,
            'expected_main_head':base,
        },
    }
    expected_refs=[
        f'generation-head:{G}',
        f'verification/{cohort}.json@{vh}#{vb}',
        f'integration/{cohort}.json@{ih}#{ib}',
        f'github-status:{G}:supernova/active-static-control=success',
        f'github-status:{vh}:supernova/branch-verify=success',
        f'github-status:{vh}:supernova/branch-report-admission=success',
        f'github-status:{ih}:supernova/branch-integrate=success',
    ]
    return _matches(consolidation,expected) and consolidation.get('safe_history_refs')==expected_refs

def exact_root11_successor_promotion(root,base,old,changed):
    """Generic root11 stage -> admit -> later promote transition, including Gen13 -> Gen14."""
    rc,old_blob_text=_state_blob(root,base)
    if rc:return False
    old_blob=old_blob_text.strip()
    exceptional=old.get('generation_seq')==12
    if exceptional:
        if old_blob!=GEN12_STATE_BLOB:return False
        terminal=_root11_gen12_terminal(old)
        if terminal is None:return False
        credit=0;fresh_consumed=False;disposition=GEN12_SUPERSESSION_DISPOSITION
    else:
        terminal=_root11_clean_terminal(old)
        if terminal is None:return False
        credit=1;fresh_consumed=False;disposition='CLEAN_COUNTABLE_COHORT_COMPLETE_ROOT11_SUCCESSOR'
    try:
        new=_load_json(root,'state/CURRENT.json');pointer=_load_json(root,'state/STAGED.json')
    except Exception:return False
    old_cohort=old.get('active_cohort_id');cohort=pointer.get('candidate_cohort_id')
    if not isinstance(cohort,str) or not cohort or cohort==old_cohort or cohort in set(old.get('superseded_cohorts') or []):return False
    if new.get('active_cohort_id')!=cohort:return False
    cp=f'control/{cohort}.json';ap=f'assignments/{cohort}.json';lp=f'liveness/{cohort}.json';sp=f'scheduler/{cohort}.json';sap=f'scheduler_admission/{cohort}.json';sup=f'superseded/{old_cohort}.json';hist=f'history/{old_cohort}/CONSOLIDATION.json';archive=f'staging/{cohort}.json'
    if set(changed)!={'state/CURRENT.json',cp,ap,lp,sp,sup,hist,archive}:return False
    try:
        control=_load_json(root,cp);assignment=_load_json(root,ap);live=_load_json(root,lp);manifest=_load_json(root,sp);admission=_load_json(root,sap);receipt=_load_json(root,sup);consolidation=_load_json(root,hist);archived=_load_json(root,archive)
    except Exception:return False
    R=pointer.get('generation_root_sha');G=pointer.get('generation_head_sha');nonce=pointer.get('candidate_nonce')
    if not _schema_valid('schemas/staged_candidate.schema.json',pointer) or archived!=pointer:return False
    if pointer.get('stage_base_head')!=R or pointer.get('active_state_git_identity')!=old_blob or pointer.get('active_cohort_id')!=old_cohort or pointer.get('active_generation_seq')!=old.get('generation_seq'):return False
    if pointer.get('candidate_generation_seq')!=old.get('generation_seq',0)+1 or pointer.get('generation_branch')!=f'ps/gen/{cohort}' or pointer.get('scheduler_admission_path')!=sap or G==R:return False
    if control.get('scheduler_admission_required') is not True or control.get('scheduler_manifest_path')!=sp or 'scheduler_manifest_git_identity' in control:return False
    if candidate_fresh_gate_errors(control,assignment) or validate_scheduler_manifest(root,control,assignment,live,manifest):return False
    production_snapshot=_remote_inactive_production_snapshot(manifest,G)
    if production_snapshot is None:return False
    if any(obj.get('candidate_nonce')!=nonce for obj in (control,assignment,live,manifest)) or any(obj.get('generation_root_sha')!=R for obj in (control,assignment,live,manifest)):return False
    if 'generation_head_sha' in manifest:return False
    rc_pb,pb=run(['git','rev-parse',base+':state/STAGED.json'],root);rc_ph,ph=run(['git','rev-parse','HEAD:state/STAGED.json'],root)
    rc_ab,ab=run(['git','rev-parse',base+':'+sap],root);rc_ah,ah=run(['git','rev-parse','HEAD:'+sap],root);rc_ar,ar=run(['git','rev-parse','HEAD:'+archive],root)
    if rc_pb or rc_ph or pb.strip()!=ph.strip() or rc_ar or ar.strip()!=pb.strip() or rc_ab or rc_ah or ab.strip()!=ah.strip():return False
    if admission.get('staged_candidate_git_identity')!=pb.strip() or not _schema_valid('schemas/scheduler_admission_copy.schema.json',admission):return False
    artifacts=((cp,'control_git_identity'),(ap,'assignment_git_identity'),(lp,'liveness_git_identity'),(sp,'scheduler_manifest_git_identity'))
    created_paths=tuple(path for path,_ in artifacts)+(sup,hist,archive)
    if not _root11_promotion_paths_are_create_once(root,base,R,created_paths):return False
    for path,key in artifacts:
        rc_blob,observed=run(['git','rev-parse','HEAD:'+path],root)
        if rc_blob or observed.strip()!=pointer.get(key):return False
    if _remote_branch_head(pointer.get('generation_branch'))!=G:return False
    generation_commit=api('/commits/'+G) or {};parents=generation_commit.get('parents') or [];files=generation_commit.get('files') or []
    if len(parents)!=1 or parents[0].get('sha')!=R or len(files)!=4:return False
    expected_generation_blobs={path:pointer.get(key) for path,key in artifacts}
    if {row.get('filename'):(row.get('sha'),row.get('status')) for row in files}!={path:(blob,'added') for path,blob in expected_generation_blobs.items()}:return False
    try:
        contract_candidate=_load_json(root,'config/countable_control_set_v25.json')
        _,contract_r=_remote_json('config/countable_control_set_v25.json',R)
        rc_contract,raw_contract=run(['git','show',base+':config/countable_control_set_v25.json'],root)
        if rc_contract:return False
        contract_base=strict_json.loads(raw_contract)
        if not _root11_countable_control_contract_matches(control,contract_r,contract_base,contract_candidate):return False
    except Exception:return False
    if control.get('expected_base_head')!=R or assignment.get('expected_base_head')!=R:return False
    if new.get('expected_base_head')!=base or base==R or new.get('generation_head_sha')!=G or new.get('generation_branch')!=pointer.get('generation_branch'):return False
    if new.get('generation_seq')!=pointer.get('candidate_generation_seq') or new.get('calibration_countable_current') is not True:return False
    if new.get('active_parent_state_git_identity')!=old_blob or new.get('active_control_manifest_path')!=cp or new.get('active_assignment_path')!=ap:return False
    if new.get('active_control_manifest_git_identity')!=pointer.get('control_git_identity') or new.get('active_assignment_git_identity')!=pointer.get('assignment_git_identity'):return False
    if new.get('active_staged_candidate_path')!=archive or new.get('active_staged_candidate_git_identity')!=pb.strip():return False
    expected_streak=_root11_next_streak(old.get('calibration_streak',0),credit)
    if new.get('calibration_streak')!=expected_streak or new.get('fresh_allowed_globally') is not (expected_streak==2) or new.get('calibration_required_clean_cohorts')!=2:return False
    if expected_streak<2:
        if new.get('current_runtime_blocker')!='O-T0-TWO_CLEAN_COUNTABLE_V25_COHORTS' or new.get('goal1_status')!='BLOCKED_T0' or new.get('goal2_status')!='BLOCKED_BY_GOAL1':return False
        if new.get('authority_note')!=f'ROOT11_COUNTABLE_COHORT_ACTIVE_STREAK_{expected_streak}_OF_2_FRESH_DISABLED':return False
    else:
        if new.get('current_runtime_blocker')!='NONE' or new.get('goal1_status')!='PASSED' or new.get('goal2_status')!='OPEN':return False
        if new.get('authority_note')!='T0_FIXED_TWO_CONSECUTIVE_CLEAN_COUNTABLE_PROTOCOL_2_5_COHORTS':return False
    if set(new.get('superseded_cohorts') or [])!=set(old.get('superseded_cohorts') or [])|{old_cohort} or cohort in set(new.get('superseded_cohorts') or []):return False
    branches=new.get('worker_branches') or {}
    if set(branches)!=WORKERS or any(branches[role]!=f'ps/work/{cohort}/{role}' for role in WORKERS):return False
    if new.get('verifier_branch')!=f'ps/verify/{cohort}' or new.get('integrator_branch')!=f'ps/integrate/{cohort}' or new.get('consolidation_branch')!=f'ps/consolidate/{cohort}':return False
    for key in ('protocol_version','task_network_plan_id','transport_mode','base_runtime_state_id','runtime_state_id','foundry_sha256','mastermind_sha256','actual_runtime_plan_id','accepted_network_checkpoint_id','canonical_bus_repo','private_vault_repo','benchmark_registry_path','benchmark_registry_git_identity','repo_policy_status','network_mode','runtime_update_receipt_path','worker_auth_scheme'):
        if new.get(key)!=old.get(key):return False
    expected_receipt=_receipt(old_cohort,old.get('generation_head_sha'),old_blob,disposition,pointer.get('candidate_generation_seq'),True) if exceptional else _clean_supersession_receipt(old_cohort,old.get('generation_head_sha'),old_blob,pointer.get('candidate_generation_seq'))
    if receipt!=expected_receipt:return False
    if not _schema_valid('schemas/branch_consolidation.schema.json',consolidation):return False
    if not _root11_consolidation_evidence_matches(consolidation,old,base,terminal):return False
    if exceptional:
        if consolidation.get('calibration_counted') is not False:return False
    else:
        if consolidation.get('calibration_counted') is not True:return False
    try:
        source_branch=admission['source_preactivation_admission_branch'];source_commit=admission['source_preactivation_admission_commit_sha'];source_path=admission['source_preactivation_admission_path'];source_blob,source=_remote_json(source_path,source_commit)
        if _remote_branch_head(source_branch)!=source_commit or source_blob!=admission.get('source_preactivation_admission_blob_sha'):return False
        if not _one_path_child(source_commit,G,source_path,source_blob) or not _schema_valid('schemas/scheduler_admission.schema.json',source):return False
        if not _source_bound_preactivation_status(source_commit,'MM06',cohort,G,manifest.get('admission_cutoff_utc')):return False
        for key in ('protocol_version','task_network_plan_id','candidate_nonce','cohort_id','generation_root_sha','generation_head_sha','staged_candidate_git_identity','scheduler_manifest_git_identity','admission_verdict'):
            if admission.get(key)!=source.get(key):return False
        if admission.get('source_schema_version')!=source.get('schema_version'):return False
        rc_manifest_blob,manifest_blob=run(['git','rev-parse','HEAD:'+sp],root)
        if rc_manifest_blob or validate_scheduler_admission(root,manifest,admission,staged=archived,source=source,observed_manifest_blob=manifest_blob.strip(),require_inactive_production_fence=True,expected_generation_head=archived.get("generation_head_sha")):return False
        if _remote_worker_preactivation_errors(source,manifest,archived):return False
        if _remote_inactive_production_snapshot(manifest,G)!=production_snapshot:return False
    except Exception:return False
    return True

def stage_pointer_admission(root,pr,base,head,changed):
    if 'state/STAGED.json' not in changed:return []
    if changed!=['state/STAGED.json']:return ['staging pointer PR must change only state/STAGED.json']
    h=pr.get('head') or {}
    try:
        errors,pointer=_trusted_branch_module().stage_pointer_errors(root,head,base,h.get('ref'),(h.get('repo') or {}).get('full_name'),(pr.get('user') or {}).get('login'))
        if errors:return errors
        if not _source_bound_generation_status(pointer['generation_head_sha'],pr):return ['staging pointer lacks exact-PR source-bound branch-generation Actions success']
        return []
    except Exception as exc:return ['staging pointer admission: '+repr(exc)]

def scheduler_admission_transaction(root,pr,base,head,changed):
    paths=[path for path in changed if path.startswith('scheduler_admission/') and path.endswith('.json')]
    if not paths:return []
    if len(changed)!=1 or len(paths)!=1:return ['scheduler admission must be a create-once one-path transaction']
    path=paths[0];cohort=path[len('scheduler_admission/'):-5]
    if (pr.get('head') or {}).get('ref')!=f'ps/admit/{cohort}':return ['scheduler admission PR branch mismatch']
    if run(['git','cat-file','-e',base+':'+path],root)[0]==0:return ['scheduler admission path already exists in base']
    if not _one_path_child(head,base,path):return ['scheduler admission PR must be exactly one added-path commit child of base']
    try:
        pointer=_load_json(root,'state/STAGED.json');copy=_load_json(root,path)
        if not _schema_valid('schemas/staged_candidate.schema.json',pointer):return ['staged pointer schema invalid before scheduler admission']
        if not _schema_valid('schemas/scheduler_admission_copy.schema.json',copy):return ['scheduler admission copy schema invalid']
        rc,pointer_blob=run(['git','rev-parse','HEAD:state/STAGED.json'],root)
        if rc:return ['cannot bind staged pointer blob']
        G=pointer.get('generation_head_sha');R=pointer.get('generation_root_sha');branch=pointer.get('generation_branch')
        if _remote_branch_head(branch)!=G:return ['generation branch moved before scheduler admission']
        manifest_blob,manifest=_remote_json(pointer.get('scheduler_manifest_path'),G)
        if manifest_blob!=pointer.get('scheduler_manifest_git_identity') or not _schema_valid('schemas/scheduler_manifest.schema.json',manifest):return ['scheduler manifest pointer/schema mismatch']
        production_snapshot=_remote_inactive_production_snapshot(manifest,G)
        if production_snapshot is None:return ['production refs are not exact generation head before scheduler admission']
        source_branch=copy.get('source_preactivation_admission_branch');source_commit=copy.get('source_preactivation_admission_commit_sha');source_path=copy.get('source_preactivation_admission_path');source_blob=copy.get('source_preactivation_admission_blob_sha')
        if source_branch!=f'ps/preactivate/{cohort}/MM06' or source_path!=f'preactivation/{cohort}/MM06.json':return ['MM06 admission source branch/path mismatch']
        if _remote_branch_head(source_branch)!=source_commit:return ['MM06 admission source branch moved']
        observed_blob,source=_remote_json(source_path,source_commit)
        if observed_blob!=source_blob or not _one_path_child(source_commit,G,source_path,source_blob):return ['MM06 admission source commit/blob is not exact one-path child of G']
        if not _schema_valid('schemas/scheduler_admission.schema.json',source):return ['MM06 admission source schema invalid']
        if not _source_bound_preactivation_status(source_commit,'MM06',cohort,pointer.get('generation_head_sha'),manifest.get('admission_cutoff_utc')):return ['MM06 admission source lacks exact-PR trusted success by admission cutoff']
        pointer_expected={'candidate_nonce':copy.get('candidate_nonce'),'candidate_cohort_id':copy.get('cohort_id'),'generation_root_sha':copy.get('generation_root_sha'),'generation_head_sha':copy.get('generation_head_sha'),'scheduler_manifest_git_identity':copy.get('scheduler_manifest_git_identity')}
        if not _matches(pointer,pointer_expected) or copy.get('staged_candidate_git_identity')!=pointer_blob.strip():return ['scheduler admission copy does not bind exact staged pointer']
        manifest_expected={'candidate_nonce':copy.get('candidate_nonce'),'cohort_id':copy.get('cohort_id'),'generation_root_sha':R}
        if not _matches(manifest,manifest_expected):return ['scheduler admission copy does not bind exact manifest semantics']
        for key in ('protocol_version','task_network_plan_id','candidate_nonce','cohort_id','generation_root_sha','generation_head_sha','staged_candidate_git_identity','scheduler_manifest_git_identity','admission_verdict'):
            if copy.get(key)!=source.get(key):return ['scheduler admission copy/MM06 semantic mismatch: '+key]
        if copy.get('source_schema_version')!=source.get('schema_version'):return ['scheduler admission source schema-version mismatch']
        guard_errors=validate_scheduler_admission(root,manifest,copy,staged=pointer,source=source,observed_manifest_blob=manifest_blob,require_inactive_production_fence=True,expected_generation_head=pointer.get("generation_head_sha"))
        if guard_errors:return ['scheduler admission trusted guard: '+guard_errors[0]]
        remote_worker_errors=_remote_worker_preactivation_errors(source,manifest,pointer)
        if remote_worker_errors:return ['scheduler admission worker source: '+remote_worker_errors[0]]
        if _remote_inactive_production_snapshot(manifest,G)!=production_snapshot:return ['production refs moved during scheduler admission validation']
        if copy.get('creation_mode')!='CREATE_ONCE' or G==R:return ['scheduler admission create-once/root-head invariant failed']
        return []
    except Exception as exc:return ['scheduler admission transaction: '+repr(exc)]

def report_admission(root,base,changed):
    if "state/CURRENT.json" not in changed:return []
    rc,text=run(["git","show",base+":state/CURRENT.json"],root)
    if rc:return ["cannot read base state: "+text[-800:]]
    try:
        old=strict_json.loads(text)
        if exact_noncountable_gen6_bootstrap_parent(root,base,old):return []
        for predicate in (exact_invalidated_gen7_repair_parent,exact_noncountable_substrate_staging_parent,exact_gen9_zero_credit_reset_parent,exact_gen10_zero_credit_terminal_parent,exact_gen11_zero_credit_terminal_parent,exact_root11_successor_promotion):
            if predicate(root,base,old,changed):return []
        if old.get('generation_seq',0)>=12 or old.get('active_staged_candidate_path'):
            return ['root11 transition does not match the exact staged/admitted successor promotion contract']
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
    n=pr["number"];trusted=trusted_main_sha(root);run(["git","fetch","--no-tags","origin",f"pull/{n}/head","+refs/heads/ps/*:refs/remotes/origin/ps/*"],root)
    if not is_ancestor(root,trusted,sha):fail_contexts(sha,"trusted admission refused: PR head does not descend from exact current main");return
    changed=changed_files(root,trusted,sha);authority=authority_path_changes(changed)
    if any(path=='state/STAGED.json' or path.startswith('scheduler_admission/') for path in changed) and base!=trusted:fail_contexts(sha,"trusted admission refused: stage/admit base is not exact current main");return
    historical=[path for path in changed if path.startswith('history/') or path.startswith('superseded/')]
    if historical and 'state/CURRENT.json' not in changed:fail_contexts(sha,"trusted admission refused: historical/supersession evidence is immutable outside an exact state transition");return
    if any(run(['git','cat-file','-e',trusted+':'+path],root)[0]==0 for path in historical):fail_contexts(sha,"trusted admission refused: historical/supersession evidence is create-once and may not be modified or deleted");return
    try:
        rc,old_state_text=run(['git','show',trusted+':state/CURRENT.json'],root)
        if rc:raise ValueError('base state unavailable')
        old_state=strict_json.loads(old_state_text);active_paths={old_state.get('active_control_manifest_path'),old_state.get('active_assignment_path')}
        archive_path=old_state.get('active_staged_candidate_path')
        if archive_path:
            rc,archive_text=run(['git','show',trusted+':'+archive_path],root)
            if rc:raise ValueError('active staged archive unavailable')
            archived=strict_json.loads(archive_text)
            active_paths.update({archived.get('control_path'),archived.get('assignment_path'),archived.get('liveness_path'),archived.get('scheduler_manifest_path')})
        active_paths.discard(None)
    except Exception as exc:fail_contexts(sha,"trusted admission refused: cannot bind active frozen cohort artifacts: "+str(exc));return
    if active_paths.intersection(changed) and 'state/CURRENT.json' not in changed:fail_contexts(sha,"trusted admission refused: active frozen C/A/L/S artifacts may change only inside an exact state transition");return
    archives=[path for path in changed if path.startswith('staging/') and path.endswith('.json')]
    if archives and 'state/CURRENT.json' not in changed:fail_contexts(sha,"trusted admission refused: archived staged evidence is immutable outside exact promotion");return
    if any(run(['git','cat-file','-e',trusted+':'+path],root)[0]==0 for path in archives):fail_contexts(sha,"trusted admission refused: archived staged evidence may only be added once");return
    if authority and not trusted_bootstrap_success(sha,base,n):fail_contexts(sha,"trusted admission refused: authority bytes changed without source-verified bootstrap: "+authority[0]);return
    modes=changed_file_mode_errors(root,sha,changed)
    if modes:fail_contexts(sha,"trusted admission refused: "+modes[0]);return
    tmp=pathlib.Path(tempfile.mkdtemp(prefix=f"supernova-pr-{n}-"))
    try:
        rc,_=run(["git","worktree","add","--detach",str(tmp),sha],root)
        if rc:fail_contexts(sha,"trusted admission could not create candidate data worktree");return
        transaction_errors=stage_pointer_admission(root,pr,trusted,sha,changed)+scheduler_admission_transaction(tmp,pr,trusted,sha,changed)
        ruleset_errors=trusted_ruleset_errors()
        results={"supernova/static-control":trusted_static_control(root,tmp)+transaction_errors+ruleset_errors,"supernova/report-admission":report_admission(tmp,trusted,changed)+transaction_errors+ruleset_errors,"supernova/transition-admission":transition_admission(root,tmp,trusted,sha,changed)+transaction_errors+ruleset_errors}
        final_transaction_errors=stage_pointer_admission(root,pr,trusted,sha,changed)+scheduler_admission_transaction(tmp,pr,trusted,sha,changed)
        if final_transaction_errors:
            results={context:errors+final_transaction_errors for context,errors in results.items()}
        current=api('/pulls/'+str(n)) or {};current_head=(current.get('head') or {}).get('sha');current_base=(current.get('base') or {}).get('sha')
        if current_head!=sha or current_base!=trusted:
            race=['trusted admission refused: PR head/base moved during validation']
            results={context:errors+race for context,errors in results.items()}
        for context,errors in results.items():
            if errors:post_status(sha,context,"failure","FAIL "+errors[0])
            else:
                provenance="trusted-bootstrap-run" if authority else "trusted-main";scope="PASS" if "state/CURRENT.json" in changed else "PASS/N-A non-transition";post_status(sha,context,"success",provenance+" exact-head "+scope)
    finally:
        run(["git","worktree","remove","--force",str(tmp)],root);shutil.rmtree(tmp,ignore_errors=True)
def open_main_prs():
    """Return a bounded exhaustive, de-duplicated inventory of every open main PR."""
    observed=[];seen=set();errors=[]
    for page in range(1,101):
        try:rows=api(f'/pulls?state=open&base=main&per_page=100&page={page}') or []
        except Exception as exc:return observed,['open main PR inventory failed before completion: '+repr(exc)]
        if not isinstance(rows,list):return observed,['open main PR inventory is not a list']
        for pr in rows:
            key=pr.get('number') if isinstance(pr,dict) else None
            if key not in seen:seen.add(key);observed.append(pr)
        if len(rows)<100:return observed,errors
    return observed,['open main PR inventory exceeds bounded exhaustive scan']

def main():
    root=pathlib.Path.cwd().resolve();prs,inventory_errors=open_main_prs();trusted_errors=trusted_self_check(root)+inventory_errors
    for pr in prs:
        if pr.get("draft"):continue
        try:validate_pr(root,pr,trusted_errors=trusted_errors)
        except Exception as exc:
            sha=(pr.get("head") or {}).get("sha")
            if sha and HEX40.fullmatch(sha):fail_contexts(sha,"trusted admission exception: "+repr(exc))
    return 1 if trusted_errors else 0
if __name__=="__main__":raise SystemExit(main())
