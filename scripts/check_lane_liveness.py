#!/usr/bin/env python3
"""Out-of-band receipt-deadline monitor for Revision-4 cohorts.

The monitor consumes an explicit frozen cohort liveness contract. A receipt is on
time only when it is directly observed before the deadline, has a separately
trusted immutable creation-time witness at/before the deadline, or has an
expected-source exact-head structural status whose GitHub server timestamp proves
the report existed by the deadline. Git author/committer timestamps are never
treated as authoritative receipt-creation time. Missing, late, or timing-unknown
GitHub receipts fail closed after the frozen deadline. Future countable contracts
must also reserve the root9 minimum publication slack before they are eligible.
"""
from __future__ import annotations
import argparse, datetime as dt, os, pathlib, urllib.error, urllib.parse, urllib.request
from typing import Any, Callable
try:
    from scripts import strict_json
except ImportError:
    import strict_json
UTC=dt.timezone.utc
EXPECTED_STATUS_CONTEXT='supernova/branch-worker'
EXPECTED_STATUS_CREATOR='github-actions[bot]'
minimum_worker_liveness_window_minutes=45

def parse_time(s: str) -> dt.datetime:
    x=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
    if x.tzinfo is None: raise ValueError('times must be timezone-aware')
    return x.astimezone(UTC)

def _observed(meta: Any) -> bool:
    if isinstance(meta,bool): return meta
    return isinstance(meta,dict) and meta.get('exists') is True

def _time(meta: Any,key: str) -> dt.datetime | None:
    if not isinstance(meta,dict): return None
    raw=meta.get(key)
    if not isinstance(raw,str) or not raw: return None
    try: return parse_time(raw)
    except Exception: return None

def _branch_worker_status_witness(statuses: Any) -> dict[str,Any] | None:
    if not isinstance(statuses,list): return None
    for status in statuses:
        if not isinstance(status,dict) or status.get('context')!=EXPECTED_STATUS_CONTEXT:
            continue
        creator=(status.get('creator') or {}) if isinstance(status.get('creator'),dict) else {}
        if status.get('state')!='success' or creator.get('login')!=EXPECTED_STATUS_CREATOR:
            return None
        raw=status.get('created_at')
        if not isinstance(raw,str): return None
        try: parse_time(raw)
        except Exception: return None
        return {'trusted_observed_at_utc':raw,'witness_status_id':status.get('id'),'witness_creator_login':creator.get('login'),'witness_context':EXPECTED_STATUS_CONTEXT}
    return None

def _slack_minutes(lane: dict) -> float:
    return (parse_time(lane['deadline_utc'])-parse_time(lane['expected_window_start_utc'])).total_seconds()/60.0

def evaluate(contract: dict, now: dt.datetime, observe_fn: Callable[[str,str], Any]) -> dict:
    if now.tzinfo is None: raise ValueError('now must be timezone-aware')
    now=now.astimezone(UTC); observations=[]; blocking=[]
    for lane in contract['lanes']:
        deadline=parse_time(lane['deadline_utc']); meta=observe_fn(lane['branch'],lane['path']); exists=_observed(meta)
        created=_time(meta,'trusted_created_at_utc'); witnessed=_time(meta,'trusted_observed_at_utc'); notes=[]
        if _slack_minutes(lane) < minimum_worker_liveness_window_minutes:
            receipt_status='RUN_TIMING_UNKNOWN' if exists else 'NO_RECEIPT'; late=max(1,int((now-deadline).total_seconds())) if now>deadline else 0; blocking.append(lane['lane_id'])
            notes.append(f'Frozen countable liveness publication window is below {minimum_worker_liveness_window_minutes} minutes; fail closed.')
        elif exists:
            if created is not None and created>deadline:
                receipt_status='RUN_LATE'; late=max(1,int((created-deadline).total_seconds())); blocking.append(lane['lane_id']); notes.append('Trusted receipt creation timestamp is after frozen deadline.')
            elif created is not None:
                receipt_status='RUN_OBSERVED'; late=0; notes.append('Trusted receipt creation timestamp is at/before frozen deadline.')
            elif now<=deadline:
                receipt_status='RUN_OBSERVED'; late=0; notes.append('Receipt was directly observed before frozen deadline.')
            elif witnessed is not None and witnessed<=deadline:
                receipt_status='RUN_OBSERVED'; late=0; notes.append('Expected-source exact-head branch-worker status proves receipt existed by frozen deadline.')
            else:
                receipt_status='RUN_TIMING_UNKNOWN'; late=max(1,int((now-deadline).total_seconds())); blocking.append(lane['lane_id'])
                notes.append('First trusted exact-head structural witness is after frozen deadline; creation time is unproven.' if witnessed is not None else 'Receipt exists after deadline without a trusted pre-deadline server-time witness; fail closed.')
        elif now>deadline:
            receipt_status='NO_RECEIPT'; late=int((now-deadline).total_seconds()); blocking.append(lane['lane_id']); notes.append('No receipt after frozen deadline.')
        else:
            receipt_status='NO_RECEIPT'; late=0; notes.append('No receipt yet; frozen deadline has not passed.')
        if isinstance(meta,dict):
            for key,label in [('head_sha','head'),('blob_sha','blob'),('trusted_created_at_utc','trusted_created_at'),('trusted_observed_at_utc','trusted_observed_at'),('witness_creator_login','witness_creator')]:
                if meta.get(key): notes.append(label+'='+str(meta[key]))
        observations.append({'lane_id':lane['lane_id'],'task_id':None,'associated_chat_ref':None,'expected_window_start':lane['expected_window_start_utc'],'expected_window_end':lane['deadline_utc'],'observation_time':now.isoformat().replace('+00:00','Z'),'receipt_status':receipt_status,'task_state':'TASK_STATE_UNKNOWN','observation_source':'GITHUB_RECEIPT_MONITOR','receipt_ref':f"{lane['branch']}:{lane['path']}" if exists else None,'lateness_seconds':late,'notes':' '.join(notes)})
    blocking=list(dict.fromkeys(blocking))
    return {'schema_version':'PS-LIVENESS-MONITOR-4','cohort_id':contract['cohort_id'],'generation_root_sha':contract['generation_root_sha'],'minimum_worker_liveness_window_minutes':minimum_worker_liveness_window_minutes,'observation_time':now.isoformat().replace('+00:00','Z'),'observations':observations,'blocking_lanes':blocking,'transition_liveness_pass':not blocking}

def github_observer(repo: str, token: str):
    api='https://api.github.com/repos/'+repo
    def req(url: str):
        r=urllib.request.Request(url); r.add_header('Accept','application/vnd.github+json'); r.add_header('X-GitHub-Api-Version','2022-11-28')
        if token: r.add_header('Authorization','Bearer '+token)
        with urllib.request.urlopen(r,timeout=20) as z: return strict_json.loads(z.read().decode('utf-8'))
    def observe(branch,path):
        url=api+'/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(branch,safe='')
        try: obj=req(url)
        except urllib.error.HTTPError as e:
            if e.code==404: return {'exists':False}
            raise
        if not isinstance(obj,dict) or obj.get('type')!='file': return {'exists':False}
        meta={'exists':True,'blob_sha':obj.get('sha')}
        try:
            b=req(api+'/branches/'+urllib.parse.quote(branch,safe='')); head=(b.get('commit') or {}).get('sha'); meta['head_sha']=head
            if isinstance(head,str):
                statuses=req(api+'/commits/'+head+'/statuses?per_page=100'); witness=_branch_worker_status_witness(statuses)
                if witness: meta.update(witness)
        except Exception as exc: meta['timing_error']=type(exc).__name__
        return meta
    return observe

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--contract',required=True); ap.add_argument('--out',required=True); ap.add_argument('--now'); ap.add_argument('--repo',default=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-')); ns=ap.parse_args()
    contract=strict_json.loads(pathlib.Path(ns.contract).read_text(encoding='utf-8')); now=parse_time(ns.now) if ns.now else dt.datetime.now(UTC)
    result=evaluate(contract,now,github_observer(ns.repo,os.environ.get('GITHUB_TOKEN','')))
    pathlib.Path(ns.out).write_text(strict_json.pretty_dumps(result),encoding='utf-8'); print(strict_json.canonical_dumps(result))
    return 0 if result['transition_liveness_pass'] else 3
if __name__=='__main__': raise SystemExit(main())
