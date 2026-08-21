#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, re, shutil, subprocess, tempfile, urllib.request

ROOT=pathlib.Path.cwd().resolve()
REPO=os.environ.get("GITHUB_REPOSITORY","Kitahl/Project-supernova-")
TOKEN=os.environ.get("GITHUB_TOKEN","")
API="https://api.github.com/repos/"+REPO
OWNER=REPO.split("/",1)[0]
PLAN="0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
HEX40=re.compile(r"^[0-9a-f]{40}$")
POLICY_PATH="config/gen9_reset_compat_seed_v25.json"
GEN9_COHORT="CAL-BR-009-v25-b53ab205"
GEN9_G="67bcfef1a5a1e65c9cc4adb1a2f308ec51c70c3f"
GEN9_STATE_BLOB="31071464144bde197aca0e3f13153be2d85208d7"

def api(path,method="GET",data=None):
    req=urllib.request.Request(API+path,data=(json.dumps(data).encode() if data is not None else None),method=method)
    req.add_header("Accept","application/vnd.github+json"); req.add_header("X-GitHub-Api-Version","2022-11-28")
    if TOKEN:req.add_header("Authorization","Bearer "+TOKEN)
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read(); return json.loads(raw) if raw else None

def run(cmd,cwd=ROOT):
    p=subprocess.run(cmd,cwd=str(cwd),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    return p.returncode,p.stdout

def load(root,path): return json.loads((root/path).read_text(encoding="utf-8"))

def git_blob(path):
    rc,out=run(["git","rev-parse","HEAD:"+path])
    return out.strip() if rc==0 else None

def post(sha,ctx,state,desc):
    target=f"https://github.com/{REPO}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}"
    api("/statuses/"+sha,"POST",{"state":state,"context":ctx,"description":desc[:140],"target_url":target})

def fail(sha,reason,policy):
    if isinstance(sha,str) and HEX40.fullmatch(sha):
        post(sha,policy["seed_context"],"failure","Gen9 reset compat seed refused: "+reason)
        for ctx in policy["required_status_contexts"]:
            post(sha,ctx,"failure","Gen9 reset compat seed refused: "+reason)
    print("GEN9 RESET COMPAT SEED REFUSED:",reason)
    return 1

def main():
    policy=load(ROOT,POLICY_PATH)
    try:number=int(os.environ.get("PR_NUMBER","0"))
    except ValueError:number=0
    if number<=0:return 1
    pr=api(f"/pulls/{number}"); head=pr.get("head") or {}; base=pr.get("base") or {}; sha=head.get("sha")
    if os.environ.get("CANDIDATE_DIAGNOSTICS_RESULT")!="success":
        return fail(sha,"read-only candidate diagnostics did not succeed",policy)
    diagnosed_head=os.environ.get("DIAGNOSED_HEAD_SHA"); diagnosed_base=os.environ.get("DIAGNOSED_BASE_SHA")
    if sha!=diagnosed_head or base.get("sha")!=diagnosed_base:
        return fail(sha,"diagnosed head/base no longer match PR",policy)
    rc,out=run(["git","rev-parse","HEAD"]); trusted=out.strip()
    if rc or trusted!=diagnosed_base:
        return fail(sha,"diagnosed base is not exact accepted main",policy)
    if base.get("ref")!="main" or (head.get("repo") or {}).get("full_name")!=REPO or (pr.get("user") or {}).get("login")!=OWNER:
        return fail(sha,"same-repo owner PR to main required",policy)
    if not str(head.get("ref","")).startswith(policy["head_prefix_required"]):
        return fail(sha,"head prefix not reset-compat eligible",policy)

    state=load(ROOT,"state/CURRENT.json")
    if git_blob("state/CURRENT.json")!=GEN9_STATE_BLOB or state.get("active_cohort_id")!=GEN9_COHORT or state.get("generation_head_sha")!=GEN9_G:
        return fail(sha,"canonical state is not exact zero-credit Gen9 target",policy)
    if state.get("calibration_streak")!=0 or state.get("fresh_allowed_globally") is not False:
        return fail(sha,"streak must be zero and fresh disabled",policy)
    root_now=load(ROOT,"config/root_tcb_epoch_v25.json")
    if root_now.get("epoch")!=policy["required_current_root_tcb_epoch"]:
        return fail(sha,"accepted root TCB epoch is not the required predecessor",policy)
    if (ROOT/policy["one_shot_marker_path"]).exists():
        return fail(sha,"compatibility epoch marker exists; seed permanently inert",policy)

    run(["git","fetch","--no-tags","origin",f"pull/{number}/head"])
    rc,_=run(["git","merge-base","--is-ancestor",trusted,sha])
    if rc:return fail(sha,"candidate does not descend from exact accepted main",policy)
    rc,out=run(["git","diff","--name-only",trusted+"..."+sha]); changed=[x for x in out.splitlines() if x]
    required=set(policy["required_root_candidate_paths"]); allowed=set(policy["allowed_root_candidate_paths"]); seed=set(policy["seed_paths"])
    if rc or set(changed)!=required:return fail(sha,"candidate diff is not exactly the authorized root repair set",policy)
    if seed.intersection(changed):return fail(sha,"seed self-modification forbidden",policy)
    if any(p not in allowed for p in changed):return fail(sha,"candidate path outside compatibility allowlist",policy)
    for prefix in policy["forbidden_candidate_prefixes"]:
        if any(p.startswith(prefix) for p in changed):return fail(sha,"forbidden state/runtime/scientific path changed",policy)

    tmp=pathlib.Path(tempfile.mkdtemp(prefix="supernova-gen9-reset-compat-"))
    try:
        rc,_=run(["git","worktree","add","--detach",str(tmp),sha])
        if rc:return fail(sha,"cannot create candidate data worktree",policy)
        if load(tmp,"state/CURRENT.json")!=state:return fail(sha,"state changed in root repair candidate",policy)
        marker=load(tmp,"config/gen9_reset_compat_epoch_v25.json")
        if marker.get("schema_version")!="PS-GEN9-RESET-COMPAT-EPOCH-2.5-1" or marker.get("epoch")!=1:
            return fail(sha,"invalid compatibility epoch marker",policy)
        if marker.get("seed_install_commit_sha")!=trusted:return fail(sha,"marker does not bind accepted seed install commit",policy)
        for key,path in (("seed_policy_blob","config/gen9_reset_compat_seed_v25.json"),("seed_reconciler_blob","scripts/reconcile_gen9_reset_compat_seed.py"),("seed_workflow_blob",".github/workflows/supernova-gen9-reset-compat-seed.yml")):
            if marker.get(key)!=git_blob(path):return fail(sha,"marker does not bind accepted "+key,policy)
        old_root_blob=git_blob("config/root_tcb_epoch_v25.json")
        new_root=load(tmp,"config/root_tcb_epoch_v25.json")
        if new_root.get("schema_version")!="PS-ROOT-TCB-EPOCH-2.5-4" or new_root.get("epoch")!=4:
            return fail(sha,"root TCB epoch 4 not installed",policy)
        if new_root.get("previous_epoch_blob")!=old_root_blob or new_root.get("gen9_reset_compat_seed_install_commit_sha")!=trusted:
            return fail(sha,"root TCB epoch 4 does not bind predecessor/seed install",policy)
        source=(tmp/"scripts/reconcile_open_prs.py").read_text(encoding="utf-8")
        bad='"control_manifest_path":cp,"assignment_path":ap'
        if bad in source:return fail(sha,"unsatisfiable liveness path predicate still present",policy)
        for token in ("control_manifest_git_identity","assignment_git_identity","HEAD:\"+cp","HEAD:\"+ap"):
            if token not in source:return fail(sha,"schema-bound liveness identity check missing: "+token,policy)
        adm=load(tmp,"config/admission_authority.json")
        helpers=set(adm.get("trusted_authority_helpers") or [])
        if not set(policy["seed_paths"][:3]+[policy["one_shot_marker_path"]]).issubset(helpers):
            return fail(sha,"new root TCB does not inventory compatibility seed/marker",policy)
        controls=set(load(tmp,"config/countable_control_set_v25.json").get("required_control_paths") or [])
        if not set(policy["seed_paths"]+[policy["one_shot_marker_path"],"tests/test_gen9_reset_compat_root.py"]).issubset(controls):
            return fail(sha,"countable control set does not freeze compatibility repair controls",policy)
    finally:
        run(["git","worktree","remove","--force",str(tmp)]); shutil.rmtree(tmp,ignore_errors=True)

    post(sha,policy["seed_context"],"success","accepted-main Gen9 reset compatibility seed PASS; exact head/base")
    for ctx in policy["required_status_contexts"]:
        post(sha,ctx,"success","one-shot Gen9 reset compatibility root repair exact-head PASS/N-A state")
    print("GEN9 RESET COMPAT SEED PASS",number,sha)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
