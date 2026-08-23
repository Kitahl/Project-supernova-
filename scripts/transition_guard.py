#!/usr/bin/env python3
from __future__ import annotations
import os,pathlib,subprocess,sys
TRUSTED_ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TRUSTED_ROOT/'scripts'))
import strict_json
from liveness_contract_guard import validate as validate_liveness
from scheduler_admission_guard import validate_countable_scheduler, validate_scheduler_admission
ROOT=pathlib.Path(os.environ.get("SUPERNOVA_VALIDATE_ROOT",str(TRUSTED_ROOT))).resolve()
CONTROL_PREFIXES=("state/","control/","assignments/","liveness/","scheduler/","scheduler_admission/","superseded/","benchmark/registry.json","plan/PLAN.json","PROTOCOL.md","WORKER_PROTOCOL.md","SESSION_STANDARD.md","config/","schemas/","scripts/","tests/",".github/workflows/")
def git(*args):
 p=subprocess.run(["git","-C",str(ROOT),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);return p.returncode,p.stdout.strip(),p.stderr.strip()
def load(p):return strict_json.loads((ROOT/p).read_text(encoding="utf-8"))
def changed(base,head):
 c,out,err=git("diff","--name-only",f"{base}...{head}")
 return [] if c else [x for x in out.splitlines() if x]
def validate(base=None,head=None):
 e=[];s=load("state/CURRENT.json");c=load(s["active_control_manifest_path"]);a=load(s["active_assignment_path"])
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
     required.add(f"scheduler_admission/{cohort}.json")
   missing=required-set(names)
   if missing:e.append("atomic transition missing paths: "+",".join(sorted(missing)))
   if s.get("expected_base_head")!=base:e.append(f"stale/wrong expected base head {s.get('expected_base_head')} != {base}")
 return e
def main():
 base=os.getenv("SUPERNOVA_BASE_SHA");head=os.getenv("SUPERNOVA_HEAD_SHA");e=validate(base,head)
 if e:
  print("SUPERNOVA TRANSITION ADMISSION FAILED");[print("-",x) for x in e];return 1
 print("SUPERNOVA TRANSITION ADMISSION PASS");return 0
if __name__=="__main__":sys.exit(main())
