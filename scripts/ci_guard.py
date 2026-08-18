#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
HEX40=re.compile(r"^[0-9a-f]{40}$")
def run_git(root,*args):
 p=subprocess.run(["git","-C",str(root),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);return p.returncode,p.stdout.strip(),p.stderr.strip()
def git_blob_sha(path):
 b=path.read_bytes();return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def load(path,errors):
 try:return json.loads(path.read_text())
 except Exception as e:errors.append(f"{path}: invalid JSON: {e}");return None
def verify_report_ref(root,cohort,ref,errors):
 w=ref.get("worker_id");expected=f"reports/{cohort}/{w}.json"
 if ref.get("path")!=expected:errors.append(f"{cohort}/{w}: path mismatch");return
 p=root/expected
 if not p.is_file():errors.append(f"{cohort}/{w}: missing safe report");return
 observed=git_blob_sha(p)
 if ref.get("blob_sha")!=observed:errors.append(f"{cohort}/{w}: blob mismatch")
 commit=ref.get("commit_sha")
 if not isinstance(commit,str) or not HEX40.fullmatch(commit):errors.append(f"{cohort}/{w}: non-null 40-hex creation commit required");return
 code,out,err=run_git(root,"ls-tree",commit,"--",expected)
 if code or not out:errors.append(f"{cohort}/{w}: report absent at creation commit")
 else:
  parts=out.split("\t",1)[0].split();tree_blob=parts[2] if len(parts)>=3 else None
  if tree_blob!=observed:errors.append(f"{cohort}/{w}: creation blob differs from current blob")
 code,out,err=run_git(root,"log","--format=%H","--",expected);hist=[x for x in out.splitlines() if x] if code==0 else []
 if len(hist)!=1 or hist[0]!=commit:errors.append(f"{cohort}/{w}: report not create-once immutable; history={hist}")
 code,out,err=run_git(root,"log","--diff-filter=A","--format=%H","--",expected);adds=[x for x in out.splitlines() if x] if code==0 else []
 if adds!=[commit]:errors.append(f"{cohort}/{w}: creation commit mismatch; git={adds}")
def validate(root):
 errors=[];state=load(root/"state/CURRENT.json",errors)
 if not isinstance(state,dict):return errors or ["missing state"]
 cohort=state.get("active_cohort_id");a=load(root/"assignments"/f"{cohort}.json",errors)
 expected=set((a or {}).get("workers",{}))
 vp=root/"verification"/f"{cohort}.json"
 if not vp.exists():return errors
 v=load(vp,errors)
 if not isinstance(v,dict):return errors
 safe=v.get("safe_report_refs",[]);quar=v.get("quarantined_report_refs",[]);missing=v.get("missing_workers",[]);auth=v.get("worker_auth_verification",{})
 safe_ids=[];quar_ids=[]
 for r in safe:
  if not isinstance(r,dict):errors.append("safe ref must be object");continue
  safe_ids.append(r.get("worker_id"));verify_report_ref(root,cohort,r,errors)
 for r in quar:
  if not isinstance(r,dict):errors.append("quarantine ref must be object");continue
  required={"worker_id","expected_path","observed_blob_sha","observed_commit_sha","reason_code","summary","evidence_refs","disposition"}
  if set(r)!=required:errors.append(f"quarantine closed schema mismatch for {r.get('worker_id')}")
  quar_ids.append(r.get("worker_id"))
 miss=list(missing) if isinstance(missing,list) else []
 for label,ids in [("safe",safe_ids),("quarantine",quar_ids),("missing",miss)]:
  if len(ids)!=len(set(ids)):errors.append(f"duplicate worker in {label}")
 ss,qs,ms=set(safe_ids),set(quar_ids),set(miss)
 if ss&qs or ss&ms or qs&ms:errors.append("worker partitions overlap")
 if ss|qs|ms!=expected:errors.append(f"worker partitions not exhaustive expected={sorted(expected)} observed={sorted(ss|qs|ms)}")
 if set(auth)!=expected:errors.append("auth map not exhaustive")
 if v.get("calibration_pass") is True or v.get("verdict")=="VERIFIED_COMPLETE":
  if ss!=expected or qs or ms:errors.append("complete/pass requires every worker safe")
  if any(auth.get(w)!="PASS" for w in expected):errors.append("complete/pass requires PASS auth for every worker")
 return errors
def main():
 e=validate(ROOT)
 if e:
  print("SUPERNOVA REPORT ADMISSION FAILED");[print("-",x) for x in e];return 1
 print("SUPERNOVA REPORT ADMISSION PASS");return 0
if __name__=="__main__":sys.exit(main())
