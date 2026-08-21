#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,pathlib,re,subprocess,sys
from jsonschema import Draft202012Validator

TRUSTED_ROOT=pathlib.Path(__file__).resolve().parents[1]
ROOT=pathlib.Path(os.environ.get("SUPERNOVA_VALIDATE_ROOT",str(TRUSTED_ROOT))).resolve()
HEX40=re.compile(r"^[0-9a-f]{40}$")
RECEIPT_PATH=re.compile(r"^runtime/updates/[A-Za-z0-9._-]+\.json$")
RUNTIME=("base_runtime_state_id","runtime_state_id","foundry_sha256","mastermind_sha256","actual_runtime_plan_id","canonical_bus_repo","private_vault_repo")
REPLAY_SUBSTRATE_CLASS="REPLAY_CALIBRATION_SUBSTRATE_BINDING"

def git(root,*args):
 p=subprocess.run(["git","-C",str(root),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);return p.returncode,p.stdout.strip(),p.stderr.strip()

def load(p,e):
 try:return json.loads(p.read_text(encoding="utf-8"))
 except Exception as x:e.append(f"{p}: {x}");return None

def git_blob_sha(path):
 b=path.read_bytes();return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()

def blob_json(root,sha,e):
 c,t,_=git(root,"cat-file","-t",sha)
 if c or t!="blob":e.append(f"parent {sha} is not a resolvable blob");return None
 c,p,_=git(root,"cat-file","-p",sha)
 try:return json.loads(p)
 except Exception as x:e.append(f"parent {sha} not JSON: {x}");return None

def historical_state(root,sha):
 c,out,_=git(root,"log","--all","--format=%H","--","state/CURRENT.json")
 if c:return False
 for commit in out.splitlines():
  c,t,_=git(root,"ls-tree",commit,"--","state/CURRENT.json")
  if not c and t:
   parts=t.split("\t",1)[0].split()
   if len(parts)>=3 and parts[2]==sha:return True
 return False

def pass_rows(rows,label,e):
 if not isinstance(rows,list) or not rows:
  e.append(f"runtime update receipt {label} must be a nonempty array")
  return
 for i,row in enumerate(rows):
  if not isinstance(row,dict) or row.get("status")!="PASS":
   e.append(f"runtime update receipt {label}[{i}] is not PASS")

def runtime_receipt_errors(root,parent,current,drift):
 e=[]
 receipt=current.get("runtime_update_receipt_path")
 if not isinstance(receipt,str) or not RECEIPT_PATH.fullmatch(receipt):
  return ["runtime-bound identity drift requires runtime/updates/<id>.json receipt: "+",".join(drift)]
 root_resolved=root.resolve();path=(root/receipt).resolve()
 try:path.relative_to(root_resolved)
 except ValueError:return ["runtime update receipt path escapes repository root"]
 if not path.is_file():return ["runtime-bound identity drift without runtime update receipt: "+",".join(drift)]
 obj=load(path,e)
 if not isinstance(obj,dict):return e or ["runtime update receipt is not an object"]
 try:
  schema=json.loads((root/"schemas/runtime_update.schema.json").read_text(encoding="utf-8"))
  Draft202012Validator.check_schema(schema)
  for x in Draft202012Validator(schema).iter_errors(obj):e.append("runtime update receipt schema: "+x.message)
 except Exception as x:e.append("runtime update receipt schema execution failed: "+repr(x))
 if obj.get("status")!="VALIDATED":e.append("runtime update receipt status is not VALIDATED")
 if obj.get("task_network_plan_id")!=current.get("task_network_plan_id"):e.append("runtime update receipt plan mismatch")
 if obj.get("runtime_before")!=parent.get("runtime_state_id"):e.append("runtime update receipt runtime_before mismatch")
 if obj.get("runtime_after")!=current.get("runtime_state_id"):e.append("runtime update receipt runtime_after mismatch")
 diag=obj.get("before_after_diagnostics") or {}
 before=diag.get("runtime_bound_before") if isinstance(diag,dict) else None
 after=diag.get("runtime_bound_after") if isinstance(diag,dict) else None
 if not isinstance(before,dict):e.append("runtime update receipt missing runtime_bound_before")
 else:
  for k in RUNTIME:
   if before.get(k)!=parent.get(k):e.append(f"runtime update receipt before binding mismatch: {k}")
 if not isinstance(after,dict):e.append("runtime update receipt missing runtime_bound_after")
 else:
  for k in RUNTIME:
   if after.get(k)!=current.get(k):e.append(f"runtime update receipt after binding mismatch: {k}")
 pass_rows(obj.get("validator_results"),"validator_results",e)
 pass_rows(obj.get("preservation_regression_checks"),"preservation_regression_checks",e)

 substrate_drift=bool({"foundry_sha256","mastermind_sha256"}.intersection(drift))
 replay_only=substrate_drift and parent.get("runtime_state_id")==current.get("runtime_state_id")
 if replay_only:
  if diag.get("update_class")!=REPLAY_SUBSTRATE_CLASS:e.append("replay substrate drift missing replay-calibration update_class")
  if obj.get("fresh_prospective_evidence_refs")!=[]:e.append("replay substrate binding consumed fresh prospective evidence")
  artifacts=obj.get("artifact_hashes") or {}
  if artifacts.get("foundry_sha256")!=current.get("foundry_sha256"):e.append("runtime update receipt Foundry hash mismatch")
  if artifacts.get("mastermind_sha256")!=current.get("mastermind_sha256"):e.append("runtime update receipt Mastermind hash mismatch")
  if artifacts.get("substrate_epoch_path")!="config/substrate_epoch_v25.json":e.append("runtime update receipt substrate epoch path mismatch")
  substrate_path=root/"config/substrate_epoch_v25.json"
  if not substrate_path.is_file():e.append("runtime update receipt frozen substrate epoch missing")
  else:
   expected_blob=git_blob_sha(substrate_path)
   if artifacts.get("substrate_epoch_git_identity")!=expected_blob:e.append("runtime update receipt substrate epoch blob mismatch")
   substrate=load(substrate_path,e)
   if isinstance(substrate,dict):
    mf=(substrate.get("math_foundry") or {}).get("source_archive_sha256")
    mm=(substrate.get("mastermind") or {}).get("sha256")
    if current.get("foundry_sha256")!=mf:e.append("current Foundry hash not frozen substrate epoch")
    if current.get("mastermind_sha256")!=mm:e.append("current Mastermind hash not frozen substrate epoch")
  independent=obj.get("independent_verification") or {}
  if independent.get("status")!="PASS":e.append("runtime update receipt independent verification not PASS")
  if independent.get("qualification_class")!="SOFTWARE_REPLAY_CALIBRATION_ONLY":e.append("runtime update receipt qualification class mismatch")
  if independent.get("scientific_status_changed") is not False:e.append("runtime update receipt incorrectly changes scientific status")
  if independent.get("fresh_evidence_consumed") is not False:e.append("runtime update receipt incorrectly consumes fresh evidence")
 return e

def validate(root):
 e=[];s=load(root/"state/CURRENT.json",e)
 if not isinstance(s,dict):return e or ["missing state"]
 g=s.get("generation_seq");parent_sha=s.get("active_parent_state_git_identity")
 if not isinstance(g,int) or g<2:return e
 if not isinstance(parent_sha,str) or not HEX40.fullmatch(parent_sha):return e+["parent must be 40-hex blob"]
 p=blob_json(root,parent_sha,e)
 if not p:return e
 if not historical_state(root,parent_sha):e.append("parent blob was never historical state/CURRENT.json")
 if p.get("generation_seq")!=g-1:e.append("parent generation is not current-1")
 old=set(p.get("superseded_cohorts",[]));new=set(s.get("superseded_cohorts",[]))
 if not old<=new:e.append("supersession history regressed")
 drift=[k for k in RUNTIME if p.get(k)!=s.get(k)]
 if drift:e.extend(runtime_receipt_errors(root,p,s,drift))
 for label,pathkey in [("control","active_control_manifest_path"),("assignment","active_assignment_path")]:
  path=s.get(pathkey);o=load(root/path,e) if isinstance(path,str) and (root/path).exists() else None
  if not isinstance(o,dict):e.append(f"active {label} missing");continue
  if o.get("parent_state_git_identity")!=parent_sha:e.append(f"{label} parent mismatch")
  if o.get("generation_seq")!=g:e.append(f"{label} generation mismatch")
  if o.get("cohort_id")!=s.get("active_cohort_id"):e.append(f"{label} cohort mismatch")
 return e

def main():
 e=validate(ROOT)
 if e:
  print("SUPERNOVA PARENT LINEAGE FAILED");[print("-",x) for x in e];return 1
 print("SUPERNOVA PARENT LINEAGE PASS");return 0
if __name__=="__main__":sys.exit(main())
