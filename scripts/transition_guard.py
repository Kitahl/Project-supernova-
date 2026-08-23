#!/usr/bin/env python3
from __future__ import annotations
import os,pathlib,subprocess,sys
TRUSTED_ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TRUSTED_ROOT/'scripts'))
import strict_json
from liveness_contract_guard import validate as validate_liveness
from scheduler_admission_guard import validate_countable_scheduler, validate_scheduler_admission
ROOT=pathlib.Path(os.environ.get("SUPERNOVA_VALIDATE_ROOT",str(TRUSTED_ROOT))).resolve()
CONTROL_PREFIXES=("state/","staging/","control/","assignments/","liveness/","scheduler/","scheduler_admission/","superseded/","benchmark/registry.json","plan/PLAN.json","PROTOCOL.md","WORKER_PROTOCOL.md","SESSION_STANDARD.md","config/","schemas/","scripts/","tests/",".github/workflows/")
def git(*args):
 p=subprocess.run(["git","-C",str(ROOT),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);return p.returncode,p.stdout.strip(),p.stderr.strip()
def load(p):return strict_json.loads((ROOT/p).read_text(encoding="utf-8"))
def changed(base,head):
 c,out,err=git("diff","--name-only",f"{base}...{head}")
 return [] if c else [x for x in out.splitlines() if x]
def validate(base=None,head=None):
 e=[];s=load("state/CURRENT.json");c=load(s["active_control_manifest_path"]);a=load(s["active_assignment_path"])
 staged=None;staged_path=s.get("active_staged_candidate_path")
 try:
  if staged_path and (ROOT/staged_path).is_file():staged=load(staged_path)
  elif (ROOT/"state/STAGED.json").is_file():staged=load("state/STAGED.json")
 except Exception:e.append("staged candidate pointer invalid")
 root11=bool(staged and staged.get("candidate_cohort_id")==s.get("active_cohort_id"))
 if root11:
  if not staged_path or staged_path!=f"staging/{s.get('active_cohort_id')}.json":e.append("root11 active state lacks canonical archived staged pointer")
  rc_archive,archive_blob,_=git("rev-parse",f"HEAD:{staged_path}") if staged_path else (1,"","")
  if rc_archive or archive_blob!=s.get("active_staged_candidate_git_identity"):e.append("root11 archived staged pointer blob mismatch")
  generation_root=staged.get("generation_root_sha")
  if c.get("expected_base_head")!=generation_root or a.get("expected_base_head")!=generation_root:e.append("root11 control/assignment generation-base mismatch")
  if s.get("expected_base_head")==generation_root:e.append("root11 promotion CAS must differ from generation root")
 else:
  if s.get("expected_base_head")!=c.get("expected_base_head") or s.get("expected_base_head")!=a.get("expected_base_head"):e.append("state/control/assignment expected_base_head mismatch")
 if s.get("active_parent_state_git_identity")!=c.get("parent_state_git_identity") or s.get("active_parent_state_git_identity")!=a.get("parent_state_git_identity"):e.append("parent binding mismatch")
 if s.get("generation_seq")!=c.get("generation_seq") or s.get("generation_seq")!=a.get("generation_seq"):e.append("generation binding mismatch")
 if s.get("active_cohort_id")!=c.get("cohort_id") or s.get("active_cohort_id")!=a.get("cohort_id"):e.append("cohort binding mismatch")
 if s.get("calibration_countable_current") is True:
  e.extend(validate_liveness(ROOT,s["active_cohort_id"]))
  if c.get("scheduler_admission_required") is True:
   e.extend(validate_countable_scheduler(ROOT,c,a,load(f"liveness/{s['active_cohort_id']}.json"),require_admission=True))
 if base and head:
  names=changed(base,head);mut=any(n=="state/CURRENT.json" for n in names)
  if mut:
   required={s["active_control_manifest_path"],s["active_assignment_path"],"state/CURRENT.json"}
   if s.get("calibration_countable_current") is True:
    cohort=s["active_cohort_id"]
    required.add(f"liveness/{cohort}.json")
    if c.get("scheduler_admission_required") is True:
     required.add(c["scheduler_manifest_path"])
     if root11:required.add(f"staging/{cohort}.json")
     else:required.add(f"scheduler_admission/{cohort}.json")
   missing=required-set(names)
   if missing:e.append("atomic transition missing paths: "+",".join(sorted(missing)))
   if s.get("expected_base_head")!=base:e.append(f"stale/wrong expected base head {s.get('expected_base_head')} != {base}")
   if root11:
    admission=f"scheduler_admission/{cohort}.json"
    if admission in names:e.append("root11 promotion must not introduce or modify scheduler admission")
    rc0,b0,_=git("rev-parse",f"{base}:{admission}");rc1,b1,_=git("rev-parse",f"{head}:{admission}")
    if rc0 or rc1 or b0!=b1:e.append("root11 scheduler admission must already exist in base unchanged")
    if "state/STAGED.json" in names:e.append("root11 promotion must preserve exact staged pointer blob")
    archive=f"staging/{cohort}.json"
    rc_pointer,pointer_blob,_=git("rev-parse",f"{base}:state/STAGED.json");rc_archive,archive_blob,_=git("rev-parse",f"{head}:{archive}")
    if rc_pointer or rc_archive or pointer_blob!=archive_blob:e.append("root11 promotion archive must exactly preserve staged pointer bytes")
 return e
def main():
 base=os.getenv("SUPERNOVA_BASE_SHA");head=os.getenv("SUPERNOVA_HEAD_SHA");e=validate(base,head)
 if e:
  print("SUPERNOVA TRANSITION ADMISSION FAILED");[print("-",x) for x in e];return 1
 print("SUPERNOVA TRANSITION ADMISSION PASS");return 0
if __name__=="__main__":sys.exit(main())
