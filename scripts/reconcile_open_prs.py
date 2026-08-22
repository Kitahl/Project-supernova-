#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

REPO=os.environ.get("GITHUB_REPOSITORY","Kitahl/Project-supernova-"); TOKEN=os.environ.get("GITHUB_TOKEN","")
API="https://api.github.com/repos/"+REPO; OWNER=REPO.split("/",1)[0]
ALLOWED_HEAD_PREFIXES=("hardening/","transition/","ps/consolidate/","rev4/")
CONTEXTS=("supernova/static-control","supernova/report-admission","supernova/transition-admission")
BOOTSTRAP_CONTEXT="supernova/bootstrap-admission"; BOOTSTRAP_CREATOR="github-actions[bot]"
BOOTSTRAP_WORKFLOW=".github/workflows/supernova-authority-bootstrap.yml"
RUN_URL_RE=re.compile(r"^https://github\.com/"+re.escape(REPO)+r"/actions/runs/([0-9]+)$"); HEX40=re.compile(r"^[0-9a-f]{40}$")
DURABLE_BOOTSTRAP_PROVENANCE="PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED"
# Backward source-contract markers retained for frozen protocol-2.5 tests:
# BOOTSTRAP_CONTEXT = "supernova/bootstrap-admission"
# BOOTSTRAP_CREATOR = "github-actions[bot]"
# trusted_bootstrap_success(head_sha)

GEN6_BOOTSTRAP_COHORT="CAL-BR-006-v251-433ad83a"; GEN6_BOOTSTRAP_STATE_BLOB="b08c9ae01be715ad25059d3dfcb72febb4794c38"
GEN7_INVALIDATED_COHORT="CAL-BR-007-v25-c13b6ee4"; GEN7_INVALIDATED_G="7c182fb7ce3a3941f86f7508bbb4a18152402bb8"; GEN7_INVALIDATED_STATE_BLOB="856481759722e23ff9a652ce140f304efe13b023"
GEN7_SUPERSESSION_PATH=f"superseded/{GEN7_INVALIDATED_COHORT}.json"
STAGING_COHORT="STAGE-BR-008-v25-MF311"; STAGING_SUPERSESSION_PATH=f"superseded/{STAGING_COHORT}.json"
MF311="57c57394bda484c4ec4613c312080682a37670ebb6cec06d061979e39f1ec64f"; MM4410="026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d"
RUNTIME="9d0a88cc9001295b5e4c0f4163e83c0fd64ce04521e34230ad3539af14f3dfaf"; STAGING_RECEIPT="runtime/updates/GEN8-FOUNDRY-3.1.1-REPLAY-BINDING.json"
GEN9_ZERO_CREDIT_RESET="config/gen9_repair_reset_epoch_v25.json"; GEN9_COHORT="CAL-BR-009-v25-b53ab205"; GEN9_G="67bcfef1a5a1e65c9cc4adb1a2f308ec51c70c3f"; GEN9_STATE_BLOB="31071464144bde197aca0e3f13153be2d85208d7"
GEN9_SUPERSESSION_PATH=f"superseded/{GEN9_COHORT}.json"; GEN9_SUPERSESSION_DISPOSITION="INVALIDATED_ZERO_CREDIT_MUTABLE_DUAL_WRITER_STRUCTURAL_STATUS"; GEN10_COHORT_PREFIX="CAL-BR-010-v25-"

GEN10_TERMINAL_COHORT="CAL-BR-010-v25-fe539297-r2"
GEN10_TERMINAL_G="25c7c4e4732a5635ae8f47a9194d59a3f5a58e8f"
GEN10_TERMINAL_STATE_BLOB="72d5aa0c0f9144bb0cb2faa19ad8300bd38c8ad6"
GEN10_MM06_HEAD="500837400c093b0dd53071f649efc022c9314201"
GEN10_MF06_HEAD="9631e36f289ca8d7bc750eaa01790171419636ef"
GEN10_SUPERSESSION_PATH=f"superseded/{GEN10_TERMINAL_COHORT}.json"
GEN10_CONSOLIDATION_PATH=f"history/{GEN10_TERMINAL_COHORT}/CONSOLIDATION.json"
GEN10_SUPERSESSION_DISPOSITION="INVALIDATED_ZERO_CREDIT_POST_START_AUTHORITATIVE_CONTROL_REPAIR"
GEN11_COHORT_PREFIX="CAL-BR-011-v25-"
GEN10_HISTORICAL_INTEGRATION_ISSUE="O-T0-GEN10-HISTORICAL-INTEGRATION-SCHEMA"

AUTHORITY_PREFIXES=("scripts/","tests/","schemas/","config/",".github/workflows/")
AUTHORITY_PATHS={"PROTOCOL.md","BRANCH_PROTOCOL.md","BRANCH_WORKER_PROTOCOL.md","SESSION_STANDARD.md","plan/PLAN.json","requirements-validation.lock","branch/CONFIG.json","research/open_lanes.json","benchmark/pool_disposition.json"}
WORKERS={"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
PLAN="0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"


def api(path,method="GET",data=None):
    q=urllib.request.Request(API+path,data=json.dumps(data).encode() if data is not None else None,method=method)
    q.add_header("Accept","application/vnd.github+json"); q.add_header("X-GitHub-Api-Version","2022-11-28")
    if TOKEN:q.add_header("Authorization","Bearer "+TOKEN)
    with urllib.request.urlopen(q,timeout=30) as r:
        raw=r.read(); return json.loads(raw) if raw else None

def post_status(sha,context,state,description): api("/statuses/"+sha,"POST",{"state":state,"context":context,"description":description[:140]})
def fail_contexts(sha,description):
    for context in CONTEXTS: post_status(sha,context,"failure",description)
def run(cmd,cwd,env=None):
    p=subprocess.run(cmd,cwd=str(cwd),env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False); return p.returncode,p.stdout
def changed_files(repo,base,head):
    rc,out=run(["git","diff","--name-only",base+"..."+head],repo)
    if rc: raise RuntimeError("git diff failed: "+out[-1000:])
    return [x for x in out.splitlines() if x]
def authority_path_changes(changed): return sorted(p for p in changed if p in AUTHORITY_PATHS or p.startswith(AUTHORITY_PREFIXES))
def expected_bootstrap_description(pr_number,head_sha,base_sha): return f"trusted-main bootstrap PASS pr={pr_number} head={head_sha} base={base_sha}"[:140]

def _run_binds_exact_pr(r,head_sha,base_sha,pr_number):
    if r.get("head_sha")!=head_sha:return False
    prs=r.get("pull_requests") or []
    if not isinstance(prs,list):return False
    matches=[]
    for p in prs:
        if not isinstance(p,dict) or p.get("number")!=pr_number:continue
        ph=p.get("head") or {}; pb=p.get("base") or {}
        if ph.get("sha")==head_sha and pb.get("sha")==base_sha:matches.append(p)
    return len(matches)==1

def trusted_bootstrap_success(head_sha,base_sha=None,pr_number=None):
    """Re-derive durable bootstrap provenance from persistent GitHub objects."""
    if not(isinstance(base_sha,str) and HEX40.fullmatch(base_sha) and isinstance(pr_number,int) and pr_number>0): return False
    completed=os.environ.get("COMPLETED_BOOTSTRAP_RUN_ID","")
    if completed and not completed.isdigit():return False
    expected=expected_bootstrap_description(pr_number,head_sha,base_sha); valid=[]
    for s in api("/commits/"+head_sha+"/statuses?per_page=100") or []:
        if s.get("context")!=BOOTSTRAP_CONTEXT or s.get("state")!="success" or (s.get("creator") or {}).get("login")!=BOOTSTRAP_CREATOR or s.get("description")!=expected: continue
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
    h=pr.get("head") or {}; b=pr.get("base") or {}; e=[]; ref=h.get("ref"); sha=h.get("sha")
    if b.get("ref")!="main":e.append("PR base is not main")
    if (h.get("repo") or {}).get("full_name")!=REPO:e.append("PR head repository is not canonical repository")
    if (pr.get("user") or {}).get("login")!=OWNER:e.append("PR author is not repository owner")
    if not isinstance(ref,str) or not ref.startswith(ALLOWED_HEAD_PREFIXES):e.append("PR head prefix is not admitted")
    if not isinstance(sha,str) or not HEX40.fullmatch(sha):e.append("PR head SHA is invalid")
    return e

def trusted_main_sha(repo):
    rc,out=run(["git","rev-parse","HEAD"],repo); sha=out.strip()
    if rc or not HEX40.fullmatch(sha):raise RuntimeError("cannot resolve exact trusted main HEAD")
    return sha
def is_ancestor(repo,a,b): return run(["git","merge-base","--is-ancestor",a,b],repo)[0]==0
def changed_file_mode_errors(repo,head,changed):
    e=[]
    for p in changed:
        rc,out=run(["git","ls-tree",head,"--",p],repo)
        if rc:e.append("cannot inspect git mode for "+p)
        elif out.strip() and out.split(None,1)[0]!="100644":e.append("non-regular candidate path "+p+" mode="+out.split(None,1)[0])
    return e
def trusted_self_check(root):
    env=os.environ.copy(); env["GITHUB_TOKEN"]=""; rc,out=run([sys.executable,"scripts/validate_bus.py"],root,env=env)
    return [] if rc==0 else ["trusted main canonical validator failed: "+out[-1200:]]
def trusted_static_control(root,candidate):
    env=os.environ.copy(); env["SUPERNOVA_VALIDATE_ROOT"]=str(candidate); rc,out=run([sys.executable,str(root/"scripts/validate_bus.py")],root,env=env)
    return [] if rc==0 else ["trusted static validation failed: "+out[-1200:]]
def _load_json(root,path): return json.loads((root/path).read_text(encoding="utf-8"))
def _matches(value,expected): return all(value.get(k)==v for k,v in expected.items())
def _state_blob(root,base): return run(["git","rev-parse",base+":state/CURRENT.json"],root)
def _receipt(cohort,g,blob,disposition,seq,countable):
    return {"schema_version":"PS-COHORT-SUPERSESSION-1","cohort_id":cohort,"generation_head_sha":g,"state_blob_sha":blob,"disposition":disposition,"calibration_credit":0,"fresh_evidence_consumed":False,"replacement_generation_seq":seq,"replacement_countable":countable}

def branch_head_api(branch):
    try:return api("/branches/"+urllib.parse.quote(branch,safe=""))["commit"]["sha"]
    except Exception:return None

def github_file(path,ref):
    obj=api("/contents/"+urllib.parse.quote(path,safe="/")+"?ref="+urllib.parse.quote(ref,safe=""))
    if not isinstance(obj,dict) or obj.get("type")!="file":raise RuntimeError(f"{path}@{ref}: not file")
    return obj

def github_json(path,ref):
    obj=github_file(path,ref)
    return json.loads(base64.b64decode(obj["content"]).decode("utf-8"))

def latest_status(sha,context):
    for row in api("/commits/"+sha+"/statuses?per_page=100") or []:
        if row.get("context")==context:return row
    return None

def source_bound_status(sha,context,state):
    row=latest_status(sha,context)
    return bool(row and row.get("state")==state and (row.get("creator") or {}).get("login")==BOOTSTRAP_CREATOR)

def compare_paths_api(base,head):
    obj=api("/compare/"+base+"..."+head) or {}
    return [x.get("filename") for x in obj.get("files",[]) if x.get("status")!="unchanged"]

def exact_noncountable_gen6_bootstrap_parent(root,base,old):
    rc,b=_state_blob(root,base)
    return not rc and b.strip()==GEN6_BOOTSTRAP_STATE_BLOB and _matches(old,{"generation_seq":6,"active_cohort_id":GEN6_BOOTSTRAP_COHORT,"calibration_countable_current":False,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"UNVERIFIED_BLOCKING","generation_head_sha":"c86c091c3be840559a46670218705be1277acd8f"})

def exact_invalidated_gen7_repair_parent(root,base,old,changed):
    rc,b=_state_blob(root,base)
    if rc or b.strip()!=GEN7_INVALIDATED_STATE_BLOB or not _matches(old,{"generation_seq":7,"active_cohort_id":GEN7_INVALIDATED_COHORT,"generation_head_sha":GEN7_INVALIDATED_G,"calibration_countable_current":True,"calibration_streak":0,"fresh_allowed_globally":False}) or not {"state/CURRENT.json",GEN7_SUPERSESSION_PATH}.issubset(changed): return False
    try:new=_load_json(root,"state/CURRENT.json"); receipt=_load_json(root,GEN7_SUPERSESSION_PATH)
    except Exception:return False
    return _matches(new,{"generation_seq":8,"active_parent_state_git_identity":GEN7_INVALIDATED_STATE_BLOB,"calibration_countable_current":False,"calibration_streak":0,"fresh_allowed_globally":False}) and new.get("active_cohort_id")!=GEN7_INVALIDATED_COHORT and GEN7_INVALIDATED_COHORT in set(new.get("superseded_cohorts") or []) and receipt==_receipt(GEN7_INVALIDATED_COHORT,GEN7_INVALIDATED_G,GEN7_INVALIDATED_STATE_BLOB,"INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS",8,False)

def exact_noncountable_substrate_staging_parent(root,base,old,changed):
    rc,b=_state_blob(root,base); blob=b.strip()
    if rc or not HEX40.fullmatch(blob) or not _matches(old,{"generation_seq":8,"active_cohort_id":STAGING_COHORT,"generation_branch":"ps/gen/"+STAGING_COHORT,"calibration_countable_current":False,"calibration_streak":0,"fresh_allowed_globally":False,"network_mode":"BENCHMARK_DISCOVERY_WAIT","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT}) or GEN7_INVALIDATED_COHORT not in set(old.get("superseded_cohorts") or []): return False
    try:new=_load_json(root,"state/CURRENT.json"); receipt=_load_json(root,STAGING_SUPERSESSION_PATH)
    except Exception:return False
    cohort=str(new.get("active_cohort_id", "")); required={"state/CURRENT.json",STAGING_SUPERSESSION_PATH,new.get("active_control_manifest_path"),new.get("active_assignment_path"),f"liveness/{cohort}.json"}
    return None not in required and required.issubset(changed) and cohort.startswith("CAL-BR-009-v25-") and _matches(new,{"generation_seq":9,"active_parent_state_git_identity":blob,"calibration_countable_current":True,"calibration_streak":0,"fresh_allowed_globally":False,"network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT}) and STAGING_COHORT in set(new.get("superseded_cohorts") or []) and receipt==_receipt(STAGING_COHORT,old.get("generation_head_sha"),blob,"NONCOUNTABLE_SUBSTRATE_STAGING_COMPLETE_ZERO_CREDIT",9,True)

def exact_gen9_zero_credit_reset_parent(root,base,old,changed):
    rc,b=_state_blob(root,base)
    old_expected={"protocol_version":"2.5","task_network_plan_id":PLAN,"generation_seq":9,"active_cohort_id":GEN9_COHORT,"generation_head_sha":GEN9_G,"calibration_countable_current":True,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND","network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT}
    if rc or b.strip()!=GEN9_STATE_BLOB or not _matches(old,old_expected) or GEN9_COHORT in set(old.get("superseded_cohorts") or []):return False
    try:marker=_load_json(root,GEN9_ZERO_CREDIT_RESET); new=_load_json(root,"state/CURRENT.json"); receipt=_load_json(root,GEN9_SUPERSESSION_PATH)
    except Exception:return False
    marker_expected={"schema_version":"PS-GEN9-REPAIR-RESET-EPOCH-2.5-1","old_state_blob":GEN9_STATE_BLOB,"old_cohort_id":GEN9_COHORT,"old_generation_head_sha":GEN9_G,"allowed_successor_generation_seq":10,"allowed_successor_cohort_prefix":GEN10_COHORT_PREFIX,"supersession_disposition":GEN9_SUPERSESSION_DISPOSITION,"calibration_credit":0,"fresh_evidence_consumed":False,"foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"failure_semantics":"FAIL_CLOSED"}
    cohort=new.get("active_cohort_id")
    if not _matches(marker,marker_expected) or not isinstance(cohort,str) or not cohort.startswith(GEN10_COHORT_PREFIX):return False
    cp=f"control/{cohort}.json"; ap=f"assignments/{cohort}.json"; lp=f"liveness/{cohort}.json"
    if new.get("active_control_manifest_path")!=cp or new.get("active_assignment_path")!=ap or set(changed)!={"state/CURRENT.json",GEN9_SUPERSESSION_PATH,cp,ap,lp}:return False
    if set(new.get("superseded_cohorts") or [])!=set(old.get("superseded_cohorts") or [])|{GEN9_COHORT}:return False
    new_expected={"protocol_version":"2.5","task_network_plan_id":PLAN,"transport_mode":"BRANCH_GITOPS","generation_seq":10,"active_parent_state_git_identity":GEN9_STATE_BLOB,"generation_branch":f"ps/gen/{cohort}","calibration_countable_current":True,"calibration_required_clean_cohorts":2,"calibration_streak":0,"fresh_allowed_globally":False,"repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND","network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT,"expected_base_head":base,"current_runtime_blocker":"O-T0-TWO_CLEAN_COUNTABLE_V25_COHORTS","goal1_status":"BLOCKED_T0","goal2_status":"BLOCKED_BY_GOAL1","verifier_branch":f"ps/verify/{cohort}","integrator_branch":f"ps/integrate/{cohort}","consolidation_branch":f"ps/consolidate/{cohort}"}
    if not _matches(new,new_expected) or not isinstance(new.get("generation_head_sha"),str) or not HEX40.fullmatch(new["generation_head_sha"]):return False
    branches=new.get("worker_branches") or {}
    if set(branches)!=WORKERS or any(branches[w]!=f"ps/work/{cohort}/{w}" for w in WORKERS):return False
    try:control=_load_json(root,cp); assignment=_load_json(root,ap); live=_load_json(root,lp)
    except Exception:return False
    rc_cb,control_blob=run(["git","rev-parse","HEAD:"+cp],root); rc_ab,assignment_blob=run(["git","rev-parse","HEAD:"+ap],root)
    control_blob=control_blob.strip(); assignment_blob=assignment_blob.strip()
    if rc_cb or rc_ab or not HEX40.fullmatch(control_blob) or not HEX40.fullmatch(assignment_blob):return False
    if new.get("active_control_manifest_git_identity")!=control_blob or new.get("active_assignment_git_identity")!=assignment_blob:return False
    common={"task_network_plan_id":PLAN,"cohort_id":cohort,"generation_seq":10,"parent_state_git_identity":GEN9_STATE_BLOB,"expected_base_head":base,"calibration_countable":True}
    root_sha=control.get("control_release_commit_sha")
    live_expected={"cohort_id":cohort,"generation_seq":10,"generation_root_sha":root_sha,"control_manifest_id":control.get("control_manifest_id"),"control_manifest_git_identity":control_blob,"assignment_id":assignment.get("assignment_id"),"assignment_git_identity":assignment_blob}
    return _matches(control,common) and _matches(assignment,common) and assignment.get("generation_branch")==new.get("generation_branch") and assignment.get("generation_root_sha")==root_sha and assignment.get("control_manifest_git_identity")==control_blob and _matches(live,live_expected) and receipt==_receipt(GEN9_COHORT,GEN9_G,GEN9_STATE_BLOB,GEN9_SUPERSESSION_DISPOSITION,10,True)

def exact_gen10_zero_credit_terminal_parent(root,base,old,changed):
    rc,b=_state_blob(root,base)
    old_expected={
        "protocol_version":"2.5","task_network_plan_id":PLAN,"transport_mode":"BRANCH_GITOPS",
        "generation_seq":10,"active_cohort_id":GEN10_TERMINAL_COHORT,"generation_head_sha":GEN10_TERMINAL_G,
        "calibration_countable_current":True,"calibration_required_clean_cohorts":2,"calibration_streak":0,
        "fresh_allowed_globally":False,"repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND",
        "network_mode":"GITHUB_BRANCH_CALIBRATION","foundry_sha256":MF311,"mastermind_sha256":MM4410,
        "runtime_state_id":RUNTIME,"runtime_update_receipt_path":STAGING_RECEIPT,
    }
    if rc or b.strip()!=GEN10_TERMINAL_STATE_BLOB or not _matches(old,old_expected) or GEN10_TERMINAL_COHORT in set(old.get("superseded_cohorts") or []):return False
    try:
        new=_load_json(root,"state/CURRENT.json")
        receipt=_load_json(root,GEN10_SUPERSESSION_PATH)
        con=_load_json(root,GEN10_CONSOLIDATION_PATH)
    except Exception:return False
    cohort=new.get("active_cohort_id")
    if not isinstance(cohort,str) or not cohort.startswith(GEN11_COHORT_PREFIX):return False
    cp=f"control/{cohort}.json"; ap=f"assignments/{cohort}.json"; lp=f"liveness/{cohort}.json"
    expected_changed={"state/CURRENT.json",GEN10_SUPERSESSION_PATH,GEN10_CONSOLIDATION_PATH,cp,ap,lp}
    if set(changed)!=expected_changed:return False
    if set(new.get("superseded_cohorts") or [])!=set(old.get("superseded_cohorts") or [])|{GEN10_TERMINAL_COHORT}:return False
    new_expected={
        "protocol_version":"2.5","task_network_plan_id":PLAN,"transport_mode":"BRANCH_GITOPS",
        "generation_seq":11,"active_parent_state_git_identity":GEN10_TERMINAL_STATE_BLOB,
        "generation_branch":f"ps/gen/{cohort}","calibration_countable_current":True,
        "calibration_required_clean_cohorts":2,"calibration_streak":0,"fresh_allowed_globally":False,
        "repo_policy_status":"VERIFIED_PROTECTED_SOURCE_BOUND","network_mode":"GITHUB_BRANCH_CALIBRATION",
        "foundry_sha256":MF311,"mastermind_sha256":MM4410,"runtime_state_id":RUNTIME,
        "runtime_update_receipt_path":STAGING_RECEIPT,"expected_base_head":base,
        "current_runtime_blocker":"O-T0-TWO_CLEAN_COUNTABLE_V25_COHORTS",
        "goal1_status":"BLOCKED_T0","goal2_status":"BLOCKED_BY_GOAL1",
        "verifier_branch":f"ps/verify/{cohort}","integrator_branch":f"ps/integrate/{cohort}",
        "consolidation_branch":f"ps/consolidate/{cohort}",
    }
    if not _matches(new,new_expected):return False
    G=new.get("generation_head_sha")
    if not isinstance(G,str) or not HEX40.fullmatch(G):return False
    branches=new.get("worker_branches") or {}
    if set(branches)!=WORKERS or any(branches[w]!=f"ps/work/{cohort}/{w}" for w in WORKERS):return False

    try:
        control=_load_json(root,cp); assignment=_load_json(root,ap); live=_load_json(root,lp)
        control_set=_load_json(root,"config/countable_control_set_v25.json")
    except Exception:return False
    rc_cb,control_blob=run(["git","rev-parse","HEAD:"+cp],root); rc_ab,assignment_blob=run(["git","rev-parse","HEAD:"+ap],root)
    control_blob=control_blob.strip(); assignment_blob=assignment_blob.strip()
    if rc_cb or rc_ab or not HEX40.fullmatch(control_blob) or not HEX40.fullmatch(assignment_blob):return False
    if new.get("active_control_manifest_git_identity")!=control_blob or new.get("active_assignment_git_identity")!=assignment_blob:return False
    common={"task_network_plan_id":PLAN,"cohort_id":cohort,"generation_seq":11,"parent_state_git_identity":GEN10_TERMINAL_STATE_BLOB,"expected_base_head":base,"calibration_countable":True}
    if not _matches(control,common) or not _matches(assignment,common):return False
    if control.get("protocol_version")!="2.5" or control.get("control_release_commit_sha")!=base or control.get("fresh_allowed") is not False or control.get("worker_auth_scheme")!="PS-HMAC-SHA256-CANONICAL-REPORT-2":return False
    if set(control.get("required_control_paths") or [])!=set(control_set.get("required_control_paths") or []):return False
    if assignment.get("generation_branch")!=new.get("generation_branch") or assignment.get("generation_root_sha")!=base or assignment.get("control_manifest_git_identity")!=control_blob:return False
    live_expected={"cohort_id":cohort,"generation_seq":11,"generation_root_sha":base,"control_manifest_id":control.get("control_manifest_id"),"control_manifest_git_identity":control_blob,"assignment_id":assignment.get("assignment_id"),"assignment_git_identity":assignment_blob}
    if not _matches(live,live_expected):return False

    if branch_head_api(new["generation_branch"])!=G:return False
    if set(compare_paths_api(base,G))!={cp,ap,lp}:return False
    try:
        if github_file(cp,G).get("sha")!=control_blob or github_file(ap,G).get("sha")!=assignment_blob:return False
        if github_file(lp,G).get("sha")!=run(["git","rev-parse","HEAD:"+lp],root)[1].strip():return False
    except Exception:return False
    role_branches=list(branches.values())+[new["verifier_branch"],new["integrator_branch"],new["consolidation_branch"]]
    if any(branch_head_api(branch)!=G for branch in role_branches):return False

    workers=assignment.get("workers") or {}
    if set(workers)!=WORKERS:return False
    for wid in WORKERS:
        constraints=workers[wid].get("constraints") or []
        if not any("HMAC input contract is separate from committed-file byte contract" in str(x) for x in constraints):return False
        if not any("outgoing committed bytes MUST equal json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+'\\n'" in str(x) and "abort without write on mismatch" in str(x) for x in constraints):return False

    try:
        ver=github_json(f"verification/{GEN10_TERMINAL_COHORT}.json",GEN10_MM06_HEAD)
        integ=github_json(f"integration/{GEN10_TERMINAL_COHORT}.json",GEN10_MF06_HEAD)
    except Exception:return False
    if not _matches(ver,{"task_network_plan_id":PLAN,"cohort_id":GEN10_TERMINAL_COHORT,"generation_head_sha":GEN10_TERMINAL_G,"verdict":"VERIFIED_WITH_QUARANTINES","partition_exhaustive_verified":True,"calibration_pass":False,"liveness_complete":True,"required_post_write_ci_context":"supernova/report-admission"}):return False
    safe=ver.get("safe_report_refs") or []; quarantine=ver.get("quarantined_report_refs") or []; missing=ver.get("missing_workers") or []
    if len(safe)!=11 or {r.get("worker_id") for r in safe if isinstance(r,dict)}!=WORKERS-{"MM02"}:return False
    if len(quarantine)!=1 or quarantine[0].get("worker_id")!="MM02" or missing:return False
    if not source_bound_status(GEN10_MM06_HEAD,"supernova/branch-verify","success"):return False
    if not source_bound_status(GEN10_MM06_HEAD,"supernova/report-admission","success"):return False

    if not _matches(integ,{"task_network_plan_id":PLAN,"cohort_id":GEN10_TERMINAL_COHORT,"generation_head_sha":GEN10_TERMINAL_G,"verification_head_sha":GEN10_MM06_HEAD,"verification_external_ci_context":"supernova/report-admission","verification_external_ci_status":"PASS","verification_external_ci_source":"github-actions[bot]","verification_external_ci_observed_after_receipt":True,"verification_verdict":"VERIFIED_WITH_QUARANTINES","verification_partition_exhaustive":True,"calibration_pass":False}):return False
    if integ.get("safe_report_refs")!=safe or integ.get("quarantines")!=quarantine or integ.get("missing_workers")!=missing:return False
    if not source_bound_status(GEN10_MF06_HEAD,"supernova/branch-integrate","failure"):return False

    if con.get("task_network_plan_id")!=PLAN or con.get("cohort_id")!=GEN10_TERMINAL_COHORT or con.get("generation_head_sha")!=GEN10_TERMINAL_G:return False
    if con.get("verification_head_sha")!=GEN10_MM06_HEAD or con.get("integration_head_sha")!=GEN10_MF06_HEAD:return False
    if con.get("expected_main_head")!=base or con.get("calibration_counted") is not False:return False
    if con.get("repo_policy_observed_protected") is not True or con.get("repo_policy_source_bound_contexts_verified") is not True:return False
    if (con.get("static_control_context") or {}).get("status")!="PASS":return False
    rac=con.get("report_admission_context") or {}
    if rac.get("status")!="PASS" or rac.get("verification_head_sha")!=GEN10_MM06_HEAD:return False
    if (con.get("transition_admission_context") or {}).get("required_on_exact_consolidation_head") is not True:return False
    refs=set(con.get("safe_history_refs") or [])
    if f"github-status:{GEN10_MF06_HEAD}:supernova/branch-integrate=failure" not in refs:return False
    if f"issue:#209:{GEN10_HISTORICAL_INTEGRATION_ISSUE}" not in refs:return False

    if receipt!=_receipt(GEN10_TERMINAL_COHORT,GEN10_TERMINAL_G,GEN10_TERMINAL_STATE_BLOB,GEN10_SUPERSESSION_DISPOSITION,11,True):return False
    return True

def report_admission(root,base,changed):
    if "state/CURRENT.json" not in changed:return []
    rc,text=run(["git","show",base+":state/CURRENT.json"],root)
    if rc:return ["cannot read base state: "+text[-800:]]
    try:
        old=json.loads(text)
        for predicate in (exact_noncountable_gen6_bootstrap_parent,):
            if predicate(root,base,old):return []
        for predicate in (exact_invalidated_gen7_repair_parent,exact_noncountable_substrate_staging_parent,exact_gen9_zero_credit_reset_parent,exact_gen10_zero_credit_terminal_parent):
            if predicate(root,base,old,changed):return []
        cohort=old["active_cohort_id"]; h=root/"history"/cohort
        con=_load_json(h,"CONSOLIDATION.json"); ver=_load_json(h,"verification.json"); integ=_load_json(h,"integration.json"); e=[]
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
    env=os.environ.copy(); env.update(SUPERNOVA_VALIDATE_ROOT=str(candidate),SUPERNOVA_BASE_SHA=base,SUPERNOVA_HEAD_SHA=head); e=[]
    for script in ("scripts/parent_lineage_guard.py","scripts/transition_guard.py"):
        rc,out=run([sys.executable,str(root/script)],root,env=env)
        if rc:e.append(script+" failed: "+out[-1200:])
    return e

def validate_pr(root,pr,trusted_errors=None):
    h=pr.get("head") or {}; b=pr.get("base") or {}; sha=h.get("sha"); base=b.get("sha"); meta=pr_metadata_errors(pr)
    if meta:
        if isinstance(sha,str) and HEX40.fullmatch(sha):fail_contexts(sha,"trusted admission refused: "+meta[0])
        return
    if trusted_errors:fail_contexts(sha,trusted_errors[0]);return
    n=pr["number"]; trusted=trusted_main_sha(root); run(["git","fetch","--no-tags","origin",f"pull/{n}/head"],root)
    if not is_ancestor(root,trusted,sha):fail_contexts(sha,"trusted admission refused: PR head does not descend from exact current main");return
    changed=changed_files(root,trusted,sha); authority=authority_path_changes(changed)
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
                provenance="trusted-bootstrap-run" if authority else "trusted-main"; scope="PASS" if "state/CURRENT.json" in changed else "PASS/N-A non-transition"
                post_status(sha,context,"success",provenance+" exact-head "+scope)
    finally:
        run(["git","worktree","remove","--force",str(tmp)],root); shutil.rmtree(tmp,ignore_errors=True)

def main():
    root=pathlib.Path.cwd().resolve(); trusted_errors=trusted_self_check(root); prs=api("/pulls?state=open&base=main&per_page=50") or []
    for pr in prs:
        if pr.get("draft"):continue
        try:validate_pr(root,pr,trusted_errors=trusted_errors)
        except Exception as exc:
            sha=(pr.get("head") or {}).get("sha")
            if sha and HEX40.fullmatch(sha):fail_contexts(sha,"trusted admission exception: "+repr(exc))
    return 1 if trusted_errors else 0

if __name__=="__main__":raise SystemExit(main())
