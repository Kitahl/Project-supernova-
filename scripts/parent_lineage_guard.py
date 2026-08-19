#!/usr/bin/env python3
from __future__ import annotations
import json,os,pathlib,re,subprocess,sys
TRUSTED_ROOT=pathlib.Path(__file__).resolve().parents[1]
ROOT=pathlib.Path(os.environ.get("SUPERNOVA_VALIDATE_ROOT",str(TRUSTED_ROOT))).resolve()
HEX40=re.compile(r"^[0-9a-f]{40}$")
RUNTIME=("base_runtime_state_id","runtime_state_id","foundry_sha256","mastermind_sha256","actual_runtime_plan_id","canonical_bus_repo","private_vault_repo")
def git(root,*args):
 p=subprocess.run(["git","-C",str(root),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);return p.returncode,p.stdout.strip(),p.stderr.strip()
def load(p,e):
 try:return json.loads(p.read_text())
 except Exception as x:e.append(f"{p}: {x}");return None
def blob_json(root,sha,e):
 c,t,s=git(root,"cat-file","-t",sha)
 if c or t!="blob":e.append(f"parent {sha} is not a resolvable blob");return None
 c,p,s=git(root,"cat-file","-p",sha)
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
 receipt=s.get("runtime_update_receipt_path")
 if drift and not (isinstance(receipt,str) and receipt and (root/receipt).is_file()):e.append("runtime-bound identity drift without runtime update receipt: "+",".join(drift))
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
