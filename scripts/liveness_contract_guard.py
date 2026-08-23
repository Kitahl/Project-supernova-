#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, pathlib
from datetime import datetime
from jsonschema import Draft202012Validator, FormatChecker
try:
    from scripts import strict_json
except ImportError:
    import strict_json

PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
WORKERS={'MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01'}

def load(p): return strict_json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def blob(p):
    b=pathlib.Path(p).read_bytes()
    return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def dt(x): return datetime.fromisoformat(x.replace('Z','+00:00'))

def validate(root:pathlib.Path, cohort:str):
    e=[]
    cp=root/f'control/{cohort}.json'; ap=root/f'assignments/{cohort}.json'; lp=root/f'liveness/{cohort}.json'
    for p in (cp,ap,lp):
        if not p.is_file(): e.append(f'missing {p.relative_to(root)}')
    if e:return e
    c,a,l=load(cp),load(ap),load(lp)
    schema=load(root/'schemas/cohort_liveness_contract.schema.json')
    Draft202012Validator.check_schema(schema)
    for x in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(l): e.append('liveness schema: '+x.message)
    if l.get('protocol_version')!='2.5' or l.get('task_network_plan_id')!=PLAN:e.append('liveness protocol/plan mismatch')
    if l.get('cohort_id')!=cohort or c.get('cohort_id')!=cohort or a.get('cohort_id')!=cohort:e.append('liveness cohort mismatch')
    if l.get('generation_seq')!=c.get('generation_seq') or l.get('generation_seq')!=a.get('generation_seq'):e.append('liveness generation mismatch')
    if l.get('generation_root_sha')!=c.get('control_release_commit_sha') or l.get('generation_root_sha')!=a.get('generation_root_sha'):e.append('liveness generation-root mismatch')
    # Root11 requires a single nonce across C -> A -> L.  The property remains
    # optional in the closed schemas so immutable Gen12/root9 evidence still validates.
    if any(x.get('candidate_nonce') is not None for x in (c,a,l)):
        nonce=c.get('candidate_nonce')
        if not isinstance(nonce,str) or len(nonce)!=64 or a.get('candidate_nonce')!=nonce or l.get('candidate_nonce')!=nonce:
            e.append('root11 candidate nonce chain mismatch')
        if c.get('generation_root_sha')!=c.get('control_release_commit_sha'):
            e.append('root11 control generation root mismatch')
    if l.get('control_manifest_id')!=c.get('control_manifest_id') or l.get('control_manifest_git_identity')!=blob(cp):e.append('liveness control binding mismatch')
    if l.get('assignment_id')!=a.get('assignment_id') or l.get('assignment_git_identity')!=blob(ap):e.append('liveness assignment binding mismatch')
    cfg=load(root/'branch/CONFIG.json')
    minimum_worker_liveness_window_minutes=cfg.get('minimum_worker_liveness_window_minutes')
    if not isinstance(minimum_worker_liveness_window_minutes,int) or minimum_worker_liveness_window_minutes < 45:
        e.append('minimum_worker_liveness_window_minutes must be an integer >= 45')
        minimum_worker_liveness_window_minutes=45
    lanes=l.get('lanes',[]); ids=[x.get('lane_id') for x in lanes if isinstance(x,dict)]
    if len(ids)!=12 or set(ids)!=WORKERS or len(ids)!=len(set(ids)):e.append('liveness lane set is not exact unique 12-worker set')
    aw=a.get('workers',{})
    for row in lanes:
        if not isinstance(row,dict):continue
        w=row.get('lane_id'); expected=aw.get(w,{})
        if row.get('branch')!=expected.get('worker_branch'):e.append(f'{w} liveness branch mismatch')
        if row.get('path')!=f'reports/{cohort}/{w}.json':e.append(f'{w} liveness report path mismatch')
        try:
            start=dt(row.get('expected_window_start_utc','')); deadline=dt(row.get('deadline_utc',''))
            if start>=deadline:e.append(f'{w} liveness window is not strictly increasing')
            else:
                minutes=(deadline-start).total_seconds()/60.0
                if minutes < minimum_worker_liveness_window_minutes:
                    e.append(f'{w} liveness publication window {minutes:.1f}m < {minimum_worker_liveness_window_minutes}m')
        except Exception:e.append(f'{w} liveness time parse failed')
    return e

def main():
    q=argparse.ArgumentParser();q.add_argument('--root',default='.');q.add_argument('--cohort',required=True);z=q.parse_args()
    e=validate(pathlib.Path(z.root).resolve(),z.cohort)
    if e:
        print('COHORT LIVENESS CONTRACT FAILED');[print('-',x) for x in e];return 1
    print('COHORT LIVENESS CONTRACT PASS');return 0
if __name__=='__main__':raise SystemExit(main())
